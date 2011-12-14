#!/bin/sh

for NR in `ls patches`; do
	if [ -d target/SF${NR} ]; then
		diff -r -x*.pyc -N -u ori/${NR}/ target/SF${NR} > patches/${NR}
	fi
done

