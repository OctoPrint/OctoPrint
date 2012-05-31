import sys
try:
	import cx_Freeze
except:
	print "ERROR: You need cx-Freeze installed to build this package"
	sys.exit(1)

freezeVersion = map(int, cx_Freeze.version.split('.'))
if freezeVersion[0] < 4 or freezeVersion[0] == 4 and freezeVersion[1] < 2:
	print "ERROR: Your cx-Freeze version is too old to use with Cura."
	sys.exit(1)

sys.path.append('./cura_sf/')

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": [
	'encodings.utf_8',
	"OpenGL", "OpenGL.arrays", "OpenGL.platform", "OpenGL.GLU",
], "excludes": ['Tkinter', 'tcl'], "optimize": 0, "include_files": [
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

cx_Freeze.setup(  name = "Cura",
        version = "RC5",
        description = "Cura",
        options = {"build_exe": build_exe_options},
        executables = [cx_Freeze.Executable("cura.py", base=base)])

