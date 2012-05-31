import sys
from cx_Freeze import setup, Executable

sys.path.append('./cura_sf/')

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": [
	'encodings.utf_8',
	"OpenGL", "OpenGL.arrays", "OpenGL.platform",
], "excludes": [], "optimize": 0, "include_files": [
	('images', 'images'),
	('cura.py', 'cura.py'),
	('__init__.py', '__init__.py'),
	('util', 'util'),
	('cura_sf', 'cura_sf')
]}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(  name = "Cura",
        version = "RC5",
        description = "Cura",
        options = {"build_exe": build_exe_options},
        executables = [Executable("cura.py", base=base)])

