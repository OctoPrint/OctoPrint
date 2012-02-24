from __future__ import absolute_import
import __init__

SUCCESS = 0
WARNING = 1
ERROR   = 2

class validFloat():
	def __init__(self, ctrl, minValue = None, maxValue = None):
		self.ctrl = ctrl
		self.ctrl.main.validators.append(self)
		self.minValue = minValue
		self.maxValue = maxValue
	
	def validate(self):
		try:
			f = float(self.ctrl.GetValue())
			if self.minValue != None and f < self.minValue:
				return ERROR, 'Should not be below ' + str(self.minValue)
			if self.maxValue != None and f > self.maxValue:
				return ERROR, 'Should not be above ' + str(self.maxValue)
			return SUCCESS, ''
		except ValueError:
			return ERROR, 'Not a valid number'

class validInt():
	def __init__(self, ctrl, minValue = None, maxValue = None):
		self.ctrl = ctrl
		self.ctrl.main.validators.append(self)
		self.minValue = minValue
		self.maxValue = maxValue
	
	def validate(self):
		try:
			f = int(self.ctrl.GetValue())
			if self.minValue != None and f < self.minValue:
				return ERROR, 'Should not be below ' + str(self.minValue)
			if self.maxValue != None and f > self.maxValue:
				return ERROR, 'Should not be above ' + str(self.maxValue)
			return SUCCESS, ''
		except ValueError:
			return ERROR, 'Not a valid number'

