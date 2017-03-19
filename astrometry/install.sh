#!/usr/bin/env sh
echo 'This file will download and compile a local version of astrometry-net. To download index files, please'
echo ' use the download.sh script'
echo '-----------------------------------------'
wget http://astrometry.net/downloads/astrometry.net-0.70.tar.gz
tar zxvf astrometry.net-0.70.tar.gz
rm *.tar.gz
mv astrometry.net-0.70 build
cd build
make -j
mkdir install
INSTALL_DIR=/home/rprechelt/projects/seo/astrometry/install make install -j
