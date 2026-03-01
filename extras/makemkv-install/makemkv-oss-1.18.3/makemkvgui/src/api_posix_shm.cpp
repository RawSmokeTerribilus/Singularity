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
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>

void* ApOpenShmem(const char *Name)
{
    int fd;
    void* pmap;
    struct stat st;

    fd=shm_open(Name,O_RDWR,0);
    if (fd<0)
    {
        return NULL;
    }
    shm_unlink(Name);

    if (fstat(fd,&st))
    {
        return NULL;
    }

    pmap=mmap(NULL,st.st_size,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    if (MAP_FAILED==pmap)
    {
        return NULL;
    }

    return pmap;
}

