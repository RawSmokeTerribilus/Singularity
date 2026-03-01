/*
    libDriveIo - MMC drive interrogation library

    Copyright (C) 2007-2025 GuinpinSoft inc <libdriveio@makemkv.com>

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
#include <stddef.h>
#include <stdint.h>
#include <driveio/scsicmd.h>
#include <driveio/driveio.h>
#include <driveio/error.h>
#include <stdlib.h>
#include <string.h>

#ifdef DRIVEIO_HAVE_ARCHDEFS
#include <archdefs.h>
#endif

namespace LibDriveIo
{

class CDriveInfoItem
{
public:
    CDriveInfoItem* m_next;
    DriveInfoItem   m_item;
private:
    CDriveInfoItem(const uint8_t* Data,size_t Size)
    {
        m_item.Data = Data;
        m_item.Size = Size;
    }
    ~CDriveInfoItem()
    {
    }
    void* operator new(size_t,CDriveInfoItem* p)
    {
        return p;
    }
    void operator delete(void*,CDriveInfoItem*)
    {
    }
public:
    static CDriveInfoItem* Create(size_t Size);
    static void Destroy(CDriveInfoItem* Ptr);
};

class CDriveInfoList
{
private:
    CDriveInfoItem* m_first;
    CDriveInfoItem* m_last;
    size_t          m_count;
public:
    CDriveInfoList()
    {
        m_first=NULL;
        m_last=NULL;
        m_count=0;
    }
    ~CDriveInfoList();
    bool AddItem(DriveInfoId Id,const void* Data,size_t Size);
    bool AddOrUpdateItem(DriveInfoId Id, const void* Data, size_t Size);
    bool CopyAllItemsFrom(const CDriveInfoList* Src);
    void MoveAllItemsFrom(CDriveInfoList* Src);
    size_t GetCount();
    CDriveInfoItem* GetItem(size_t Index);
    bool GetItemById(DriveInfoId Id,DriveInfoItem *Item);
    bool RemoveItem(size_t Index);
    bool RemoveItemById(DriveInfoId Id);
    size_t Serialize(void* Buffer,size_t BufferSize);
    bool Deserialize(const void* Buffer,size_t BufferSize);
    void* operator new(size_t,CDriveInfoList* p)
    {
        return p;
    }
    void operator delete(void*,CDriveInfoList*)
    {
    }
private:
    void AddItem(CDriveInfoItem* pitem);
};

CDriveInfoItem* CDriveInfoItem::Create(size_t Size)
{
    size_t all_size = sizeof(CDriveInfoItem) + Size;

    CDriveInfoItem* pitem = (CDriveInfoItem*) malloc(all_size);
    if (NULL==pitem) return NULL;

    return new(pitem) CDriveInfoItem( ((uint8_t*)pitem) + sizeof(CDriveInfoItem) , Size );
}

void CDriveInfoItem::Destroy(CDriveInfoItem* Ptr)
{
    Ptr->~CDriveInfoItem();
    free(Ptr);
}

CDriveInfoList::~CDriveInfoList()
{
    CDriveInfoItem* pitem;
    while(m_first!=NULL)
    {
        pitem = m_first;
        m_first = pitem->m_next;

        CDriveInfoItem::Destroy(pitem);
    }
}

bool CDriveInfoList::AddItem(DriveInfoId Id,const void* Data,size_t Size)
{
    CDriveInfoItem* pitem = CDriveInfoItem::Create(Size);
    if (NULL==pitem) return false;

    memcpy( (void*) pitem->m_item.Data,Data,Size);
    pitem->m_item.Id = Id;

    AddItem(pitem);

    return true;
}

void CDriveInfoList::AddItem(CDriveInfoItem* pitem)
{
    pitem->m_next = NULL;

    if (NULL == m_first)
    {
        m_first = pitem;
    } else {
        m_last->m_next = pitem;
    }

    m_last = pitem;
    m_count++;
}

size_t CDriveInfoList::GetCount()
{
    return m_count;
}

CDriveInfoItem* CDriveInfoList::GetItem(size_t Index)
{
    if (Index>=m_count) return NULL;

    CDriveInfoItem* pitem;

    if (Index==(m_count-1))
    {
        pitem = m_last;
    } else {
        // slist is way too slow for random access.
        // on the other hand this list normally contains less than
        // 100 items, so enumeration/search performance should
        // not be an issue
        pitem = m_first;
        for (size_t i=0;i<Index;i++)
        {
            pitem = pitem->m_next;
        }
    }

    return pitem;
}

bool CDriveInfoList::RemoveItem(size_t Index)
{
    if (Index >= m_count) return false;

    if (m_count == 1)
    {
        CDriveInfoItem::Destroy(m_first);
        m_first = m_last = NULL;
        m_count = 0;
        return true;
    }

    CDriveInfoItem* p_item = NULL;
    if (Index == 0)
    {
        p_item = m_first;
        m_first = p_item->m_next;
        CDriveInfoItem::Destroy(p_item);
        m_count--;
        return true;
    }

    CDriveInfoItem* p_prev = m_first;
    for (unsigned int i = 1; i < Index; i++)
    {
        p_prev = p_prev->m_next;
    }
    p_item = p_prev->m_next;

    p_prev->m_next = p_item->m_next;
    if (Index == (m_count - 1))
    {
        m_last = p_prev;
    }

    CDriveInfoItem::Destroy(p_item);
    m_count--;
    return true;
}

bool CDriveInfoList::RemoveItemById(DriveInfoId Id)
{
    size_t ndx = 0;
    for (CDriveInfoItem* pitem = m_first; pitem != NULL; pitem = pitem->m_next)
    {
        if (pitem->m_item.Id == Id)
        {
            return RemoveItem(ndx);
        }
        ndx++;
    }
    return false;
}

bool CDriveInfoList::GetItemById(DriveInfoId Id,DriveInfoItem *Item)
{
    CDriveInfoItem* pitem;

    for (pitem=m_first;pitem!=NULL;pitem=pitem->m_next)
    {
        if (pitem->m_item.Id==Id)
        {
            *Item = pitem->m_item;
            return true;
        }
    }
    return false;
}

bool CDriveInfoList::AddOrUpdateItem(DriveInfoId Id, const void* Data, size_t Size)
{
    CDriveInfoItem* pitem;

    for (pitem = m_first; pitem != NULL; pitem = pitem->m_next)
    {
        if (pitem->m_item.Id == Id)
        {
            if (pitem->m_item.Size >= Size)
            {
                pitem->m_item.Size = Size;
                memcpy((void*)(pitem->m_item.Data), Data, Size);
            } else {
                return false;
            }
        }
    }

    return AddItem(Id,Data,Size);
}

bool CDriveInfoList::CopyAllItemsFrom(const CDriveInfoList* Src)
{
    CDriveInfoItem* pitem;
    CDriveInfoList  temp;
    bool r = true;

    for (pitem = Src->m_first; pitem != NULL; pitem = pitem->m_next)
    {
        if (pitem->m_item.Id == diid_DriveioTag) continue;
        if (false == temp.AddItem(pitem->m_item.Id, pitem->m_item.Data, pitem->m_item.Size))
        {
            r = false;
            break;
        }
    }
    if (r)
    {
        MoveAllItemsFrom(&temp);
    }

    return r;
}

void CDriveInfoList::MoveAllItemsFrom(CDriveInfoList* Src)
{
    CDriveInfoItem *pitem,*pnext;

    pnext = Src->m_first;
    while (pnext != NULL)
    {
        pitem = pnext;
        pnext = pnext->m_next;

        if (pitem->m_item.Id == diid_DriveioTag) continue;
        this->AddItem(pitem);
    }

    Src->m_first = Src->m_last = NULL;
    Src->m_count = 0;
}

static void uint32_put_ns(uint32_t Value,void *Buf)
{
    ((uint8_t*)Buf)[0] = (uint8_t)(Value>>(3*8));
    ((uint8_t*)Buf)[1] = (uint8_t)(Value>>(2*8));
    ((uint8_t*)Buf)[2] = (uint8_t)(Value>>(1*8));
    ((uint8_t*)Buf)[3] = (uint8_t)(Value>>(0*8));
}

size_t CDriveInfoList::Serialize(void* Buffer,size_t BufferSize)
{
    CDriveInfoItem* pitem;
    size_t all_size=0;
    uint8_t* bptr;

    // calculate size
    for (pitem = m_first;pitem!=NULL;pitem=pitem->m_next)
    {
        if (pitem->m_item.Size>=0x7fffffff) return 0;
        all_size+=(2*sizeof(uint32_t));
        all_size+=pitem->m_item.Size;
    }

    if (Buffer==NULL)
    {
        return all_size;
    }

    if (BufferSize<all_size)
    {
        return 0;
    }

    bptr = (uint8_t*) Buffer;
    for (pitem = m_first;pitem!=NULL;pitem=pitem->m_next)
    {
        uint32_put_ns((uint32_t)(pitem->m_item.Id),bptr);
        uint32_put_ns((uint32_t)(pitem->m_item.Size),bptr+4);
        memcpy(bptr+8,pitem->m_item.Data,pitem->m_item.Size);
        bptr += (8+pitem->m_item.Size);
    }

    return all_size;
}

bool CDriveInfoList::Deserialize(const void* Buffer,size_t BufferSize)
{
    size_t rest=BufferSize;
    const char * pbuf = (const char*)Buffer;

    while(rest!=0)
    {
        size_t sz;
        DriveInfoItem item;

        if (rest<8) return false;
        sz = DriveInfoList_GetSerializedChunkSize(pbuf);
        if (sz>rest)
        {
            return false;
        }
        DriveInfoList_GetSerializedChunkInfo(pbuf,&item);

        if (!AddItem(item.Id,item.Data,item.Size)) return false;

        pbuf += sz;
        rest -= sz;
    }
    return true;
}

}; // namespace LibDriveIo

//
// C wrappers
//
using namespace LibDriveIo;

#ifdef ARCH_NAME
#define LIBDRIVEIO_PLATFORM "[" ARCH_NAME "]"
#else
#define LIBDRIVEIO_PLATFORM ""
#endif

extern "C" DIO_INFOLIST DIO_CDECL DriveInfoList_Create()
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) malloc(sizeof(LibDriveIo::CDriveInfoList));
    if (NULL==plist) return NULL;

    new(plist) LibDriveIo::CDriveInfoList();

    static const char TagText[] = "\n\n\nCreated by libdriveio v" LIBDRIVEIO_VERSION LIBDRIVEIO_PLATFORM " http://www.makemkv.com/libdriveio\n\n\n";

    plist->AddItem(diid_DriveioTag,TagText,sizeof(TagText));

    return (DIO_INFOLIST) plist;
}

extern "C" void DIO_CDECL DriveInfoList_Destroy(DIO_INFOLIST List)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;
    if (NULL==plist) return;

    plist->~CDriveInfoList();

    free(plist);
}

extern "C" int DIO_CDECL DriveInfoList_AddItem(DIO_INFOLIST List,DriveInfoId Id,const void* Data,size_t Size)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;
    if (plist == NULL) return DRIVEIO_ERROR_INVALID_ARG;

    return plist->AddItem(Id,Data,Size) ? 0 : DRIVEIO_ERR_NO_MEMORY;
}

extern "C" int DIO_CDECL DriveInfoList_AddOrUpdateItem(DIO_INFOLIST List, DriveInfoId Id, const void* Data, size_t Size)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;
    if (plist == NULL) return DRIVEIO_ERROR_INVALID_ARG;

    return plist->AddOrUpdateItem(Id, Data, Size) ? 0 : DRIVEIO_ERR_NO_MEMORY;
}

extern "C" size_t DIO_CDECL DriveInfoList_GetCount(DIO_INFOLIST List)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;
    if (plist == NULL) return 0;

    return plist->GetCount();
}

extern "C" int DIO_CDECL DriveInfoList_GetItem(DIO_INFOLIST List,size_t Index,DriveInfoItem *Item)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;
    if (plist == NULL) return DRIVEIO_ERROR_INVALID_ARG;

    CDriveInfoItem* pitem = plist->GetItem(Index);
    if (NULL==pitem) return DRIVEIO_ERROR_INVALID_ARG;

    *Item = pitem->m_item;

    return 0;
}

extern "C" int DIO_CDECL DriveInfoList_GetItemById(DIO_INFOLIST List,DriveInfoId Id,DriveInfoItem *Item)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;

    if (List==NULL) return DRIVEIO_ERROR_INVALID_ARG;
    return plist->GetItemById(Id,Item) ? 0 : DRIVEIO_ERR_NOT_FOUND;
}

extern "C" int DIO_CDECL DriveInfoList_RemoveItem(DIO_INFOLIST List, size_t Index)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;

    if (List == NULL) return DRIVEIO_ERROR_INVALID_ARG;
    return plist->RemoveItem(Index) ? 0 : DRIVEIO_ERROR_INVALID_ARG;
}

extern "C" int DIO_CDECL DriveInfoList_RemoveItemById(DIO_INFOLIST List, DriveInfoId Id)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;

    if (List == NULL) return DRIVEIO_ERROR_INVALID_ARG;
    return plist->RemoveItemById(Id) ? 0 : DRIVEIO_ERR_NOT_FOUND;
}

extern "C" int DIO_CDECL DriveInfoList_CopyAllItemsFrom(DIO_INFOLIST List, const DIO_INFOLIST Src)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;
    const LibDriveIo::CDriveInfoList* psrc = (const LibDriveIo::CDriveInfoList*) Src;
    return plist->CopyAllItemsFrom(psrc) ? 0 : DRIVEIO_ERR_NO_MEMORY;
}

extern "C" int DIO_CDECL DriveInfoList_MoveAllItemsFrom(DIO_INFOLIST List, DIO_INFOLIST Src)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;
    LibDriveIo::CDriveInfoList* psrc = (LibDriveIo::CDriveInfoList*) Src;
    plist->MoveAllItemsFrom(psrc);
    return 0;
}

extern "C" size_t DIO_CDECL DriveInfoList_Serialize(DIO_INFOLIST List,void* Buffer,size_t BufferSize)
{
    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) List;

    return plist->Serialize(Buffer,BufferSize);
}

extern "C" DIO_INFOLIST DIO_CDECL DriveInfoList_Deserialize(const void* Buffer,size_t BufferSize)
{
    DIO_INFOLIST list = DriveInfoList_Create();
    if (NULL==list) return NULL;

    LibDriveIo::CDriveInfoList* plist = (LibDriveIo::CDriveInfoList*) list;

    if (false==plist->Deserialize(Buffer,BufferSize))
    {
        DriveInfoList_Destroy(list);
        return NULL;
    }

    return list;
}

