#!/usr/bin/python
try:
	import serial
except:
	print('You do not have pySerial installed, which is needed to control the serial port.')
	print('Information on pySerial is at:\nhttp://pyserial.wiki.sourceforge.net/pySerial')

import reprap, time, sys

#reprap.snap.printOutgoingPackets = True
#reprap.snap.printIncomingPackets = True
#reprap.snap.printFailedPackets = True
#reprap.printDebug = True

#work surface approx x 2523, y 2743

#reprap.serial = serial.Serial(0, 19200, timeout = reprap.snap.messageTimeout)
reprap.serial = serial.Serial(0, 19200, timeout = 60)

reprap.cartesian.x.active = True	# these devices are present in network
reprap.cartesian.y.active = True
reprap.cartesian.z.active = True
reprap.extruder.active = True

reprap.cartesian.x.setNotify()						
reprap.cartesian.y.setNotify()
reprap.cartesian.z.setNotify()
reprap.cartesian.x.limit = 2523
#reprap.cartesian.y.limit = 2743
reprap.cartesian.y.limit = 2000

def printPos():
	x, y, z = reprap.cartesian.getPos()
	print "Location [" + str(x) + ", " + str(y) + ", " + str(z) + "]"


print "================================================================"


########### control of cartesian frame as a whole #########

#stop all steppers
if sys.argv[1] == "stop":
	reprap.cartesian.stop()

#goto 0,0
if sys.argv[1] == "reset":
	reprap.cartesian.homeReset( 200, True )
	#time.sleep(2)
	printPos()

#print current positon
if sys.argv[1] == "pos":
	printPos()

#goto a specific location
if sys.argv[1] == "goto":
	reprap.cartesian.seek( ( int(sys.argv[2]), int(sys.argv[3]), 0 ), 200, False)
	printPos()

#goto a specific location (use sync)
if sys.argv[1] == "gotos":
	reprap.cartesian.syncSeek( ( int(sys.argv[2]), int(sys.argv[3]), 0 ), 200, False)
	printPos()

if sys.argv[1] == "power":
	reprap.cartesian.setPower( int( sys.argv[2] ) )	# This is a value from 0 to 63 (6 bits)


#test routine
if sys.argv[1] == "go":	#stepper test
	reprap.cartesian.seek( (1000, 1000, 0), 200, True )	
	time.sleep(2)
	reprap.cartesian.seek( (500, 1000, 0), 200, True )
	time.sleep(2)
	reprap.cartesian.seek( (500, 500, 0), 200, True )
	time.sleep(2)
	reprap.cartesian.seek( (10, 10, 0), 200, True )

#free motors (switch off all coils)
if sys.argv[1] == "free":
	reprap.axies.free(reprap.axisX)
	reprap.axies.free(reprap.axisY)

############## control of individual steppers #############

#spin stepper
if sys.argv[1] == "run":	# run axis
	if sys.argv[2] == "x":
		reprap.cartesian.x.forward( int(sys.argv[3]) )
	elif sys.argv[2] == "y":
		reprap.cartesian.y.forward( int(sys.argv[3]) )

#spin stepper in reverse
if sys.argv[1] == "runb":	#runb axis
	if sys.argv[2] == "x":
		reprap.axies.backward( reprap.axisX, int(sys.argv[3]) )
	elif sys.argv[2] == "y":
		reprap.axies.backward( reprap.axisY, int(sys.argv[3]) )

if sys.argv[1] == "step":
	if sys.argv[2] == "x":
		reprap.cartesian.x.forward1()
	elif sys.argv[2] == "y":
		reprap.cartesian.y.forward1()	

################# control of extruder #####################

#test extrder motor
elif sys.argv[1] == "motor":
	nn = 0
	while 1:
		if nn > 0:
			nn = 0
		else:
			nn = 150
		reprap.extruder.setMotor(reprap.CMD_REVERSE, nn)
		time.sleep(1)

elif sys.argv[1] == "getinfo":
	mtype = reprap.extruder.getModuleType()
	version = reprap.extruder.getVersion()
	print "module", mtype, "version", version

elif sys.argv[1] == "heat":
	reprap.extruder.setHeat(255, 255, 255, 255)

#setHeat(self, lowHeat, highHeat, tempTarget, tempMax

elif sys.argv[1] == "temp":
	print "Temp is ", reprap.extruder.getTemp()

elif sys.argv[1] == "setref":
	reprap.extruder.setVoltateReference( int(sys.argv[2]) )




############### scan network for devices ###################

#scan snap network
elif sys.argv[1] == "scan":
	reprap.scanNetwork()

