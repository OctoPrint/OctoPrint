#Name: Pause at height
#Info: Pause the printer at a certain height
#Depend: GCode
#Type: postprocess
#Param: pauseLevel(float:5.0) Pause height (mm)
#Param: parkX(float:190) Head park X (mm)
#Param: parkY(float:190) Head park Y (mm)
#Param: retractAmount(float:5) Retraction amount (mm)

import re

def getValue(line, key, default = None):
	if not key in line or (';' in line and line.find(key) > line.find(';')):
		return default
	subPart = line[line.find(key) + 1:]
	m = re.search('^[0-9]+\.?[0-9]*', subPart)
	if m == None:
		return default
	try:
		return float(m.group(0))
	except:
		return default

with open(filename, "r") as f:
	lines = f.readlines()

z = 0
x = 0
y = 0
pauseState = 0
with open(filename, "w") as f:
	for line in lines:
		if getValue(line, 'G', None) == 1:
			newZ = getValue(line, 'Z', z)
			x = getValue(line, 'X', x)
			y = getValue(line, 'Y', y)
			if newZ != z:
				z = newZ
				if z < pauseLevel and pauseState == 0:
					pauseState = 1
				if z >= pauseLevel and pauseState == 1:
					pauseState = 2
					#Retract
					f.write("M83\n")
					f.write("G1 E-%f F6000\n" % (retractAmount))
					#Move the head away
					f.write("G1 X%f Y%f F9000\n" % (parkX, parkY))
					#Wait till the user continues printing
					f.write("M0\n")
					#Move the head back
					f.write("G1 X%f Y%f F9000\n" % (x, y))
					f.write("G1 E%f F6000\n" % (retractAmount))
					f.write("G1 F9000\n")
					f.write("M82\n")
		f.write(line)
