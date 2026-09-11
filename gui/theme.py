STYLE = '''
QMainWindow, QWidget { background: #10151c; color: #dbe4ed; font-family: "Noto Sans CJK SC", "DejaVu Sans"; font-size: 12px; }
QWidget#header { background: #161e28; border-bottom: 1px solid #293440; }
QWidget#sidebar, QWidget#inspector { background: #161e28; }
QLabel { background: transparent; }
QLabel#brand { color: #f2f7fb; font-size: 20px; font-weight: 700; }
QLabel#eyebrow { color: #68dac0; font-size: 10px; font-weight: 700; }
QLabel#section { color: #eef4fa; font-size: 15px; font-weight: 600; }
QLabel#muted { color: #8d9dad; font-size: 11px; }
QLabel#badge { background: #20372f; color: #8ce7c6; padding: 5px 10px; border-radius: 5px; }
QLabel#stat { color: #f2f7fb; font-size: 27px; font-weight: 600; }
QLabel#notice { background: #202c3b; color: #a7bad0; border-radius: 6px; padding: 10px; }
QPushButton { background: #24313f; border: 1px solid #354454; border-radius: 6px; padding: 8px 12px; color: #e4edf6; }
QPushButton:hover { background: #304152; border-color: #587189; }
QPushButton:pressed { background: #1d2935; }
QPushButton:disabled { background: #1b242e; border-color: #28333e; color: #586775; }
QPushButton#primary { background: #65d8b5; color: #10241d; border-color: #65d8b5; font-weight: 700; }
QPushButton#primary:hover { background: #8de8cb; }
QPushButton#primary:disabled { background: #253f37; border-color: #253f37; color: #618077; }
QPushButton#quiet { background: transparent; border: 1px solid #344151; }
QTreeWidget { background: transparent; border: none; outline: none; }
QTreeWidget::item { padding: 9px 3px; border-radius: 5px; }
QTreeWidget::item:selected { background: #233b3b; color: #9aefd5; }
QTreeWidget::item:disabled { color: #5c6b79; }
QGroupBox { background: #1b2530; border: 1px solid #2c3947; border-radius: 8px; margin-top: 15px; padding: 17px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #cfdae5; }
QDoubleSpinBox { background: #111b25; border: 1px solid #364655; border-radius: 5px; padding: 7px 5px; min-height: 18px; selection-background-color: #327d70; }
QDoubleSpinBox:focus { border-color: #65d8b5; }
QDoubleSpinBox:disabled { color: #5d6d7c; border-color: #293541; }
QCheckBox { spacing: 8px; background: transparent; }
QCheckBox::indicator, QTreeWidget::indicator { width: 14px; height: 14px; border: 1px solid #5b7183; border-radius: 3px; background: #14212c; }
QCheckBox::indicator:checked, QTreeWidget::indicator:checked { background: #65d8b5; border: 2px solid #355d54; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #161e28; width: 7px; }
QScrollBar::handle:vertical { background: #3a4a58; min-height: 30px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QSplitter::handle { background: #283541; width: 1px; }
QPlainTextEdit { background: #101820; color: #92a6b9; border: 1px solid #293744; border-radius: 5px; padding: 6px; font-size: 11px; }
QStatusBar { background: #161e28; color: #9fb2c3; border-top: 1px solid #293440; }
QMenuBar { background: #10151c; color: #93a5b6; }
QMenuBar::item:selected, QMenu::item:selected { background: #2c4350; }
QMenu { background: #1b2631; border: 1px solid #3a4956; }
QProgressBar { background: #22303c; border: none; border-radius: 3px; max-height: 5px; }
QProgressBar::chunk { background: #65d8b5; }
QToolTip { background: #243440; color: #e1ecf4; border: 1px solid #587080; padding: 6px; }
QLineEdit, QSpinBox { background: #111b25; border: 1px solid #364655; border-radius: 5px; padding: 7px 5px; min-height: 18px; selection-background-color: #327d70; }
QLineEdit:focus, QSpinBox:focus { border-color: #65d8b5; }
QTabWidget::pane { border: none; background: #161e28; }
QTabBar::tab { background: #161e28; color: #8d9dad; padding: 12px 22px; border-bottom: 2px solid #293440; }
QTabBar::tab:selected { color: #8ce7c6; border-bottom: 2px solid #65d8b5; }
'''

STYLE += '''
QWidget#viewportTools { background: #192430; border: 1px solid #2a3948; border-radius: 6px; }
QPushButton#tool { padding: 6px 8px; min-width: 22px; border-radius: 4px; background: transparent; border: 1px solid transparent; }
QPushButton#tool:hover { background: #2a3c4a; }
QPushButton#tool:checked { background: #284a43; color: #9ceacf; border-color: #436b60; }
QWidget#processingFooter { background: #19232e; border-top: 1px solid #334352; }
'''
