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
#include <lgpl/aproxy.h>
#include <strings.h>

void CMMBDApClient::SetTrackInfo(unsigned int id,unsigned int trkid,uint64_t handle)
{
}

void CMMBDApClient::SetChapterInfo(unsigned int id,unsigned int chid,uint64_t handle)
{
}

void CMMBDApClient::SetTitleInfo(unsigned int id,uint64_t handle,unsigned int TrackCount,unsigned int ChapterCount,uint64_t chap_handle)
{
}

void CMMBDApClient::SetTitleCollInfo(uint64_t handle,unsigned int Count)
{
    m_TitleCount = Count;
}

bool CMMBDApClient::OpenMMBD(const utf8_t* Prefix,const utf8_t* Locator)
{
    size_t len = 0, slen;

    if (NULL != Prefix)
    {
        slen = strlen(Prefix);
        memcpy( ((char*)m_mem->strbuf) + len, Prefix, slen);
        len += slen;
    }
    slen = strlen(Locator) + 1;
    memcpy(((char*)m_mem->strbuf) + len, Locator, slen);
    len += slen;

    ExecCmd(apCallOpenMMBD,0,len);
    return (m_mem->args[0]!=0);
}

bool CMMBDApClient::InitMMBD(const utf8_t* argp[])
{
    char* p = (char*)m_mem->strbuf;
    if (argp==NULL)
    {
        m_mem->args[0]=0;
    } else {
        unsigned int count =0;
        while(argp[count]!=NULL)
        {
            size_t len;

            len = strlen(argp[count]) + 1;
            memcpy(p, argp[count], len);
            p += len;

            count ++;
        }
        m_mem->args[0] = count;
    }

    ExecCmd(apCallInitMMBD, 1, p-((char*)m_mem->strbuf) );
    return (m_mem->args[0]!=0);
}

const uint8_t* CMMBDApClient::DiscInfoMMBD(uint32_t *Flags,uint8_t *BusKey,uint8_t *DiscId,uint32_t *MkbVersion,uint32_t* ClipCount)
{
    ExecCmd(apCallDiscInfoMMBD,0,0);

    if (m_mem->args[0]==0) return NULL;

    *Flags = (uint32_t)m_mem->args[1];
    *MkbVersion = (uint32_t)m_mem->args[2];
    *ClipCount = (uint32_t)m_mem->args[3];

    const uint8_t* p = (const uint8_t*)m_mem->strbuf;

    memcpy(BusKey,p,16);
    memcpy(DiscId,p+16,20);

    return p+36;
}

const uint8_t* CMMBDApClient::DecryptUnitMMBD(uint32_t NameFlags,uint32_t* ClipInfo,uint64_t FileOffset,const uint8_t* Data,unsigned int Size)
{
    m_mem->args[0]=NameFlags;
    m_mem->args[1]=*ClipInfo;
    m_mem->args[2]=(uint32_t)FileOffset;
    m_mem->args[3]=(uint32_t)(FileOffset>>32);
    if (Size) memcpy((void*)(m_mem->strbuf),Data,Size);

    ExecCmd(apCallDecryptUnitMMBD,4,Size);

    if (m_mem->args[0]==0) return NULL;

    *ClipInfo = (uint32_t)m_mem->args[1];

    return (const uint8_t*)(m_mem->strbuf);
}

