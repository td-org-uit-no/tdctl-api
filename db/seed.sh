#!/usr/bin/env bash
for file in `ls seeds`; do
	echo "Seeding $file"
	collection=`echo $file | cut -d"." -f1`
	mongoimport --port 27018 --db tdctl --collection $collection --file seeds/$file --jsonArray
	echo ""
done