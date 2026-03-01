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


bool CStdPipeTransport::Init1(char* name)
{
    strcpy(name, "std");
    return true;
}

bool CStdPipeTransport::Init2(CApClient* client, const char* response,const uint64_t* stdh)
{
    uint8_t c;

    m_hrd = stdh[0];
    m_hwr = stdh[1];

    client->m_mem = (AP_SHMEM*)malloc(sizeof(AP_SHMEM));
    if (NULL == client->m_mem)
    {
        DebugFail(0, "ma");
        return false;
    }
    memset((void*)client->m_mem, 0, sizeof(AP_SHMEM));

    do
    {
        if (1 != ApReadPipe(m_hrd, &c, 1, AP_SEM_TIMEOUT))
        {
            DebugFail(0, "rdm");
            return false;
        }
    } while (c != 0xaa);

    c = 0xbb;
    if (1 != ApWritePipe(m_hwr, &c, 1))
    {
        DebugFail(0, "wrm");
        return false;
    }

    m_client = client;

    DebugFail(0,"ok");
    return true;
}

bool CStdPipeTransport::Transact()
{
    if (false == SendCmd((AP_SHMEM*)m_client->m_mem))
    {
        return false;
    }

    if (false == RecvCmd((AP_SHMEM*)m_client->m_mem))
    {
        return false;
    }

    return true;
}

bool CStdPipeTransport::SendData(const void* Buffer, unsigned int Size)
{
    return (Size == ApWritePipe(m_hwr, Buffer, Size));
}

bool CStdPipeTransport::RecvData(void* Buffer, unsigned int Size, unsigned int *p_Received)
{
    int r = ApReadPipe(m_hrd, Buffer, Size, AP_SEM_TIMEOUT);
    if (r <= 0) return false;
    *p_Received = r;
    return true;
}

