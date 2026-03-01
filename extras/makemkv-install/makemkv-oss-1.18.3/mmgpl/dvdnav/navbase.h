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
#ifndef DVDNAVBASE_H_INCLUDED
#define DVDNAVBASE_H_INCLUDED

#include <dvdnav/dvdnav.h>

class IDvdNavBase
{
public:
    virtual void DvdNavLog(dvdnav_logger_level_t level, const char *str, va_list lst) = 0;
    virtual bool DvdNavReadVob(unsigned int id, uint32_t sector, uint8_t* data) = 0;
public:
    dvdnav_t* DvdNavOpen(bool EnableLog);
public:
    static void CbLog(void *ctx, dvdnav_logger_level_t level, const char *str, va_list lst);
    static int CbRead(void *p_stream, void* buffer, int i_read);
    static IDvdNavBase* GetBase(void* ctx, const dvdnav_stream_cb* strcb);
public:
    void Log(const char* fmt, ...);
};


#endif // DVDNAVBASE_H_INCLUDED
