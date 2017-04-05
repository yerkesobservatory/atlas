#!/usr/bin/env sh
echo 'This file will download and compile a local version of astrometry-net. To download index files, please'
echo ' use the download.sh script'
echo '-----------------------------------------'
wget http://astrometry.net/downloads/astrometry.net-0.70.tar.gz
tar zxvf astrometry.net-0.70.tar.gz
rm *.tar.gz
mv astrometry.net-0.70 build
cd build
make -ji || true # continue even if errors occur as it tries to build optional components
mkdir install
INSTALL_DIR=`pwd`/../install make install -j
cd ../install/data/
for i in `seq -f %02g 0 1 11`; do
    wget -c data.astrometry.net/4200/index-4207-${i}.fits
done
