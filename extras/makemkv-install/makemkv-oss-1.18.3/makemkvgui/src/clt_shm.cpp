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

bool CShMemTransport::Init1(char* name)
{
    strcpy(name, "shm");

    return true;
}

bool CShMemTransport::Init2(CApClient* client, const char* response,const uint64_t* stdh)
{
    ApClosePipe(stdh[0]);

    client->m_mem = (AP_SHMEM*) ApOpenShmem(response);
    if (NULL== client->m_mem)
    {
        DebugFail(0,NULL);
        return false;
    }

    if (false==ApOpenSgrp(&m_sem,(uint64_t*)client->m_mem->args))
    {
        DebugFail(0,NULL);
        return false;
    }

    client->m_mem->flags |= AP_SHMEM_FLAG_START;

    m_client = client;

    DebugFail(0,"ok");
    return true;
}

bool CShMemTransport::Transact()
{
    if (0 != (m_client->m_mem->flags&AP_SHMEM_FLAG_NOMEM)) return false;

    if (false==ApSemInc(&m_sem,m_sem.a_id))
    {
        return false;
    }

    if (0 != (m_client->m_mem->flags&AP_SHMEM_FLAG_NOMEM)) return false;

    if (false==ApSemDec(&m_sem,m_sem.b_id))
    {
        return false;
    }

    if (0 != (m_client->m_mem->flags&AP_SHMEM_FLAG_NOMEM)) return false;

    return true;
}

