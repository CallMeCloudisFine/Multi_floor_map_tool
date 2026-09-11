"""Desktop entry point. Linux X11 / XWayland is the initial viewer backend."""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description='多楼层 PCD 可视化人工切分工具')
    parser.add_argument('pcd', nargs='?', help='启动后打开的 PCD 文件')
    args = parser.parse_args()
    if not sys.platform.startswith('linux'):
        parser.error('当前窗口适配器支持 Linux X11 / XWayland')
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    from gui.runtime import prepare_runtime
    prepare_runtime()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from gui.main_window import MainWindow
    app = QApplication(sys.argv[:1])
    try:
        window = MainWindow()
    except Exception as exc:
        QMessageBox.critical(None, '视图初始化失败', str(exc))
        return 1
    window.show()
    if args.pcd:
        QTimer.singleShot(0, lambda: window.controller.load_path(args.pcd))
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
