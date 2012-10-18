
import stl
import obj
import dae

def supportedExtensions():
	return ['.stl', '.obj', '.dae']

def wildcardFilter():
	wildcardList = ';'.join(map(lambda s: '*' + s, supportedExtensions()))
	return "Mesh files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())

def loadMesh(filename):
	ext = filename[filename.rfind('.'):].lower()
	if ext == '.stl':
		return stl.stlModel().load(filename)
	if ext == '.obj':
		return obj.objModel().load(filename)
	if ext == '.dae':
		return dae.daeModel().load(filename)
	print 'Error: Unknown model extension: %s' % (ext)
	return None

