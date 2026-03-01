/*
    GPL is cancer. A hacky and otherwise useless glue code to comply with GPL licensing.

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
#include <stdio.h>
#include <string.h>
#include <dvdnav/mmdvdnav.h>

#ifdef _WIN32

#include <Windows.h>
#include <winnt.h>

#endif


extern "C"
int main(int argc,char **argv)
{
    if (argc <= 1)
    {
        return 0;
    }

    if ((argc >= 2) && (0 == strcmp(argv[1], "libdvdnav-server")))
    {
        uint64_t pipe_in, pipe_out;

#ifdef _WIN32
        pipe_in = (uintptr_t)(void*)GetStdHandle(STD_INPUT_HANDLE);
        pipe_out = (uintptr_t)(void*)GetStdHandle(STD_OUTPUT_HANDLE);
#else
        pipe_in = 0;
        pipe_out = 1;
#endif

        DvdNavRunServer(pipe_in, pipe_out);
        return 0;
    }

    return -1;
}

