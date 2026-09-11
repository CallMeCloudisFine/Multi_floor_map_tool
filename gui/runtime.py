"""Optional project-local XCB library, for machines without libxcb-cursor0."""
import ctypes
import os
from pathlib import Path


def prepare_runtime():
    # Qt and GLFW must both select X11; Qt's platform flag alone is insufficient.
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    os.environ.pop('WAYLAND_DISPLAY', None)
    os.environ['XDG_SESSION_TYPE'] = 'x11'
    library = (Path(__file__).resolve().parents[1] / '.runtime' / 'usr' / 'lib'
               / 'x86_64-linux-gnu' / 'libxcb-cursor.so.0')
    if library.exists():
        ctypes.CDLL(str(library), mode=ctypes.RTLD_GLOBAL)
