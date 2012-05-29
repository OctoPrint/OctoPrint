from __future__ import absolute_import
import __init__

import wx, os, platform, types, webbrowser, math, subprocess, threading, time, re
import ConfigParser

from wx import glcanvas
import wx
try:
	import OpenGL
	OpenGL.ERROR_CHECKING = False
	from OpenGL.GLU import *
	from OpenGL.GL import *
	hasOpenGLlibs = True
except:
	print "Failed to find PyOpenGL: http://pyopengl.sourceforge.net/"
	hasOpenGLlibs = False

from gui import opengl
from gui import toolbarUtil
from gui import icon
from gui import configBase
from gui import validators
from gui import printWindow
from util import profile
from util import util3d
from util import stl
from util import sliceRun
from util import gcodeInterpreter
from util import exporer

class Action(object):
	pass

class ProjectObject(stl.stlModel):
	def __init__(self, parent, filename):
		super(ProjectObject, self).__init__()

		self.load(filename)

		self.parent = parent
		self.filename = filename
		self.scale = 1.0
		self.rotate = 0.0
		self.flipX = False
		self.flipY = False
		self.flipZ = False
		self.swapXZ = False
		self.swapYZ = False
		self.extruder = 0
		self.profile = None
		
		self.modelDisplayList = None
		self.modelDirty = False

		self.origonalVertexes = list(self.vertexes)
		for i in xrange(0, len(self.origonalVertexes)):
			self.origonalVertexes[i] = self.origonalVertexes[i].copy()
		self.getMinimumZ()
		
		self.centerX = -self.getMinimum().x + 5
		self.centerY = -self.getMinimum().y + 5
		
		self.updateModelTransform()

		self.centerX = -self.getMinimum().x + 5
		self.centerY = -self.getMinimum().y + 5

	def isSameExceptForPosition(self, other):
		if self.filename != other.filename:
			return False
		if self.scale != other.scale:
			return False
		if self.rotate != other.rotate:
			return False
		if self.flipX != other.flipX:
			return False
		if self.flipY != other.flipY:
			return False
		if self.flipZ != other.flipZ:
			return False
		if self.swapXZ != other.swapXZ:
			return False
		if self.swapYZ != other.swapYZ:
			return False
		if self.extruder != other.extruder:
			return False
		if self.profile != other.profile:
			return False
		return True

	def updateModelTransform(self):
		self.setRotateMirror(self.rotate, self.flipX, self.flipY, self.flipZ, self.swapXZ, self.swapYZ)
		self.modelDirty = True
	
	def clone(self):
		p = ProjectObject(self.parent, self.filename)

		p.centerX = self.centerX + 5
		p.centerY = self.centerY + 5
		
		p.filename = self.filename
		p.scale = self.scale
		p.rotate = self.rotate
		p.flipX = self.flipX
		p.flipY = self.flipY
		p.flipZ = self.flipZ
		p.swapXZ = self.swapXZ
		p.swapYZ = self.swapYZ
		p.extruder = self.extruder
		p.profile = self.profile
		
		p.updateModelTransform()
		
		return p
	
	def clampXY(self):
		if self.centerX < -self.getMinimum().x * self.scale + self.parent.extruderOffset[self.extruder].x:
			self.centerX = -self.getMinimum().x * self.scale + self.parent.extruderOffset[self.extruder].x
		if self.centerY < -self.getMinimum().y * self.scale + self.parent.extruderOffset[self.extruder].y:
			self.centerY = -self.getMinimum().y * self.scale + self.parent.extruderOffset[self.extruder].y
		if self.centerX > self.parent.machineSize.x + self.parent.extruderOffset[self.extruder].x - self.getMaximum().x * self.scale:
			self.centerX = self.parent.machineSize.x + self.parent.extruderOffset[self.extruder].x - self.getMaximum().x * self.scale
		if self.centerY > self.parent.machineSize.y + self.parent.extruderOffset[self.extruder].y - self.getMaximum().y * self.scale:
			self.centerY = self.parent.machineSize.y + self.parent.extruderOffset[self.extruder].y - self.getMaximum().y * self.scale

class projectPlanner(wx.Frame):
	"Main user interface window"
	def __init__(self):
		super(projectPlanner, self).__init__(None, title='Cura - Project Planner')
		
		wx.EVT_CLOSE(self, self.OnClose)
		self.panel = wx.Panel(self, -1)
		self.SetSizer(wx.BoxSizer(wx.VERTICAL))
		self.GetSizer().Add(self.panel, 1, flag=wx.EXPAND)
		#self.SetIcon(icon.getMainIcon())
		
		self.list = []
		self.selection = None

		self.machineSize = util3d.Vector3(profile.getPreferenceFloat('machine_width'), profile.getPreferenceFloat('machine_depth'), profile.getPreferenceFloat('machine_height'))
		self.headSizeMin = util3d.Vector3(profile.getPreferenceFloat('extruder_head_size_min_x'), profile.getPreferenceFloat('extruder_head_size_min_y'),0)
		self.headSizeMax = util3d.Vector3(profile.getPreferenceFloat('extruder_head_size_max_x'), profile.getPreferenceFloat('extruder_head_size_max_y'),0)

		self.extruderOffset = [
			util3d.Vector3(0,0,0),
			util3d.Vector3(profile.getPreferenceFloat('extruder_offset_x1'), profile.getPreferenceFloat('extruder_offset_y1'), 0),
			util3d.Vector3(profile.getPreferenceFloat('extruder_offset_x2'), profile.getPreferenceFloat('extruder_offset_y2'), 0),
			util3d.Vector3(profile.getPreferenceFloat('extruder_offset_x3'), profile.getPreferenceFloat('extruder_offset_y3'), 0)]

		self.toolbar = toolbarUtil.Toolbar(self.panel)

		toolbarUtil.NormalButton(self.toolbar, self.OnLoadProject, 'open.png', 'Open project')
		toolbarUtil.NormalButton(self.toolbar, self.OnSaveProject, 'save.png', 'Save project')
		self.toolbar.AddSeparator()
		group = []
		toolbarUtil.RadioButton(self.toolbar, group, 'object-3d-on.png', 'object-3d-off.png', '3D view', callback=self.On3DClick)
		toolbarUtil.RadioButton(self.toolbar, group, 'object-top-on.png', 'object-top-off.png', 'Topdown view', callback=self.OnTopClick).SetValue(True)
		self.toolbar.AddSeparator()
		toolbarUtil.NormalButton(self.toolbar, self.OnPreferences, 'preferences.png', 'Project planner preferences')
		self.toolbar.AddSeparator()
		toolbarUtil.NormalButton(self.toolbar, self.OnCutMesh, 'cut-mesh.png', 'Cut a plate STL into multiple STL files, and add those files to the project.\nNote: Splitting up plates sometimes takes a few minutes.')
		self.toolbar.AddSeparator()
		toolbarUtil.NormalButton(self.toolbar, self.OnQuit, 'exit.png', 'Close project planner')
		
		self.toolbar.Realize()

		self.toolbar2 = toolbarUtil.Toolbar(self.panel)

		toolbarUtil.NormalButton(self.toolbar2, self.OnAddModel, 'object-add.png', 'Add model')
		toolbarUtil.NormalButton(self.toolbar2, self.OnRemModel, 'object-remove.png', 'Remove model')
		self.toolbar2.AddSeparator()
		toolbarUtil.NormalButton(self.toolbar2, self.OnMoveUp, 'move-up.png', 'Move model up in print list')
		toolbarUtil.NormalButton(self.toolbar2, self.OnMoveDown, 'move-down.png', 'Move model down in print list')
		toolbarUtil.NormalButton(self.toolbar2, self.OnCopy, 'copy.png', 'Make a copy of the current selected object')
		toolbarUtil.NormalButton(self.toolbar2, self.OnSetCustomProfile, 'set-profile.png', 'Set a custom profile to be used to slice a specific object.')
		self.toolbar2.AddSeparator()
		toolbarUtil.NormalButton(self.toolbar2, self.OnAutoPlace, 'autoplace.png', 'Automaticly organize the objects on the platform.')
		toolbarUtil.NormalButton(self.toolbar2, self.OnSlice, 'slice.png', 'Slice to project into a gcode file.')
		self.toolbar2.Realize()

		self.toolbar3 = toolbarUtil.Toolbar(self.panel)
		self.mirrorX = toolbarUtil.ToggleButton(self.toolbar3, 'flip_x', 'object-mirror-x-on.png', 'object-mirror-x-off.png', 'Mirror X', callback=self.OnMirrorChange)
		self.mirrorY = toolbarUtil.ToggleButton(self.toolbar3, 'flip_y', 'object-mirror-y-on.png', 'object-mirror-y-off.png', 'Mirror Y', callback=self.OnMirrorChange)
		self.mirrorZ = toolbarUtil.ToggleButton(self.toolbar3, 'flip_z', 'object-mirror-z-on.png', 'object-mirror-z-off.png', 'Mirror Z', callback=self.OnMirrorChange)
		self.toolbar3.AddSeparator()

		# Swap
		self.swapXZ = toolbarUtil.ToggleButton(self.toolbar3, 'swap_xz', 'object-swap-xz-on.png', 'object-swap-xz-off.png', 'Swap XZ', callback=self.OnMirrorChange)
		self.swapYZ = toolbarUtil.ToggleButton(self.toolbar3, 'swap_yz', 'object-swap-yz-on.png', 'object-swap-yz-off.png', 'Swap YZ', callback=self.OnMirrorChange)
		self.toolbar3.Realize()
		
		sizer = wx.GridBagSizer(2,2)
		self.panel.SetSizer(sizer)
		self.preview = PreviewGLCanvas(self.panel, self)
		self.listbox = wx.ListBox(self.panel, -1, choices=[])
		self.addButton = wx.Button(self.panel, -1, "Add")
		self.remButton = wx.Button(self.panel, -1, "Remove")
		self.sliceButton = wx.Button(self.panel, -1, "Slice")
		self.autoPlaceButton = wx.Button(self.panel, -1, "Auto Place")
		
		sizer.Add(self.toolbar, (0,0), span=(1,1), flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(self.toolbar2, (0,1), span=(1,2), flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(self.preview, (1,0), span=(5,1), flag=wx.EXPAND)
		sizer.Add(self.listbox, (1,1), span=(1,2), flag=wx.EXPAND)
		sizer.Add(self.toolbar3, (2,1), span=(1,2), flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(self.addButton, (3,1), span=(1,1))
		sizer.Add(self.remButton, (3,2), span=(1,1))
		sizer.Add(self.sliceButton, (4,1), span=(1,1))
		sizer.Add(self.autoPlaceButton, (4,2), span=(1,1))
		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(1)
		
		self.addButton.Bind(wx.EVT_BUTTON, self.OnAddModel)
		self.remButton.Bind(wx.EVT_BUTTON, self.OnRemModel)
		self.sliceButton.Bind(wx.EVT_BUTTON, self.OnSlice)
		self.autoPlaceButton.Bind(wx.EVT_BUTTON, self.OnAutoPlace)
		self.listbox.Bind(wx.EVT_LISTBOX, self.OnListSelect)

		panel = wx.Panel(self.panel, -1)
		sizer.Add(panel, (5,1), span=(1,2))
		
		sizer = wx.GridBagSizer(2,2)
		panel.SetSizer(sizer)
		
		self.scaleCtrl = wx.TextCtrl(panel, -1, '')
		self.rotateCtrl = wx.SpinCtrl(panel, -1, '', size=(21*4,21), style=wx.SP_ARROW_KEYS)
		self.rotateCtrl.SetRange(0, 360)

		sizer.Add(wx.StaticText(panel, -1, 'Scale'), (0,0), flag=wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.scaleCtrl, (0,1), flag=wx.ALIGN_BOTTOM|wx.EXPAND)
		sizer.Add(wx.StaticText(panel, -1, 'Rotate'), (1,0), flag=wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.rotateCtrl, (1,1), flag=wx.ALIGN_BOTTOM|wx.EXPAND)

		if int(profile.getPreference('extruder_amount')) > 1:
			self.extruderCtrl = wx.ComboBox(panel, -1, '1', choices=map(str, range(1, int(profile.getPreference('extruder_amount'))+1)), style=wx.CB_DROPDOWN|wx.CB_READONLY)
			sizer.Add(wx.StaticText(panel, -1, 'Extruder'), (2,0), flag=wx.ALIGN_CENTER_VERTICAL)
			sizer.Add(self.extruderCtrl, (2,1), flag=wx.ALIGN_BOTTOM|wx.EXPAND)
			self.extruderCtrl.Bind(wx.EVT_COMBOBOX, self.OnExtruderChange)

		self.scaleCtrl.Bind(wx.EVT_TEXT, self.OnScaleChange)
		self.rotateCtrl.Bind(wx.EVT_SPINCTRL, self.OnRotateChange)

		self.SetSize((800,600))

	def OnClose(self, e):
		self.Destroy()

	def OnQuit(self, e):
		self.Close()
	
	def OnPreferences(self, e):
		prefDialog = preferencesDialog(self)
		prefDialog.Centre()
		prefDialog.Show(True)
	
	def OnCutMesh(self, e):
		dlg=wx.FileDialog(self, "Open file to cut", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("STL files (*.stl)|*.stl;*.STL")
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetPath()
			parts = stl.stlModel().load(filename).splitToParts()
			for part in parts:
				partFilename = filename[:filename.rfind('.')] + "_part%d.stl" % (parts.index(part))
				stl.saveAsSTL(part, partFilename)
				item = ProjectObject(self, partFilename)
				self.list.append(item)
				self.selection = item
				self._updateListbox()
				self.OnListSelect(None)
		self.preview.Refresh()
		dlg.Destroy()
	
	def OnSaveProject(self, e):
		dlg=wx.FileDialog(self, "Save project file", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("Project files (*.curaproject)|*.curaproject")
		if dlg.ShowModal() == wx.ID_OK:
			cp = ConfigParser.ConfigParser()
			i = 0
			for item in self.list:
				section = 'model_%d' % (i)
				cp.add_section(section)
				cp.set(section, 'filename', item.filename.encode("utf-8"))
				cp.set(section, 'centerX', str(item.centerX))
				cp.set(section, 'centerY', str(item.centerY))
				cp.set(section, 'scale', str(item.scale))
				cp.set(section, 'rotate', str(item.rotate))
				cp.set(section, 'flipX', str(item.flipX))
				cp.set(section, 'flipY', str(item.flipY))
				cp.set(section, 'flipZ', str(item.flipZ))
				cp.set(section, 'swapXZ', str(item.swapXZ))
				cp.set(section, 'swapYZ', str(item.swapYZ))
				cp.set(section, 'extruder', str(item.extruder+1))
				if item.profile != None:
					cp.set(section, 'profile', item.profile)
				i += 1
			cp.write(open(dlg.GetPath(), "w"))
		dlg.Destroy()

	def OnLoadProject(self, e):
		dlg=wx.FileDialog(self, "Open project file", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("Project files (*.curaproject)|*.curaproject")
		if dlg.ShowModal() == wx.ID_OK:
			cp = ConfigParser.ConfigParser()
			cp.read(dlg.GetPath())
			self.list = []
			i = 0
			while cp.has_section('model_%d' % (i)):
				section = 'model_%d' % (i)
				
				item = ProjectObject(self, unicode(cp.get(section, 'filename'), "utf-8"))
				item.centerX = float(cp.get(section, 'centerX'))
				item.centerY = float(cp.get(section, 'centerY'))
				item.scale = float(cp.get(section, 'scale'))
				item.rotate = float(cp.get(section, 'rotate'))
				item.flipX = cp.get(section, 'flipX') == 'True'
				item.flipY = cp.get(section, 'flipY') == 'True'
				item.flipZ = cp.get(section, 'flipZ') == 'True'
				item.swapXZ = cp.get(section, 'swapXZ') == 'True'
				item.swapYZ = cp.get(section, 'swapYZ') == 'True'
				if cp.has_option(section, 'extruder'):
					item.extuder = int(cp.get(section, 'extruder')) - 1
				if cp.has_option(section, 'profile'):
					item.profile = cp.get(section, 'profile')
				item.updateModelTransform()
				i += 1
				
				self.list.append(item)

			self.selected = self.list[0]
			self._updateListbox()			
			self.OnListSelect(None)
			self.preview.Refresh()

		dlg.Destroy()

	def On3DClick(self):
		self.preview.yaw = 30
		self.preview.pitch = 60
		self.preview.zoom = 300
		self.preview.view3D = True
		self.preview.Refresh()

	def OnTopClick(self):
		self.preview.view3D = False
		self.preview.zoom = self.machineSize.x / 2 + 10
		self.preview.offsetX = 0
		self.preview.offsetY = 0
		self.preview.Refresh()

	def OnListSelect(self, e):
		if self.listbox.GetSelection() == -1:
			return
		self.selection = self.list[self.listbox.GetSelection()]
		self.scaleCtrl.SetValue(str(self.selection.scale))
		self.rotateCtrl.SetValue(int(self.selection.rotate))
		if int(profile.getPreference('extruder_amount')) > 1:
			self.extruderCtrl.SetValue(str(self.selection.extruder+1))

		self.mirrorX.SetValue(self.selection.flipX)
		self.mirrorY.SetValue(self.selection.flipY)
		self.mirrorZ.SetValue(self.selection.flipZ)
		self.swapXZ.SetValue(self.selection.swapXZ)
		self.swapYZ.SetValue(self.selection.swapYZ)
		
		self.preview.Refresh()
	
	def OnAddModel(self, e):
		dlg=wx.FileDialog(self, "Open file to print", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
		dlg.SetWildcard("STL files (*.stl)|*.stl;*.STL")
		if dlg.ShowModal() == wx.ID_OK:
			for filename in dlg.GetPaths():
				item = ProjectObject(self, filename)
				profile.putPreference('lastFile', item.filename)
				self.list.append(item)
				self.selection = item
				self._updateListbox()
				self.OnListSelect(None)
		self.preview.Refresh()
		dlg.Destroy()
	
	def OnRemModel(self, e):
		if self.selection == None:
			return
		self.list.remove(self.selection)
		self._updateListbox()
		self.preview.Refresh()
	
	def OnMoveUp(self, e):
		if self.selection == None:
			return
		i = self.listbox.GetSelection()
		if i == 0:
			return
		self.list.remove(self.selection)
		self.list.insert(i-1, self.selection)
		self._updateListbox()
		self.preview.Refresh()

	def OnMoveDown(self, e):
		if self.selection == None:
			return
		i = self.listbox.GetSelection()
		if i == len(self.list) - 1:
			return
		self.list.remove(self.selection)
		self.list.insert(i+1, self.selection)
		self._updateListbox()
		self.preview.Refresh()
	
	def OnCopy(self, e):
		if self.selection == None:
			return
		
		item = self.selection.clone()
		self.list.append(item)
		self.selection = item
		
		self._updateListbox()
		self.preview.Refresh()
	
	def OnSetCustomProfile(self, e):
		if self.selection == None:
			return

		dlg=wx.FileDialog(self, "Select profile", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("Profile files (*.ini)|*.ini;*.INI")
		if dlg.ShowModal() == wx.ID_OK:
			self.selection.profile = dlg.GetPath()
		else:
			self.selection.profile = None
		self._updateListbox()
		dlg.Destroy()
	
	def _updateListbox(self):
		self.listbox.Clear()
		for item in self.list:
			if item.profile != None:
				self.listbox.AppendAndEnsureVisible(os.path.split(item.filename)[1] + " *")
			else:
				self.listbox.AppendAndEnsureVisible(os.path.split(item.filename)[1])
		if self.selection in self.list:
			self.listbox.SetSelection(self.list.index(self.selection))
		elif len(self.list) > 0:
			self.selection = self.list[0]
			self.listbox.SetSelection(0)
		else:
			self.selection = None
			self.listbox.SetSelection(-1)

	def OnAutoPlace(self, e):
		bestAllowedSize = int(self.machineSize.y)
		bestArea = self._doAutoPlace(bestAllowedSize)
		for i in xrange(10, int(self.machineSize.y), 10):
			area = self._doAutoPlace(i)
			if area < bestArea:
				bestAllowedSize = i
				bestArea = area
		self._doAutoPlace(bestAllowedSize)
		for item in self.list:
			item.clampXY()
		self.preview.Refresh()
	
	def _doAutoPlace(self, allowedSizeY):
		extraSizeMin = self.headSizeMin
		extraSizeMax = self.headSizeMax
		if profile.getProfileSettingFloat('skirt_line_count') > 0:
			skirtSize = profile.getProfileSettingFloat('skirt_line_count') * profile.calculateEdgeWidth() + profile.getProfileSettingFloat('skirt_gap')
			extraSizeMin = extraSizeMin + util3d.Vector3(skirtSize, skirtSize, 0)
			extraSizeMax = extraSizeMax + util3d.Vector3(skirtSize, skirtSize, 0)
		if profile.getProfileSetting('support') != 'None':
			extraSizeMin = extraSizeMin + util3d.Vector3(3.0, 0, 0)
			extraSizeMax = extraSizeMax + util3d.Vector3(3.0, 0, 0)

		if extraSizeMin.x > extraSizeMax.x:
			posX = self.machineSize.x
			dirX = -1
		else:
			posX = 0
			dirX = 1
		posY = 0
		dirY = 1
		
		minX = self.machineSize.x
		minY = self.machineSize.y
		maxX = 0
		maxY = 0
		for item in self.list:
			item.centerX = posX + item.getMaximum().x * item.scale * dirX
			item.centerY = posY + item.getMaximum().y * item.scale * dirY
			if item.centerY + item.getSize().y >= allowedSizeY:
				if dirX < 0:
					posX = minX - extraSizeMax.x - 1
				else:
					posX = maxX + extraSizeMin.x + 1
				posY = 0
				item.centerX = posX + item.getMaximum().x * item.scale * dirX
				item.centerY = posY + item.getMaximum().y * item.scale * dirY
			posY += item.getSize().y  * item.scale * dirY + extraSizeMin.y + 1
			minX = min(minX, item.centerX - item.getSize().x * item.scale / 2)
			minY = min(minY, item.centerY - item.getSize().y * item.scale / 2)
			maxX = max(maxX, item.centerX + item.getSize().x * item.scale / 2)
			maxY = max(maxY, item.centerY + item.getSize().y * item.scale / 2)
		
		for item in self.list:
			if dirX < 0:
				item.centerX -= minX / 2
			else:
				item.centerX += (self.machineSize.x - maxX) / 2
			item.centerY += (self.machineSize.y - maxY) / 2
		
		if minX < 0 or maxX > self.machineSize.x:
			return ((maxX - minX) + (maxY - minY)) * 100
		
		return (maxX - minX) + (maxY - minY)

	def OnSlice(self, e):
		put = profile.setTempOverride
		oldProfile = profile.getGlobalProfileString()

		put('model_multiply_x', '1')
		put('model_multiply_y', '1')
		put('enable_raft', 'False')
		put('add_start_end_gcode', 'False')
		put('gcode_extension', 'project_tmp')
		
		clearZ = 0
		actionList = []
		for item in self.list:
			if item.profile != None and os.path.isfile(item.profile):
				profile.loadGlobalProfile(item.profile)
			put('machine_center_x', item.centerX - self.extruderOffset[item.extruder].x)
			put('machine_center_y', item.centerY - self.extruderOffset[item.extruder].y)
			put('model_scale', item.scale)
			put('flip_x', item.flipX)
			put('flip_y', item.flipY)
			put('flip_z', item.flipZ)
			put('model_rotate_base', item.rotate)
			put('swap_xz', item.swapXZ)
			put('swap_yz', item.swapYZ)
			
			action = Action()
			action.sliceCmd = sliceRun.getSliceCommand(item.filename)
			action.centerX = item.centerX
			action.centerY = item.centerY
			action.extruder = item.extruder
			action.filename = item.filename
			clearZ = max(clearZ, item.getMaximum().z * item.scale + 5.0)
			action.clearZ = clearZ
			action.leaveResultForNextSlice = False
			action.usePreviousSlice = False
			actionList.append(action)

			if self.list.index(item) > 0 and item.isSameExceptForPosition(self.list[self.list.index(item)-1]):
				actionList[-2].leaveResultForNextSlice = True
				actionList[-1].usePreviousSlice = True

			if item.profile != None:
				profile.loadGlobalProfileFromString(oldProfile)
		
		#Restore the old profile.
		profile.resetTempOverride()
		
		dlg=wx.FileDialog(self, "Save project gcode file", os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("GCode file (*.gcode)|*.gcode")
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		resultFilename = dlg.GetPath()
		dlg.Destroy()
		
		pspw = ProjectSliceProgressWindow(actionList, resultFilename)
		pspw.extruderOffset = self.extruderOffset
		pspw.Centre()
		pspw.Show(True)
	
	def OnScaleChange(self, e):
		if self.selection == None:
			return
		try:
			self.selection.scale = float(self.scaleCtrl.GetValue())
		except ValueError:
			self.selection.scale = 1.0
		self.preview.Refresh()
	
	def OnRotateChange(self, e):
		if self.selection == None:
			return
		self.selection.rotate = float(self.rotateCtrl.GetValue())
		self.selection.updateModelTransform()
		self.preview.Refresh()

	def OnExtruderChange(self, e):
		if self.selection == None:
			return
		self.selection.extruder = int(self.extruderCtrl.GetValue()) - 1
		self.preview.Refresh()
		
	def OnMirrorChange(self):
		if self.selection == None:
			return
		self.selection.flipX = self.mirrorX.GetValue()
		self.selection.flipY = self.mirrorY.GetValue()
		self.selection.flipZ = self.mirrorZ.GetValue()
		self.selection.swapXZ = self.swapXZ.GetValue()
		self.selection.swapYZ = self.swapYZ.GetValue()
		self.selection.updateModelTransform()
		self.preview.Refresh()

class PreviewGLCanvas(glcanvas.GLCanvas):
	def __init__(self, parent, projectPlannerWindow):
		attribList = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24, glcanvas.WX_GL_STENCIL_SIZE, 8)
		glcanvas.GLCanvas.__init__(self, parent, attribList = attribList)
		self.parent = projectPlannerWindow
		self.context = glcanvas.GLContext(self)
		wx.EVT_PAINT(self, self.OnPaint)
		wx.EVT_SIZE(self, self.OnSize)
		wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
		wx.EVT_LEFT_DOWN(self, self.OnMouseLeftDown)
		wx.EVT_MOTION(self, self.OnMouseMotion)
		wx.EVT_MOUSEWHEEL(self, self.OnMouseWheel)
		self.yaw = 30
		self.pitch = 60
		self.zoom = self.parent.machineSize.x / 2 + 10
		self.offsetX = 0
		self.offsetY = 0
		self.view3D = False
		self.allowDrag = False
	
	def OnMouseLeftDown(self,e):
		self.allowDrag = True
	
	def OnMouseMotion(self,e):
		if self.allowDrag and e.Dragging() and e.LeftIsDown():
			if self.view3D:
				self.yaw += e.GetX() - self.oldX
				self.pitch -= e.GetY() - self.oldY
				if self.pitch > 170:
					self.pitch = 170
				if self.pitch < 10:
					self.pitch = 10
			else:
				item = self.parent.selection
				if item != None:
					item.centerX += float(e.GetX() - self.oldX) * self.zoom / self.GetSize().GetHeight() * 2
					item.centerY -= float(e.GetY() - self.oldY) * self.zoom / self.GetSize().GetHeight() * 2
					item.clampXY()
			self.Refresh()
		else:
			self.allowDrag = False
		if e.Dragging() and e.RightIsDown():
			if self.view3D:
				self.zoom += e.GetY() - self.oldY
				if self.zoom < 1:
					self.zoom = 1
			self.Refresh()
		self.oldX = e.GetX()
		self.oldY = e.GetY()
	
	def OnMouseWheel(self,e):
		if self.view3D:
			self.zoom *= 1.0 - float(e.GetWheelRotation() / e.GetWheelDelta()) / 10.0
			if self.zoom < 1.0:
				self.zoom = 1.0
			self.Refresh()
	
	def OnEraseBackground(self,event):
		#Workaround for windows background redraw flicker.
		pass
	
	def OnSize(self,event):
		self.Refresh()

	def OnPaint(self,event):
		dc = wx.PaintDC(self)
		if not hasOpenGLlibs:
			dc.Clear()
			dc.DrawText("No PyOpenGL installation found.\nNo preview window available.", 10, 10)
			return
		self.SetCurrent(self.context)
		opengl.InitGL(self, self.view3D, self.zoom)
		if self.view3D:
			glTranslate(0,0,-self.zoom)
			glRotate(-self.pitch, 1,0,0)
			glRotate(self.yaw, 0,0,1)
			if False: #self.parent.triangleMesh != None:
				glTranslate(0,0,-self.parent.triangleMesh.getMaximum().z / 2)
		else:
			glScale(1.0/self.zoom, 1.0/self.zoom, 1.0)
			glTranslate(self.offsetX, self.offsetY, 0.0)
		glTranslate(-self.parent.machineSize.x/2, -self.parent.machineSize.y/2, 0)

		self.OnDraw()
		self.SwapBuffers()

	def OnDraw(self):
		machineSize = self.parent.machineSize
		opengl.DrawMachine(machineSize)
		extraSizeMin = self.parent.headSizeMin
		extraSizeMax = self.parent.headSizeMax
		if profile.getProfileSettingFloat('skirt_line_count') > 0:
			skirtSize = profile.getProfileSettingFloat('skirt_line_count') * profile.calculateEdgeWidth() + profile.getProfileSettingFloat('skirt_gap')
			extraSizeMin = extraSizeMin + util3d.Vector3(skirtSize, skirtSize, 0)
			extraSizeMax = extraSizeMax + util3d.Vector3(skirtSize, skirtSize, 0)

		for item in self.parent.list:
			item.validPlacement = True
			item.gotHit = False
		
		for idx1 in xrange(0, len(self.parent.list)):
			item = self.parent.list[idx1]
			iMin1 = item.getMinimum() * item.scale + util3d.Vector3(item.centerX, item.centerY, 0) - extraSizeMin - self.parent.extruderOffset[item.extruder]
			iMax1 = item.getMaximum() * item.scale + util3d.Vector3(item.centerX, item.centerY, 0) + extraSizeMax - self.parent.extruderOffset[item.extruder]
			for idx2 in xrange(0, idx1):
				item2 = self.parent.list[idx2]
				iMin2 = item2.getMinimum() * item2.scale + util3d.Vector3(item2.centerX, item2.centerY, 0)
				iMax2 = item2.getMaximum() * item2.scale + util3d.Vector3(item2.centerX, item2.centerY, 0)
				if item != item2 and iMax1.x >= iMin2.x and iMin1.x <= iMax2.x and iMax1.y >= iMin2.y and iMin1.y <= iMax2.y:
					item.validPlacement = False
					item2.gotHit = True
		
		seenSelected = False
		for item in self.parent.list:
			if item == self.parent.selection:
				seenSelected = True
			if item.modelDisplayList == None:
				item.modelDisplayList = glGenLists(1);
			if item.modelDirty:
				item.modelDirty = False
				modelSize = item.getMaximum() - item.getMinimum()
				glNewList(item.modelDisplayList, GL_COMPILE)
				opengl.DrawSTL(item)
				glEndList()
			
			if item.validPlacement:
				if self.parent.selection == item:
					glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.9, 0.7, 1.0])
					glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.3, 0.2, 0.0])
				else:
					glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.8, 0.6, 1.0])
					glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.1, 0.1, 0.0])
			else:
				if self.parent.selection == item:
					glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.0, 0.0, 0.0])
					glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.0, 0.0, 0.0])
				else:
					glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.0, 0.0, 0.0])
					glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.2, 0.0, 0.0, 0.0])
			glPushMatrix()
			
			glEnable(GL_LIGHTING)
			glTranslate(item.centerX, item.centerY, 0)
			glPushMatrix()
			glEnable(GL_NORMALIZE)
			glScalef(item.scale, item.scale, item.scale)
			glCallList(item.modelDisplayList)
			glPopMatrix()
			
			vMin = item.getMinimum() * item.scale
			vMax = item.getMaximum() * item.scale
			vMinHead = vMin - extraSizeMin - self.parent.extruderOffset[item.extruder]
			vMaxHead = vMax + extraSizeMax - self.parent.extruderOffset[item.extruder]

			glDisable(GL_LIGHTING)

			if self.parent.selection == item:
				if item.gotHit:
					glColor3f(1.0,0.0,0.3)
				else:
					glColor3f(1.0,0.0,1.0)
				opengl.DrawBox(vMin, vMax)
				if item.gotHit:
					glColor3f(1.0,0.3,0.0)
				else:
					glColor3f(1.0,1.0,0.0)
				opengl.DrawBox(vMinHead, vMaxHead)
			elif seenSelected:
				if item.gotHit:
					glColor3f(0.5,0.0,0.1)
				else:
					glColor3f(0.5,0.0,0.5)
				opengl.DrawBox(vMinHead, vMaxHead)
			else:
				if item.gotHit:
					glColor3f(0.7,0.1,0.0)
				else:
					glColor3f(0.7,0.7,0.0)
				opengl.DrawBox(vMin, vMax)
			
			glPopMatrix()
		
		glFlush()

class ProjectSliceProgressWindow(wx.Frame):
	def __init__(self, actionList, resultFilename):
		super(ProjectSliceProgressWindow, self).__init__(None, title='Cura')
		self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
		
		self.actionList = actionList
		self.resultFilename = resultFilename
		self.abort = False
		self.prevStep = 'start'
		self.totalDoneFactor = 0.0
		self.startTime = time.time()
		self.sliceStartTime = time.time()
		
		self.sizer = wx.GridBagSizer(2, 2) 
		self.statusText = wx.StaticText(self, -1, "Building: %s" % (resultFilename))
		self.progressGauge = wx.Gauge(self, -1)
		self.progressGauge.SetRange(10000)
		self.progressGauge2 = wx.Gauge(self, -1)
		self.progressGauge2.SetRange(len(self.actionList))
		self.abortButton = wx.Button(self, -1, "Abort")
		self.sizer.Add(self.statusText, (0,0), span=(1,4))
		self.sizer.Add(self.progressGauge, (1, 0), span=(1,4), flag=wx.EXPAND)
		self.sizer.Add(self.progressGauge2, (2, 0), span=(1,4), flag=wx.EXPAND)

		self.sizer.Add(self.abortButton, (3,0), span=(1,4), flag=wx.ALIGN_CENTER)
		self.sizer.AddGrowableCol(0)
		self.sizer.AddGrowableRow(0)

		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.abortButton)
		self.SetSizer(self.sizer)
		self.Layout()
		self.Fit()
		
		threading.Thread(target=self.OnRun).start()

	def OnAbort(self, e):
		if self.abort:
			self.Close()
		else:
			self.abort = True
			self.abortButton.SetLabel('Close')

	def SetProgress(self, stepName, layer, maxLayer):
		if self.prevStep != stepName:
			self.totalDoneFactor += sliceRun.sliceStepTimeFactor[self.prevStep]
			newTime = time.time()
			#print "#####" + str(newTime-self.startTime) + " " + self.prevStep + " -> " + stepName
			self.startTime = newTime
			self.prevStep = stepName
		
		progresValue = ((self.totalDoneFactor + sliceRun.sliceStepTimeFactor[stepName] * layer / maxLayer) / sliceRun.totalRunTimeFactor) * 10000
		self.progressGauge.SetValue(int(progresValue))
		self.statusText.SetLabel(stepName + " [" + str(layer) + "/" + str(maxLayer) + "]")
	
	def OnRun(self):
		resultFile = open(self.resultFilename, "w")
		put = profile.setTempOverride
		self.progressLog = []
		for action in self.actionList:
			wx.CallAfter(self.SetTitle, "Building: [%d/%d]"  % (self.actionList.index(action) + 1, len(self.actionList)))
			if not action.usePreviousSlice:
				p = subprocess.Popen(action.sliceCmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
				line = p.stdout.readline()
		
				maxValue = 1
				while(len(line) > 0):
					line = line.rstrip()
					if line[0:9] == "Progress[" and line[-1:] == "]":
						progress = line[9:-1].split(":")
						if len(progress) > 2:
							maxValue = int(progress[2])
						wx.CallAfter(self.SetProgress, progress[0], int(progress[1]), maxValue)
					else:
						print line
						self.progressLog.append(line)
						wx.CallAfter(self.statusText.SetLabel, line)
					if self.abort:
						p.terminate()
						wx.CallAfter(self.statusText.SetLabel, "Aborted by user.")
						resultFile.close()
						return
					line = p.stdout.readline()
				self.returnCode = p.wait()
			
			put('machine_center_x', action.centerX - self.extruderOffset[action.extruder].x)
			put('machine_center_y', action.centerY - self.extruderOffset[action.extruder].y)
			put('clear_z', action.clearZ)
			put('extruder', action.extruder)
			
			if action == self.actionList[0]:
				resultFile.write(';TYPE:CUSTOM\n')
				resultFile.write('T%d\n' % (action.extruder))
				currentExtruder = action.extruder
				resultFile.write(profile.getAlterationFileContents('start.gcode'))
			else:
				#reset the extrusion length, and move to the next object center.
				resultFile.write(';TYPE:CUSTOM\n')
				resultFile.write(profile.getAlterationFileContents('nextobject.gcode'))
			resultFile.write(';PRINTNR:%d\n' % self.actionList.index(action))
			profile.resetTempOverride()
			
			if not action.usePreviousSlice:
				f = open(sliceRun.getExportFilename(action.filename, "project_tmp"), "r")
				data = f.read(4096)
				while data != '':
					resultFile.write(data)
					data = f.read(4096)
				f.close()
				savedCenterX = action.centerX
				savedCenterY = action.centerY
			else:
				f = open(sliceRun.getExportFilename(action.filename, "project_tmp"), "r")
				for line in f:
					if line[0] != ';':
						if 'X' in line:
							line = self._adjustNumberInLine(line, 'X', action.centerX - savedCenterX)
						if 'Y' in line:
							line = self._adjustNumberInLine(line, 'Y', action.centerY - savedCenterY)
					resultFile.write(line)
				f.close()

			if not action.leaveResultForNextSlice:
				os.remove(sliceRun.getExportFilename(action.filename, "project_tmp"))
			
			wx.CallAfter(self.progressGauge.SetValue, 10000)
			self.totalDoneFactor = 0.0
			wx.CallAfter(self.progressGauge2.SetValue, self.actionList.index(action) + 1)
		
		resultFile.write(';TYPE:CUSTOM\n')
		resultFile.write('G1 Z%f F%f\n' % (self.actionList[-1].clearZ, profile.getProfileSettingFloat('max_z_speed') * 60))
		resultFile.write(profile.getAlterationFileContents('end.gcode'))
		resultFile.close()
		
		gcode = gcodeInterpreter.gcode()
		gcode.load(self.resultFilename)
		
		self.abort = True
		sliceTime = time.time() - self.sliceStartTime
		status = "Build: %s" % (self.resultFilename)
		status += "\nSlicing took: %02d:%02d" % (sliceTime / 60, sliceTime % 60)
		status += "\nFilament: %.2fm %.2fg" % (gcode.extrusionAmount / 1000, gcode.calculateWeight() * 1000)
		status += "\nPrint time: %02d:%02d" % (int(gcode.totalMoveTimeMinute / 60), int(gcode.totalMoveTimeMinute % 60))
		cost = gcode.calculateCost()
		if cost != False:
			status += "\nCost: %s" % (cost)
		wx.CallAfter(self.statusText.SetLabel, status)
		wx.CallAfter(self.OnSliceDone)
	
	def _adjustNumberInLine(self, line, tag, f):
		m = re.search('^(.*'+tag+')([0-9\.]*)(.*)$', line)
		return m.group(1) + str(float(m.group(2)) + f) + m.group(3) + '\n'
	
	def OnSliceDone(self):
		self.abortButton.Destroy()
		self.closeButton = wx.Button(self, -1, "Close")
		self.printButton = wx.Button(self, -1, "Print")
		self.logButton = wx.Button(self, -1, "Show log")
		self.sizer.Add(self.closeButton, (3,0), span=(1,1))
		self.sizer.Add(self.printButton, (3,1), span=(1,1))
		self.sizer.Add(self.logButton, (3,2), span=(1,1))
		if exporer.hasExporer():
			self.openFileLocationButton = wx.Button(self, -1, "Open file location")
			self.Bind(wx.EVT_BUTTON, self.OnOpenFileLocation, self.openFileLocationButton)
			self.sizer.Add(self.openFileLocationButton, (3,3), span=(1,1))
		self.Bind(wx.EVT_BUTTON, self.OnAbort, self.closeButton)
		self.Bind(wx.EVT_BUTTON, self.OnPrint, self.printButton)
		self.Bind(wx.EVT_BUTTON, self.OnShowLog, self.logButton)
		self.Layout()
		self.Fit()

	def OnOpenFileLocation(self, e):
		exporer.openExporer(self.resultFilename)
	
	def OnPrint(self, e):
		printWindow.printFile(self.resultFilename)

	def OnShowLog(self, e):
		LogWindow('\n'.join(self.progressLog))

class preferencesDialog(configBase.configWindowBase):
	def __init__(self, parent):
		super(preferencesDialog, self).__init__(title="Project Planner Preferences")
		
		self.parent = parent
		wx.EVT_CLOSE(self, self.OnClose)
		
		extruderAmount = int(profile.getPreference('extruder_amount'))
		
		left, right, main = self.CreateConfigPanel(self)
		configBase.TitleRow(left, 'Machine head size')
		c = configBase.SettingRow(left, 'Head size - X towards home (mm)', 'extruder_head_size_min_x', '0', 'Size of your printer head in the X direction, on the Ultimaker your fan is in this direction.', type = 'preference')
		validators.validFloat(c, 0.1)
		c = configBase.SettingRow(left, 'Head size - X towards end (mm)', 'extruder_head_size_max_x', '0', 'Size of your printer head in the X direction.', type = 'preference')
		validators.validFloat(c, 0.1)
		c = configBase.SettingRow(left, 'Head size - Y towards home (mm)', 'extruder_head_size_min_y', '0', 'Size of your printer head in the Y direction.', type = 'preference')
		validators.validFloat(c, 0.1)
		c = configBase.SettingRow(left, 'Head size - Y towards end (mm)', 'extruder_head_size_max_y', '0', 'Size of your printer head in the Y direction.', type = 'preference')
		validators.validFloat(c, 0.1)
		
		self.okButton = wx.Button(left, -1, 'Ok')
		left.GetSizer().Add(self.okButton, (left.GetSizer().GetRows(), 1))
		self.okButton.Bind(wx.EVT_BUTTON, self.OnClose)
		
		self.MakeModal(True)
		main.Fit()
		self.Fit()

	def OnClose(self, e):
		self.parent.headSizeMin = util3d.Vector3(profile.getPreferenceFloat('extruder_head_size_min_x'), profile.getPreferenceFloat('extruder_head_size_min_y'),0)
		self.parent.headSizeMax = util3d.Vector3(profile.getPreferenceFloat('extruder_head_size_max_x'), profile.getPreferenceFloat('extruder_head_size_max_y'),0)
		self.parent.Refresh()

		self.MakeModal(False)
		self.Destroy()

class LogWindow(wx.Frame):
	def __init__(self, logText):
		super(LogWindow, self).__init__(None, title="Slice log")
		self.textBox = wx.TextCtrl(self, -1, logText, style=wx.TE_MULTILINE|wx.TE_DONTWRAP|wx.TE_READONLY)
		self.SetSize((400,300))
		self.Centre()
		self.Show(True)

def main():
	app = wx.App(False)
	projectPlanner().Show(True)
	app.MainLoop()

if __name__ == '__main__':
	main()
