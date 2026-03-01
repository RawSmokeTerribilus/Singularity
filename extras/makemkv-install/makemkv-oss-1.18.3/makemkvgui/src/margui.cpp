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
#include <strings.h>

void CGUIApClient::SetOutputFolder(const utf8_t *Name)
{
    SetOutputFolder(SetUtf8(Name));
}

void CGUIApClient::SetOutputFolder(const utf16_t *Name)
{
    SetOutputFolder(SetUtf16(Name));
}

void CGUIApClient::SetOutputFolder(size_t NameSize)
{
    ExecCmd(apCallSetOutputFolder,0, NameSize);
}

bool CGUIApClient::OpenFile(const utf8_t* FileName, uint32_t Flags)
{
    return OpenFile(SetUtf8(FileName), Flags);
}

bool CGUIApClient::OpenFile(const utf16_t* FileName, uint32_t Flags)
{
    return OpenFile(SetUtf16(FileName), Flags);
}

bool CGUIApClient::OpenFile(size_t FileNameSize, uint32_t Flags)
{
    m_mem->args[0]=Flags;
    ExecCmd(apCallOpenFile,1, FileNameSize);
    return (m_mem->args[0]!=0);
}

bool CGUIApClient::OpenTitleCollection(const utf8_t* Source, uint32_t Flags)
{
    return OpenTitleCollection(SetUtf8(Source), Flags);
}

bool CGUIApClient::OpenTitleCollection(const utf16_t* Source, uint32_t Flags)
{
    return OpenTitleCollection(SetUtf16(Source), Flags);
}

bool CGUIApClient::OpenTitleCollection(size_t SourceSize, uint32_t Flags)
{
    m_mem->args[0]=Flags;
    ExecCmd(apCallOpenTitleCollection,1, SourceSize);
    return (m_mem->args[0]!=0);
}

bool CGUIApClient::OpenCdDisk(unsigned int Id,uint32_t Flags)
{
    m_mem->args[0]=Id;
    m_mem->args[1]=Flags;
    ExecCmd(apCallOpenCdDisk,2,0);
    return (m_mem->args[0]!=0);
}

bool CGUIApClient::EjectDisk(unsigned int Id)
{
    m_mem->args[0]=Id;
    ExecCmd(apCallEjectDisk,1,0);
    return (m_mem->args[0]!=0);
}

bool CGUIApClient::SaveAllSelectedTitlesToMkv()
{
    ExecCmd(apCallSaveAllSelectedTitlesToMkv,0,0);
    return (m_mem->args[0]!=0);
}

bool CGUIApClient::BackupDisc(unsigned int Id, const utf8_t* Folder, uint32_t Flags)
{
    return BackupDisc(Id, SetUtf8(Folder), Flags);
}

bool CGUIApClient::BackupDisc(unsigned int Id, const utf16_t* Folder, uint32_t Flags)
{
    return BackupDisc(Id, SetUtf16(Folder), Flags);
}

bool CGUIApClient::BackupDisc(unsigned int Id, size_t FolderSize, uint32_t Flags)
{
    m_mem->args[0]=Id;
    m_mem->args[1]=Flags;
    ExecCmd(apCallBackupDisc,2, FolderSize);
    return (m_mem->args[0]!=0);
}

void AP_UiItem::syncFlags()
{
    if (!isset(&m_flags,7))
    {
        m_client->m_mem->args[0] = (uint32_t)m_handle;
        m_client->m_mem->args[1] = (uint32_t)(m_handle>>32);
        m_client->ExecCmd(apCallGetUiItemState,2,0);
        m_flags = (bmp_type_t)(m_client->m_mem->args[0]) | 0x80;
    }
}

void AP_UiItem::set_Flag(unsigned int Index,bool State)
{
    uint32_t oldFlags;

    syncFlags();

    oldFlags = m_flags;

    if (State)
    {
        setone(&m_flags,Index);
    } else {
        setzero(&m_flags,Index);
    }
    if (oldFlags != m_flags)
    {
        m_client->m_mem->args[0] = (uint32_t)(m_handle);
        m_client->m_mem->args[1] = (uint32_t)(m_handle>>32);
        m_client->m_mem->args[2] = m_flags;
        m_client->ExecCmd(apCallSetUiItemState,3,0);
    }
}

bool AP_UiItem::get_Enabled()
{
    syncFlags();
    return isset(&m_flags,0);
}

bool AP_UiItem::get_Expanded()
{
    syncFlags();
    return isset(&m_flags,1);
}

void AP_UiItem::set_Enabled(bool State)
{
    set_Flag(0,State);
}

void AP_UiItem::set_Expanded(bool State)
{
    set_Flag(1,State);
}

bool AP_UiItem::isset(bmp_type_t bmp[],unsigned int Index)
{
    return ((bmp[Index/BmpBitsPerItem]&(1<<(Index%BmpBitsPerItem)))!=0);
}

void AP_UiItem::setone(bmp_type_t bmp[],unsigned int Index)
{
    bmp[Index/BmpBitsPerItem] |= (1<<(Index%BmpBitsPerItem));
}

void AP_UiItem::setzero(bmp_type_t bmp[],unsigned int Index)
{
    bmp[Index/BmpBitsPerItem] |= (1<<(Index%BmpBitsPerItem));
    bmp[Index/BmpBitsPerItem] ^= (1<<(Index%BmpBitsPerItem));
}

AP_UiItem::AP_UiItem()
{
    bzero(m_infos_alloc,sizeof(m_infos_alloc));
    Clear();
}

AP_UiItem::AP_UiItem(const AP_UiItem&)
{
    bzero(m_infos_alloc,sizeof(m_infos_alloc));
    Clear();
}

AP_UiItem::~AP_UiItem()
{
    Clear();
}

void AP_UiItem::Clear()
{
    for (unsigned int i=0;i<ap_iaMaxValue;i++)
    {
        if (isset(m_infos_alloc,i))
        {
            delete[] m_infos[i];
        }
    }
    bzero(m_infos_known,sizeof(m_infos_known));
    bzero(m_infos_alloc,sizeof(m_infos_alloc));
    bzero(m_infos_write,sizeof(m_infos_write));
    bzero(m_infos_change,sizeof(m_infos_change));
    m_flags = 0;
}

const utf16_t* AP_UiItem::GetInfo(AP_ItemAttributeId Id)
{
    if (isset(m_infos_known,Id)) return m_infos[Id];

    m_client->m_mem->args[0]=(uint32_t)m_handle;
    m_client->m_mem->args[1]=(uint32_t)(m_handle>>32);
    m_client->m_mem->args[2]=Id;
    m_client->ExecCmd(apCallGetUiItemInfo,3,0);
    setone(m_infos_known,Id);
    if (0!=m_client->m_mem->args[0])
    {
        m_infos[Id]=(utf16_t*)AppGetString((unsigned int)m_client->m_mem->args[0]);
        setzero(m_infos_alloc,Id);
    } else {
        if (0==m_client->m_mem->args[1])
        {
            m_infos[Id]=NULL;
            setzero(m_infos_alloc,Id);
        } else {
            const utf8_t* src = (utf8_t*)m_client->m_mem->strbuf;
            size_t len8  = strlen(src);
            size_t len16 = utf8toutf16len(src);
            utf16_t* dst = m_infos[Id] = new utf16_t[len16+1];
            utf8toutf16(dst, len16, src, len8); dst[len16] = 0;
            setone(m_infos_alloc,Id);
        }
    }
    if (m_client->m_mem->args[2])
    {
        setone(m_infos_write,Id);
    }
    return m_infos[Id];
}

bool AP_UiItem::GetInfoWritable(AP_ItemAttributeId Id)
{
    GetInfo(Id);
    return isset(m_infos_write,Id);
}

bool AP_UiItem::GetInfoChanged(AP_ItemAttributeId Id)
{
    return isset(m_infos_change,Id);
}

bool AP_UiItem::GetInfoConst(AP_ItemAttributeId Id)
{
    return !isset(m_infos_alloc,Id);
}

void AP_UiItem::Forget(AP_ItemAttributeId Id)
{
    if (isset(m_infos_alloc,Id))
    {
        delete[] m_infos[Id];
        setzero(m_infos_alloc,Id);
    }
    setzero(m_infos_known,Id);
}

int AP_UiItem::SetInfo(AP_ItemAttributeId Id,const utf16_t* Value)
{
    m_client->m_mem->args[0]=(uint32_t)m_handle;
    m_client->m_mem->args[1]=(uint32_t)(m_handle>>32);
    m_client->m_mem->args[2]=Id;

    size_t size = 0;
    if (Value==NULL)
    {
        m_client->m_mem->args[3]=0;
    } else {
        if (Value[0]==0)
        {
            m_client->m_mem->args[3]=0;
        } else {
            size = m_client->SetUtf16(Value);
            m_client->m_mem->args[3]=1;
        }
    }
    m_client->ExecCmd(apCallSetUiItemInfo,4,size);

    Forget(Id);
    setone(m_infos_change,Id);
    return (int) m_client->m_mem->args[0];
}

int AP_UiItem::RevertInfo(AP_ItemAttributeId Id)
{
    m_client->m_mem->args[0]=(uint32_t)m_handle;
    m_client->m_mem->args[1]=(uint32_t)(m_handle>>32);
    m_client->m_mem->args[2]=Id;
    m_client->m_mem->args[3]=2;
    m_client->ExecCmd(apCallSetUiItemInfo,4,0);

    Forget(Id);
    setzero(m_infos_change,Id);

    return (int) m_client->m_mem->args[0];
}

uint64_t AP_UiItem::GetInfoNumeric(AP_ItemAttributeId Id)
{
    const utf16_t* p = GetInfo(Id);
    if (!p) return 0;

    uint64_t v=0;
    while(*p!=0)
    {
        v *= 10;
        v += (*p-'0');
        p++;
    }
    return v;
}

void AP_UiItem::SetInfo(uint64_t handle,CApClient* client,AP_UiItem::item_type_t type)
{
    m_client = client;
    m_handle = handle;
    m_type = type;
    Clear();
}

void CGUIApClient::SetTrackInfo(unsigned int id,unsigned int trkid,uint64_t handle)
{
    m_TitleCollection.m_Titles[id].m_Tracks[trkid].SetInfo(handle,this,AP_UiItem::uiTrack);
}

void CGUIApClient::SetChapterInfo(unsigned int id,unsigned int chid,uint64_t handle)
{
    m_TitleCollection.m_Titles[id].m_Chapters[chid].SetInfo(handle,this,AP_UiItem::uiOther);
}

void CGUIApClient::SetTitleInfo(unsigned int id,uint64_t handle,unsigned int TrackCount,unsigned int ChapterCount,uint64_t chap_handle)
{
    m_TitleCollection.m_Titles[id].SetInfo(handle,this,AP_UiItem::uiTitle);
    m_TitleCollection.m_Titles[id].m_Tracks.reserve(TrackCount);
    m_TitleCollection.m_Titles[id].m_Tracks.clear();
    m_TitleCollection.m_Titles[id].m_Tracks.resize(TrackCount);
    m_TitleCollection.m_Titles[id].m_Chapters.reserve(ChapterCount);
    m_TitleCollection.m_Titles[id].m_Chapters.clear();
    m_TitleCollection.m_Titles[id].m_Chapters.resize(ChapterCount);
    m_TitleCollection.m_Titles[id].m_ChaptersContainer.SetInfo(chap_handle,this,AP_UiItem::uiOther);
}

void CGUIApClient::SetTitleCollInfo(uint64_t handle,unsigned int Count)
{
    m_TitleCollection.SetInfo(handle,this,AP_UiItem::uiOther);
    m_TitleCollection.m_Titles.reserve(Count);
    m_TitleCollection.m_Titles.clear();
    m_TitleCollection.m_Titles.resize(Count);
    m_TitleCollection.m_Updated=true;
}

const void* CGUIApClient::GetInterfaceLanguageData(unsigned int Id,unsigned int* Size1,unsigned int* Size2)
{
    m_mem->args[0]=Id;
    ExecCmd(apCallGetInterfaceLanguageData,1,0);
    if (m_mem->args[0]==0)
    {
        return NULL;
    }
    *Size1 = (unsigned int) m_mem->args[0];
    *Size2 = (unsigned int) m_mem->args[1];
    return (void*)m_mem->strbuf;
}

int CGUIApClient::SetProfile(unsigned int Index)
{
    m_mem->args[0] = Index;
    ExecCmd(apCallSetProfile,1,0);
    return (int)(m_mem->args[0]);
}

int CGUIApClient::SetExternAppFlags(const uint32_t* Flags,unsigned int Count)
{
    m_mem->args[0] = Count;
    for (unsigned int i = 0; i < Count; i++)
    {
        m_mem->args[i + 1] = Flags[i];
    }
    ExecCmd(apCallSetExternAppFlags,1+Count, 0);
    return (int)(m_mem->args[0]);
}

