#!/bin/sh

#
# Utility script for keeping track of which preference settings a file was processed
# with, by copying the current preferences to a date-tagged directory together
# with the output files.
#
# Usage: runskeinforge.sh <model.gts>
#

dir=`dirname $1`
file=`basename $1`

for s in .gts .GTS .stl .STL; do
  if [ ! `basename $file $s` = $file ]; then suffix=$s; fi
done

if [ -n $suffix ]; then
  filename=`basename $file $suffix`
  newdir=$filename-`date +%m%d%H%M`
  mkdir -p $newdir/skeinforge-prefs
  cp $1 $newdir
  cp ~/.skeinforge/*.csv $newdir/skeinforge-prefs
  python skeinforge.py $newdir/$filename$suffix
  echo $PWD/$newdir/${filename}_export.gcode
fi
