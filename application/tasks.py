from PySide6.QtCore import QThread, Signal
from core.pointcloud_io import load_pcd
from core.pointcloud_processor import PointCloudProcessor
from core.export_manager import export_pcd


class LoadTask(QThread):
    loaded = Signal(object)
    failed = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            self.loaded.emit(load_pcd(self.path))
        except Exception as exc:
            self.failed.emit(str(exc))


class ProcessTask(QThread):
    processed = Signal(object, object)
    failed = Signal(str)

    def __init__(self, original, params, parent=None):
        super().__init__(parent)
        self.original, self.params = original, params

    def run(self):
        try:
            self.processed.emit(PointCloudProcessor.process(self.original, self.params), self.params)
        except Exception as exc:
            self.failed.emit(str(exc))


class ExportTask(QThread):
    exported = Signal(object)
    failed = Signal(str)

    def __init__(self, source, cloud, params, identity, path, overwrite=False, parent=None):
        super().__init__(parent)
        self.args = source, cloud, params, identity, path, overwrite

    def run(self):
        try:
            self.exported.emit(export_pcd(*self.args))
        except Exception as exc:
            self.failed.emit(str(exc))
