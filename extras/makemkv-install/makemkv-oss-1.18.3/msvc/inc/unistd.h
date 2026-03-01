/*
    Written by GuinpinSoft inc <oss@makemkv.com>

    This file is hereby placed into public domain,
    no copyright is claimed.

*/
#ifndef MSVC_UNISTD_H_INCLUDED
#define MSVC_UNISTD_H_INCLUDED

#if defined(_MSC_VER)

#include <stddef.h>
#include <stdint.h>
#include <direct.h>
#include <io.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef _SSIZE_T_DEFINED
#define _SSIZE_T_DEFINED
typedef intptr_t ssize_t;
#endif

typedef uint16_t uid_t;
typedef uint64_t useconds_t;

#define geteuid() (0)
#define getuid() (0)

void msleep_native(unsigned int mseconds);
int usleep(useconds_t usec);

static unsigned int __inline sleep(unsigned int sec)
{
    msleep_native(sec*1000);
    return 0;
}

#ifdef __cplusplus
};
#endif


#endif

#endif // MSVC_UNISTD_H_INCLUDED
