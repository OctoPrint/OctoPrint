# bring reprap to temperature
# Frank Davies
import serial
import time
import sys

def out_rep(out_string):
   ser.write(out_string)
   print out_string
   #print "waiting for OK"
   start_time=time.clock()
   while (ser.inWaiting()==0) and (time.clock()<start_time+40):
      c=2
   line=ser.readline() # read a '\n' terminated line
   #print "02:",line
   return(0)

print "starting"

ser=serial.Serial('/dev/ttyUSB0',19200,timeout = 1)

print "wait 1 seconds for serial port to settle"
time.sleep(1)

print "sending termperature command\n"
ser.write("M104 S230\n") # set initial temperature
time.sleep(1)
ser.write("M104 S230\n") # set initial temperature

line=ser.readline() 

# read temperature until it is good
t=0

while (t<225):

   ser.write("M105\n") # set initial temperature
   while (ser.inWaiting()==0):
      t=t
   line1=ser.readline() # read a '\n' terminated line
   #print "line1:",line1
   line2=line1[(line1.find(":")+1):]
   #print "line2:",line2
   t=int(line2)
   print "t:",t

#ser.close	
