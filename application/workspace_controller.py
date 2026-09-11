"""Unified object selection, independent processing, and disk export."""
from pathlib import Path
from dataclasses import replace
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTreeWidgetItem
from application.tasks import LoadTask, ProcessTask, ExportTask
from core.export_manager import export_paths


class WorkspaceController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.session = window.session
        self.items = {}
        self._updating = False
        p = window.panel
        p.changed.connect(self.draft_changed)
        p.preview_requested.connect(self.preview)
        p.save_requested.connect(self.choose_save)
        p.cancel_requested.connect(self.cancel)
        p.reset_requested.connect(self.reset)
        window.tree.currentItemChanged.connect(self.select_item)
        window.tree.itemChanged.connect(self.visibility_changed)
        window.add_floor_button.clicked.connect(self.add_floor)
        window.delete_floor_button.clicked.connect(self.delete_floor)

    def load_path(self, path):
        if self.window.task is not None:
            return
        task = LoadTask(path, self.window)
        task.loaded.connect(self.loaded)
        self.window.start_task(task, '读取完整 PCD…')

    def loaded(self, source):
        self._updating = True
        try:
            self.session.load(source)
            self.items.clear()
            self.window.floors_item.takeChildren()
            self.window.tree.setCurrentItem(self.window.full_item)
            self.window.full_item.setCheckState(0, Qt.CheckState.Checked)
        finally:
            self._updating = False
        self.window.source_count.setText(f'{source.count:,}')
        self.window.properties.setText(source.path.name + '\n\n' + '\n'.join(
            f'{axis}   {lo:.3f} ～ {hi:.3f} m' for axis,lo,hi in zip('XYZ',source.minimum,source.maximum)))
        self.window.properties.setToolTip(str(source.path))
        self.window.panel.restore(self.session.current, source)
        self.show_current(reset_camera=True)
        self.window.log.appendPlainText(f'载入 {source.path.name} · {source.count:,} 点')

    def update_tree(self):
        self._updating = True
        try:
            for key, floor in self.session.manager.floors.items():
                if key not in self.items:
                    self.items[key] = QTreeWidgetItem(self.window.floors_item)
                    self.items[key].setData(0, Qt.ItemDataRole.UserRole, key)
                state = self.session.states[key]
                status = '未保存' if state.saved_path is None else ('有修改' if state.dirty else '已保存')
                self.items[key].setText(0, f'{floor.map_name} · {status}')
                self.items[key].setCheckState(0, Qt.CheckState.Checked if floor.visible else Qt.CheckState.Unchecked)
                self.items[key].setToolTip(0, str(state.saved_path or '基于完整原始地图，独立编辑'))
            self.window.floors_item.setExpanded(True)
        finally:
            self._updating = False

    def add_floor(self):
        if self.window.task is not None or self.session.source is None:
            return
        floor = self.session.add_floor()
        self.update_tree()
        self.window.tree.setCurrentItem(self.items[floor.key])
        self.window.log.appendPlainText(f'新建 {floor.floor_id} · 从完整原始点云开始，未继承其他对象参数')

    def select_item(self, item, _previous=None):
        if self._updating or item is None or self.session.source is None:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if item is not self.window.full_item and key not in self.session.states:
            return
        self.session.selected = key
        self.window.panel.restore(self.session.current, self.session.source)
        self.show_current()
        self.refresh()

    def draft_changed(self):
        if self.session.source is None or self.window.task is not None:
            return
        params = self.window.panel.params()
        processing_changed=params != self.session.current.draft
        self.session.edit(params, self.window.panel.identity(params))
        self.update_tree()
        self.show_current(update_cloud=processing_changed)
        self.refresh()

    def refresh(self):
        ready = self.session.source is not None and self.window.task is None
        self.window.panel.setEnabled(ready)
        self.window.add_floor_button.setEnabled(ready)
        self.window.delete_floor_button.setEnabled(ready and self.session.selected is not None)
        self.window.panel.save_button.setEnabled(False)
        if not ready:
            return
        try:
            self.session.validate()
            self.window.panel.preview_button.setEnabled(True)
        except ValueError as exc:
            self.window.panel.preview_button.setEnabled(False)
            self.window.panel.notice.setText(str(exc))
            return
        try:
            self.session.export_ready()
            self.window.panel.save_button.setEnabled(True)
        except ValueError as exc:
            if self.session.current.preview is not None:
                self.window.panel.notice.setText(str(exc))

    def show_current(self, reset_camera=False, update_cloud=True):
        if self.session.source is None:
            return
        state = self.session.current
        cloud = state.preview if state.preview is not None else (state.saved_cloud if state.saved_cloud is not None else self.session.source.cloud)
        color = state.identity.color if state.identity is not None else None
        item = self.window.full_item if self.session.selected is None else self.items[self.session.selected]
        if update_cloud:
            self.window.viewer.set_cloud(cloud, reset=reset_camera, base_color=color)
        self.window.viewer.set_cloud_visible(item.checkState(0) == Qt.CheckState.Checked)
        try:
            state.draft.validate()
            self.window.viewer.set_crop_box(state.draft)
        except ValueError:
            self.window.viewer.set_crop_box(None)
        self.window.viewer.set_height_range(state.identity,self.session.source.minimum,self.session.source.maximum)
        name = state.identity.map_name if state.identity else '完整地图'
        self.window.file_title.setText(name)
        self.window.file_title.setToolTip(str(state.saved_path or self.session.source.path))
        if state.preview is not None:
            status = '已保存' if state.saved_path and not state.dirty else '预览 · 未保存'
            message = f'保留 {len(cloud.points):,} 点。' + ('可保存为独立 PCD。' if len(cloud.points) else '结果为空，请调整参数。')
        elif state.saved_cloud is not None:
            status, message = '上次保存结果', '参数已修改，重新预览后才能保存。'
        else:
            status, message = '完整原始数据', '从完整原始地图开始，调整参数后预览。'
        self.window.badge.setText(status)
        self.window.panel.notice.setText(message)
        self.window.stats.setText(f'当前 {len(cloud.points):,} / 原始 {self.session.source.count:,} 点   ·   1 左视  2 右视  3 俯视  4 仰视')

    def preview(self):
        if self.window.task is not None or self.session.source is None:
            return
        try:
            self.session.validate()
        except ValueError as exc:
            self.window.panel.notice.setText(str(exc))
            return
        task = ProcessTask(self.session.source.cloud, self.session.current.draft, self.window)
        task.processed.connect(self.preview_ready)
        self.window.start_task(task, '从完整原始点云计算裁切 / 降采样 / 去噪…')

    def preview_ready(self, cloud, params):
        self.session.stage(cloud, params)
        self.show_current()
        self.window.log.appendPlainText(f'预览完成 · {len(cloud.points):,} 点 · 原始点云未修改')

    def choose_save(self):
        try:
            self.session.export_ready()
        except ValueError as exc:
            self.window.panel.notice.setText(str(exc))
            return
        state = self.session.current
        name = state.identity.map_name if state.identity else self.session.source.path.stem + '_processed'
        suggestion = state.saved_path or self.session.source.path.parent / f'{name}.pcd'
        path, _ = QFileDialog.getSaveFileName(self.window, '保存独立 PCD 与参数文件', str(suggestion),
            'PCD (*.pcd)', options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return
        targets = export_paths(path)
        exists = [target.name for target in targets if target.exists()]
        overwrite = False
        if exists:
            overwrite = QMessageBox.question(self.window, '覆盖已有导出',
                '以下文件已存在，是否覆盖？\n' + '\n'.join(exists),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
            if not overwrite:
                return
        self.save_path(path, overwrite)

    def save_path(self, path, overwrite=False):
        if self.window.task is not None:
            return
        try:
            self.session.export_ready()
            output, _ = export_paths(path)
            for key, other in self.session.states.items():
                if key != self.session.selected and other.saved_path and other.saved_path.resolve() == output.resolve():
                    raise ValueError('该文件已属于其他对象，请使用独立文件名。')
        except ValueError as exc:
            self.window.panel.notice.setText(str(exc))
            return
        state = self.session.current
        task = ExportTask(self.session.source.path, state.preview, state.draft,
                          state.identity, path, overwrite, self.window)
        task.exported.connect(self.saved)
        self.window.start_task(task, '保存独立 PCD 和处理参数…')

    def saved(self, path):
        self.session.commit_saved(path)
        self.window.panel.restore(self.session.current, self.session.source)
        self.update_tree()
        self.show_current()
        self.window.panel.notice.setText('已保存 PCD、处理参数和 floors.yaml 楼层高度索引。'
            if self.session.current.identity else '已保存 PCD 与 .rules.yaml 参数文件。')
        self.window.log.appendPlainText(f'已保存：{path}')

    def cancel(self):
        if self.window.task is not None or self.session.source is None:
            return
        self.session.cancel()
        self.window.panel.restore(self.session.current,self.session.source)
        self.update_tree()
        self.show_current()
        self.refresh()

    def reset(self):
        if self.window.task is not None or self.session.source is None:
            return
        self.session.reset()
        self.window.panel.restore(self.session.current,self.session.source)
        self.update_tree()
        self.show_current()
        self.refresh()

    def delete_floor(self):
        if self.window.task is not None or self.session.selected is None:
            return
        if self.session.current.dirty and QMessageBox.question(self.window, '删除楼层',
            '该楼层有未保存的编辑，是否删除？已导出的文件不会删除。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        key = self.session.selected
        self.session.delete_selected()
        self._updating = True
        self.window.floors_item.removeChild(self.items.pop(key))
        self._updating = False
        self.window.tree.setCurrentItem(self.window.full_item)
        self.select_item(self.window.full_item)
        self.refresh()

    def visibility_changed(self, item, _column):
        if self._updating:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key in self.session.manager.floors:
            visible = item.checkState(0) == Qt.CheckState.Checked
            self.session.manager.set_visible(key, visible)
            state = self.session.states[key]
            state.identity = replace(state.identity, visible=visible)
            state.saved_identity = replace(state.saved_identity, visible=visible)
            if key == self.session.selected:
                self.window.panel.current_identity = state.identity
        if (item is self.window.full_item and self.session.selected is None) or (key is not None and key == self.session.selected):
            self.window.viewer.set_cloud_visible(item.checkState(0) == Qt.CheckState.Checked)
