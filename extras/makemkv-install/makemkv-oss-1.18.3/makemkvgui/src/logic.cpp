/*
    MakeMKV GUI - Graphics user interface application for MakeMKV

    Copyright (C) 2007-2025 GuinpinSoft inc <makemkvgui@makemkv.com>

    You may use this file in accordance with the end user license
    agreement provided with the Software. For licensing terms and
    conditions see License.txt

    This Software is distributed on an "AS IS" basis, WITHOUT WARRANTY
    OF ANY KIND, either express or implied. See the License.txt for
    the specific language governing rights and limitations.

*/
#include "mainwnd.h"
#include <lgpl/smem.h>
#include <lgpl/sstring.h>

uint64_t    get_free_space(const utf8_t* Folder);

QString FormatDiskFreeSpace(const utf8_t* FolderName)
{
    uint64_t free_sp = get_free_space(FolderName);

    if (0==free_sp) return QString();

    char suf;

    free_sp >>=(10-8);
    if (free_sp < 2*1024*256)
    {
        suf = 'K';
    } else {
        free_sp >>= 10;
        suf = 'M';
        if (free_sp > (20*1024*256))
        {
            free_sp >>= 10;
            suf = 'G';
        }
    }

    unsigned int sz = (unsigned int) free_sp;
    unsigned int dt = ((sz&0xff)*10)>>8;
    sz >>= 8;

    char str[64];
    size_t slen;

    slen = sprintf_s(str, sizeof(str), "%u.%u %c", sz, dt, suf);

    return QString::fromLatin1(str,(int)slen);
}

