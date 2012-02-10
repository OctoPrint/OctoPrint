#!/bin/sh
#
# Script to open the bash terminal in this directory.
#
# Usage: set the executable property to true if it isn't already.  Then double click the file.
#
echo 'Directory listing:'
echo ''
ls
echo ''
echo 'To run a python script (.py) listed above, try typing something like:'
echo 'python filename'
echo ''
echo 'For example, in the skeinforge_application directory you could run skeinforge by typing:'
echo 'python skeinforge.py'
echo ''
echo 'To skeinforge the test.stl file from the command line, in the skeinforge_application directory you could type:'
echo 'python skeinforge.py test.stl'
echo ''
echo 'To run a script in a subdirectory, append the directory path.  For example, to run skeinforge from the top directory you could type:'
echo 'python skeinforge_application/skeinforge.py'
echo ''
bash

