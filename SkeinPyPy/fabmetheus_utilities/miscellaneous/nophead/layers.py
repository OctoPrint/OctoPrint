from vector3 import Vector3
import Image, ImageDraw

def bounding_cube(layers):
    min_x = 999999
    min_y = 999999
    min_z = 999999
    max_x = -999999
    max_y = -999999
    max_z = -999999
    for layer in layers:
        for thread in layer:
            for point in thread:
                if point.x > max_x:
                    max_x = point.x
                if point.y > max_y:
                    max_y = point.y
                if point.z > max_z:
                    max_z = point.z
                if point.x < min_x:
                    min_x = point.x
                if point.y < min_y:
                    min_y = point.y
                if point.z < min_z:
                    min_z = point.z
    return Vector3(min_x, min_y, min_z), Vector3(max_x, max_y, max_z)

def make_images(layers):
    palette = []
    for i in xrange(256):
        #resistor colour codes
        if i == 1:
            palette.extend((134, 100,  57)) # brown
        elif i == 2:
            palette.extend((255,   0,   0)) # red
        elif i == 3:
            palette.extend((218,  90,  35)) # orange
        elif i == 4:
            palette.extend((255, 255,   0)) # yellow
        elif i == 5:
            palette.extend((  0, 255,   0)) # green
        elif i == 6:
            palette.extend((  0,   0, 255)) # blue
        elif i == 7:
            palette.extend((255,   0, 255)) # purple
        else:
            palette.extend((i, i, i))       # shades of grey
    cube = bounding_cube(layers)
    scale = 10
    x0 = int(cube[0].x) - 1
    y0 = int(cube[0].y) - 1
    width  = int(round(cube[1].x - x0) + 1) * scale
    height = int(round(cube[1].y - y0) + 1) * scale
    last_pos = None
    images = []
    for layer in layers:
        image = Image.new('P', (width, height), 255)
        image.putpalette(palette)
        draw = ImageDraw.Draw(image)
        segment = 0
        for thread in layer:
            if last_pos != None:
                draw.line(((( last_pos.x - x0) * scale, height - ( last_pos.y - y0) * scale),
                           ((thread[0].x - x0) * scale, height - (thread[0].y - y0) * scale)), fill = 128)
            last_pos = thread[0].copy()
            for point in thread[1:]:
                draw.line((((last_pos.x - x0) * scale, height - (last_pos.y - y0) * scale),
                          ( (point.x    - x0) * scale, height - (point.y    - y0) * scale)), fill = segment % 8)
                last_pos = point.copy()
            segment = segment + 1
        images.append(image)
    return images
