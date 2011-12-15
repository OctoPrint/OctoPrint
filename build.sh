#!/bin/sh

7z > /dev/null 2>&1
if [ $? != 0 ]; then
	echo $0 requires 7zip to run.
	exit 1
fi

#Get portable python and extract it.
if [ ! -f "PortablePython_2.7.2.1.exe" ]; then
	wget http://ftp.nluug.nl/languages/python/portablepython/v2.7/PortablePython_2.7.2.1.exe
fi
if [ ! -d target/python ]; then
	7z x PortablePython_2.7.2.1.exe \$_OUTDIR/App
	7z x PortablePython_2.7.2.1.exe \$_OUTDIR/Lib/site-packages/wx-2.8-msw-unicode
	mkdir -p target/python
	mv \$_OUTDIR/App/* target/python
	mv \$_OUTDIR/Lib target/python
	rm -rf \$_OUTDIR
fi

#Get pypy and extract it
if [ ! -f "pypy-1.7-win32.zip" ]; then
	wget https://bitbucket.org/pypy/pypy/downloads/pypy-1.7-win32.zip
fi
if [ ! -d target/pypy-1.7 ]; then
	mkdir -p target/pypy-1.7
	cd target
	7z x ../pypy-1.7-win32.zip
	cd ..
fi

for NR in `ls patches`; do
	if [ ! -f "${NR}_reprap_python_beanshell.zip" ]; then
		wget http://fabmetheus.crsndoo.com/files/${NR}_reprap_python_beanshell.zip
	fi
	if [ ! -d "ori/${NR}" ]; then
		mkdir -p ori/${NR}
		cd ori/${NR}
		7z x ../../${NR}_reprap_python_beanshell.zip
		cd ../..
	fi
	rm -rf target/SF${NR}
	cp -a ori/${NR} target/SF${NR}
	cd target/SF${NR}
	patch -p 2 < ../../patches/${NR}
	cd ../..
	echo "python/python.exe SF${NR}/skeinforge_application/skeinforge.py" > target/SF${NR}.bat
	echo $NR
done

cd target
7z a ../Skeinforge_PyPy.zip *
cd ..

