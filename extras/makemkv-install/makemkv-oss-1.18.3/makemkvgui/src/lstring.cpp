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
#include <lgpl/aproxy.h>
#include <zlib.h>
#include <algorithm>

#include "dstring.h"

static uint32_t*    stringData=NULL;
static utf8_t**     stringDataUtf8=NULL;

static const utf16_t* GetStringFromData(unsigned int code, unsigned int* p_ndx)
{
    const utf16_t* string;
    uint32_t count;
    const uint32_t* item;

    if (!stringData)
    {
        return NULL;
    }

    string = NULL;
    count = stringData[0];

    item = std::lower_bound(stringData+1,stringData+1+count,((uint32_t)code));
    if (*item==code)
    {
        string = (const utf16_t*)(stringData + item[count]);
        if (p_ndx)
        {
            *p_ndx = (unsigned int)(item - (stringData + 1));
        }
    }

    return string;
}

extern const utf16_t* AppGetString(unsigned int code)
{
    const utf16_t* string = GetStringFromData(code, NULL);

    if (!string)
    {
        string = str_default_utf16(code);
    }

    return string;
}

const utf8_t* AppGetStringUtf8(unsigned int code)
{
    unsigned int count,ndx;

    const utf16_t* str16 = GetStringFromData(code, &ndx);
    utf8_t* str8;

    if (!str16)
    {
        return str_default_utf8(code);
    }

    count = stringData[0];

    if (!stringDataUtf8)
    {
        stringDataUtf8 = new utf8_t*[count];
        memset(stringDataUtf8, 0, count * sizeof(utf8_t*));
    }

    if (stringDataUtf8[ndx])
    {
        return stringDataUtf8[ndx];
    }

    size_t len = utf16toutf8len(str16);

    stringDataUtf8[ndx] = str8 = new utf8_t[len+1];

    utf16toutf8(str8, len, str16, utf16len(str16));
    str8[len] = 0;

    return str8;
}

extern bool AppGetInterfaceLanguageData(CGUIApClient* app)
{
    const void*     data;
    unsigned int    dataSize1;
    unsigned int    dataSize2;
    uLongf          zlibDataSize;

    delete[] stringData;
    delete[] stringDataUtf8;
    stringData = NULL;
    stringDataUtf8 = NULL;

    if (NULL==app->GetAppString(AP_vastr_InterfaceLanguage,AP_APP_LOC_MAX,0)) return false;

    data=app->GetInterfaceLanguageData(AP_APP_LOC_MAX,&dataSize1,&dataSize2);

    if (!data) return false;

    stringData = new uint32_t[(dataSize1+sizeof(uint32_t))/sizeof(uint32_t)];

    zlibDataSize = (uLongf) dataSize1;

    if (uncompress( (Bytef*) stringData , &zlibDataSize , (const Bytef*)data , dataSize2 ) != Z_OK )
    {
        delete[] stringData;
        stringData = NULL;
        return false;
    }

    return true;
}

