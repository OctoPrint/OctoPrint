import sys
try:
    import Tkinter
except:
    print('You do not have Tkinter, which is needed for the graphical interface.')
    print('Information on how to download Tkinter is at:\nwww.tcl.tk/software/tcltk/')
try:
    from layers import *
    from gRead import *
    import ImageTk
except:
    print('You do not have the Python Imaging Library, which is needed by preview and gifview to view the gcode.')
    print('The Python Imaging Library can be downloaded from:\nwww.pythonware.com/products/pil/')

class Preview:
    def __init__(self, layers):
        self.images = make_images(layers)
        self.index = 0
        size = self.images[0].size
        self.root = Tkinter.Tk()
        self.root.title("Gifscene from HydraRaptor")
        frame = Tkinter.Frame(self.root)
        frame.pack()
        self.canvas = Tkinter.Canvas(frame, width = size[0], height = size[1])
        self.canvas.pack()
        self.canvas.config(scrollregion=self.canvas.bbox(Tkinter.ALL))
        self.exit_button = Tkinter.Button(frame, text = "Exit", fg = "red", command = frame.quit)
        self.exit_button.pack(side=Tkinter.RIGHT)
        self.down_button = Tkinter.Button(frame, text = "Down", command = self.down)
        self.down_button.pack(side=Tkinter.LEFT)
        self.up_button = Tkinter.Button(frame, text = "Up", command = self.up)
        self.up_button.pack(side=Tkinter.LEFT)
        self.update()
        self.root.mainloop()

    def update(self):
        # FIXME: Somehow this fails if this is launched using the Preferences,
        # but works from the command-line.
        self.image = ImageTk.PhotoImage(self.images[self.index])
        self.canvas.create_image(0,0, anchor= Tkinter.NW, image = self.image)
        if self.index < len(self.images) - 1:
            self.up_button.config(state = Tkinter.NORMAL)
        else:
            self.up_button.config(state = Tkinter.DISABLED)
        if self.index > 0:
            self.down_button.config(state = Tkinter.NORMAL)
        else:
            self.down_button.config(state = Tkinter.DISABLED)

    def up(self):
        self.index += 1
        self.update()

    def down(self):
        self.index -= 1
        self.update()


def viewGif( fileName, gcodeText = ''):
    layers = []
    try:
        gRead(fileName, layers, gcodeText)
        Preview(layers)
    except Exception, why:
        print('Preview failed: ' + str( why ) )


if __name__ == "__main__":
    viewGif(' '.join(sys.argv[1 :]))
