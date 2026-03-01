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
#include <lgpl/sstring.h>

static const char* AbiTag = "Apr0><y-ABI-versi0n-" AP_ABI_VER "#tAg\n";

void CApClient::SetUiNotifier(CApClient::INotifier* Notifier)
{
    m_Ui = Notifier;
}

CApClient::CApClient()
{
    m_Transport = NULL;
    m_Ui = NULL;
    m_debug = 0;
    m_mem = NULL;
}

void CApClient::AppExiting()
{
    if (NULL!=m_mem)
    {
        m_mem->flags |= (AP_SHMEM_FLAG_EXIT | 2);
    }
}

bool CApClient::Init(CApClient::ITransport* Transport, const char* AppName, unsigned int* Code)
{
    char *p;
    const char *args[2];
    int error;
    char response[512];
    uint64_t stdh[2];

    *Code = 0;

    strcpy(response, AP_ABI_VER);
    p = response + strlen(response);
    *(p++) = '+';
    *p = 0;

    if (false == Transport->Init1(p))
    {
        DebugFail(0, NULL);
        return false;
    }

    error = ApSpawnApp(response, AppName, stdh);
    if (error != 0)
    {
        DebugFail(error, NULL);
        *Code = 1;
        return false;
    }

    // read answer
    for (unsigned int i=0;i<(sizeof(response)-1);i++)
    {
        if (1!=ApReadPipe(stdh[0],response+i,1,AP_SEM_TIMEOUT))
        {
            *Code = 4;
            return false;
        }

        if (response[i]=='$')
        {
            response[i]=0;
            break;
        }
    }

    p = response;
    args[0] = p; p = strchr(p, ':'); *p = 0; p++;
    args[1] = p;

    if (0!=strcmp(AP_ABI_VER, args[0]))
    {
        DebugFail(0, AP_ABI_VER);
        DebugFail(0, args[0]);
        *Code = 2;
        return false;
    }

    if (false == Transport->Init2(this, args[1], stdh))
    {
        DebugFail(0, args[1]);
        *Code = 3;
        return false;
    }

    m_shutdown = false;
    m_Transport = Transport;

    return true;
}

AP_CMD CApClient::Transact(uint32_t cmd)
{
    if (m_shutdown)
    {
        DebugFail(cmd, NULL);
        return apReturn;
    }

    DebugFail(cmd, "in");

    m_mem->cmd = cmd;
    if (false == m_Transport->Transact())
    {
        DebugFail(m_mem->cmd, NULL);
        DebugFail(m_mem->flags, NULL);
        m_shutdown = true;
        if (0 != (m_mem->flags&AP_SHMEM_FLAG_NOMEM))
        {
            return apBackOutOfMem;
        }
        return apBackFatalCommError;
    }

    DebugFail(m_mem->cmd, "out");

    return (AP_CMD)(m_mem->cmd>>24);
}

void CApClient::ReportFatalError(uint32_t code)
{
    m_shutdown = true;
    if (NULL!=m_Ui)
    {
        m_Ui->ReportUiMessage(APP_IFACE_FATAL_COMM, AP_UIMSG_BOXERROR, AppGetStringUtf8(code), 0);
        m_Ui->ExitApp();
    }
}

void CApClient::ExecCmdPacked(uint32_t cmd)
{
    AP_CMD r;
    unsigned int args, size;

    while(apReturn!=(r=Transact(cmd)))
    {
        // process command
        args = size = 0;
        switch(r)
        {
        case apNop:
            break;
        case apBackEnterJobMode:
            m_Ui->EnterJobMode((unsigned int) m_mem->args[0]);
            break;
        case apBackLeaveJobMode:
            m_Ui->LeaveJobMode();
            break;
        case apBackExit:
            m_shutdown = true;
            m_Ui->ExitApp();
            return;
            break;
        case apBackFatalCommError:
            ReportFatalError(APP_IFACE_FATAL_COMM);
            return;
            break;
        case apBackOutOfMem:
            ReportFatalError(APP_IFACE_FATAL_MEM);
            return;
            break;
        case apBackUpdateDrive:
            const utf8_t* p_str,*drv_name,*dsk_name,*dev_name;

            p_str = (const utf8_t*) m_mem->strbuf;
            if ((m_mem->args[1]&1)==0)
            {
                drv_name = NULL;
            } else {
                drv_name = p_str;
                p_str += (strlen(p_str)+1);
            }
            if ((m_mem->args[1]&2)==0)
            {
                dsk_name = NULL;
            } else {
                dsk_name = p_str;
                p_str += (strlen(p_str)+1);
            }
            if ((m_mem->args[1]&4)==0)
            {
                dev_name = NULL;
            } else {
                dev_name = p_str;
                p_str += (strlen(p_str)+1);
            }
            m_Ui->UpdateDrive(
                (unsigned int) m_mem->args[0],
                drv_name,
                (AP_DriveState)(m_mem->args[2]),
                dsk_name,
                dev_name,
                (AP_DiskFsFlags)(m_mem->args[3]),
                ((uint8_t*)p_str),
                (unsigned int) m_mem->args[4]
                );
            break;
        case apBackSetTotalName:
            m_Ui->SetTotalName( (unsigned long) m_mem->args[0] );
            break;
        case apBackUpdateLayout:
            unsigned int n_size;
            unsigned long c_name;
            unsigned int name_index;
            unsigned int flags;
            unsigned long names[AP_Progress_MaxLayoutItems];
            c_name = (unsigned long) m_mem->args[0];
            name_index = (unsigned int) m_mem->args[1];
            flags = (unsigned int) m_mem->args[2];
            n_size = (unsigned int) m_mem->args[3];
            for (unsigned int i=0;i<n_size;i++)
            {
                names[i] = (unsigned long) m_mem->args[4+i];
            }
            m_Ui->UpdateLayout(c_name,name_index,flags,n_size,names);
            break;
        case apBackUpdateCurrentInfo:
            m_Ui->UpdateCurrentInfo( (unsigned int) m_mem->args[0] , (utf8_t*)m_mem->strbuf );
            break;
        case apBackReportUiMessage:
            int rr;
            if (m_Ui)
            {
                rr = m_Ui->ReportUiMessage((unsigned long)m_mem->args[0], (unsigned long)m_mem->args[1], (utf8_t*)m_mem->strbuf, Get64(2));
            } else {
                rr = 0;
            }
            m_mem->args[0] = rr;
            args = 1;
            break;
        case apBackReportUiDialog:
            if (m_Ui)
            {
                const utf8_t* text[32];
                unsigned int codes[32];
                unsigned int len,count = (unsigned int) m_mem->args[2];
                if (count>32) count=32;
                const uint8_t* p = (uint8_t*)m_mem->strbuf;

                for (unsigned int i=0;i<count;i++)
                {
                    len = *p++; len <<= 8; len |= *p++;
                    if ((len&0x8000)==0)
                    {
                        codes[i] = 0;
                        text[i] = (char*)p;
                        p += len;
                    } else {
                        len &= 0x7fff;
                        len <<= 8;
                        len |= *p++;
                        len <<= 8;
                        len |= *p++;
                        codes[i] = len;
                        text[i] = NULL;
                    }
                }
                m_mem->strbuf[0] = 0;
                m_mem->args[0] = m_Ui->ReportUiDialog((unsigned long) m_mem->args[0] , (unsigned long) m_mem->args[1] , count, codes, text , (utf8_t*)m_mem->strbuf );
                size = strlen((utf8_t*)m_mem->strbuf) + 1;
            } else {
                m_mem->args[0] = -1;
            }
            args = 1;
            break;
        case apBackUpdateCurrentBar:
            m_Ui->UpdateCurrentBar( (unsigned int) m_mem->args[0] );
            break;
        case apBackUpdateTotalBar:
            m_Ui->UpdateTotalBar( (unsigned int) m_mem->args[0] );
            break;
        case apBackSetTitleCollInfo:
            SetTitleCollInfo(Get64(0),(unsigned int) m_mem->args[2]);
            break;
        case apBackSetTitleInfo:
            SetTitleInfo((unsigned int) m_mem->args[0],Get64(1),(unsigned int) m_mem->args[3],(unsigned int) m_mem->args[4],Get64(5));
            break;
        case apBackSetTrackInfo:
            SetTrackInfo((unsigned int) m_mem->args[0],(unsigned int) m_mem->args[1],Get64(2));
            break;
        case apBackSetChapterInfo:
            SetChapterInfo((unsigned int) m_mem->args[0],(unsigned int) m_mem->args[1],Get64(2));
            break;
        default:
            DebugFail(r,NULL);
            m_mem->args[0] = 0;
            *(volatile uintptr_t*)(m_mem->args + 30) = (uintptr_t)(void*)AbiTag;
            args = 1;
            break;
        }

        cmd = CmdPack(apClientDone,args,size);
    }
}

bool CApClient::EnableDebug(const char* LogName)
{
    m_debug = ApDebugOpen(LogName);
    return (m_debug!=0);
}

void CApClient::DebugFailRoutine(uintptr_t arg0,const char* arg1,int line)
{
    char    buffer[1024];

    if (m_debug==0) return;
    sprintf_s(buffer,sizeof(buffer),"DEBUG: %p %s %u\n",((void*)arg0),(arg1==NULL)?"(null)":arg1,line);

    ApDebugOut(m_debug,buffer);
}

void CApClient::ITransport::DebugFailRoutine(uintptr_t arg0, const char* arg1, int line)
{
    m_client->DebugFailRoutine(arg0, arg1, line);
}

size_t CApClient::SetUtf8(const char* Str)
{
    size_t size;

    if (NULL == Str)
    {
        size = 0;
    } else {
        size = strlen(Str) + 1;
        memcpy((uint8_t*)m_mem->strbuf, Str, size);
    }
    return size;
}

size_t CApClient::SetUtf16(const utf16_t* Str)
{
    size_t size;

    if (NULL == Str)
    {
        size = 0;
    } else {
        size = utf16toutf8((char*)m_mem->strbuf, 65000, Str, utf16len(Str) + 1);
    }
    return size;
}

