import sys, math, re, os, struct, time
from xml.etree import ElementTree

import profile

def processRect(e):
	x = float(e.get('x'))
	y = float(e.get('y'))
	width = float(e.get('width'))
	height = float(e.get('height'))
	return [[complex(x, -y), complex(x+width, -y), complex(x+width, -(y+height)), complex(x, -(y+height)), complex(x, -y)]]

def processPath(e):
	d = e.get('d').replace(',', ' ')
	num = ""
	cmd = None
	paths = []
	curPath = None
	
	p = complex(0, 0)
	for c in d + "#":
		if c in "-+.0123456789e":
			num += c
		if c in " \t\n\r#":
			if len(num) > 0:
				param.append(float(num))
			num = ""
		if c in "MmZzLlHhVvCcSsQqTtAa#":
			if cmd == 'M':
				p = complex(param[0], -param[1])
				curPath = None
				i = 2
				while i < len(param):
					if curPath == None:
						curPath = [p]
						paths.append(curPath)
					p = complex(param[i], -param[i+1])
					curPath.append(p)
					i += 2
			elif cmd == 'm':
				p += complex(param[0], -param[1])
				curPath = None
				i = 2
				while i < len(param):
					if curPath == None:
						curPath = [p]
						paths.append(curPath)
					p += complex(param[i], -param[i+1])
					curPath.append(p)
					i += 2
			elif cmd == 'L':
				if curPath == None:
					curPath = [p]
					paths.append(curPath)
				i = 0
				while i < len(param):
					p = complex(param[i], -param[i+1])
					curPath.append(p)
					i += 2
			elif cmd == 'l':
				if curPath == None:
					curPath = [p]
					paths.append(curPath)
				i = 0
				while i < len(param):
					p += complex(param[i], -param[i+1])
					curPath.append(p)
					i += 2
				curPath.append(p)
			elif cmd == 'C':
				if curPath == None:
					curPath = [p]
					paths.append(curPath)
				i = 0
				while i < len(param):
					addCurve(curPath, p, complex(param[i], -param[i+1]), complex(param[i+2], -param[i+3]), complex(param[i+4], -param[i+5]))
					p = complex(param[i+4], -param[i+5])
					curPath.append(p)
					i += 6
			elif cmd == 'c':
				if curPath == None:
					curPath = [p]
					paths.append(curPath)
				i = 0
				while i < len(param):
					addCurve(curPath, p, p + complex(param[i], -param[i+1]), p + complex(param[i+2], -param[i+3]), p + complex(param[i+4], -param[i+5]))
					p += complex(param[i+4], -param[i+5])
					curPath.append(p)
					i += 6
			elif cmd == 'a':
				if curPath == None:
					curPath = [p]
					paths.append(curPath)
				i = 0
				print(param)
				while i < len(param):
					endPoint = p + complex(param[i+5], -param[i+6])
					addArc(curPath, p, endPoint, complex(param[i], param[i+1]), param[i+2], param[i+3], param[i+4])
					p = endPoint
					curPath.append(p)
					i += 7
			elif cmd == 'Z' or cmd == 'z':
				curPath.append(curPath[0])
			elif cmd != None:
				print(cmd)
			cmd = c
			param = []
	return paths

def interpolate(p0, p1, f):
	return complex(p0.real + (p1.real - p0.real) * f, p0.imag + (p1.imag - p0.imag) * f)

def addCurve(path, p0, q0, q1, p1):
	oldPoint = p0
	for n in xrange(0, 100):
		k = n / 100.0
		r0 = interpolate(p0, q0, k);
		r1 = interpolate(q0, q1, k);
		r2 = interpolate(q1, p1, k);
		b0 = interpolate(r0, r1, k);
		b1 = interpolate(r1, r2, k);
		s = interpolate(b0, b1, k);
		if abs(s - oldPoint) > 1.0:
			path.append(s)
			oldPoint = s

def addArc(path, begin, end, radius, xAxisRotation, largeArcFlag, sweepFlag):
	xAxisRotationComplex = complex(math.cos(math.radians(xAxisRotation)), math.sin(math.radians(xAxisRotation)))
	reverseXAxisRotationComplex = complex(xAxisRotationComplex.real, -xAxisRotationComplex.imag)
	beginRotated = begin * reverseXAxisRotationComplex
	endRotated = end * reverseXAxisRotationComplex
	beginTransformed = complex(beginRotated.real / radius.real, beginRotated.imag / radius.imag)
	endTransformed = complex(endRotated.real / radius.real, endRotated.imag / radius.imag)
	midpointTransformed = 0.5 * (beginTransformed + endTransformed)
	midMinusBeginTransformed = midpointTransformed - beginTransformed
	midMinusBeginTransformedLength = abs(midMinusBeginTransformed)

	if midMinusBeginTransformedLength > 1.0:
		radius *= midMinusBeginTransformedLength
		beginTransformed /= midMinusBeginTransformedLength
		endTransformed /= midMinusBeginTransformedLength
		midpointTransformed /= midMinusBeginTransformedLength
		midMinusBeginTransformed /= midMinusBeginTransformedLength
		midMinusBeginTransformedLength = 1.0
	midWiddershinsTransformed = complex(-midMinusBeginTransformed.imag, midMinusBeginTransformed.real)
	midWiddershinsLengthSquared = 1.0 - midMinusBeginTransformedLength * midMinusBeginTransformedLength
	if midWiddershinsLengthSquared < 0.0:
		midWiddershinsLengthSquared = 0.0
	midWiddershinsLength = math.sqrt(midWiddershinsLengthSquared)
	midWiddershinsTransformed *= midWiddershinsLength / abs(midWiddershinsTransformed)
	centerTransformed = midpointTransformed
	if largeArcFlag == sweepFlag:
		centerTransformed -= midWiddershinsTransformed
	else:
		centerTransformed += midWiddershinsTransformed
	beginMinusCenterTransformed = beginTransformed - centerTransformed
	beginMinusCenterTransformedLength = abs(beginMinusCenterTransformed)
	if beginMinusCenterTransformedLength <= 0.0:
		return end
	beginAngle = math.atan2(beginMinusCenterTransformed.imag, beginMinusCenterTransformed.real)
	endMinusCenterTransformed = endTransformed - centerTransformed
	angleDifference = getAngleDifferenceByComplex(endMinusCenterTransformed, beginMinusCenterTransformed)
	if sweepFlag:
		if angleDifference < 0.0:
			angleDifference += 2.0 * math.pi
	else:
		if angleDifference > 0.0:
			angleDifference -= 2.0 * math.pi

	center = complex(centerTransformed.real * radius.real, centerTransformed.imag * radius.imag) * xAxisRotationComplex
	for side in xrange(1, 32):
		a = beginAngle + float(side) * math.pi * 2 / 32
		circumferential = complex(math.cos(a) * radius.real, math.sin(a) * radius.imag) * beginMinusCenterTransformedLength
		point = center + circumferential * xAxisRotationComplex
		path.append(point)

def getAngleDifferenceByComplex( subtractFromComplex, subtractComplex ):
	subtractComplexMirror = complex( subtractComplex.real , - subtractComplex.imag )
	differenceComplex = subtractComplexMirror * subtractFromComplex
	return math.atan2( differenceComplex.imag, differenceComplex.real )


def movePath(p, offset):
	return map(lambda _p: _p - offset, p)

class SVG(object):
	def __init__(self, filename):
		tagProcess = {}
		tagProcess['rect'] = processRect
		tagProcess['path'] = processPath

		self.paths = []
		for e in ElementTree.parse(open(filename, "r")).getiterator():
			tag = e.tag[e.tag.find('}')+1:]
			if not tag in tagProcess:
				#print 'unknown tag: %s' % (tag)
				continue
			self.paths.extend(tagProcess[tag](e))
	
	def center(self, centerPoint):
		offset = complex(0, 0)
		n = 0
		for path in self.paths:
			for point in path:
				offset += point
				n += 1
		offset /= n
		offset -= centerPoint
		
		self.paths = [movePath(p, offset) for p in self.paths]

if __name__ == '__main__':
	svg = SVG("../logo.svg")
	f = open("../../test_export.gcode", "w")

	f.write(';TYPE:CUSTOM\n')
	f.write(profile.getAlterationFileContents('start.gcode'))
	svg.center(complex(profile.getProfileSettingFloat('machine_center_x'), profile.getProfileSettingFloat('machine_center_y')))

	layerThickness = 0.4
	filamentRadius = profile.getProfileSettingFloat('filament_diameter') / 2
	filamentArea = math.pi * filamentRadius * filamentRadius
	lineWidth = profile.getProfileSettingFloat('nozzle_size') * 2

	e = 0
	z = layerThickness

	for n in xrange(0, 20):
		f.write("G1 Z%f F%f\n" % (z, profile.getProfileSettingFloat('max_z_speed')*60))
		for path in svg.paths:
			oldPoint = path[0]
			extrusionMMperDist = lineWidth * layerThickness / filamentArea
			f.write("G1 X%f Y%f F%f\n" % (oldPoint.real, oldPoint.imag, profile.getProfileSettingFloat('travel_speed')*60))
			f.write("G1 F%f\n" % (profile.getProfileSettingFloat('print_speed')*60))
			for point in path[1:]:
				dist = abs(oldPoint - point)
				e += dist * extrusionMMperDist
				f.write("G1 X%f Y%f E%f\n" % (point.real, point.imag, e))
				oldPoint = point
		z += layerThickness
	f.write(profile.getAlterationFileContents('end.gcode'))
	f.close()

