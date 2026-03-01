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
#include <unistd.h>
#include <errno.h>
#include <spawn.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <sys/time.h>
#include <stdio.h>
#include <spawn.h>
#include <lgpl/sysabi.h>
#include <dlfcn.h>

#ifdef _darwin_
static const cpu_type_t     cpu_TYPE_ARM64  = (CPU_TYPE_ARM | CPU_ARCH_ABI64);
static const cpu_subtype_t  cpu_SUBTYPE_ANY = ((cpu_subtype_t) -1);
static const cpu_type_t     cpu_types[2]    = { cpu_TYPE_ARM64,  CPU_TYPE_ANY };
static const cpu_subtype_t  cpu_subtypes[2] = { cpu_SUBTYPE_ANY, cpu_SUBTYPE_ANY };

typedef int (*posix_spawnattr_setarchpref_np_t)(posix_spawnattr_t *, size_t, const cpu_type_t *, const cpu_subtype_t *, size_t *);

static void darwin_spawnattr_set_best_arch(posix_spawnattr_t * attr)
{
    size_t count = 0;

    posix_spawnattr_setarchpref_np_t setarchpref_np = (posix_spawnattr_setarchpref_np_t) dlsym(RTLD_DEFAULT,"posix_spawnattr_setarchpref_np");
    if (setarchpref_np)
    {
        (*setarchpref_np)(attr,2,cpu_types,cpu_subtypes,&count);
    }
}
#endif

int SYS_posix_launch(char** argv,int fdstdin,int fdstdout,int fdstderr,char ** envp)
{
    return SYS_posix_launch2(NULL,argv,fdstdin,fdstdout,fdstderr,envp);
}

int SYS_posix_launch2(uintptr_t* ppid,char** argv,int fdstdin,int fdstdout,int fdstderr,char ** envp)
{
    posix_spawn_file_actions_t  spawn_actions;
    posix_spawnattr_t           spawn_attr;
    pid_t   pid;
    int     err;

    if (posix_spawnattr_init(&spawn_attr))
    {
        return -1;
    }
    if (posix_spawnattr_setflags(&spawn_attr,POSIX_SPAWN_SETPGROUP))
    {
        return -1;
    }
    if (posix_spawnattr_setpgroup(&spawn_attr,0))
    {
        return -1;
    }
#ifdef _darwin_
    darwin_spawnattr_set_best_arch(&spawn_attr);
#endif

    if (posix_spawn_file_actions_init(&spawn_actions))
    {
        return -1;
    }
    if (fdstdin)
    {
        if (posix_spawn_file_actions_adddup2(&spawn_actions,fdstdin,STDIN_FILENO))
        {
            return -1;
        }
    }
    if (fdstdout)
    {
        if (posix_spawn_file_actions_adddup2(&spawn_actions,fdstdout,STDOUT_FILENO))
        {
            return -1;
        }
    }
    if (fdstderr)
    {
        if (posix_spawn_file_actions_adddup2(&spawn_actions,fdstderr,STDERR_FILENO))
        {
            return -1;
        }
    }

    err = posix_spawn(&pid,argv[0],&spawn_actions,&spawn_attr,argv,envp);

    if (ppid)
    {
        *ppid = (uintptr_t)pid;
    }

    posix_spawn_file_actions_destroy(&spawn_actions);
    posix_spawnattr_destroy(&spawn_attr);

    return err;
}
