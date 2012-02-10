#!/usr/bin/python2.5
# encoding: utf-8
"""
Created by Brendan Erwin on 2008-05-21.
Modified by John Gilmore 2008-08-23
Copyright (c) 2008 Brendan Erwin. All rights reserved.
Copyright (c) 2008 John Gilmore.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import getopt
import RepRapArduinoSerialSender

help_message = '''
Usage:	send [options] <filename or gcode> [<filename or gcode>...]
	--verbose : Verbose - print ALL communication, not just comments.
	       -v : prints responses from the arduino, and every command sent.

	--quiet   : Quiet - don't print anything, whereas
	       -q : normally comments are printed.

	--noreset : skip the reset.
	       -n : causes the arduino to not be deliberately reset.

	--port    : Set the port to write to
	       -p : default is "/dev/ttyUSB0" for posix, "COM3" for windows.

	--baud    : Set the baud rate to use
	       -b : defaults to 19200

You may call this with either a single statement of g-code
to be sent to the arduino, or with the name of a g-code file.
------------------------------------------------------------------
Copyright (C) 2008 Brendan Erwin
Copyright (C) 2008 John Gilmore

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
#This was originally release by Brendan under GPLv2 or later



class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg

def main(argv=None):

	# Set resonable defaults for port, verbosity, and reset.
	verbose = 1
	baud = 19200
	reset = True
	if os.name == "posix":
		port = "/dev/ttyUSB0"
	elif os.name == "nt":
		port = "COM3"
	else:
		port = "/dev/ttyUSB0"

	if argv is None:
		argv = sys.argv

	try:
		try:
			opts, argv = getopt.getopt(argv[1:], "vqnhb:p:", ["verbose","quiet","noreset","help","baud=","port="])
		except getopt.error, msg:
			raise Usage(msg)

		# option processing
		for option, value in opts:
			if option in ( "-v" , "--verbose" ):
				verbose = 2
				print "You have requested that verbosity be set to True"
				print "All communication with the arduino will be printed"
			elif option in ( "-q" , "--quiet" ):
				verbose = 0
				#don't print "quiet mode on"
			elif option in ( "-n" , "--noreset" ):
				reset = False
				if verbose:
					print "Arduino will not be reset before sending gcode"
			elif option in ( "-p" , "--port" ):
				port = value
			elif option in ("-h", "--help" ):
				raise Usage(help_message)
			elif option in ("-b", "--baud" ):
					baud = int(value)

		if verbose:
			print "Arduino port set to " + port

	except Usage, err:
		#print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, str(err.msg)
		print >> sys.stderr, "For help use --help"
		return 2


	sender = RepRapArduinoSerialSender.RepRapArduinoSerialSender(port, baud, verbose>1)
	if reset:
		sender.reset()

	for filename in argv:
		processfile(filename,sender,verbose)

def processfile(filename,sender,verbose):
	try:
		datafile = open(filename)
	except IOError:
		#Ignore verbosity settings here, as if it's a typo we'll want to know.
		line=filename
		if line.lstrip().startswith(("G","X","Y","Z","M")):
			if verbose:
				print "Unable to open file \"" + line + "\", assuming it's one line of direct G-code..."
			sender.write(line)
			return 0
		else:
			print "Unable to open file \"" + line + "\""
			sys.exit(-1)

	try:
		for line in datafile:
			line=line.rstrip()
			# Ignore lines with comments (not technically correct, should ignore only the comment,
			# but all gcode files that I've actually seen so far don't have code on comment lines.
			if line.lstrip().startswith( ('(', '"' , '\\') ):
				if verbose:
					print line
				continue

			# This is the place to insert G-Code interpretation.
			# Subroutines, Variables, all sorts of fun stuff.
			# probably by calling a "gcode interpreter" class intead
			# of simply "sender".

			sender.write(line)
	finally:
		datafile.close()

	return 0

if __name__ == "__main__":
	sys.exit(main())
