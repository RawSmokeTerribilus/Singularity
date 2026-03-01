
MakeMKV 1.18.3 for Linux is available

Post by mike admin » Thu Apr 09, 2009 8:51 am
Thank you for beta-testing MakeMKV. Please see https://www.makemkv.com/forum2/viewtopic.php?f=5&t=1054 for information about latest version.

The linux release includes full source code for MakeMKV GUI, libmakemkv multiplexer library and libdriveio MMC drive interrogation library. Please use this forum for an up to date download and setup instructions. You need to follow the steps outlined below to compile and install the application and all libraries.
Download both binary and source packages:
https://www.makemkv.com/download/makemk ... 8.3.tar.gz
https://www.makemkv.com/download/makemk ... 8.3.tar.gz

Make sure you have all required tools and libraries installed. You'll need GNU compiler and linker and header and library files for following libraries: glibc, openssl-0.9.8, zlib, expat, libavcodec and qt5. You may use the following command to install all prerequisites on debian-based system like ubuntu:

Code: Select all

sudo apt-get install build-essential pkg-config libc6-dev libssl-dev libexpat1-dev libavcodec-dev libgl1-mesa-dev qtbase5-dev zlib1g-dev

Unpack both packages and starting from source package do the following steps:
For makemkv-oss package:

Code: Select all

./configure
make
sudo make install

For makemkv-bin package:

Code: Select all

make
sudo make install

The application will be installed as "/usr/bin/makemkv".

OPTIONAL: Building with latest libavcodec
Starting with version 1.8.6 MakeMKV links directly to libavcodec. Please note that most distributions ship a very outdated version of libavcodec (either from ffmpeg or libav projects). You will have to compile a recent ffmpeg (at least 2.0) if you need a FLAC encoder that handles 24-bit audio. Also you will have to enable libfdk-aac support in ffmpeg in order to use AAC encoder. Starting from version 1.12.1 DTS-HD decoding is handled by ffmpeg as well, so you would need a recent one. Here are generic instructions for building makemkv-oss with latest ffmpeg:
- download ffmpeg tarball from https://ffmpeg.org/download.html
- configure and build ffmpeg:

Code: Select all

./configure --prefix=/tmp/ffmpeg --enable-static --disable-shared --enable-pic

or with libfdk-aac support

Code: Select all

./configure --prefix=/tmp/ffmpeg --enable-static --disable-shared --enable-pic --enable-libfdk-aac

followed by

Code: Select all

make install

- configure and build makemkv-oss:

Code: Select all

PKG_CONFIG_PATH=/tmp/ffmpeg/lib/pkgconfig ./configure
make
sudo make install

- remove temporary ffmpeg files:

Code: Select all

rm -rf /tmp/ffmpeg

Please share your experience in this forum.

