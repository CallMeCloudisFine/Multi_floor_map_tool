"""A hidden GLFW window is attached to Qt before it is ever mapped on screen."""
import copy
import re
import subprocess
import uuid
import numpy as np
import open3d as o3d
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QWidget, QVBoxLayout


class PointCloudView(QWidget):
    view_changed = Signal(str)
    color_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vis = o3d.visualization.VisualizerWithKeyCallback()
        self._closed = False
        self._cloud = None
        self._box = None
        self._crop_box = None
        self._height_planes = None
        self._visible = True
        self.color_mode = 'default'
        self.window_title = 'multi-floor-' + uuid.uuid4().hex
        if not self.vis.create_window(window_name=self.window_title, width=900,
                                      height=650, visible=False):
            raise RuntimeError('Open3D 无法创建 OpenGL 视图，请检查 DISPLAY 和显卡驱动')
        try:
            result = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True,
                                    text=True, check=True, timeout=5)
            match = re.search(r'(0x[0-9a-fA-F]+)\s+"' + re.escape(self.window_title) + '"', result.stdout)
            if not match:
                raise RuntimeError('未找到 Open3D X11 视图，请通过项目 main.py 启动')
            self.native_id = int(match.group(1), 16)
            self.native = QWindow.fromWinId(self.native_id)
            if self.native is None:
                raise RuntimeError('Qt 无法包装 Open3D 视图')
            self.container = QWidget.createWindowContainer(self.native, self)
            self.container.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.container)
            options = self.vis.get_render_option()
            options.background_color = [0.043, 0.063, 0.086]
            options.point_size = 3.0
            # Embedded viewport must not become fullscreen or close independently.
            for key in (70, 81, 256, 257, 48, 57):
                self.vis.register_key_callback(key, lambda _vis: False)
            for number in (1, 2, 3, 4):
                self.vis.register_key_callback(48 + number,
                    lambda _vis, number=number: self.handle_view_key(number))
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._tick)
            self.timer.start(16)
        except Exception:
            self.vis.destroy_window()
            raise

    def _tick(self):
        if not self._closed:
            self.vis.poll_events()
            self.vis.update_renderer()

    def set_cloud(self, cloud, *, preview=False, reset=True, preserve_colors=False, base_color=None):
        for geometry in (self._cloud, self._box):
            if geometry is not None:
                self.vis.remove_geometry(geometry, reset_bounding_box=False)
        self._cloud = copy.deepcopy(cloud)
        self._box = None
        if len(cloud.points):
            points = np.asarray(cloud.points)
            z = points[:, 2]
            t = ((z - z.min()) / max(float(np.ptp(z)), 1e-6))[:, None]
            low, high = (np.array([0.27, 0.65, 0.90]), np.array([0.64, 0.91, 0.81]))
            if preview:
                low, high = np.array([0.20, 0.80, 0.59]), np.array([0.80, 1.0, 0.72])
            if base_color is not None:
                self._cloud.paint_uniform_color(base_color)
            elif not preserve_colors:
                self._cloud.colors = o3d.utility.Vector3dVector(low * (1 - t) + high * t)
            self._box = cloud.get_axis_aligned_bounding_box()
            self._box.color = [0.27, 0.36, 0.44]
            if self._visible:
                self.vis.add_geometry(self._cloud, reset_bounding_box=reset)
                self.vis.add_geometry(self._box, reset_bounding_box=False)
            if reset:
                self.reset_view()
        self.set_color_mode(self.color_mode)

    def set_crop_box(self, params):
        if self._crop_box is not None:
            self.vis.remove_geometry(self._crop_box, reset_bounding_box=False)
            self._crop_box = None
        if params is not None and params.crop_min is not None:
            self._crop_box = o3d.geometry.AxisAlignedBoundingBox(params.crop_min, params.crop_max)
            self._crop_box.color = [1.0, 0.65, 0.28]
            self.vis.add_geometry(self._crop_box, reset_bounding_box=False)

    def set_cloud_visible(self, visible):
        if self._cloud is None or visible == self._visible:
            return
        operation = self.vis.add_geometry if visible else self.vis.remove_geometry
        for geometry in (self._cloud, self._box):
            if geometry is not None and not geometry.is_empty():
                operation(geometry, reset_bounding_box=False)
        self._visible = visible

    def set_height_range(self, floor, minimum, maximum):
        if self._height_planes is not None:
            self.vis.remove_geometry(self._height_planes, reset_bounding_box=False)
            self._height_planes=None
        if floor is None or floor.ground_z is None or floor.ceiling_z is None or floor.ground_z >= floor.ceiling_z:
            return
        points=[]
        for z in (floor.ground_z,floor.ceiling_z):
            points.extend([[minimum[0],minimum[1],z],[maximum[0],minimum[1],z],
                           [maximum[0],maximum[1],z],[minimum[0],maximum[1],z]])
        lines=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4]]
        geometry=o3d.geometry.LineSet(o3d.utility.Vector3dVector(points),o3d.utility.Vector2iVector(lines))
        geometry.colors=o3d.utility.Vector3dVector([[.46,.87,.74]]*4+[[.94,.69,.42]]*4)
        self._height_planes=geometry
        self.vis.add_geometry(geometry,reset_bounding_box=False)

    def reset_view(self):
        self.set_view('iso')

    def set_view(self, name):
        """World axes: left = camera at -X, right = +X, top = +Z."""
        views = {'iso': ([.9,-1.2,.8], [0,0,1]),
                 'left': ([-1,0,0], [0,0,1]), 'right': ([1,0,0], [0,0,1]),
                 'top': ([0,0,1], [0,1,0]), 'bottom': ([0,0,-1], [0,1,0])}
        if name not in views:
            raise ValueError(f'未知视角：{name}')
        self.vis.reset_view_point(True)
        control = self.vis.get_view_control()
        front, up = views[name]
        control.set_front(front)
        control.set_up(up)
        target_fov = 60.0 if name == 'iso' else 5.0  # Open3D uses 5° as orthographic mode.
        control.change_field_of_view((target_fov - control.get_field_of_view()) / 5.0)
        control.set_zoom(0.72)
        self.vis.update_renderer()
        self.view_changed.emit(name)

    def handle_view_key(self, number):
        self.set_view({1:'left', 2:'right', 3:'top', 4:'bottom'}[number])
        return False

    def set_color_mode(self, mode):
        options = o3d.visualization.PointColorOption
        modes = {'default': options.Color, 'x': options.XCoordinate,
                 'y': options.YCoordinate, 'z': options.ZCoordinate}
        self.vis.get_render_option().point_color_option = modes[mode]
        self.color_mode = mode
        if self._cloud is not None and len(self._cloud.points):
            self.vis.update_geometry(self._cloud)
        self.vis.update_renderer()
        self.color_changed.emit(mode)

    def capture_image(self):
        """Capture the actual Open3D framebuffer (Qt grab omits native children)."""
        from PySide6.QtGui import QImage
        frame = np.asarray(self.vis.capture_screen_float_buffer(do_render=True))
        rgb = np.ascontiguousarray(np.clip(frame * 255, 0, 255).astype(np.uint8))
        return QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0],
                      QImage.Format.Format_RGB888).copy()

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self.timer.stop()
        self.container.hide()
        self.native.setParent(None)
        self.vis.destroy_window()
