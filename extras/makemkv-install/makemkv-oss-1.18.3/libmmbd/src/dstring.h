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

static const utf8_t* str_default_utf8(unsigned int code)
{
    switch (code)
    {
    case 1001: return "DBG ASSERT: %1 at %2:%3";
    case 1002: return "LIBMKV_TRACE: %1";
    case 1003: return "DEBUG: Code %1 at %2:%3";
    case 1006: return "";
    case 1011: return "%1";
    case 1012: return "%1 %2";
    case 5009: return "Application failed to initialize";
    case 6001: return "MakeMKV";
    default: break;
    }
    return "---error---";
}

static const utf16_t msg_1001[] = { 'D', 'B', 'G', ' ', 'A', 'S', 'S', 'E', 'R', 'T', ':', ' ', '%', '1', ' ', 'a', 't', ' ', '%', '2', ':', '%', '3', 0 };
static const utf16_t msg_1002[] = { 'L', 'I', 'B', 'M', 'K', 'V', '_', 'T', 'R', 'A', 'C', 'E', ':', ' ', '%', '1', 0 };
static const utf16_t msg_1003[] = { 'D', 'E', 'B', 'U', 'G', ':', ' ', 'C', 'o', 'd', 'e', ' ', '%', '1', ' ', 'a', 't', ' ', '%', '2', ':', '%', '3', 0 };
static const utf16_t msg_1006[] = { 0 };
static const utf16_t msg_1011[] = { '%', '1', 0 };
static const utf16_t msg_1012[] = { '%', '1', ' ', '%', '2', 0 };
static const utf16_t msg_5009[] = { 'A','p','p','l','i','c','a','t','i','o','n',' ','f','a','i','l','e','d',' ','t','o',' ','i','n','i','t','i','a','l','i','z','e',0 };
static const utf16_t msg_6001[] = { 'M', 'a', 'k', 'e', 'M', 'K', 'V', 0, };
static const utf16_t msg_errr[] = { '-','-','-',' ','e','r','r','o','r',' ','-','-','-',0 };

static const utf16_t* str_default_utf16(unsigned int code)
{
    switch (code)
    {
    case 1001: return msg_1001;
    case 1002: return msg_1002;
    case 1003: return msg_1003;
    case 1006: return msg_1006;
    case 1011: return msg_1011;
    case 1012: return msg_1012;
    case 5009: return msg_5009;
    case 6001: return msg_6001;
    default: break;
    }
    return msg_errr;
}

