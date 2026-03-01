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
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <fcntl.h>
#include <stdio.h>
#include <lgpl/sysabi.h>
#include <poll.h>

const char* const* ApGetAppLocations();

static mode_t mstat(const char* path)
{
    struct stat buf;

    if (stat(path,&buf)!=0) return 0;
    return buf.st_mode;
}

int ApSpawnApp(char* verstr, const char* AppName, uint64_t* stdh)
{
    int     pipe_fd_stdout[2],pipe_fd_stdin[2],err;
    char    app_path[1024+32];
    char*   argv[4];
    char    str_guiserver[sizeof("guiserver")+2];

    if (pipe(pipe_fd_stdout))
    {
        return errno|0x80000000;
    }
    if (pipe(pipe_fd_stdin))
    {
        return errno|0x81000000;
    }

    if (AppName[0]==':')
    {
        bool app_found = false;
        const char* const* app_locations = ApGetAppLocations();
        const char* p_env = getenv("MAKEMKVCON");

        AppName++;

        if (p_env!=NULL)
        {
            strcpy(app_path,p_env);
            app_found = true;
        } else {
            for (size_t i=0;app_locations[i]!=NULL;i++)
            {
                strcpy(app_path,app_locations[i]);
                strcat(app_path,"/");
                strcat(app_path,AppName);

                if ( (mstat(app_path)&(S_IFREG|S_IXUSR|S_IXGRP|S_IXOTH)) ==
                    (S_IFREG|S_IXUSR|S_IXGRP|S_IXOTH) )
                {
                    app_found = true;
                    break;
                }
            }
        }
        if (app_found==false)
        {
            return -4;
        }
    } else {
        char*   p;
        int     app_len;

        app_len = SYS_posix_getmyname(app_path,(int)(sizeof(app_path)-1));
        if (app_len<=0)
        {
            return -2;
        }
        app_path[app_len]=0;
        p=app_path+app_len;
        while(p!=app_path)
        {
            if(*p=='/')
            {
                p++;
                break;
            }
            p--;
        }
        strcpy(p,AppName);
    }

    strcpy(str_guiserver,"guiserver");

    argv[0]=app_path;
    argv[1]=str_guiserver;
    argv[2]=verstr;
    argv[3]=NULL;

    err = SYS_posix_launch(argv,pipe_fd_stdin[0],pipe_fd_stdout[1],0,SYS_posix_envp());

    close(pipe_fd_stdout[1]);
    close(pipe_fd_stdin[0]);

    if (err)
    {
        return err;
    }

    stdh[0] = pipe_fd_stdout[0];
    stdh[1] = pipe_fd_stdin[1];

    return 0;
}

int ApSpawnNewInstance()
{
    int     err;
    char    app_path[1024+32];
    char*   argv[2];

    err = SYS_posix_getmyname(app_path,(int)(sizeof(app_path)-1));
    if (err<=0)
    {
        return -2;
    }
    app_path[err]=0;

    argv[0]=app_path;
    argv[1]=NULL;

    err = SYS_posix_launch(argv,0,0,0,SYS_posix_envp());

    return err;
}

uintptr_t ApDebugOpen(const char* name)
{
    int fd = open(name,O_WRONLY|O_CREAT|O_TRUNC|O_SYNC,S_IRUSR|S_IWUSR|S_IRGRP|S_IROTH);
    if (fd<0) return 0;
    return (uintptr_t)fd;
}

void ApDebugOut(uintptr_t file,const char* string)
{
    int written;

    if (file==0) return;

    size_t len = strlen(string);
    while(len>0)
    {
        written = write((int)file,string,len);
        if (written<0) return;
        len -= written;
        string += written;
        fsync((int)file);
    }
}

int ApClosePipe(uint64_t handle)
{
    return close((int)handle);
}

int ApReadPipe(uint64_t handle, void* buffer, unsigned int size,unsigned int timeout)
{
    struct pollfd pf;
    int err;

    bzero(&pf,sizeof(pf));
    pf.fd = (int)handle;
    pf.events = POLLIN;

    err = poll(&pf,1,timeout << 10);
    if (err<=0) return -1;

    err = read((int)handle,buffer,size);
    if (err<=0) return -1;


    return err;
}

int ApWritePipe(uint64_t handle, const void* buffer, unsigned int size)
{

    return write((int)handle,buffer,size);
}

