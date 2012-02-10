from vector3 import Vector3

# Get the entire text of a file.
# @param  fileName name of the file
# @return  entire text of a file.
def getFileText(fileName):
    file = open( fileName, 'r')
    fileText = file.read()
    file.close()
    return fileText

# Get the all the lines of text of a text.
# @param  text text
# @return  the lines of text of a text
def getTextLines(text):
    return text.replace('\r', '\n').split('\n')

# Get the double value of the word after the first letter.
# @param  word string with value starting after the first letter
# @return  double value of the word after the first letter
def getDoubleAfterFirstLetter(word):
    return float( word[1 :] )

# Get index of the first occurence of the given letter in the split line, starting with the second word.  Return - 1 if letter is not found
def getIndexOfStartingWithSecond(letter, splitLine):
    for wordIndex in xrange( 1, len(splitLine) ):
        word = splitLine[ wordIndex ]
        firstLetter = word[0]
        if firstLetter == letter:
            return wordIndex
    return - 1


class gRead:
    def __init__(self,fileName, layers,gcodeText = ''):
        if gcodeText == '':
            gcodeText = getFileText(fileName)
        textLines = getTextLines(gcodeText)
        self.last_pos = Vector3()
        self.layers = layers
        self.layer = None
        self.thread = None
        self.skeinforge = 0
        self.max_z = -9999999999
        for line in textLines:
            self.parseLine(line)
        self.newLayer()

    def parseLine(self, line):
        if line.startswith( "(" ):
            if line.startswith( "(<layer>" ):
                self.newLayer()
            return
        splitLine = line.split()
        if len(splitLine) < 1:
            return 0
        firstWord = splitLine[0]
        if firstWord == 'G1':
            self.linearMove(splitLine)
        if firstWord == 'M110':             #filament height only sent by skeinforge at the moment
            self.skeinforge = 1
            self.newThread()
        if firstWord == 'M103':             #extruder off
            if self.skeinforge:
                self.newThread()            #end of thread if skeinforge
        if firstWord == 'G92':              #offset coordinate system
            self.newThread()                #for RepRap

    # Set a point to the gcode split line.
    def setPointComponent( self, point, splitLine ):
        indexOfX = getIndexOfStartingWithSecond( "X", splitLine )
        if indexOfX > 0:
            point.x = getDoubleAfterFirstLetter( splitLine[indexOfX] )
        indexOfY = getIndexOfStartingWithSecond( "Y", splitLine )
        if indexOfY > 0:
            point.y = getDoubleAfterFirstLetter( splitLine[indexOfY] )
        indexOfZ = getIndexOfStartingWithSecond( "Z", splitLine )
        if indexOfZ > 0:
            point.z = getDoubleAfterFirstLetter( splitLine[indexOfZ] )

    def newLayer(self):
        self.newThread()
        if self.layer:
            self.layers.append(self.layer)
        self.layer = []

    def newThread(self):
        if self.thread:
            self.layer.append(self.thread)
        self.thread = []

    def linearMove( self, splitLine ):
        if self.thread != None:
            pos = self.last_pos.copy()
            self.setPointComponent( pos, splitLine )
            if pos.z > self.max_z:
#                self.newLayer()
                self.max_z = pos.z
            if pos.z < self.last_pos.z:
                self.newThread()
            if self.skeinforge or pos.z < self.max_z:
                self.thread.append(pos)
            self.last_pos = pos
