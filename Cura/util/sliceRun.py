from __future__ import absolute_import

import platform, os, subprocess, sys

if not hasattr(sys, 'frozen'):
	cura_sf_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../cura_sf/"))
	if cura_sf_path not in sys.path:
		sys.path.append(cura_sf_path)
	from skeinforge_application.skeinforge_utilities import skeinforge_craft

from util import profile

#How long does each step take compared to the others. This is used to make a better scaled progress bar, and guess time left.
sliceStepTimeFactor = {
	'start': 3.3713991642,
	'slice': 15.4984838963,
	'preface': 5.17178297043,
	'inset': 116.362634182,
	'fill': 215.702672005,
	'multiply': 21.9536788464,
	'speed': 12.759510994,
	'raft': 31.4580039978,
	'skirt': 19.3436040878,
	'skin': 1.0,
	'joris': 1.0,
	'dwindle': 1.0,
	'comb': 23.7805759907,
	'cool': 27.148763895,
	'hop': 1.0,
	'dimension': 90.4914340973
}

totalRunTimeFactor = 0
for v in sliceStepTimeFactor.values():
	totalRunTimeFactor += v

def getPyPyExe():
	"Return the path to the pypy executable if we can find it. Else return False"
	if platform.system() == "Windows":
		exeName = "pypy.exe"
		pypyExe = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../pypy/pypy.exe"))
	else:
		exeName = "pypy"
		pypyExe = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../pypy/bin/pypy"))
	if os.path.exists(pypyExe):
		return pypyExe

	path = os.environ['PATH']
	paths = path.split(os.pathsep)
	for p in paths:
		pypyExe = os.path.join(p, exeName)
		if os.path.exists(pypyExe):
			return pypyExe 
	return False

def getSlic3rExe():
	"Return the path to the pypy executable if we can find it. Else return False"
	if platform.system() == "Windows":
		exeName = "slic3r.exe"
		slic3rExe = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../Slic3r/bin/slic3r.exe"));
	else:
		exeName = "slic3r"
		slic3rExe = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../Slic3r/bin/slic3r"));
	if os.path.exists(slic3rExe):
		return slic3rExe

	path = os.environ['PATH']
	paths = path.split(os.pathsep)
	for p in paths:
		slic3rExe = os.path.join(p, exeName)
		if os.path.exists(slic3rExe):
			return slic3rExe
	return False

def runSlice(fileNames):
	"Run the slicer on the files. If we are running with PyPy then just do the slicing action. If we are running as Python, try to find pypy."
	pypyExe = getPyPyExe()
	for fileName in fileNames:
		if fileName.startswith("#UTF8#"):
			fileName = unicode(fileName[6:], "utf-8")
		if platform.python_implementation() == "PyPy":
			skeinforge_craft.writeOutput(fileName)
		elif pypyExe == False:
			if not hasattr(sys, 'frozen'):
				print("************************************************")
				print("* Failed to find pypy, so slicing with python! *")
				print("************************************************")
				skeinforge_craft.writeOutput(fileName)
				print("************************************************")
				print("* Failed to find pypy, so sliced with python!  *")
				print("************************************************")
			else:
				print("******************************************************************")
				print("* Failed to find pypy, we need pypy to slice with a frozen build *")
				print("* Place pypy in the same directory as Cura so Cura can find it.  *")
				print("******************************************************************")
				sys.exit(1)
		else:
			subprocess.call(getSliceCommand(fileName))

def getExportFilename(filename, ext = "gcode"):
	return "%s.%s" % (filename[: filename.rfind('.')], ext)

#Get a short filename in 8.3 format for proper saving on SD.
def getShortFilename(filename):
	ext = filename[filename.rfind('.'):]
	filename = filename[: filename.rfind('.')]
	return filename[:8] + ext[:2]

def getSliceCommand(filename):
	if profile.getPreference('slicer').startswith('Slic3r') and getSlic3rExe() != False:
		slic3rExe = getSlic3rExe()
		if slic3rExe == False:
			return False
		cmd = [slic3rExe,
			'--output-filename-format', '[input_filename_base].gcode',
			'--nozzle-diameter', str(profile.calculateEdgeWidth()),
			'--print-center', '%s,%s' % (profile.getProfileSetting('machine_center_x'), profile.getProfileSetting('machine_center_y')),
			'--z-offset', '0',
			'--gcode-flavor', 'reprap',
			'--gcode-comments',
			'--filament-diameter', profile.getProfileSetting('filament_diameter'),
			'--extrusion-multiplier', str(1.0 / float(profile.getProfileSetting('filament_density'))),
			'--temperature', profile.getProfileSetting('print_temperature'),
			'--travel-speed', profile.getProfileSetting('travel_speed'),
			'--perimeter-speed', profile.getProfileSetting('print_speed'),
			'--small-perimeter-speed', profile.getProfileSetting('print_speed'),
			'--infill-speed', profile.getProfileSetting('print_speed'),
			'--solid-infill-speed', profile.getProfileSetting('print_speed'),
			'--bridge-speed', profile.getProfileSetting('print_speed'),
			'--bottom-layer-speed-ratio', str(float(profile.getProfileSetting('bottom_layer_speed')) / float(profile.getProfileSetting('print_speed'))),
			'--layer-height', profile.getProfileSetting('layer_height'),
			'--first-layer-height-ratio', '1.0',
			'--infill-every-layers', '1',
			'--perimeters', str(profile.calculateLineCount()),
			'--solid-layers', str(profile.calculateSolidLayerCount()),
			'--fill-density', str(float(profile.getProfileSetting('fill_density'))/100),
			'--fill-angle', '45',
			'--fill-pattern', 'rectilinear', #rectilinear line concentric hilbertcurve archimedeanchords octagramspiral
			'--solid-fill-pattern', 'rectilinear',
			'--start-gcode', profile.getAlterationFilePath('start.gcode'),
			'--end-gcode', profile.getAlterationFilePath('end.gcode'),
			'--retract-length', profile.getProfileSetting('retraction_amount'),
			'--retract-speed', str(int(float(profile.getProfileSetting('retraction_speed')))),
			'--retract-restart-extra', profile.getProfileSetting('retraction_extra'),
			'--retract-before-travel', profile.getProfileSetting('retraction_min_travel'),
			'--retract-lift', '0',
			'--slowdown-below-layer-time', profile.getProfileSetting('cool_min_layer_time'),
			'--min-print-speed', profile.getProfileSetting('cool_min_feedrate'),
			'--skirts', profile.getProfileSetting('skirt_line_count'),
			'--skirt-distance', str(int(float(profile.getProfileSetting('skirt_gap')))),
			'--skirt-height', '1',
			'--scale', profile.getProfileSetting('model_scale'),
			'--rotate', profile.getProfileSetting('model_rotate_base'),
			'--duplicate-x', profile.getProfileSetting('model_multiply_x'),
			'--duplicate-y', profile.getProfileSetting('model_multiply_y'),
			'--duplicate-distance', '10']
		if profile.getProfileSetting('support') != 'None':
			cmd.extend(['--support-material'])
		cmd.extend([filename])
		return cmd
	else:
		pypyExe = getPyPyExe()
		if pypyExe == False:
			pypyExe = sys.executable
		
		#In case we have a frozen exe, then argv[0] points to the executable, but we want to give pypy a real script file.
		if hasattr(sys, 'frozen'):
			mainScriptFile = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "cura_sf.zip"))
		else:
			mainScriptFile = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", os.path.split(sys.argv[0])[1]))
		cmd = [pypyExe, mainScriptFile, '-p', profile.getGlobalProfileString(), '-s']
		if platform.system() == "Windows":
			try:
				cmd.append(str(filename))
			except UnicodeEncodeError:
				cmd.append("#UTF8#" + filename.encode("utf-8"))
		else:
			cmd.append(filename)
		return cmd

def startSliceCommandProcess(cmdList):
	kwargs = {} 
	if subprocess.mswindows: 
		su = subprocess.STARTUPINFO() 
		su.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		su.wShowWindow = subprocess.SW_HIDE
		kwargs['startupinfo'] = su
	return subprocess.Popen(cmdList, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
