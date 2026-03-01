
ARCH=$(shell uname -m)
DESTDIR=
PREFIX=/usr

ifeq ($(ARCH),i586)
ARCH=i386
ARCH_OK=1
endif

ifeq ($(ARCH),i686)
ARCH=i386
ARCH_OK=1
endif

ifeq ($(ARCH),x86_64)
ARCH=amd64
ARCH_OK=1
endif

ifeq ($(ARCH),armv7l)
ARCH=armhf
ARCH_OK=1
endif

ifeq ($(ARCH),armv8l)
ARCH=armhf
ARCH_OK=1
endif

ifeq ($(ARCH),aarch64)
ARCH=arm64
ARCH_OK=1
endif

ifneq ($(ARCH_OK),1)
$(error MakeMKV is currently not available for architecture $(ARCH))
endif

all: tmp/eula_accepted
	@echo "type \"sudo make install\" to install"

clean:
	-rm -rf tmp

tmp/eula_accepted:
	@mkdir -p tmp
	@/bin/bash src/ask_eula.sh src/eula_en_linux.txt
	@echo accepted > $@

install: tmp/eula_accepted bin/$(ARCH)/makemkvcon
	rm -f $(DESTDIR)$(PREFIX)/bin/makemkvcon
	rm -f $(DESTDIR)$(PREFIX)/bin/mmdtsdec
	rm -f $(DESTDIR)$(PREFIX)/share/MakeMKV/*
	install -d $(DESTDIR)$(PREFIX)/share/MakeMKV
	install -d $(DESTDIR)$(PREFIX)/bin
	install -t $(DESTDIR)$(PREFIX)/bin bin/$(ARCH)/makemkvcon
	install -m 644 -t $(DESTDIR)$(PREFIX)/share/MakeMKV src/share/appdata.tar
	install -m 644 -t $(DESTDIR)$(PREFIX)/share/MakeMKV src/share/blues.jar
	install -m 644 -t $(DESTDIR)$(PREFIX)/share/MakeMKV src/share/blues.policy
	cd $(DESTDIR)$(PREFIX)/bin && ln -s -f makemkvcon sdftool

