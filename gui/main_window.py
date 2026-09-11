from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QMessageBox, QTreeWidget,
    QTreeWidgetItem, QSplitter, QPlainTextEdit, QProgressBar, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QButtonGroup)
from core.edit_session import EditSession
from application.workspace_controller import WorkspaceController
from gui.pointcloud_view import PointCloudView
from gui.preprocessing_panel import PreprocessingPanel, label
from gui.theme import STYLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Strata · 多楼层点云工作台')
        self.resize(1500, 980)
        self.setMinimumSize(1160, 760)
        self.setStyleSheet(STYLE)
        self.session = EditSession()
        self.task = None
        root = QWidget()
        base = QVBoxLayout(root)
        base.setContentsMargins(0,0,0,0)
        base.setSpacing(0)
        header = QWidget()
        header.setObjectName('header')
        row = QHBoxLayout(header)
        row.setContentsMargins(22,14,22,14)
        row.addWidget(label('◈  STRATA', 'brand'))
        row.addSpacing(18)
        row.addWidget(label('多楼层点云工作台'))
        row.addStretch()
        row.addWidget(label('创建楼层  →  独立处理  →  保存 PCD'))
        row.addSpacing(18)
        self.open_button = QPushButton('＋  打开 PCD')
        self.open_button.setObjectName('primary')
        self.open_button.clicked.connect(self.choose_file)
        row.addWidget(self.open_button)
        base.addWidget(header)
        splitter = QSplitter()
        base.addWidget(splitter,1)
        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        left = QVBoxLayout(sidebar)
        left.setContentsMargins(16,20,16,16)
        left.setSpacing(12)
        left.addWidget(label('WORKSPACE', 'eyebrow'))
        left.addWidget(label('地图与楼层', 'section'))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(12)
        self.full_item = QTreeWidgetItem(self.tree,['完整原始地图'])
        self.full_item.setCheckState(0,Qt.CheckState.Checked)
        self.floors_item = QTreeWidgetItem(self.tree,['独立楼层'])
        self.tree.setCurrentItem(self.full_item)
        left.addWidget(self.tree,1)
        self.add_floor_button = QPushButton('＋  创建楼层')
        self.delete_floor_button = QPushButton('删除选中楼层')
        self.add_floor_button.setEnabled(False)
        self.delete_floor_button.setEnabled(False)
        left.addWidget(self.add_floor_button)
        left.addWidget(self.delete_floor_button)
        left.addWidget(label('SOURCE / 原始点云', 'eyebrow'))
        self.source_count = label('—','stat')
        left.addWidget(self.source_count)
        self.properties = label('加载完整 PCD 开始。')
        self.properties.setTextFormat(Qt.TextFormat.PlainText)
        self.properties.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        left.addWidget(self.properties)
        splitter.addWidget(sidebar)
        center = QWidget()
        middle = QVBoxLayout(center)
        middle.setContentsMargins(12,12,12,12)
        middle.setSpacing(8)
        row = QHBoxLayout()
        self.file_title = label('尚未打开地图','section')
        self.file_title.setTextFormat(Qt.TextFormat.PlainText)
        row.addWidget(self.file_title,1)
        self.badge = label('等待载入','badge')
        row.addWidget(self.badge)
        middle.addLayout(row)
        self.viewer = PointCloudView(self)
        toolbar = QWidget()
        toolbar.setObjectName('viewportTools')
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(8,7,8,7)
        row.setSpacing(4)
        row.addWidget(label('视角'))
        self.view_buttons = {}
        self.view_group = QButtonGroup(self)
        for name,title,tip in [('left','1 左','从 −X 看向 +X'),('right','2 右','从 +X 看向 −X'),
                               ('top','3 俯','从 +Z 看向 −Z'),('bottom','4 仰','从 −Z 看向 +Z'),
                               ('iso','3D','三维透视 / 重置视角')]:
            button = QPushButton(title)
            button.setObjectName('tool')
            button.setCheckable(True)
            button.setToolTip(tip)
            self.view_group.addButton(button)
            row.addWidget(button)
            button.clicked.connect(lambda checked=False,name=name: self.viewer.set_view(name))
            self.view_buttons[name] = button
        self.view_buttons['iso'].setChecked(True)
        row.addStretch(1)
        row.addWidget(label('着色'))
        self.color_buttons = {}
        self.color_group = QButtonGroup(self)
        for mode,title in [('default','默认'),('x','X'),('y','Y'),('z','Z')]:
            button = QPushButton(title)
            button.setObjectName('tool')
            button.setCheckable(True)
            button.setToolTip('使用当前楼层颜色 / 原始视图渐变' if mode=='default' else f'按 {mode.upper()} 坐标着色')
            self.color_group.addButton(button)
            row.addWidget(button)
            button.clicked.connect(lambda checked=False,mode=mode: self.viewer.set_color_mode(mode))
            self.color_buttons[mode] = button
        self.color_buttons['default'].setChecked(True)
        self.viewer.view_changed.connect(lambda name: self.view_buttons[name].setChecked(True))
        self.viewer.color_changed.connect(lambda name: self.color_buttons[name].setChecked(True))
        # Qt shortcuts are confined to the viewport, never active in parameter inputs.
        self.shortcuts = []
        for number in (1,2,3,4):
            shortcut = QShortcut(QKeySequence(str(number)), self.viewer)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda number=number: self.viewer.handle_view_key(number))
            self.shortcuts.append(shortcut)
        middle.addWidget(toolbar)
        middle.addWidget(self.viewer,1)
        self.stats = label('左键旋转 · Ctrl + 左键平移 · 滚轮缩放')
        middle.addWidget(self.stats)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(200)
        self.log.setFixedHeight(56)
        self.log.appendPlainText('每个楼层独立处理；所有预览均从完整原始点云计算。')
        middle.addWidget(self.log)
        splitter.addWidget(center)
        self.panel = PreprocessingPanel()
        self.panel.setObjectName('inspector')
        self.panel.setMinimumWidth(350)
        splitter.addWidget(self.panel)
        splitter.setSizes([210,910,380])
        splitter.setStretchFactor(1,1)
        self.setCentralWidget(root)
        self.open_action = QAction('打开完整 PCD…',self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.choose_file)
        menu = self.menuBar().addMenu('文件')
        menu.addAction(self.open_action)
        menu.addAction('退出',self.close)
        self.progress = QProgressBar()
        self.progress.setRange(0,0)
        self.progress.setMaximumWidth(160)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().showMessage('就绪 · 单窗口工作区')
        self.controller = WorkspaceController(self)

    def choose_file(self):
        path,_ = QFileDialog.getOpenFileName(self,'打开完整 PCD','','PCD (*.pcd *.PCD)')
        if not path:
            return
        if self.session.has_unsaved and not self.confirm_discard('切换文件会丢弃未保存的编辑。已导出的文件不受影响。'):
            return
        self.controller.load_path(path)

    def confirm_discard(self,message):
        return QMessageBox.question(self,'未保存的编辑',message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def start_task(self,task,message):
        self.task = task
        for widget in (self.open_button,self.panel,self.tree,self.add_floor_button,self.delete_floor_button):
            widget.setEnabled(False)
        self.open_action.setEnabled(False)
        self.progress.show()
        self.statusBar().showMessage(message)
        task.failed.connect(self._failed)
        task.finished.connect(self._finished)
        task.start()

    def _failed(self,message):
        self.log.appendPlainText('操作失败：' + message)
        self.panel.notice.setText(message)
        QMessageBox.warning(self,'操作失败',message)

    def _finished(self):
        self.task.deleteLater()
        self.task = None
        self.open_action.setEnabled(True)
        self.open_button.setEnabled(True)
        self.tree.setEnabled(True)
        self.progress.hide()
        self.controller.refresh()
        self.statusBar().showMessage('就绪 · 原始点云始终保留')

    def closeEvent(self,event):
        if self.task is not None:
            self.statusBar().showMessage('请等待后台任务结束后关闭窗口。')
            event.ignore()
            return
        if self.session.has_unsaved and not self.confirm_discard('关闭后未保存的编辑将丢失。是否退出？'):
            event.ignore()
            return
        self.viewer.shutdown()
        event.accept()
