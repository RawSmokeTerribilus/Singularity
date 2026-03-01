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
#include <stdint.h>
#include <lgpl/aproxy.h>

typedef uint32_t    UTF32;
typedef uint16_t    UTF16;
typedef uint8_t     UTF8;
typedef bool        Boolean;

#include "ConvertUTF.c"

size_t utf16toutf8len(const uint16_t *src_string)
{
    const UTF16* s_start = (const UTF16*)src_string;
    const UTF16* s_end   = s_start + utf16len(src_string);
    UTF8* d_start = NULL;
    UTF8* d_end   = d_start + 0x0fffffff;

    ConversionResult r = ConvertUTF16toUTF8(&s_start,s_end,&d_start,d_end,lenientConversion,false);

    if (r!=conversionOK)
    {
        return 0;
    }

    return (size_t) ((uintptr_t)d_start);
}

size_t utf16toutf8(char *dst_string,size_t dst_len,const uint16_t *src_string,size_t src_len)
{
    const UTF16* s_start = (const UTF16*)src_string;
    const UTF16* s_end   = s_start + src_len;
    UTF8* d_start = (UTF8*)dst_string;
    UTF8* d_end   = d_start + dst_len;

    ConversionResult r = ConvertUTF16toUTF8(&s_start,s_end,&d_start,d_end,lenientConversion,true);

    size_t len;
    if (r!=conversionOK)
    {
        *dst_string = 0;
        len = 0;
    } else {
        len = (d_start - (UTF8*)dst_string);
    }
    return len;
}

size_t utf8toutf16(uint16_t *dst_string,size_t dst_len,const char *src_string,size_t src_len)
{
    if (!dst_len) return 0;

    const UTF8* s_start = (const UTF8*)src_string;
    const UTF8* s_end   = s_start + src_len;
    UTF16* d_start = (UTF16*) dst_string;
    UTF16* d_end   = d_start + dst_len;

    ConversionResult r = ConvertUTF8toUTF16(&s_start,s_end,&d_start,d_end,lenientConversion,true);

    size_t len;
    if (r!=conversionOK)
    {
        *dst_string = 0;
        len = 0;
    } else {
        len = (d_start - (UTF16*)dst_string);
    }
    return len;
}

size_t utf8toutf16len(const char *src_string)
{
    const UTF8* s_start = (const UTF8*)src_string;
    const UTF8* s_end   = s_start + strlen(src_string);
    UTF16* d_start = NULL;
    UTF16* d_end   = d_start + 0x0fffffff;

    ConversionResult r = ConvertUTF8toUTF16(&s_start,s_end,&d_start,d_end,lenientConversion,false);

    if (r!=conversionOK)
    {
        return 0;
    }

    return (size_t) ( ((uintptr_t)d_start) / sizeof(uint16_t) );
}

