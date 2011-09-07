#!/usr/bin/python
import sys
import zipfile

zip = zipfile.ZipFile(sys.argv[1], 'r')
for name in zip.namelist():
	info = zip.getinfo(name)
	print "%s: %d == %o" % (name, info.external_attr, info.external_attr >> 16L)
