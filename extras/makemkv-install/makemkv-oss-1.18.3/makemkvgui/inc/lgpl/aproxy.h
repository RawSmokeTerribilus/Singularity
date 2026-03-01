/*
    MakeMKV GUI - Graphics user interface application for MakeMKV

    Written by GuinpinSoft inc <makemkvgui@makemkv.com>

    This file is hereby placed into public domain,
    no copyright is claimed.

*/
#ifndef LGPL_APROXY_H_INCLUDED
#define LGPL_APROXY_H_INCLUDED

#include <stddef.h>
#include <stdint.h>
#include <lgpl/stl.h>
#include <lgpl/utf8.h>

typedef uint16_t    utf16_t;
typedef char        utf8_t;

static inline size_t utf16len(const utf16_t *SrcString)
{
    const uint16_t *p=SrcString;
    while(*p!=0)
    {
        p++;
    }
    return (p-SrcString);
}

//
// sh mem
//
typedef struct _AP_SHMEM
{
    uint32_t    cmd;
    uint32_t    flags;
    uint32_t    pad1;
    uint32_t    pad2;
    uint32_t    args[32];
    uint8_t     strbuf[65008];
} AP_SHMEM;

static const uint32_t AP_SHMEM_FLAG_START   = 0x01000000;
static const uint32_t AP_SHMEM_FLAG_EXIT    = 0x02000000;
static const uint32_t AP_SHMEM_FLAG_NOMEM   = 0x04000000;

//
// sem
//
typedef struct _AP_SGRP
{
    uintptr_t   a_id;
    uintptr_t   b_id;
} AP_SGRP;

//
// commands
//
typedef enum _AP_CMD
{
    apNop=0,
    apReturn,
    apClientDone,
    apCallSignalExit,
    apCallOnIdle,
    apCallCancelAllJobs,

    apCallSetOutputFolder=16,
    apCallUpdateAvailableDrives,
    apCallOpenFile,
    apCallOpenCdDisk,
    apCallOpenTitleCollection,
    apCallCloseDisk,
    apCallEjectDisk,
    apCallSaveAllSelectedTitlesToMkv,
    apCallGetUiItemState,
    apCallSetUiItemState,
    apCallGetUiItemInfo,
    apCallGetSettingInt,
    apCallGetSettingString,
    apCallSetSettingInt,
    apCallSetSettingString,
    apCallSaveSettings,
    apCallAppGetString,
    apCallBackupDisc,
    apCallGetInterfaceLanguageData,
    apCallSetUiItemInfo,
    apCallSetProfile,
    apCallInitMMBD,
    apCallOpenMMBD,
    apCallDiscInfoMMBD,
    apCallDecryptUnitMMBD,
    apCallSetExternAppFlags,
    apCallManageState,
    apCallAppSetString,

    apBackEnterJobMode=192,
    apBackLeaveJobMode,
    apBackUpdateDrive,
    apBackUpdateCurrentBar,
    apBackUpdateTotalBar,
    apBackUpdateLayout,
    apBackSetTotalName,
    apBackUpdateCurrentInfo,
    apBackReportUiMessage,
    apBackExit,
    apBackSetTitleCollInfo,
    apBackSetTitleInfo,
    apBackSetTrackInfo,
    apBackSetChapterInfo,
    apBackReportUiDialog,

    apBackFatalCommError=224,
    apBackOutOfMem,
    apUnknown=239
} AP_CMD;

#define AP_ABI_VER "A0001"

typedef uint32_t AP_DiskFsFlags;
typedef uint32_t AP_DriveState;

#include <lgpl/apdefs.h>

//
// Wrappers
//
class CApClient;

class AP_UiItem
{
    friend class CGUIApClient;
public:
    static const unsigned int   AP_ItemMaxCount = 64;
    static const unsigned int   BmpBitsPerItem = 32;
    typedef uint32_t bmp_type_t;
    typedef enum _item_type_t
    {
        uiOther,
        uiTitle,
        uiTrack,
        uiMax
    } item_type_t;
private:
    CApClient*  m_client;
    uint64_t    m_handle;
    bmp_type_t  m_flags;
    utf16_t*    m_infos[ap_iaMaxValue];
    bmp_type_t  m_infos_known[AP_ItemMaxCount/BmpBitsPerItem];
    bmp_type_t  m_infos_alloc[AP_ItemMaxCount/BmpBitsPerItem];
    bmp_type_t  m_infos_write[AP_ItemMaxCount/BmpBitsPerItem];
    bmp_type_t  m_infos_change[AP_ItemMaxCount/BmpBitsPerItem];
    item_type_t m_type;
public:
    AP_UiItem();
    ~AP_UiItem();
    void Clear();
    bool    get_Enabled();
    void    set_Enabled(bool State);
    bool    get_Expanded();
    void    set_Expanded(bool State);
    void    syncFlags();
    void    set_Flag(unsigned int Index,bool State);
    const utf16_t* GetInfo(AP_ItemAttributeId Id);
    int SetInfo(AP_ItemAttributeId Id,const utf16_t* Value);
    uint64_t GetInfoNumeric(AP_ItemAttributeId Id);
    bool GetInfoWritable(AP_ItemAttributeId Id);
    bool GetInfoChanged(AP_ItemAttributeId Id);
    bool GetInfoConst(AP_ItemAttributeId Id);
    void Forget(AP_ItemAttributeId Id);
    int RevertInfo(AP_ItemAttributeId);
    void SetInfo(uint64_t handle,CApClient* client,AP_UiItem::item_type_t Type);
    static bool isset(bmp_type_t bmp[],unsigned int Index);
    static void setone(bmp_type_t bmp[],unsigned int Index);
    static void setzero(bmp_type_t bmp[],unsigned int Index);
public:
    void operator=(const AP_UiItem&) {}
    AP_UiItem(const AP_UiItem&);
    AP_UiItem::item_type_t type() { return m_type; }
};

class AP_UiTitle : public AP_UiItem
{
    friend class CGUIApClient;
private:
    AP_UiItem               m_ChaptersContainer;
    stl::vector<AP_UiItem>  m_Tracks;
    stl::vector<AP_UiItem>  m_Chapters;
public:
    unsigned int GetTrackCount()
    {
        return (unsigned int) m_Tracks.size();
    }
    AP_UiItem* GetTrack(unsigned int Index)
    {
        return &m_Tracks[Index];
    }
    unsigned int GetChapterCount()
    {
        return (unsigned int) m_Chapters.size();
    }
    AP_UiItem* GetChapter(unsigned int Index)
    {
        return &m_Chapters[Index];
    }
    AP_UiItem* GetChapters()
    {
        return &m_ChaptersContainer;
    }
};

class AP_UiTitleCollection : public AP_UiItem
{
    friend class CGUIApClient;
private:
    stl::vector<AP_UiTitle> m_Titles;
public:
    bool        m_Updated;
public:
    unsigned int GetCount()
    {
        return (unsigned int)m_Titles.size();
    }
    AP_UiTitle* GetTitle(unsigned int Index)
    {
        return &m_Titles[Index];
    }
};

//
// ap class
//
class CApClient
{
public:
    static uint32_t inline CmdPack(AP_CMD Cmd, unsigned int ArgCount, size_t DataSize)
    {
        return (((uint32_t)Cmd) << 24) | (ArgCount << 16) | (DataSize & 0xffff);
    }
public:
    class ITransport
    {
    protected:
        CApClient* m_client;
    public:
        virtual bool Init1(char* Name) = 0;
        virtual bool Init2(CApClient* client, const char* response, const uint64_t* stdh) = 0;
        virtual bool Transact() = 0;
    protected:
        void DebugFailRoutine(uintptr_t arg0, const char* arg1, int line);
    };
    class INotifier
    {
    public:
        virtual void SetTotalName(unsigned long Name)=0;
        virtual void UpdateCurrentBar(unsigned int Value)=0;
        virtual void UpdateTotalBar(unsigned int Value)=0;
        virtual void UpdateLayout(unsigned long CurrentName,unsigned int NameSubindex,unsigned int Flags,unsigned int Size,const unsigned long* Names)=0;
        virtual void UpdateCurrentInfo(unsigned int Index,const utf8_t* Value)=0;
        virtual void EnterJobMode(unsigned int Flags)=0;
        virtual void LeaveJobMode()=0;
        virtual void ExitApp()=0;
        virtual void UpdateDrive(unsigned int Index,const utf8_t *DriveName,AP_DriveState DriveState,const utf8_t *DiskName,const utf8_t *DeviceName,AP_DiskFsFlags DiskFlags,const void* DiskData,unsigned int DiskDataSize)=0;
        virtual int  ReportUiMessage(unsigned long Code,unsigned long Flags,const utf8_t* Text,uint64_t ExtraData)=0;
        virtual int  ReportUiDialog(unsigned long Code,unsigned long Flags,unsigned int Count,const unsigned int* Codes,const utf8_t* Text[], utf8_t* Buffer)=0;
    };
private:
    ITransport* m_Transport;
    INotifier*  m_Ui;
    bool        m_shutdown;
    uintptr_t   m_debug;
public:
    volatile AP_SHMEM *m_mem;
public:
    void ExecCmdPacked(uint32_t CmdHdr);
    inline void ExecCmd(AP_CMD Cmd, unsigned int ArgCount, size_t DataSize)
    {
        ExecCmdPacked(CmdPack(Cmd, ArgCount, DataSize));
    }
private:
    AP_CMD Transact(uint32_t CmdHdr);
    void ReportFatalError(uint32_t code);
public:
    bool EnableDebug(const char* LogName);
    bool Init(ITransport* Transport, const char* AppName,unsigned int* Code);
    void SetUiNotifier(CApClient::INotifier* Notifier);
    CApClient();
    void AppExiting();
    size_t SetUtf8(const char* Str);
    size_t SetUtf16(const utf16_t* Str);
public:
    void SignalExit();
    void CancelAllJobs();
    void OnIdle();
    bool UpdateAvailableDrives(uint32_t Flags);
    bool CloseDisk(unsigned int EjectEd);
    int GetSettingInt(ApSettingId id);
    const utf8_t* GetSettingString(ApSettingId id);
    void SetSettingInt(ApSettingId id,int Value);
    void SetSettingString(ApSettingId id, const utf8_t* Value);
    void SetSettingString(ApSettingId id, const utf16_t* Value);
    void SetAppString(unsigned int id, const utf8_t* Value, unsigned int Index1 = 0, unsigned int Index2 = 0);
    void SetAppString(unsigned int id, const utf16_t* Value, unsigned int Index1 = 0, unsigned int Index2 = 0);
    void SetAppString(unsigned int id, size_t Size, const utf8_t* Value, unsigned int Index1 = 0, unsigned int Index2 = 0);
    bool SaveSettings();
    const utf8_t* GetAppString(unsigned int Id,unsigned int Index1=0,unsigned int Index2=0);
private:
    void SetSettingString(ApSettingId id, size_t ValueSize);
    void SetAppString(size_t ValueSize, unsigned int Id, unsigned int Index1, unsigned int Index2);
private:
    virtual void SetTitleCollInfo(uint64_t handle,unsigned int Count)=0;
    virtual void SetTitleInfo(unsigned int id,uint64_t handle,unsigned int TrackCount,unsigned int ChapterCount,uint64_t chap_handle)=0;
    virtual void SetTrackInfo(unsigned int id,unsigned int trkid,uint64_t handle)=0;
    virtual void SetChapterInfo(unsigned int id,unsigned int chid,uint64_t handle)=0;
private:
    void DebugFailRoutine(uintptr_t arg0,const char* arg1,int line);
    void DebugOut(const char* string);
private:
    inline uint64_t Get64(unsigned int index)
    {
        return m_mem->args[index] | (((uint64_t)(m_mem->args[index + 1])) << 32);
    }
};
#define DebugFail(arg0,arg1) DebugFailRoutine(arg0,arg1,__LINE__)

class CGUIApClient : public CApClient
{
public:
    AP_UiTitleCollection    m_TitleCollection;
private:
    void SetTitleCollInfo(uint64_t handle,unsigned int Count);
    void SetTitleInfo(unsigned int id,uint64_t handle,unsigned int TrackCount,unsigned int ChapterCount,uint64_t chap_handle);
    void SetTrackInfo(unsigned int id,unsigned int trkid,uint64_t handle);
    void SetChapterInfo(unsigned int id,unsigned int chid,uint64_t handle);
public:
    void SetOutputFolder(const utf8_t *Name);
    void SetOutputFolder(const utf16_t *Name);
    bool OpenFile(const utf8_t* FileName,uint32_t Flags);
    bool OpenFile(const utf16_t* FileName,uint32_t Flags);
    bool OpenCdDisk(unsigned int Id,uint32_t Flags);
    bool OpenTitleCollection(const utf8_t* Source,uint32_t Flags);
    bool OpenTitleCollection(const utf16_t* Source,uint32_t Flags);
    bool EjectDisk(unsigned int Id);
    bool SaveAllSelectedTitlesToMkv();
    bool BackupDisc(unsigned int Id,const utf8_t* Folder,uint32_t Flags);
    bool BackupDisc(unsigned int Id,const utf16_t* Folder,uint32_t Flags);
    const void* GetInterfaceLanguageData(unsigned int Id,unsigned int* Size1,unsigned int* Size2);
    int SetProfile(unsigned int Index);
    int SetExternAppFlags(const uint32_t* Flags,unsigned int Count);
private:
    void SetOutputFolder(size_t NameSize);
    bool OpenFile(size_t FileNameSize, uint32_t Flags);
    bool OpenTitleCollection(size_t SourceSize, uint32_t Flags);
    bool BackupDisc(unsigned int Id, size_t FolderSize, uint32_t Flags);
};

class CMMBDApClient : public CApClient
{
public:
    unsigned int            m_TitleCount;
private:
    void SetTitleCollInfo(uint64_t handle,unsigned int Count);
    void SetTitleInfo(unsigned int id,uint64_t handle,unsigned int TrackCount,unsigned int ChapterCount,uint64_t chap_handle);
    void SetTrackInfo(unsigned int id,unsigned int trkid,uint64_t handle);
    void SetChapterInfo(unsigned int id,unsigned int chid,uint64_t handle);
public:
    CMMBDApClient() { m_TitleCount=0; }
    bool InitMMBD(const char* argp[]);
    bool OpenMMBD(const char* Prefix,const char* Locator);
    const uint8_t* DiscInfoMMBD(uint32_t *Flags,uint8_t *BusKey,uint8_t *DiscId,uint32_t *MkbVersion,uint32_t* ClipCount);
    const uint8_t* DecryptUnitMMBD(uint32_t NameFlags,uint32_t* ClipInfo,uint64_t FileOffset,const uint8_t* Data,unsigned int Size);
};

class CShMemTransport : public CApClient::ITransport
{
private:
    AP_SGRP     m_sem;
public:
    bool Init1(char* Name) override;
    bool Init2(CApClient* client, const char* response, const uint64_t* stdh) override;
    bool Transact() override;
};

#ifndef AP_SEM_TIMEOUT
#define AP_SEM_TIMEOUT 29
#endif

class CPipeTransport
{
protected:
    virtual bool SendData(const void* Buffer, unsigned int Size) = 0;
    virtual bool RecvData(void* Buffer, unsigned int Size, unsigned int *p_Received) = 0;
protected:
    bool SendCmd(AP_SHMEM* p_mem);
    bool RecvCmd(AP_SHMEM* p_mem);
};

class CStdPipeTransport : public CApClient::ITransport , private CPipeTransport
{
private:
    uint64_t    m_hrd;
    uint64_t    m_hwr;
public:
    bool Init1(char* Name) override;
    bool Init2(CApClient* client, const char* response, const uint64_t* stdh) override;
private:
    bool Transact() override;
    bool SendData(const void* Buffer, unsigned int Size) override;
    bool RecvData(void* Buffer, unsigned int Size, unsigned int *p_Received) override;
public:
    CStdPipeTransport() : m_hrd(0), m_hwr(0) {}
};

#if 0
class CNetPipeTransport : public CPipeTransport
{
private:
    SOCKET      m_srd;
    SOCKET      m_swr;
    uint32_t    m_proto;
    union _addr
    {
        struct sockaddr     s;
        struct sockaddr_in  s4;
        struct sockaddr_in6 s6;
    } m_addr;
private:
    bool SendData(const void* Buffer, unsigned int Size) override;
    bool RecvData(void* Buffer, unsigned int Size, unsigned int *p_Received) override;
protected:
    CNetPipeTransport() : m_srd(0), m_swr(0), m_proto(0) {}
    bool ParseAddress(const char* AddrString);
public:
    bool InitClient(const char* AddrString);
};

class CNetTransport : public CApClient::ITransport, private CNetPipeTransport
{
public:
    bool Init1(char* Name) override;
    bool Init2(CApClient* client, const char* response, const uint64_t* stdh) override;
private:
    bool Transact() override;
};
#endif


//
// API
//
int  ApSpawnApp(char* verstr, const char* AppName, uint64_t* stdh);
void*   ApOpenShmem(const char *name);
bool ApOpenSgrp(AP_SGRP *sgrp,const uint64_t *data);
bool ApSemInc(AP_SGRP *sgrp,uintptr_t sid);
bool ApSemDec(AP_SGRP *sgrp,uintptr_t sid);
uintptr_t ApDebugOpen(const char* name);
void ApDebugOut(uintptr_t file,const char* string);
void ApDebugDump(const char* name, const void* buffer, unsigned int size);
int ApClosePipe(uint64_t handle);
int ApReadPipe(uint64_t handle,void* buffer,unsigned int size,unsigned int timeout);
int ApWritePipe(uint64_t handle,const void* buffer,unsigned int size);


//
// UI
//
extern const utf16_t* AppGetString(unsigned int code);
extern const utf8_t*  AppGetStringUtf8(unsigned int code);
extern bool AppGetInterfaceLanguageData(CGUIApClient* app);

#define AP_UI_STRING(msg) AppGetString(msg)

#endif
