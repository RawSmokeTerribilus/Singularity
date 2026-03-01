/*
    libMMBD - MakeMKV BD decryption API library

    Copyright (C) 2007-2025 GuinpinSoft inc <libmmbd@makemkv.com>

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

*/
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <lgpl/utf8.h>
#include <alloca.h>
#include "aacslog.h"
#include "fakejni.h"

//
// stderr logger
//
static void __cdecl stderr_print(void* user_context, uint32_t flags, const char* message, const void*)
{
    fprintf(stderr, "MMBD: %s\n", message);
    fflush(stderr);
}

mmbd_output_proc_t aacs_log_stderr()
{
    return stderr_print;
}

//
// windbg logger
//
#ifdef MMBD_WIN32_DEBUG
#include <Windows.h>
static void __cdecl windbg_print(void* user_context, uint32_t flags, const char* message, const void*)
{
    OutputDebugStringA(message);
    OutputDebugStringA("\n");
}
mmbd_output_proc_t aacs_log_windbg()
{
    return stderr_print;
}
#else
mmbd_output_proc_t aacs_log_windbg()
{
    return NULL;
}
#endif

//
// Dll access
//
#ifdef _WIN32

#include <Windows.h>

static void* GetDllByAddr(void* caller)
{
    MEMORY_BASIC_INFORMATION mi;

    bzero(&mi, sizeof(mi));
    if (0 == VirtualQuery(caller, &mi, sizeof(mi))) {
        return NULL;
    }
    return mi.AllocationBase;
}

static inline void* GetDllByName(const char* name)
{
    return GetModuleHandleA(name);
}

static inline void* GetFunctionByName(void* dll, const char* name)
{
    return GetProcAddress((HMODULE)dll, name);
}

#else

#include <dlfcn.h>

static void* GetDllByName(const char* name)
{
    void* p = dlopen(name, RTLD_NOLOAD);
    if (NULL != p) {
        dlclose(p);
    }
    return p;
}


static void* GetDllByAddr(void* caller)
{
    Dl_info mi;

    bzero(&mi, sizeof(mi));
    if (0 == dladdr(caller, &mi)) {
        return NULL;
    }
    if (NULL == mi.dli_fname) {
        return NULL;
    }
    return GetDllByName(mi.dli_fname);
}

static inline void* GetFunctionByName(void* dll, const char* name)
{
    return dlsym(dll, name);
}

#endif

//
// JRiver logger
//

typedef int (__cdecl *JRLogExternal_t)(const uint16_t* strAction, const uint16_t* strLogOutput);

#ifdef _WIN32

static void __cdecl jriver_print(void* user_context, uint32_t flags, const char* message, const void*)
{
    size_t slen = strlen(message);
    size_t wlen = utf8toutf16len(message);

    uint16_t*   wbuf;
    void*       fbuf;
    if (wlen < 256)
    {
        wbuf = (uint16_t*)alloca((wlen + 1) * sizeof(uint16_t*));
        fbuf = NULL;
    } else {
        wbuf = (uint16_t*)malloc((wlen + 1) * sizeof(uint16_t*));
        if (NULL == wbuf) return;
        fbuf = wbuf;
    }

    size_t clen = utf8toutf16(wbuf, wlen, message, slen);
    wbuf[clen] = 0;
    wbuf[wlen] = 0;
    const uint16_t* tag;
    switch (flags&(MMBD_MESSAGE_FLAG_WARNING|MMBD_MESSAGE_FLAG_ERROR|MMBD_MESSAGE_FLAG_MMBD_ERROR))
    {
    case MMBD_MESSAGE_FLAG_WARNING: tag = (const uint16_t*)L"libmmbd_warning"; break;
    case MMBD_MESSAGE_FLAG_ERROR:
    case MMBD_MESSAGE_FLAG_MMBD_ERROR: tag = (const uint16_t*)L"libmmbd_error"; break;
    default: tag = (const uint16_t*)L"libmmbd_info"; break;
    }

    JRLogExternal_t JRLogExternal = (JRLogExternal_t)user_context;

    (*JRLogExternal)(tag, wbuf);

    if (NULL!=fbuf) free(fbuf);
}

mmbd_output_proc_t aacs_log_jriver(void** p_context)
{
    void* dll = GetDllByName("JRTools.dll");
    if (NULL == dll) return NULL;

    void* func = GetFunctionByName(dll, "JRLogExternal");

    if (NULL == func) {
        return NULL;
    }

    *p_context = func;
    return jriver_print;
}

#else

mmbd_output_proc_t aacs_log_jriver(void** p_context)
{
    return NULL;
}

#endif

//
// libbluray logger
//
// This is a (stable) hack that should be removed once libbluray would call mmbd_create_context in place of aacs_init
//

typedef void (JNICALL *Java_org_videolan_Logger_logN_t)(JNIEnv *env, void* cls, jboolean error, jstring jfile, jint line, jstring string);

static jsize JNICALL jniGetStringLength(JNIEnv *, jstring str)
{
    return (jsize)strlen(str);
}

static const char* JNICALL jniGetStringUTFChars(JNIEnv *, jstring str, jboolean *isCopy)
{
    if (NULL != isCopy) *isCopy = 0;
    return str;
}

static void JNICALL jniReleaseStringUTFChars(JNIEnv *, jstring , const char* )
{
}

static void __cdecl libbluray_print(void* user_context, uint32_t flags, const char* message, const void*)
{
    jboolean error = 1; // 0;
    if (0 != (flags & (MMBD_MESSAGE_FLAG_ERROR| MMBD_MESSAGE_FLAG_MMBD_ERROR))) error = 1;

    struct JNINativeInterface_s jenv;

    bzero(&jenv, sizeof(jenv));
    jenv.GetStringLength = jniGetStringLength;
    jenv.GetStringUTFLength = jniGetStringLength;
    jenv.GetStringUTFChars = jniGetStringUTFChars;
    jenv.ReleaseStringUTFChars = jniReleaseStringUTFChars;

    Java_org_videolan_Logger_logN_t Java_org_videolan_Logger_logN = (Java_org_videolan_Logger_logN_t)user_context;

    uintptr_t penv = ((uintptr_t)(void*)&jenv) - JNINativeInterfaceOffset;

    (*Java_org_videolan_Logger_logN)(&penv, NULL, error, "LibMMBD", flags & 0x00ffffff, message);
}

mmbd_output_proc_t aacs_log_libbluray(void** p_context,void* caller)
{
    void* dll = GetDllByAddr(caller);
    if (NULL == dll) return NULL;

    void* func = GetFunctionByName(dll, "Java_org_videolan_Logger_logN");
    if (NULL == func) {
        func = GetFunctionByName(dll, "_Java_org_videolan_Logger_logN");
    }
    if (NULL == func) {
        func = GetFunctionByName(dll, "Java_org_videolan_Logger_logN@24");
    }

    if (NULL == func) {
        return NULL;
    }

    *p_context = func;
    return libbluray_print;
}

