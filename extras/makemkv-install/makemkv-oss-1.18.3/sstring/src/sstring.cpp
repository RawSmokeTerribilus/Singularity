/*
    Written by GuinpinSoft inc <oss@makemkv.com>

    This file is hereby placed into public domain,
    no copyright is claimed.

*/
#include <lgpl/sstring.h>
#include <errno.h>
#include <stdio.h>
#include <stdarg.h>

#if !defined(ALREADY_HAVE_SSTRING_API) || defined(FORCE_SSTRING_API)

int __cdecl sprintf_s(char *buffer,size_t sizeOfBuffer,const char *format,...)
{
    if ( (sizeOfBuffer==0) || (buffer==NULL) || (format==NULL) )
    {
        errno = EINVAL;
        return -1;
    }

    if (sizeOfBuffer==1)
    {
        *buffer=0;
        return 0;
    }

    va_list args;
    va_start(args,format);

    int rtn = vsnprintf(buffer,sizeOfBuffer,format,args);

    va_end(args);

    if ( (rtn<0) || ( ((size_t)rtn) >= sizeOfBuffer) )
    {
        buffer[0]=0;
        errno = EINVAL;
        return -1;
    }

    buffer[rtn]=0;
    return rtn;
}

#endif // ALREADY_HAVE_SSTRING_API

int __cdecl tolower_ascii(int c)
{
    if ((c >= 'A') && (c <= 'Z'))
    {
        return (c + ('a' - 'A'));
    } else {
        return c;
    }
}

