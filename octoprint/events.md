TODO: Add to config documentation

There are two types of event handlers at the moment:
  * ''systemCommandTrigger'': invokes an external command without waiting for the result
  * ''gcodeCommandTrigger'': sends some gcode to the printer.  Separate multiple commands with a comma

Example: 

    events:
        systemCommandTrigger:
            enabled: True
            subscriptions:
                - event: Disconnected
                  command: python ~/growl.py -t mygrowlserver -d "Lost connection to printer" -a OctoPrint -i http://rasppi:8080/Octoprint_logo.png
                - event: PrintStarted
                  command: python ~/growl.py -t mygrowlserver -d "Starting _FILE_" -a OctoPrint -i http://rasppi:8080/Octoprint_logo.png
                - event: PrintDone
                  command: python ~/growl.py -t mygrowlserver -d "Completed _FILE_" -a OctoPrint -i http://rasppi:8080/Octoprint_logo.png
        gcodeCommandTrigger:
            enabled: True
            subscriptions:
                - event: Connected
                  command: M115,M17 printer connected!,G28


command values support the following dynamic tokens:
  * ''%(data)s'': the data associated with the event (not all events have data, when they do, it's often a filename)
  * ''%(filename)s'': filename of the current print (not always the same as _DATA_ filename)
  * ''%(progress)s'': the progress of the print in percent
  * ''%(zheight)s'': the current Z position of the head
  * ''%(now)s'': the date and time of the event in ISO 8601

Available Events:

  * ''Startup'': the server has started
  * ''Connected'': the server has connected to the printer (data is port and baudrate)
  * ''Disconnected'': the server has disconnected from the printer
  * ''ClientOpen'': a client has connected to the web server
  * ''ClientClosed'': a client has disconnected from the web server
  * ''PowerOn'': the GCode has turned on the printer power via M80
  * ''PowerOff'': the GCode has turned on the printer power via M81
  * ''Upload'': a gcode file upload has been uploaded (data is filename)
  * ''FileSelected'': a gcode file has been selected for printing (data is filename)
  * ''TransferStart'': a gcode file transfer to SD has started (data is filename)
  * ''TransferDone'': a gcode file transfer to SD has finished (data is filename)
  * ''PrintStarted'': a print has started
  * ''PrintFailed'': a print failed
  * ''PrintDone'': a print completed successfully
  * ''Cancelled'': the print has been cancelled via the cancel button
  * ''Home'': the head has gone home via G28
  * ''ZChange'': the printer's Z-Height has changed (new layer)
  * ''Paused'': the print has been paused
  * ''Waiting'': the print is paused due to a gcode wait command
  * ''Cooling'': the GCode has enabled the platform cooler via M245
  * ''Alert'': the GCode has issued a user alert (beep) via M300
  * ''Conveyor'': the GCode has enabled the conveyor belt via M240
  * ''Eject'': the GCode has enabled the part ejector via M40
  * ''CaptureStart'': a timelapse image is starting to be captured  (data is image filename)
  * ''CaptureDone'': a timelapse image has completed being captured (data is image filename)
  * ''MovieDone'': the timelapse movie is completed (data is movie filename)
  * ''EStop'': the GCode has issued a panic stop via M112
  * ''Error'': an error has occurred (data is error string)
