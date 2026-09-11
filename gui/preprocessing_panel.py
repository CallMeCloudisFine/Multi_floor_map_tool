"""One processing panel shared by Full Map and every independent floor."""
from dataclasses import replace
import math
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QLabel, QGroupBox, QCheckBox, QDoubleSpinBox, QPushButton,
    QSpinBox, QLineEdit, QScrollArea, QSizePolicy)
from core.pointcloud_processor import PreprocessingParams
from gui.height_range_slider import HeightRangeSlider


def label(text, name='muted'):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(True)
    return widget


def real_spin(minimum, maximum, value, decimals=3, step=.1):
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setValue(value)
    spin.setSingleStep(step)
    spin.setKeyboardTracking(False)
    return spin


def int_spin(minimum, maximum, value):
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    spin.setKeyboardTracking(False)
    return spin


class PreprocessingPanel(QWidget):
    changed = Signal()
    preview_requested = Signal()
    save_requested = Signal()
    cancel_requested = Signal()
    reset_requested = Signal()

    def __init__(self):
        super().__init__()
        self._updating = False
        self.current_identity = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(0)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16,16,16,16)
        layout.setSpacing(12)
        layout.addWidget(label('PROCESSING', 'eyebrow'))
        self.title = label('完整地图 · 预处理', 'section')
        layout.addWidget(self.title)
        self.origin = label('每个楼层均从完整原始点云开始。')
        layout.addWidget(self.origin)
        self.identity_group = QGroupBox('楼层信息')
        identity_form = QFormLayout(self.identity_group)
        self.floor_id, self.map_name = QLineEdit(), QLineEdit()
        self.map_id = int_spin(0, 2147483647, 1)
        for title, widget in [('floor_id', self.floor_id), ('map_id', self.map_id), ('map_name', self.map_name)]:
            identity_form.addRow(title, widget)
        layout.addWidget(self.identity_group)
        self.height_group = QGroupBox('楼层高度 · 原始地图坐标')
        height_form = QFormLayout(self.height_group)
        self.height_confirmed = QCheckBox('已人工确认地面与天花板')
        self.ground_z = real_spin(-1e12, 1e12, 0, 6)
        self.ground_z.setSuffix(' m')
        self.ceiling_z = real_spin(-1e12, 1e12, 3, 6)
        self.ceiling_z.setSuffix(' m')
        endpoints = QWidget()
        endpoints_layout = QHBoxLayout(endpoints)
        endpoints_layout.setContentsMargins(0,0,0,0)
        for title,spin,color in [('地面 Z',self.ground_z,'#75dfbd'),('天花板 Z',self.ceiling_z,'#f0b16b')]:
            spin.setMinimumWidth(0)
            spin.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
            column=QVBoxLayout()
            caption=label(title)
            caption.setStyleSheet(f'color: {color};')
            column.addWidget(caption)
            column.addWidget(spin)
            endpoints_layout.addLayout(column)
        self.height_slider = HeightRangeSlider()
        self.height_slider.values_changed.connect(self._slider_changed)
        self.ground_z_tolerance = real_spin(.000001, 1000, .3, 6, .05)
        self.ground_z_tolerance.setSuffix(' m')
        self.coordinate_frame = QLineEdit('source_map')
        height_form.addRow(endpoints)
        height_form.addRow(self.height_slider)
        height_form.addRow('地面高度容差 ±', self.ground_z_tolerance)
        height_form.addRow('坐标系', self.coordinate_frame)
        height_form.addRow(self.height_confirmed)
        self.height_hint = label('地面高度不是裁切 Z Min，也不是机器人机身高度。')
        height_form.addRow(self.height_hint)
        layout.addWidget(self.height_group)
        crop_group = QGroupBox('01   XYZ 空间裁切')
        crop_layout = QVBoxLayout(crop_group)
        self.crop_enabled = QCheckBox('启用裁切')
        crop_layout.addWidget(self.crop_enabled)
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        for i, text in enumerate(('轴', '最小值 / m', '最大值 / m')):
            grid.addWidget(label(text), 0, i)
        self.bounds = []
        for i, axis in enumerate('XYZ'):
            grid.addWidget(label(axis), i+1, 0)
            pair = [real_spin(-1e12,1e12,0,6) for _ in range(2)]
            for col, spin in enumerate(pair, 1):
                spin.setMinimumWidth(105)
                spin.valueChanged.connect(self._change)
                grid.addWidget(spin, i+1, col)
            self.bounds.append(pair)
        crop_layout.addLayout(grid)
        layout.addWidget(crop_group)
        voxel_group = QGroupBox('02   体素降采样')
        form = QFormLayout(voxel_group)
        self.voxel_enabled = QCheckBox('启用 Voxel')
        self.voxel = real_spin(.0001,1000,.05,4,.01)
        self.voxel.setSuffix(' m')
        form.addRow(self.voxel_enabled)
        form.addRow('体素大小', self.voxel)
        layout.addWidget(voxel_group)
        noise_group = QGroupBox('03   离群点过滤')
        form = QFormLayout(noise_group)
        self.statistical_enabled = QCheckBox('统计过滤 SOR')
        self.nb_neighbors = int_spin(2,100000,20)
        self.std_ratio = real_spin(.01,100,2,2)
        form.addRow(self.statistical_enabled)
        form.addRow('邻居数', self.nb_neighbors)
        form.addRow('标准差系数', self.std_ratio)
        form.addRow(label('系数越小，过滤越严格。'))
        self.radius_enabled = QCheckBox('半径过滤 Radius')
        self.radius = real_spin(.0001,1000,.2,4,.01)
        self.radius.setSuffix(' m')
        self.min_neighbors = int_spin(1,100000,3)
        form.addRow(self.radius_enabled)
        form.addRow('邻域半径', self.radius)
        form.addRow('最少邻居数', self.min_neighbors)
        form.addRow(label('降采样后点更稀疏，请相应增大半径。'))
        layout.addWidget(noise_group)
        layout.addStretch()
        scroll = QScrollArea()
        self.scroll=scroll
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        footer = QWidget()
        footer.setObjectName('processingFooter')
        actions = QVBoxLayout(footer)
        actions.setContentsMargins(16,12,16,14)
        actions.setSpacing(8)
        self.notice = label('加载 PCD 后开始。', 'notice')
        actions.addWidget(self.notice)
        row = QHBoxLayout()
        self.preview_button = QPushButton('预览结果')
        self.save_button = QPushButton('保存 PCD…')
        self.save_button.setObjectName('primary')
        row.addWidget(self.preview_button)
        row.addWidget(self.save_button)
        actions.addLayout(row)
        row = QHBoxLayout()
        self.cancel_button = QPushButton('恢复上次保存')
        self.reset_button = QPushButton('重置参数')
        row.addWidget(self.cancel_button)
        row.addWidget(self.reset_button)
        actions.addLayout(row)
        outer.addWidget(footer)
        for button, signal in [(self.preview_button,self.preview_requested), (self.save_button,self.save_requested),
                               (self.cancel_button,self.cancel_requested), (self.reset_button,self.reset_requested)]:
            button.clicked.connect(signal)
        for check in (self.crop_enabled,self.voxel_enabled,self.statistical_enabled,self.radius_enabled,self.height_confirmed):
            check.toggled.connect(self._change)
        for spin in (self.voxel,self.nb_neighbors,self.std_ratio,self.radius,self.min_neighbors,self.map_id,self.ground_z,self.ceiling_z,self.ground_z_tolerance):
            spin.valueChanged.connect(self._change)
        self.floor_id.textChanged.connect(self._change)
        self.map_name.textChanged.connect(self._change)
        self.coordinate_frame.textChanged.connect(self._change)
        self._change()
        self.identity_group.hide()
        self.height_group.hide()
        self.setEnabled(False)

    def _change(self, *_):
        for pair in self.bounds:
            for spin in pair:
                spin.setEnabled(self.crop_enabled.isChecked())
        self.voxel.setEnabled(self.voxel_enabled.isChecked())
        self.nb_neighbors.setEnabled(self.statistical_enabled.isChecked())
        self.std_ratio.setEnabled(self.statistical_enabled.isChecked())
        self.radius.setEnabled(self.radius_enabled.isChecked())
        self.min_neighbors.setEnabled(self.radius_enabled.isChecked())
        ground,ceiling=self.ground_z.value(),self.ceiling_z.value()
        if ground < ceiling:
            self.height_slider.setEnabled(True)
            self.height_slider.set_values(ground,ceiling)
            state='已确认' if self.height_confirmed.isChecked() else '候选范围 · 待人工确认'
            self.height_hint.setText(f'层内净高 {ceiling-ground:.3f} m · {state}\n绿色框为地面，橙色框为天花板；不改变裁切。')
        else:
            self.height_slider.setEnabled(False)
            self.height_hint.setText('天花板必须高于地面，请修正数值。')
        if not self._updating:
            self.changed.emit()

    def _slider_changed(self, ground, ceiling):
        self._updating=True
        try:
            self.ground_z.setValue(ground)
            self.ceiling_z.setValue(ceiling)
        finally:
            self._updating=False
        self._change()

    def params(self):
        cropped = self.crop_enabled.isChecked()
        return PreprocessingParams(
            voxel_size=self.voxel.value() if self.voxel_enabled.isChecked() else 0,
            crop_min=tuple(pair[0].value() for pair in self.bounds) if cropped else None,
            crop_max=tuple(pair[1].value() for pair in self.bounds) if cropped else None,
            statistical_enabled=self.statistical_enabled.isChecked(), nb_neighbors=self.nb_neighbors.value(),
            std_ratio=self.std_ratio.value(), radius_enabled=self.radius_enabled.isChecked(),
            radius=self.radius.value(), min_neighbors=self.min_neighbors.value())

    def identity(self, params):
        if self.current_identity is None:
            return None
        return replace(self.current_identity, floor_id=self.floor_id.text(), map_id=self.map_id.value(),
                       map_name=self.map_name.text(), params=params,
                       ground_z=self.ground_z.value(), ceiling_z=self.ceiling_z.value(),
                       height_confirmed=self.height_confirmed.isChecked(),
                       ground_z_tolerance=self.ground_z_tolerance.value(), coordinate_frame=self.coordinate_frame.text())

    def restore(self, state, source):
        params = state.draft
        self._updating = True
        try:
            self.current_identity = state.identity
            self.identity_group.setVisible(state.identity is not None)
            self.height_group.setVisible(state.identity is not None)
            if state.identity:
                self.title.setText(f'{state.identity.map_name} · 预处理')
                self.floor_id.setText(state.identity.floor_id)
                self.map_id.setValue(state.identity.map_id)
                self.map_name.setText(state.identity.map_name)
                self.height_confirmed.setChecked(state.identity.height_confirmed)
                ground=state.identity.ground_z if state.identity.ground_z is not None else source.minimum[2]
                ceiling=state.identity.ceiling_z if state.identity.ceiling_z is not None else max(source.maximum[2],ground+1.0)
                self.ground_z.setValue(ground)
                self.ceiling_z.setValue(ceiling)
                if ground < ceiling:
                    self.height_slider.set_values(ground,ceiling, min(source.minimum[2],ground), max(source.maximum[2],ceiling))
                self.ground_z_tolerance.setValue(state.identity.ground_z_tolerance)
                self.coordinate_frame.setText(state.identity.coordinate_frame)
            else:
                self.title.setText('完整地图 · 预处理')
            self.voxel_enabled.setChecked(params.voxel_size > 0)
            self.voxel.setValue(params.voxel_size or .05)
            self.crop_enabled.setChecked(params.crop_min is not None)
            for i, pair in enumerate(self.bounds):
                pair[0].setValue(params.crop_min[i] if params.crop_min else math.floor(source.minimum[i]*1e6)/1e6)
                pair[1].setValue(params.crop_max[i] if params.crop_max else math.ceil(source.maximum[i]*1e6)/1e6)
            for name in ('statistical_enabled','radius_enabled'):
                getattr(self,name).setChecked(getattr(params,name))
            for name in ('nb_neighbors','std_ratio','radius','min_neighbors'):
                getattr(self,name).setValue(getattr(params,name))
        finally:
            self._updating = False
        # Refresh enabled states without editing the restored draft.
        self._updating = True
        self._change()
        self._updating = False
