try:
	import serial
except:
	print('You do not have pySerial installed, which is needed to control the serial port.')
	print('Information on pySerial is at:\nhttp://pyserial.wiki.sourceforge.net/pySerial')
import reprap, time							# Import the reprap and pySerial modules.

reprap.serial = serial.Serial(0, 19200, timeout = reprap.snap.messageTimeout)	# Initialise serial port, here the first port (0) is used.
reprap.cartesian.x.active = True						# These devices are present in network, will automatically scan in the future.
reprap.cartesian.y.active = True
reprap.cartesian.z.active = True
reprap.extruder.active = True
# The module is now ready to recieve commands #
moveSpeed = 220
reprap.cartesian.homeReset( moveSpeed, True )					# Send all axies to home position. Wait until arrival.
reprap.cartesian.seek( (1000, 1000, 0), moveSpeed, True )			# Seek to (1000, 1000, 0). Wait until arrival.
time.sleep(2)									# Pause.
reprap.cartesian.seek( (500, 1000, 0), moveSpeed, True )			# Seek to (500, 1000, 0). Wait until arrival.
time.sleep(2)
reprap.cartesian.seek( (1000, 500, 0), moveSpeed, True )			# Seek to (1000, 500, 0). Wait until arrival.
time.sleep(2)
reprap.cartesian.seek( (100, 100, 0), moveSpeed, True )				# Seek to (100, 100, 0). Wait until arrival.
reprap.cartesian.homeReset( moveSpeed, True )					# Send all axies to home position. Wait until arrival.
reprap.cartesian.free()								# Shut off power to all motors.
