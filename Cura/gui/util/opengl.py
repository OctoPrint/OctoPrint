# coding=utf-8
from __future__ import absolute_import

import math

from Cura.util import meshLoader
from Cura.util import util3d
from Cura.util import profile
from Cura.util.resources import getPathForMesh

try:
	import OpenGL

	OpenGL.ERROR_CHECKING = False
	from OpenGL.GLU import *
	from OpenGL.GL import *

	hasOpenGLlibs = True
except:
	print "Failed to find PyOpenGL: http://pyopengl.sourceforge.net/"
	hasOpenGLlibs = False

def InitGL(window, view3D, zoom):
	# set viewing projection
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
	size = window.GetSize()
	glViewport(0, 0, size.GetWidth(), size.GetHeight())

	glLightfv(GL_LIGHT0, GL_POSITION, [0.2, 0.2, 1.0, 0.0])
	glLightfv(GL_LIGHT1, GL_POSITION, [1.0, 1.0, 1.0, 0.0])

	glEnable(GL_RESCALE_NORMAL)
	glEnable(GL_LIGHTING)
	glEnable(GL_LIGHT0)
	glEnable(GL_DEPTH_TEST)
	glEnable(GL_CULL_FACE)
	glDisable(GL_BLEND)

	glClearColor(1.0, 1.0, 1.0, 1.0)
	glClearStencil(0)
	glClearDepth(1.0)

	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	aspect = float(size.GetWidth()) / float(size.GetHeight())
	if view3D:
		gluPerspective(45.0, aspect, 1.0, 1000.0)
	else:
		glOrtho(-aspect * (zoom), aspect * (zoom), -1.0 * (zoom), 1.0 * (zoom), -1000.0, 1000.0)

	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

platformMesh = None

def DrawMachine(machineSize):
	if profile.getPreference('machine_type') == 'ultimaker':
		glPushMatrix()
		glEnable(GL_LIGHTING)
		glTranslate(100, 200, -5)
		glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8])
		glLightfv(GL_LIGHT0, GL_AMBIENT, [0.5, 0.5, 0.5])
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_COLOR, GL_ONE_MINUS_SRC_COLOR)

		global platformMesh
		if platformMesh == None:
			platformMesh = meshLoader.loadMesh(getPathForMesh('ultimaker_platform.stl'))
			platformMesh.setRotateMirror(0, False, False, False, False, False)

		DrawMesh(platformMesh)
		glPopMatrix()

	glDisable(GL_LIGHTING)
	if False:
		glColor3f(0.7, 0.7, 0.7)
		glLineWidth(2)
		glBegin(GL_LINES)
		for i in xrange(0, int(machineSize.x), 10):
			glVertex3f(i, 0, 0)
			glVertex3f(i, machineSize.y, 0)
		for i in xrange(0, int(machineSize.y), 10):
			glVertex3f(0, i, 0)
			glVertex3f(machineSize.x, i, 0)
		glEnd()

		glEnable(GL_LINE_SMOOTH)
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		glHint(GL_LINE_SMOOTH_HINT, GL_DONT_CARE);

		glColor3f(0.0, 0.0, 0.0)
		glLineWidth(4)
		glBegin(GL_LINE_LOOP)
		glVertex3f(0, 0, 0)
		glVertex3f(machineSize.x, 0, 0)
		glVertex3f(machineSize.x, machineSize.y, 0)
		glVertex3f(0, machineSize.y, 0)
		glEnd()

		glLineWidth(2)
		glBegin(GL_LINE_LOOP)
		glVertex3f(0, 0, machineSize.z)
		glVertex3f(machineSize.x, 0, machineSize.z)
		glVertex3f(machineSize.x, machineSize.y, machineSize.z)
		glVertex3f(0, machineSize.y, machineSize.z)
		glEnd()
		glBegin(GL_LINES)
		glVertex3f(0, 0, 0)
		glVertex3f(0, 0, machineSize.z)
		glVertex3f(machineSize.x, 0, 0)
		glVertex3f(machineSize.x, 0, machineSize.z)
		glVertex3f(machineSize.x, machineSize.y, 0)
		glVertex3f(machineSize.x, machineSize.y, machineSize.z)
		glVertex3f(0, machineSize.y, 0)
		glVertex3f(0, machineSize.y, machineSize.z)
		glEnd()
	else:
		glDisable(GL_CULL_FACE)
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		sx = machineSize.x
		sy = machineSize.y
		for x in xrange(-int(sx/20)-1, int(sx / 20) + 1):
			for y in xrange(-int(sx/20)-1, int(sy / 20) + 1):
				x1 = sx/2+x * 10
				x2 = x1 + 10
				y1 = sx/2+y * 10
				y2 = y1 + 10
				x1 = max(min(x1, sx), 0)
				y1 = max(min(y1, sy), 0)
				x2 = max(min(x2, sx), 0)
				y2 = max(min(y2, sy), 0)
				if (x & 1) == (y & 1):
					glColor4ub(5, 171, 231, 127)
				else:
					glColor4ub(5 * 8 / 10, 171 * 8 / 10, 231 * 8 / 10, 128)
				glBegin(GL_QUADS)
				glVertex3f(x1, y1, -0.01)
				glVertex3f(x2, y1, -0.01)
				glVertex3f(x2, y2, -0.01)
				glVertex3f(x1, y2, -0.01)
				glEnd()

		glEnable(GL_CULL_FACE)

		glColor4ub(5, 171, 231, 64)
		glBegin(GL_QUADS)
		glVertex3f(0, 0, machineSize.z)
		glVertex3f(0, machineSize.y, machineSize.z)
		glVertex3f(machineSize.x, machineSize.y, machineSize.z)
		glVertex3f(machineSize.x, 0, machineSize.z)
		glEnd()

		glColor4ub(5, 171, 231, 96)
		glBegin(GL_QUADS)
		glVertex3f(0, 0, 0)
		glVertex3f(0, 0, machineSize.z)
		glVertex3f(machineSize.x, 0, machineSize.z)
		glVertex3f(machineSize.x, 0, 0)

		glVertex3f(0, machineSize.y, machineSize.z)
		glVertex3f(0, machineSize.y, 0)
		glVertex3f(machineSize.x, machineSize.y, 0)
		glVertex3f(machineSize.x, machineSize.y, machineSize.z)
		glEnd()

		glColor4ub(5, 171, 231, 128)
		glBegin(GL_QUADS)
		glVertex3f(0, 0, machineSize.z)
		glVertex3f(0, 0, 0)
		glVertex3f(0, machineSize.y, 0)
		glVertex3f(0, machineSize.y, machineSize.z)

		glVertex3f(machineSize.x, 0, 0)
		glVertex3f(machineSize.x, 0, machineSize.z)
		glVertex3f(machineSize.x, machineSize.y, machineSize.z)
		glVertex3f(machineSize.x, machineSize.y, 0)
		glEnd()

		glDisable(GL_BLEND)

	glPushMatrix()
	glTranslate(5, 5, 2)
	glLineWidth(2)
	glColor3f(0.5, 0, 0)
	glBegin(GL_LINES)
	glVertex3f(0, 0, 0)
	glVertex3f(20, 0, 0)
	glEnd()
	glColor3f(0, 0.5, 0)
	glBegin(GL_LINES)
	glVertex3f(0, 0, 0)
	glVertex3f(0, 20, 0)
	glEnd()
	glColor3f(0, 0, 0.5)
	glBegin(GL_LINES)
	glVertex3f(0, 0, 0)
	glVertex3f(0, 0, 20)
	glEnd()

	glDisable(GL_DEPTH_TEST)
	#X
	glColor3f(1, 0, 0)
	glPushMatrix()
	glTranslate(23, 0, 0)
	noZ = ResetMatrixRotationAndScale()
	glBegin(GL_LINES)
	glVertex3f(-0.8, 1, 0)
	glVertex3f(0.8, -1, 0)
	glVertex3f(0.8, 1, 0)
	glVertex3f(-0.8, -1, 0)
	glEnd()
	glPopMatrix()

	#Y
	glColor3f(0, 1, 0)
	glPushMatrix()
	glTranslate(0, 23, 0)
	ResetMatrixRotationAndScale()
	glBegin(GL_LINES)
	glVertex3f(-0.8, 1, 0)
	glVertex3f(0.0, 0, 0)
	glVertex3f(0.8, 1, 0)
	glVertex3f(-0.8, -1, 0)
	glEnd()
	glPopMatrix()

	#Z
	if not noZ:
		glColor3f(0, 0, 1)
		glPushMatrix()
		glTranslate(0, 0, 23)
		ResetMatrixRotationAndScale()
		glBegin(GL_LINES)
		glVertex3f(-0.8, 1, 0)
		glVertex3f(0.8, 1, 0)
		glVertex3f(0.8, 1, 0)
		glVertex3f(-0.8, -1, 0)
		glVertex3f(-0.8, -1, 0)
		glVertex3f(0.8, -1, 0)
		glEnd()
		glPopMatrix()

	glPopMatrix()
	glEnable(GL_DEPTH_TEST)


def ResetMatrixRotationAndScale():
	matrix = glGetFloatv(GL_MODELVIEW_MATRIX)
	noZ = False
	if matrix[3][2] > 0:
		return False
	scale2D = matrix[0][0]
	matrix[0][0] = 1.0
	matrix[1][0] = 0.0
	matrix[2][0] = 0.0
	matrix[0][1] = 0.0
	matrix[1][1] = 1.0
	matrix[2][1] = 0.0
	matrix[0][2] = 0.0
	matrix[1][2] = 0.0
	matrix[2][2] = 1.0

	if matrix[3][2] != 0.0:
		matrix[3][0] = matrix[3][0] / (-matrix[3][2] / 100)
		matrix[3][1] = matrix[3][1] / (-matrix[3][2] / 100)
		matrix[3][2] = -100
	else:
		matrix[0][0] = scale2D
		matrix[1][1] = scale2D
		matrix[2][2] = scale2D
		matrix[3][2] = -100
		noZ = True

	glLoadMatrixf(matrix)
	return noZ


def DrawBox(vMin, vMax):
	glBegin(GL_LINE_LOOP)
	glVertex3f(vMin[0], vMin[1], vMin[2])
	glVertex3f(vMax[0], vMin[1], vMin[2])
	glVertex3f(vMax[0], vMax[1], vMin[2])
	glVertex3f(vMin[0], vMax[1], vMin[2])
	glEnd()

	glBegin(GL_LINE_LOOP)
	glVertex3f(vMin[0], vMin[1], vMax[2])
	glVertex3f(vMax[0], vMin[1], vMax[2])
	glVertex3f(vMax[0], vMax[1], vMax[2])
	glVertex3f(vMin[0], vMax[1], vMax[2])
	glEnd()
	glBegin(GL_LINES)
	glVertex3f(vMin[0], vMin[1], vMin[2])
	glVertex3f(vMin[0], vMin[1], vMax[2])
	glVertex3f(vMax[0], vMin[1], vMin[2])
	glVertex3f(vMax[0], vMin[1], vMax[2])
	glVertex3f(vMax[0], vMax[1], vMin[2])
	glVertex3f(vMax[0], vMax[1], vMax[2])
	glVertex3f(vMin[0], vMax[1], vMin[2])
	glVertex3f(vMin[0], vMax[1], vMax[2])
	glEnd()


def DrawMeshOutline(mesh):
	glEnable(GL_CULL_FACE)
	glEnableClientState(GL_VERTEX_ARRAY);
	glVertexPointer(3, GL_FLOAT, 0, mesh.vertexes)

	glCullFace(GL_FRONT)
	glLineWidth(3)
	glPolygonMode(GL_BACK, GL_LINE)
	glDrawArrays(GL_TRIANGLES, 0, mesh.vertexCount)
	glPolygonMode(GL_BACK, GL_FILL)
	glCullFace(GL_BACK)

	glDisableClientState(GL_VERTEX_ARRAY)


def DrawMesh(mesh):
	glEnable(GL_CULL_FACE)
	glEnableClientState(GL_VERTEX_ARRAY);
	glEnableClientState(GL_NORMAL_ARRAY);
	glVertexPointer(3, GL_FLOAT, 0, mesh.vertexes)
	glNormalPointer(GL_FLOAT, 0, mesh.normal)

	#Odd, drawing in batchs is a LOT faster then drawing it all at once.
	batchSize = 999    #Warning, batchSize needs to be dividable by 3
	extraStartPos = int(mesh.vertexCount / batchSize) * batchSize
	extraCount = mesh.vertexCount - extraStartPos

	glCullFace(GL_BACK)
	for i in xrange(0, int(mesh.vertexCount / batchSize)):
		glDrawArrays(GL_TRIANGLES, i * batchSize, batchSize)
	glDrawArrays(GL_TRIANGLES, extraStartPos, extraCount)

	glCullFace(GL_FRONT)
	glNormalPointer(GL_FLOAT, 0, mesh.invNormal)
	for i in xrange(0, int(mesh.vertexCount / batchSize)):
		glDrawArrays(GL_TRIANGLES, i * batchSize, batchSize)
	extraStartPos = int(mesh.vertexCount / batchSize) * batchSize
	extraCount = mesh.vertexCount - extraStartPos
	glDrawArrays(GL_TRIANGLES, extraStartPos, extraCount)
	glCullFace(GL_BACK)

	glDisableClientState(GL_VERTEX_ARRAY)
	glDisableClientState(GL_NORMAL_ARRAY);


def DrawMeshSteep(mesh, angle):
	cosAngle = math.sin(angle / 180.0 * math.pi)
	glDisable(GL_LIGHTING)
	glDepthFunc(GL_EQUAL)
	for i in xrange(0, int(mesh.vertexCount), 3):
		if mesh.normal[i][2] < -0.999999:
			if mesh.vertexes[i + 0][2] > 0.01:
				glColor3f(0.5, 0, 0)
				glBegin(GL_TRIANGLES)
				glVertex3f(mesh.vertexes[i + 0][0], mesh.vertexes[i + 0][1], mesh.vertexes[i + 0][2])
				glVertex3f(mesh.vertexes[i + 1][0], mesh.vertexes[i + 1][1], mesh.vertexes[i + 1][2])
				glVertex3f(mesh.vertexes[i + 2][0], mesh.vertexes[i + 2][1], mesh.vertexes[i + 2][2])
				glEnd()
		elif mesh.normal[i][2] < -cosAngle:
			glColor3f(-mesh.normal[i][2], 0, 0)
			glBegin(GL_TRIANGLES)
			glVertex3f(mesh.vertexes[i + 0][0], mesh.vertexes[i + 0][1], mesh.vertexes[i + 0][2])
			glVertex3f(mesh.vertexes[i + 1][0], mesh.vertexes[i + 1][1], mesh.vertexes[i + 1][2])
			glVertex3f(mesh.vertexes[i + 2][0], mesh.vertexes[i + 2][1], mesh.vertexes[i + 2][2])
			glEnd()
		elif mesh.normal[i][2] > 0.999999:
			if mesh.vertexes[i + 0][2] > 0.01:
				glColor3f(0.5, 0, 0)
				glBegin(GL_TRIANGLES)
				glVertex3f(mesh.vertexes[i + 0][0], mesh.vertexes[i + 0][1], mesh.vertexes[i + 0][2])
				glVertex3f(mesh.vertexes[i + 2][0], mesh.vertexes[i + 2][1], mesh.vertexes[i + 2][2])
				glVertex3f(mesh.vertexes[i + 1][0], mesh.vertexes[i + 1][1], mesh.vertexes[i + 1][2])
				glEnd()
		elif mesh.normal[i][2] > cosAngle:
			glColor3f(mesh.normal[i][2], 0, 0)
			glBegin(GL_TRIANGLES)
			glVertex3f(mesh.vertexes[i + 0][0], mesh.vertexes[i + 0][1], mesh.vertexes[i + 0][2])
			glVertex3f(mesh.vertexes[i + 2][0], mesh.vertexes[i + 2][1], mesh.vertexes[i + 2][2])
			glVertex3f(mesh.vertexes[i + 1][0], mesh.vertexes[i + 1][1], mesh.vertexes[i + 1][2])
			glEnd()
	glDepthFunc(GL_LESS)


def DrawGCodeLayer(layer):
	filamentRadius = profile.getProfileSettingFloat('filament_diameter') / 2
	filamentArea = math.pi * filamentRadius * filamentRadius
	lineWidth = profile.getProfileSettingFloat('nozzle_size') / 2 / 10

	fillCycle = 0
	fillColorCycle = [[0.5, 0.5, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5]]
	moveColor = [0, 0, 1]
	retractColor = [1, 0, 0.5]
	supportColor = [0, 1, 1]
	extrudeColor = [1, 0, 0]
	innerWallColor = [0, 1, 0]
	skirtColor = [0, 0.5, 0.5]
	prevPathWasRetract = False

	glDisable(GL_CULL_FACE)
	for path in layer:
		if path.type == 'move':
			if prevPathWasRetract:
				c = retractColor
			else:
				c = moveColor
		zOffset = 0.01
		if path.type == 'extrude':
			if path.pathType == 'FILL':
				c = fillColorCycle[fillCycle]
				fillCycle = (fillCycle + 1) % len(fillColorCycle)
			elif path.pathType == 'WALL-INNER':
				c = innerWallColor
				zOffset = 0.02
			elif path.pathType == 'SUPPORT':
				c = supportColor
			elif path.pathType == 'SKIRT':
				c = skirtColor
			else:
				c = extrudeColor
		if path.type == 'retract':
			c = [0, 1, 1]
		if path.type == 'extrude':
			drawLength = 0.0
			prevNormal = None
			for i in xrange(0, len(path.list) - 1):
				v0 = path.list[i]
				v1 = path.list[i + 1]

				# Calculate line width from ePerDistance (needs layer thickness and filament diameter)
				dist = (v0 - v1).vsize()
				if dist > 0 and path.layerThickness > 0:
					extrusionMMperDist = (v1.e - v0.e) / dist
					lineWidth = extrusionMMperDist * filamentArea / path.layerThickness / 2 * v1.extrudeAmountMultiply

				drawLength += (v0 - v1).vsize()
				normal = (v0 - v1).cross(util3d.Vector3(0, 0, 1))
				normal.normalize()

				vv2 = v0 + normal * lineWidth
				vv3 = v1 + normal * lineWidth
				vv0 = v0 - normal * lineWidth
				vv1 = v1 - normal * lineWidth

				glBegin(GL_QUADS)
				glColor3fv(c)
				glVertex3f(vv0.x, vv0.y, vv0.z - zOffset)
				glVertex3f(vv1.x, vv1.y, vv1.z - zOffset)
				glVertex3f(vv3.x, vv3.y, vv3.z - zOffset)
				glVertex3f(vv2.x, vv2.y, vv2.z - zOffset)
				glEnd()
				if prevNormal != None:
					n = (normal + prevNormal)
					n.normalize()
					vv4 = v0 + n * lineWidth
					vv5 = v0 - n * lineWidth
					glBegin(GL_QUADS)
					glColor3fv(c)
					glVertex3f(vv2.x, vv2.y, vv2.z - zOffset)
					glVertex3f(vv4.x, vv4.y, vv4.z - zOffset)
					glVertex3f(prevVv3.x, prevVv3.y, prevVv3.z - zOffset)
					glVertex3f(v0.x, v0.y, v0.z - zOffset)

					glVertex3f(vv0.x, vv0.y, vv0.z - zOffset)
					glVertex3f(vv5.x, vv5.y, vv5.z - zOffset)
					glVertex3f(prevVv1.x, prevVv1.y, prevVv1.z - zOffset)
					glVertex3f(v0.x, v0.y, v0.z - zOffset)
					glEnd()

				prevNormal = normal
				prevVv1 = vv1
				prevVv3 = vv3
		else:
			glBegin(GL_LINE_STRIP)
			glColor3fv(c)
			for v in path.list:
				glVertex3f(v.x, v.y, v.z)
			glEnd()
		if not path.type == 'move':
			prevPathWasRetract = False
		if path.type == 'retract' and path.list[0].almostEqual(path.list[-1]):
			prevPathWasRetract = True
	glEnable(GL_CULL_FACE)
