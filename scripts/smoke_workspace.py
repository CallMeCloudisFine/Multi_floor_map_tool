"""Actual desktop regression: native keys, independent edits, noise and saved PCDs."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gui.runtime import prepare_runtime
prepare_runtime()
from PySide6.QtCore import QTimer, Qt, QPoint, QRect
from PySide6.QtGui import QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
import numpy as np
import open3d as o3d
import yaml
from gui.main_window import MainWindow
from scripts.create_demo import generate


class XKeyEvent(ctypes.Structure):
    _fields_=[('type',ctypes.c_int),('serial',ctypes.c_ulong),('send_event',ctypes.c_int),
              ('display',ctypes.c_void_p),('window',ctypes.c_ulong),('root',ctypes.c_ulong),
              ('subwindow',ctypes.c_ulong),('time',ctypes.c_ulong),('x',ctypes.c_int),('y',ctypes.c_int),
              ('x_root',ctypes.c_int),('y_root',ctypes.c_int),('state',ctypes.c_uint),
              ('keycode',ctypes.c_uint),('same_screen',ctypes.c_int)]


class XEvent(ctypes.Union):
    _fields_=[('key',XKeyEvent),('pad',ctypes.c_long*24)]


def send_native_key(number):
    lib=ctypes.CDLL('libX11.so.6')
    lib.XOpenDisplay.argtypes=[ctypes.c_char_p]
    lib.XOpenDisplay.restype=ctypes.c_void_p
    lib.XDefaultRootWindow.argtypes=[ctypes.c_void_p]
    lib.XDefaultRootWindow.restype=ctypes.c_ulong
    lib.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    lib.XKeysymToKeycode.restype=ctypes.c_uint
    lib.XSendEvent.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_long,ctypes.POINTER(XEvent)]
    lib.XFlush.argtypes=[ctypes.c_void_p]
    lib.XCloseDisplay.argtypes=[ctypes.c_void_p]
    display=lib.XOpenDisplay(None)
    assert display
    event=XEvent()
    event.key.display=display
    event.key.window=window.viewer.native_id
    event.key.root=lib.XDefaultRootWindow(display)
    event.key.same_screen=1
    event.key.keycode=lib.XKeysymToKeycode(display,ord(str(number)))
    for kind,mask in [(2,1),(3,2)]:
        event.key.type=kind
        assert lib.XSendEvent(display,event.key.window,False,mask,ctypes.byref(event))
    lib.XFlush(display)
    lib.XCloseDisplay(display)


def assert_embedded():
    xid=window.viewer.native_id
    ancestors=[]
    while xid!=int(window.winId()) and xid not in ancestors:
        ancestors.append(xid)
        info=subprocess.check_output(['xwininfo','-id',hex(xid),'-tree'],text=True)
        xid=int(re.search(r'Parent window id: (0x[0-9a-fA-F]+)',info).group(1),16)
    assert xid==int(window.winId()), 'Renderer detached from main window'


app=QApplication([])
window=MainWindow()
window.show()
errors=[]
window._failed=errors.append
folder=tempfile.TemporaryDirectory()
root=Path(folder.name)
source=root/'complete.pcd'
generate(source)
digest=hashlib.sha256(source.read_bytes()).digest()
window.controller.load_path(str(source))
phase=0
started=time.monotonic()
first=second=None
count1=0


def check():
    global phase,first,second,count1
    try:
        assert time.monotonic()-started<90, 'GUI timeout'
        assert not errors, errors
        if window.task is not None:
            return
        ctl,panel,session=window.controller,window.panel,window.session
        if phase==0:
            assert_embedded()
            assert session.source.count==5043
            window.color_buttons['x'].click()
            send_native_key(1)
        elif 1<=phase<=4:
            expected={1:[-1,0,0],2:[1,0,0],3:[0,0,1],4:[0,0,-1]}[phase]
            camera=json.loads(window.viewer.vis.get_view_status())['trajectory'][0]
            np.testing.assert_allclose(camera['front'],expected)
            assert camera['field_of_view']==5
            assert window.viewer.color_mode=='x', 'Number key unexpectedly changed color'
            if phase<4:
                send_native_key(phase+1)
            else:
                window.color_buttons['default'].click()
                window.view_buttons['iso'].click()
                panel.crop_enabled.setChecked(True)
                panel.bounds[2][1].setValue(2.5)
                panel.preview_button.click()
        elif phase==5:
            assert len(session.current.preview.points)==1681
            window.add_floor_button.click()
            first=session.selected
            assert session.current.draft.voxel_size==0 and session.current.draft.crop_min is None
            assert len(window.viewer._cloud.points)==5043, 'floor inherits processed Full Map'
            panel.map_name.setFocus()
            panel.map_name.selectAll()
            QTest.keyClicks(panel.map_name,'floor1234')
            assert panel.map_name.text()=='floor1234'
            assert window.viewer.vis.get_view_control().get_field_of_view()==60, 'Typing numbers changed camera'
            # Both physical slider handles, crossing protection and keyboard precision.
            slider=panel.height_slider
            slider.setFocus()
            x=lambda value: round(slider.x_for_value(value))
            QTest.mousePress(slider,Qt.MouseButton.LeftButton,pos=QPoint(x(slider.upper),19))
            QTest.mouseMove(slider,QPoint(x(6.0),19),20)
            QTest.mouseRelease(slider,Qt.MouseButton.LeftButton,pos=QPoint(x(6.0),19))
            assert abs(panel.ceiling_z.value()-6.0)<.1
            QTest.mousePress(slider,Qt.MouseButton.LeftButton,pos=QPoint(x(slider.lower),19))
            QTest.mouseMove(slider,QPoint(x(7.5),19),20)
            QTest.mouseRelease(slider,Qt.MouseButton.LeftButton,pos=QPoint(x(7.5),19))
            assert panel.ground_z.value()<panel.ceiling_z.value(), 'Handles crossed'
            panel.ground_z.setValue(0.0)
            panel.ceiling_z.setValue(2.7)
            slider.active_handle='lower'
            QTest.keyClick(slider,Qt.Key.Key_Right)
            assert abs(panel.ground_z.value()-.01)<1e-6
            assert not panel.height_confirmed.isChecked()
            panel.ground_z.setValue(3)
            assert not slider.isEnabled() and not panel.preview_button.isEnabled()
            panel.ground_z.setValue(0)
            assert slider.isEnabled()
            panel.crop_enabled.setChecked(True)
            panel.bounds[2][1].setValue(2.5)
            panel.voxel_enabled.setChecked(True)
            panel.voxel.setValue(.5)
            panel.statistical_enabled.setChecked(True)
            panel.nb_neighbors.setValue(8)
            panel.std_ratio.setValue(2)
            panel.radius_enabled.setChecked(True)
            panel.radius.setValue(.8)
            panel.min_neighbors.setValue(2)
            panel.preview_button.click()
        elif phase==6:
            count1=len(session.current.preview.points)
            assert 0<count1<1681
            assert not panel.save_button.isEnabled(), 'Unconfirmed height was exportable'
            before=session.current.preview
            panel.ground_z.setValue(0.0)
            panel.ceiling_z.setValue(2.7)
            panel.height_confirmed.setChecked(True)
            assert session.current.preview is before, 'Height metadata forced point recomputation'
            assert panel.save_button.isEnabled()
            ctl.save_path(root/'floor1.pcd')
        elif phase==7:
            assert not session.current.dirty
            assert (root/'floor1.pcd').is_file() and (root/'floor1.rules.yaml').is_file()
            saved1=o3d.io.read_point_cloud(str(root/'floor1.pcd'))
            assert len(saved1.points)==count1
            rules=yaml.safe_load((root/'floor1.rules.yaml').read_text())
            assert rules['preprocessing']['statistical_enabled'] and rules['preprocessing']['radius_enabled']
            assert rules['floor']['map_name']=='floor1234'
            assert rules['floor']['ground_z']==0.0
            index=yaml.safe_load((root/'floors.yaml').read_text())
            assert index['floors'][0]['ground_z']==0.0
            window.add_floor_button.click()
            second=session.selected
            assert second!=first
            assert not panel.voxel_enabled.isChecked() and not panel.statistical_enabled.isChecked()
            assert len(window.viewer._cloud.points)==5043
            panel.crop_enabled.setChecked(True)
            panel.bounds[2][0].setValue(3)
            panel.bounds[2][1].setValue(5.5)
            panel.preview_button.click()
        elif phase==8:
            assert len(session.current.preview.points)==1681
            panel.ground_z.setValue(3.0)
            panel.ceiling_z.setValue(5.7)
            panel.ground_z_tolerance.setValue(.25)
            panel.height_confirmed.setChecked(True)
            ctl.save_path(root/'floor2.pcd')
        elif phase==9:
            assert (root/'floor2.pcd').is_file()
            index=yaml.safe_load((root/'floors.yaml').read_text())
            assert len(index['floors'])==2
            assert [f['ground_z'] for f in index['floors']]==[0.0,3.0]
            assert index['floors'][1]['ground_z_band']==[2.75,3.25]
            assert index['floors'][1]['height_range']==[3.0,5.7]
            assert index['floors'][0]['ceiling_z']==2.7
            assert len(session.states[first].saved_cloud.points)==count1
            window.tree.setCurrentItem(ctl.items[first])
            assert panel.voxel.value()==.5 and panel.statistical_enabled.isChecked()
            assert panel.ground_z.value()==0.0 and panel.height_confirmed.isChecked()
            assert panel.ceiling_z.value()==2.7
            assert panel.bounds[2][1].value()==2.5
            panel.voxel.setValue(.6)
            assert session.current.preview is None and not panel.save_button.isEnabled()
            window.tree.setCurrentItem(ctl.items[second])
            assert not panel.voxel_enabled.isChecked() and panel.bounds[2][0].value()==3
            window.tree.setCurrentItem(ctl.items[first])
            assert panel.voxel.value()==.6, 'Draft lost on object switch'
            panel.ground_z.setValue(.1)
            panel.cancel_button.click()
            assert panel.voxel.value()==.5 and len(session.current.preview.points)==count1
            assert panel.ground_z.value()==0.0
            panel.reset_button.click()
            assert len(session.current.preview.points)==5043
            assert not panel.crop_enabled.isChecked() and not panel.statistical_enabled.isChecked()
            panel.cancel_button.click()
            window.resize(1320,880)
        elif phase==10:
            assert_embedded()
            assert panel.scroll.horizontalScrollBar().maximum()==0, 'Height controls overflow horizontally'
            window.view_buttons['iso'].click()
            shot=window.grab()
            painter=QPainter(shot)
            point=window.viewer.container.mapTo(window,QPoint(0,0))
            painter.drawImage(QRect(point,window.viewer.container.size()),window.viewer.capture_image())
            painter.end()
            shot.save(str(Path(__file__).resolve().parents[1]/'docs'/'height_range_ui.png'))
            # Invalid and empty crops must not become exportable.
            panel.crop_enabled.setChecked(True)
            panel.bounds[0][0].setValue(100)
            assert not panel.preview_button.isEnabled()
            panel.bounds[0][1].setValue(101)
            panel.preview_button.click()
        elif phase==11:
            assert len(session.current.preview.points)==0 and not panel.save_button.isEnabled()
            panel.cancel_button.click()
            assert hashlib.sha256(source.read_bytes()).digest()==digest
            assert len(o3d.io.read_point_cloud(str(root/'floor1.pcd')).points)==count1
            # Removing a saved object from the workspace must not delete its export.
            window.delete_floor_button.click()
            assert first not in session.states and (root/'floor1.pcd').exists()
            # Discard only the unsaved Full Map preview before closing.
            ctl.cancel()
            timer.stop()
            window.close()
            print('PASS: single window, actual 1–4 native keys, color buttons, numeric input, independent floors, both noise filters, PCD/rules roundtrip, drafts, reset, empty guard, original preserved',flush=True)
            app.exit(0)
        phase+=1
    except Exception:
        import traceback
        traceback.print_exc()
        os._exit(1)


timer=QTimer()
timer.timeout.connect(check)
timer.start(350)
result=app.exec()
folder.cleanup()
raise SystemExit(result)
