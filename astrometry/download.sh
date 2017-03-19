#!/usr/bin/env sh

echo 'This file will download a set of index files for astrometry-net'
echo '--------------------------------'
cd install/data
for i in `seq -f %02g 0 1 11`; do
    wget -c data.astrometry.net/4200/index-4207-${i}.fits
done
