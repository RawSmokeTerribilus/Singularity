include makefile.common
include mmccextr/mmccextr.mak

GCC=gcc
GXX=g++ -std=c++11
MOC=

CFLAGS=-g -O2 -D_linux_ -Wno-deprecated-declarations
CXXFLAGS=-g -O2
LDFLAGS=
DESTDIR=
prefix=/usr
exec_prefix=${prefix}
datarootdir=${prefix}/share
libdir=${exec_prefix}/lib64
bindir=${exec_prefix}/bin
datadir=${datarootdir}
FFMPEG_CFLAGS=-I/usr/include/ffmpeg 
FFMPEG_LIBS=-lavcodec -lavutil  -lrt
ENABLE_GUI=no
ENABLE_DEBUG=no
NO_EC_DEF=
QT_INC=
QT_CFLAGS=
QT_LIB=
INSTALL=/usr/bin/install -c
OBJCOPY=objcopy
LD=/usr/bin/ld -m elf_x86_64
BUILDINFO_ARCH_NAME=$(shell $(GCC) -dumpmachine)
BUILDINFO_BUILD_DATE=$(shell date)

top_srcdir ?= .
INCF=-I$(top_srcdir)/

ifeq ($(ENABLE_GUI),yes)
OUT_GUI=out/makemkv
endif

ifeq ($(ENABLE_DEBUG),no)
STRIP_FLAGS=--strip-all --strip-debug --strip-unneeded --discard-all
endif

LIBABI_OBJ := $(patsubst %,tmp/%.o,$(LIBABI_SRC))
LIBFFABI_OBJ := $(patsubst %,tmp/%.o,$(LIBFFABI_SRC))
MMCCX_SRC := $(patsubst %,mmccextr/%,$(MMCCEXTR_SRC))

all: out/libdriveio.so.0 out/libmakemkv.so.1 $(OUT_GUI) out/libmmbd.so.0 out/mmccextr out/mmgplsrv
	@echo "type \"sudo make install\" to install"

clean:
	-rm -rf out tmp

install: out/libdriveio.so.0 out/libmakemkv.so.1 $(OUT_GUI) out/libmmbd.so.0 out/mmccextr out/mmgplsrv
	$(INSTALL) -D -m 644 out/libdriveio.so.0 $(DESTDIR)$(libdir)/libdriveio.so.0
	$(INSTALL) -D -m 644 out/libmakemkv.so.1 $(DESTDIR)$(libdir)/libmakemkv.so.1
	$(INSTALL) -D -m 644 out/libmmbd.so.0 $(DESTDIR)$(libdir)/libmmbd.so.0
ifeq ($(DESTDIR),)
	ldconfig
endif
ifeq ($(ENABLE_GUI),yes)
	$(INSTALL) -D -m 755 out/makemkv $(DESTDIR)$(bindir)/makemkv
	$(INSTALL) -D -m 644 makemkvgui/share/makemkv.desktop $(DESTDIR)$(datadir)/applications/makemkv.desktop
	$(INSTALL) -D -m 644 makemkvgui/share/icons/16x16/makemkv.png $(DESTDIR)$(datadir)/icons/hicolor/16x16/apps/makemkv.png
	$(INSTALL) -D -m 644 makemkvgui/share/icons/22x22/makemkv.png $(DESTDIR)$(datadir)/icons/hicolor/22x22/apps/makemkv.png
	$(INSTALL) -D -m 644 makemkvgui/share/icons/32x32/makemkv.png $(DESTDIR)$(datadir)/icons/hicolor/32x32/apps/makemkv.png
	$(INSTALL) -D -m 644 makemkvgui/share/icons/64x64/makemkv.png $(DESTDIR)$(datadir)/icons/hicolor/64x64/apps/makemkv.png
	$(INSTALL) -D -m 644 makemkvgui/share/icons/128x128/makemkv.png $(DESTDIR)$(datadir)/icons/hicolor/128x128/apps/makemkv.png
	$(INSTALL) -D -m 644 makemkvgui/share/icons/256x256/makemkv.png $(DESTDIR)$(datadir)/icons/hicolor/256x256/apps/makemkv.png
endif
	$(INSTALL) -D -m 755 out/mmccextr $(DESTDIR)$(bindir)/mmccextr
	$(INSTALL) -D -m 755 out/mmgplsrv $(DESTDIR)$(bindir)/mmgplsrv

out/%: out/%.full
	$(OBJCOPY) $(STRIP_FLAGS) $< $@

out/libdriveio.so.0.full:
	mkdir -p out
	$(GXX) $(CXXFLAGS) $(CFLAGS) $(LDFLAGS) -D_REENTRANT -shared -Wl,-z,defs -o$@ $(INCF)$(LIBDRIVEIO_INC) $(LIBDRIVEIO_SRC) \
	-fPIC -Xlinker -dy -Xlinker --version-script=libdriveio/src/libdriveio.vers \
	-Xlinker -soname=libdriveio.so.0 -lc -lstdc++

tmp/%.c.o: %.c
	mkdir -p $(dir $@)
	$(GCC) -c $(CFLAGS) $(NO_EC_DEF) -D_GNU_SOURCE -D_REENTRANT -o$@ $(INCF)$(LIBABI_INC) $(INCF)$(LIBFFABI_INC) \
	-DHAVE_BUILDINFO_H -Itmp $(FFMPEG_CFLAGS) -fPIC $<

out/libmakemkv.so.1.full: tmp/gen_buildinfo.h $(LIBABI_OBJ) $(LIBFFABI_OBJ)
	mkdir -p out
	$(GXX) $(CXXFLAGS) $(CFLAGS) $(LDFLAGS) $(NO_EC_DEF) -D_GNU_SOURCE -D_REENTRANT -shared -Wl,-z,defs -o$@ $(INCF)$(LIBEBML_INC) $(LIBEBML_DEF) \
	$(INCF)$(LIBMATROSKA_INC) $(INCF)$(LIBMAKEMKV_INC) $(INCF)$(SSTRING_INC) $(INCF)$(MAKEMKVGUI_INC) $(INCF)$(LIBABI_INC) \
	$(INCF)$(LIBFFABI_INC) $(LIBEBML_SRC) $(LIBMATROSKA_SRC) $(LIBMAKEMKV_SRC) $(SSTRING_SRC) $(LIBABI_SRC_LINUX) \
	$(LIBABI_OBJ) $(LIBFFABI_OBJ) \
	-DHAVE_BUILDINFO_H -Itmp \
	-fPIC -Xlinker -dy -Xlinker --version-script=libmakemkv/src/libmakemkv.vers \
	-Xlinker -soname=libmakemkv.so.1 -lc -lstdc++ -lcrypto -lz -lexpat $(FFMPEG_LIBS) -lm -lrt

out/libmmbd.so.0.full:
	mkdir -p out
	$(GXX) $(CXXFLAGS) $(CFLAGS) $(LDFLAGS) -D_REENTRANT -shared -Wl,-z,defs -o$@ $(INCF)$(MAKEMKVGUI_INC) $(INCF)$(LIBMMBD_INC) $(INCF)$(LIBDRIVEIO_INC) \
	$(INCF)$(LIBMAKEMKV_INC) $(INCF)$(SSTRING_INC) $(INCF)$(LIBABI_INC) $(LIBMMBD_SRC) $(LIBMMBD_SRC_LINUX) $(SSTRING_SRC) \
	$(LIBDRIVEIO_SRC_PUB) \
	-fPIC -Xlinker -dy -Xlinker --version-script=libmmbd/src/libmmbd.vers \
	-Xlinker -soname=libmmbd.so.0 -lc -lstdc++ -lrt -lpthread -lcrypto -ldl

out/makemkv.full: $(MAKEMKVGUI_GEN) $(MAKEMKVGUI_SRC_LINUX) tmp/gen_buildinfo.h
	mkdir -p out
	$(GXX) $(CXXFLAGS) $(CFLAGS) $(QT_CFLAGS) $(LDFLAGS) -o$@ $(INCF)$(MAKEMKVGUI_INC) $(INCF)$(LIBMAKEMKV_INC) $(INCF)$(SSTRING_INC) \
	$(INCF)$(LIBDRIVEIO_INC) $(INCF)$(LIBABI_INC) $(MAKEMKVGUI_SRC) $(MAKEMKVGUI_SRC_LINUX) $(MAKEMKVGUI_GEN) \
	$(SSTRING_SRC) $(LIBDRIVEIO_SRC_PUB) \
	-DHAVE_BUILDINFO_H -Itmp \
	$(QT_INC) -lc -lstdc++ \
	$(QT_LIB) -lpthread -lz -lrt

out/mmccextr.full: $(MMCCX_SRC) tmp/gen_buildinfo.h
	mkdir -p out
	$(GCC) $(CFLAGS) $(LDFLAGS) $(MMCCEXTR_DEF) -DHAVE_BUILDINFO_H -Itmp -D_GNU_SOURCE -o$@ $(MMCCX_SRC) -lc \
	-ffunction-sections -Wl,--gc-sections -Wl,-z,defs

out/mmgplsrv.full: $(MMGPL_SRC)
	mkdir -p out
	$(GCC) $(CFLAGS) $(LDFLAGS) $(INCF)$(MMGPL_INC) $(INCF)$(DVDNAV_INC) $(INCF)$(DVDREAD_INC) $(INCF)$(MAKEMKVGUI_INC) $(INCF)$(LIBMAKEMKV_INC) \
	$(INCF)$(LIBDRIVEIO_INC) $(INCF)$(LIBABI_INC) $(MMGPL_DEF) -D_GNU_SOURCE -Dstl=std -o$@ $(MMGPL_SRC) $(MMGPL_SRC_LINUX) -lc -lstdc++ \
	-ffunction-sections -Wl,--gc-sections -Wl,-z,defs

tmp/gen_buildinfo.h:
	mkdir -p tmp
	echo "#define BUILDINFO_ARCH_NAME \"$(BUILDINFO_ARCH_NAME)\"" >> $@
	echo "#define BUILDINFO_BUILD_DATE \"$(BUILDINFO_BUILD_DATE)\"" >> $@

tmp/moc_%.cpp : makemkvgui/src/%.h
	mkdir -p tmp
	$(MOC) -o $@ $<

tmp/image_data.o : makemkvgui/bin/image_data.bin
	mkdir -p tmp
	$(LD) -r -b binary -z noexecstack -o $@ $<

