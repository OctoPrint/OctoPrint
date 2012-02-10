import Image, ImageDraw, ImageChops
from GifImagePlugin import getheader, getdata
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

# Get the double value of the word after the first occurence of the letter in the split line.
def getDoubleForLetter(letter, splitLine):
    return getDoubleAfterFirstLetter( splitLine[ getIndexOfStartingWithSecond(letter, splitLine) ] )

# Get index of the first occurence of the given letter in the split line, starting with the second word.  Return - 1 if letter is not found
def getIndexOfStartingWithSecond(letter, splitLine):
    for wordIndex in xrange( 1, len(splitLine) ):
        word = splitLine[ wordIndex ]
        firstLetter = word[0]
        if firstLetter == letter:
            return wordIndex
    return - 1

# straightforward delta encoding taken from gifmaker.py
def makedelta(fp, sequence):
    """Convert list of image frames to a GIF animation file"""
    previous = None
    for im in sequence:
        if not previous:
            # global header
            for s in getheader(im) + getdata(im):
                fp.write(s)
        else:
            # delta frame
            delta = ImageChops.subtract_modulo(im, previous)
            bbox = delta.getbbox()
            if not bbox:
                bbox = (0,0, 1,1)
            # compress difference
            for s in getdata(im.crop(bbox), offset = bbox[:2]):
                fp.write(s)
        previous = im.copy()
    fp.write(";")



class g2gif:
    def __init__(self,fileName, outfile):
        self.last_pos = Vector3()
        self.last_pos.z = 999
        self.do_move = 1
        fileText = getFileText(fileName)
        textLines = getTextLines(fileText)
        self.images = []
        self.image = None
        for line in textLines:
            self.parseLine(line)
        self.images.append(self.image)
        # write GIF animation
        fp = open(outfile, "wb")
        makedelta(fp, self.images)
        fp.close()


    def parseLine(self, line):
        splitLine = line.split(' ')
        if len(splitLine) < 1:
            return 0
        firstWord = splitLine[0]
        if firstWord == 'G1':
            self.linearMove(splitLine)
        if firstWord == 'M101':
            self.do_move = 1

    # Set the feedRate to the gcode split line.
    def setFeedRate( self, splitLine ):
        indexOfF = getIndexOfStartingWithSecond( "F", splitLine )
        if indexOfF > 0:
            self.feedRateMinute = getDoubleAfterFirstLetter( splitLine[indexOfF] )

    # Set a point to the gcode split line.
    def setPointComponent( self, point, splitLine ):
        point.x = getDoubleForLetter( "X", splitLine )
        point.y = getDoubleForLetter( "Y", splitLine )
        indexOfZ = getIndexOfStartingWithSecond( "Z", splitLine )
        if indexOfZ > 0:
            point.z = getDoubleAfterFirstLetter( splitLine[indexOfZ] )

    def scale( self, x, y ):
        return x * 5 + 150, - y * 5 + 100

    def linearMove( self, splitLine ):
        location = Vector3()
        self.setFeedRate(splitLine)
        self.setPointComponent( location, splitLine )
        if location.z != self.last_pos.z:
            if self.image:
                for i in xrange(10):
                    self.images.append(self.image)
            self.image = Image.new('P', (300, 200), 255)
            palette = []
            for red in xrange(8):
                for green in xrange(8):
                    for blue in xrange(4):
                        palette.extend((red * 255 / 7, green * 255 / 7, blue * 255 / 3))
            self.image.putpalette(palette)
            self.segment = 0
        else:
            if self.do_move:
                draw = ImageDraw.Draw(self.image)
                draw.line( ( self.scale( self.last_pos.x, self.last_pos.y ), self.scale( location.x, location.y ) ), fill = 192 )
                self.segment = self.segment + 1
            else:
                draw = ImageDraw.Draw(self.image)
                draw.line( ( self.scale( self.last_pos.x, self.last_pos.y ), self.scale(location.x, location.y ) ), fill = self.segment )
        self.last_pos = location
        self.do_move = 0
