/*
    Copyright (C) 2007-2025 GuinpinSoft inc <mmgpl@makemkv.com>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

*/
#include <stdint.h>
#include <inttypes.h>

#define LOG_DEBUG 1
#define TRACE 1
#define DVDNAV_NO_CACHE 1
#define DVDNAV_NO_LOCKING 1
#define DVDNAV_NO_TXTDT 1
#define DVDNAV_NO_ERRSTR 1

#define this c_this

#include "dvdnav.c"
#include "highlight.c"
#include "logger.c"
#include "navigation.c"
#include "settings.c"
#include "vm/decoder.c"
#include "vm/getset.c"
#include "vm/play.c"
#include "vm/vm.c"
#include "vm/vmcmd.c"
#include "vm/vmget.c"

