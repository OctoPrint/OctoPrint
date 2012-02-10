"""
This page is in the table of contents.
Viewpoint rotate is a mouse tool to rotate the viewpoint around the origin.

When the mouse is clicked, dragged and released on the canvas, viewpoint rotate will rotate the longitude by the amount the mouse is dragged around the origin.  If the mouse is moved towards the origin, the latitude will be increased, so the viewpoint will be closer to the top.  If the mouse is moved away from the origin, the latitude will be decreased.  If the shift key is also pressed, only the latitude or longitude will be changed, whichever is being changed the most.

When the viewpoint rotate tool is chosen and the canvas has the focus, viewpoint rotate will listen to the arrow keys.  Clicking in the canvas gives the canvas the focus, and when the canvas has the focus a thick black border is drawn around the canvas.  When the right arrow key is pressed, viewpoint rotate will increase the preview longitude by one degree.  When the left arrow key is pressed, the preview longitude will be decreased.  The up arrow key increase the preview latitude by one degree and the down arow decreases the preview latitude.  Pressing the <Return> key implements the preview.

"""

from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from skeinforge_application.skeinforge_plugins.analyze_plugins.analyze_utilities.mouse_tool_base import MouseToolBase
from fabmetheus_utilities.vector3 import Vector3
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import settings
import math

__author__ = 'Enrique Perez (perez_enrique@yahoo.com)'
__date__ = '$Date: 2008/21/04 $'
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def getBoundedLatitude( latitude ):
	"Get the bounded latitude.later get rounded"
	return round( min( 179.9, max( 0.1, latitude ) ), 1 )

def getNewMouseTool():
	"Get a new mouse tool."
	return ViewpointRotate()


class LatitudeLongitude:
	"A latitude and longitude."
	def __init__( self, buttonOnePressedCanvasCoordinate, newCoordinate, skeinWindow, shift ):
		"Set the latitude and longitude."
		buttonOnePressedCentered = skeinWindow.getCenteredScreened( buttonOnePressedCanvasCoordinate )
		buttonOnePressedRadius = abs( buttonOnePressedCentered )
		buttonOnePressedComplexMirror = complex( buttonOnePressedCentered.real, - buttonOnePressedCentered.imag )
		buttonOneReleasedCentered = skeinWindow.getCenteredScreened( newCoordinate )
		buttonOneReleasedRadius = abs( buttonOneReleasedCentered )
		pressedReleasedRotationComplex = buttonOneReleasedCentered * buttonOnePressedComplexMirror
		self.deltaLatitude = math.degrees( buttonOneReleasedRadius - buttonOnePressedRadius )
		self.originalDeltaLongitude = math.degrees( math.atan2( pressedReleasedRotationComplex.imag, pressedReleasedRotationComplex.real ) )
		self.deltaLongitude = self.originalDeltaLongitude
		if skeinWindow.repository.viewpointLatitude.value > 90.0:
			self.deltaLongitude = - self.deltaLongitude
		if shift:
			if abs( self.deltaLatitude ) > abs( self.deltaLongitude ):
				self.deltaLongitude = 0.0
			else:
				self.deltaLatitude = 0.0
		self.latitude = getBoundedLatitude( skeinWindow.repository.viewpointLatitude.value + self.deltaLatitude )
		self.longitude = round( ( skeinWindow.repository.viewpointLongitude.value + self.deltaLongitude ) % 360.0, 1 )


class ViewpointRotate( MouseToolBase ):
	"Display the line when it is clicked."
	def button1( self, event, shift = False ):
		"Print line text and connection line."
		self.destroyEverything()
		x = self.canvas.canvasx(event.x)
		y = self.canvas.canvasy(event.y)
		self.buttonOnePressedCanvasCoordinate = complex(x, y)

	def buttonRelease1( self, event, shift = False ):
		"The left button was released, <ButtonRelease-1> function."
		if self.buttonOnePressedCanvasCoordinate == None:
			return
		x = self.canvas.canvasx(event.x)
		y = self.canvas.canvasy(event.y)
		buttonOneReleasedCanvasCoordinate = complex(x, y)
		self.moveViewpointGivenCoordinates( buttonOneReleasedCanvasCoordinate, shift, self.buttonOnePressedCanvasCoordinate )

	def destroyEverything(self):
		"Destroy items."
		self.buttonOnePressedCanvasCoordinate = None
		self.keyStartCanvasCoordinate = None
		self.relativeLatitude = 0.0
		self.relativeLongitude = 0.5 * math.pi
		self.canvas.delete('mouse_item')

	def getMoveCoordinate(self):
		"Get the movement coordinate from the class relative latitude and longitude."
		motionRadius = ( 0.75 + self.relativeLatitude ) * self.window.getCanvasRadius()
		return self.window.getScreenComplex( motionRadius * euclidean.getWiddershinsUnitPolar( self.relativeLongitude ) )

	def keyPressDown(self, event):
		"The down arrow was pressed."
		self.keyPressStart()
		self.relativeLatitude -= math.radians(1.0)
		self.keyPressMotion()

	def keyPressLeft(self, event):
		"The left arrow was pressed."
		self.keyPressStart()
		self.relativeLongitude += math.radians(1.0)
		self.keyPressMotion()

	def keyPressMotion(self):
		"Move the motion viewpoint for the class key press coordinates."
		self.motionGivenCoordinates( self.getMoveCoordinate(), False, self.keyStartCanvasCoordinate )

	def keyPressReturn(self, event):
		"The return key was pressed."
		if self.keyStartCanvasCoordinate == None:
			return
		self.moveViewpointGivenCoordinates( self.getMoveCoordinate(), False, self.keyStartCanvasCoordinate )

	def keyPressRight(self, event):
		"The right arrow was pressed."
		self.keyPressStart()
		self.relativeLongitude -= math.radians(1.0)
		self.keyPressMotion()

	def keyPressStart(self):
		"If necessary, destroy everything and calculate the keyStartCanvasCoordinate."
		if self.keyStartCanvasCoordinate == None:
			self.destroyEverything()
			self.keyStartCanvasCoordinate = self.window.getScreenComplex( complex( 0.0, 0.75 * self.window.getCanvasRadius() ) )

	def keyPressUp(self, event):
		"The up arrow was pressed."
		self.keyPressStart()
		self.relativeLatitude += math.radians(1.0)
		self.keyPressMotion()

	def motion( self, event, shift = False ):
		"Move the motion viewpoint if the mouse was moved."
		if self.buttonOnePressedCanvasCoordinate == None:
			return
		x = self.canvas.canvasx(event.x)
		y = self.canvas.canvasy(event.y)
		motionCoordinate = complex(x, y)
		self.motionGivenCoordinates( motionCoordinate, shift, self.buttonOnePressedCanvasCoordinate )

	def motionGivenCoordinates( self, motionCoordinate, shift, startCoordinate ):
		"Move the motion viewpoint given the motion coordinates."
		latitudeLongitude = LatitudeLongitude( startCoordinate, motionCoordinate, self.window, shift )
		viewVectors = euclidean.ProjectiveSpace().getByLatitudeLongitude( latitudeLongitude.latitude, latitudeLongitude.longitude )
		motionCentered = self.window.getCentered( motionCoordinate )
		motionCenteredNormalized = motionCentered / abs( motionCentered )
		buttonOnePressedCentered = self.window.getCentered( startCoordinate )
		buttonOnePressedAngle = math.degrees( math.atan2( buttonOnePressedCentered.imag, buttonOnePressedCentered.real ) )
		buttonOnePressedLength = abs( buttonOnePressedCentered )
		buttonOnePressedCorner = complex( buttonOnePressedLength, buttonOnePressedLength )
		buttonOnePressedCornerBottomLeft = self.window.getScreenComplex( - buttonOnePressedCorner )
		buttonOnePressedCornerUpperRight = self.window.getScreenComplex( buttonOnePressedCorner )
		motionPressedStart = buttonOnePressedLength * motionCenteredNormalized
		motionPressedScreen = self.window.getScreenComplex( motionPressedStart )
		motionColorName = '#4B0082'
		motionWidth = 9
		self.canvas.delete('mouse_item')
		if abs( latitudeLongitude.deltaLongitude ) > 0.0:
			self.canvas.create_arc(
				buttonOnePressedCornerBottomLeft.real,
				buttonOnePressedCornerBottomLeft.imag,
				buttonOnePressedCornerUpperRight.real,
				buttonOnePressedCornerUpperRight.imag,
				extent = latitudeLongitude.originalDeltaLongitude,
				start = buttonOnePressedAngle,
				outline = motionColorName,
				outlinestipple = self.window.motionStippleName,
				style = settings.Tkinter.ARC,
				tags = 'mouse_item',
				width = motionWidth )
		if abs( latitudeLongitude.deltaLatitude ) > 0.0:
			self.canvas.create_line(
				motionPressedScreen.real,
				motionPressedScreen.imag,
				motionCoordinate.real,
				motionCoordinate.imag,
				fill = motionColorName,
				arrow = 'last',
				arrowshape = self.window.arrowshape,
				stipple = self.window.motionStippleName,
				tags = 'mouse_item',
				width = motionWidth )
		self.window.getDrawnLineText( motionCoordinate, 'mouse_item', 'Latitude: %s, Longitude: %s' % ( round( latitudeLongitude.latitude ), round( latitudeLongitude.longitude ) ) )
		if self.repository.widthOfAxisPositiveSide.value > 0:
			self.window.getDrawnColoredLineMotion( self.window.positiveAxisLineX, viewVectors, self.repository.widthOfAxisPositiveSide.value )
			self.window.getDrawnColoredLineMotion( self.window.positiveAxisLineY, viewVectors, self.repository.widthOfAxisPositiveSide.value )
			self.window.getDrawnColoredLineMotion( self.window.positiveAxisLineZ, viewVectors, self.repository.widthOfAxisPositiveSide.value )

	def moveViewpointGivenCoordinates( self, moveCoordinate, shift, startCoordinate ):
		"Move the viewpoint given the move coordinates."
		if abs( startCoordinate - moveCoordinate ) < 3:
			startCoordinate = None
			self.canvas.delete('mouse_item')
			return
		latitudeLongitude = LatitudeLongitude( startCoordinate, moveCoordinate, self.window, shift )
		self.repository.viewpointLatitude.value = latitudeLongitude.latitude
		self.repository.viewpointLatitude.setStateToValue()
		self.repository.viewpointLongitude.value = latitudeLongitude.longitude
		self.repository.viewpointLongitude.setStateToValue()
		startCoordinate = None
		settings.writeSettings(self.repository)
		self.window.update()
		self.destroyEverything()
