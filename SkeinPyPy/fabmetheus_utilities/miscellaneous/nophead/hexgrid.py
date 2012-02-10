import math

# root parameters
drillDiameter = 25.4 / 16.0 # 1/16 of an inch
separationMultiplier = 2.5
safetyMultiplier = 1.0
bottomLeft = complex( - 10.0, - 10.0 )
topRight = complex( 10.0, 10.0 )

# derived parameters
separation = drillDiameter * separationMultiplier
horizontalSeparation = separation * math.cos( math.radians( 30.0 ) )
oddRowOffset = separation * math.sin( math.radians( 30.0 ) )
safetyMargin = complex( separation, separation ) * safetyMultiplier
safeBottomLeft = bottomLeft + safetyMargin
safeTopRight = topRight - safetyMargin

# generate drill locations
drillLocation = safeBottomLeft * 1.0
offset = 0.0
while drillLocation.imag < safeTopRight.imag:
	print('')
	while drillLocation.real < safeTopRight.real:
		print(drillLocation)
		drillLocation = complex( drillLocation.real + separation, drillLocation.imag )
	offset = oddRowOffset - offset
	drillLocation = complex( safeBottomLeft.real + offset, drillLocation.imag + horizontalSeparation )
print('')
