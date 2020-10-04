# use `python3 setup.py build` to freeze an executable using cx_Freeze

import sys
import os.path
from cx_Freeze import setup, Executable

PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))
os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')

if sys.platform == 'win32':
    base = 'Win32GUI'
    include_files = [
        os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tk86t.dll'),
        os.path.join(PYTHON_INSTALL_DIR, 'DLLs', 'tcl86t.dll')
    ]
else:
    base = None
    include_files = []

executables = [Executable('rfid-db-tool.py', base=base)]

packages = ['serial', 'tkinter', 'struct']

options = {
    'build_exe': {
        'packages': packages,
        'include_files': include_files,
    },
}

setup(
    name = 'rfid-db-tool',
    options = options,
    version = "0.1",
    description = 'a program for working with a device using serial protocol',
    executables = executables
)
