/*
    GPL is cancer. A hacky and otherwise useless glue code to comply with GPL licensing.

    Copyright (C) 2007-2025 GuinpinSoft inc <mmgpl@makemkv.com>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

*/
#include <dvdnav/mmdvdnav.h>
#include <dvdread/dvd_reader.h>
#include <lgpl/stl.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <dvdread_internal.h>
#include <dvdnav/navbase.h>

static const unsigned int MaxVtsCount = 100;

struct ifo_entry_t
{
    uint8_t*        data;
    unsigned int    size;
    uint32_t        tvob_offset;

    ifo_entry_t() : data(NULL) , tvob_offset(0) {}
};

static stl::vector< ifo_entry_t>    g_ifo_entries;

static uint8_t* data_malloc(unsigned int size);

bool DvdNavAddIfo(unsigned int id, unsigned int size, uint32_t tvob_offset, const uint8_t* data, unsigned int data_size)
{
    if (id >= MaxVtsCount) return false;

    if (g_ifo_entries.size() <= id)
    {
        g_ifo_entries.resize(id + 1);
    }

    if (NULL != g_ifo_entries[id].data) return false;

    g_ifo_entries[id].data = data_malloc(size);
    if (NULL == g_ifo_entries[id].data) return false;
    g_ifo_entries[id].size = size;
    g_ifo_entries[id].tvob_offset = tvob_offset;

    memcpy(g_ifo_entries[id].data, data, data_size);

    return true;
}

bool DvdNavSetIfo(unsigned int id, unsigned int offset, const uint8_t* data, unsigned int data_size)
{
    if (g_ifo_entries.size() <= id) return false;
    if (NULL == g_ifo_entries[id].data) return false;
    if (offset  > g_ifo_entries[id].size) return false;
    if ((offset + data_size) > g_ifo_entries[id].size) return false;

    memcpy(g_ifo_entries[id].data + offset, data, data_size);

    return true;
}

typedef stl::map<uint32_t, uint8_t*> data_map_t;
typedef stl::vector<data_map_t*> data_map_vector_t;

data_map_vector_t g_data_vmg;
data_map_vector_t g_data_vts;
data_map_t        g_data_phys;

static data_map_t* GetDataMap(uint32_t* p_key, unsigned int id, uint32_t sector)
{
    bool is_menu = (0 != (id&FLAG_MENU_VOB));
    unsigned int n = id & VTS_ID_MASK;

    if ((false == is_menu) &&
        (n < g_ifo_entries.size()) &&
        (0 != g_ifo_entries[n].tvob_offset))
    {
        *p_key = g_ifo_entries[n].tvob_offset + sector;
        return &g_data_phys;
    }

    data_map_vector_t& map = is_menu ? g_data_vmg : g_data_vts;

    if (map.size() <= n)
    {
        map.reserve(g_ifo_entries.size());
        map.resize(n + 1);
    }
    if (NULL == map[n])
    {
        map[n] = new data_map_t();
    }

    *p_key = sector;
    return map[n];
}


bool DvdNavAddVob(unsigned int id, uint32_t sector, const uint8_t* data)
{
    uint32_t key;
    data_map_t* p_map = GetDataMap(&key,id,sector);

    uint8_t* p_data = data_malloc(DVD_VIDEO_LB_LEN);
    if (NULL == p_data) return false;

    memcpy(p_data, data, DVD_VIDEO_LB_LEN);

    p_map->insert(data_map_t::value_type(key, p_data));

    return true;
}

dvd_reader_t *DVDOpenStream2(void *ctx, const dvd_logger_cb *logcb, dvd_reader_stream_cb *strcb)
{
    dvd_reader_s* p = (dvd_reader_s*)malloc(sizeof(dvd_reader_s));
    if (NULL == p) return NULL;

    bzero(p, sizeof(*p));

    if (NULL != logcb)
    {
        p->logcb.pf_log = logcb->pf_log;
        p->priv = ctx;
    }

    IDvdNavBase* base = IDvdNavBase::GetBase(ctx, strcb);
    p->rd = (dvd_reader_device_t*)base;

    return p;
}

dvd_reader_t *DVDOpen2(void *ctx, const dvd_logger_cb *logcb, const char *name)
{
    return NULL;
}

void DVDClose(dvd_reader_t *dvd)
{
    free(dvd);
}

struct dvd_file_s
{
    dvd_reader_t*   dvd;
    uint32_t        offset;
    uint16_t        vts_id;
};

dvd_file_t *DVDOpenFile(dvd_reader_t *dvd, int titlenum, dvd_read_domain_t domain)
{
    dvd_file_s* p = (dvd_file_s*)malloc(sizeof(dvd_file_s));
    if (NULL == p) return NULL;

    p->dvd = dvd;
    p->offset = 0;
    p->vts_id = (uint16_t)titlenum;

    if (DVD_READ_MENU_VOBS == domain)
    {
        p->vts_id |= FLAG_MENU_VOB;
    }

    return p;
}

void DVDCloseFile(dvd_file_t *dvd_file)
{
    free(dvd_file);
}

int32_t DVDFileSeek(dvd_file_t *dvd_file, int32_t seek_offset)
{
    dvd_file->offset = seek_offset;
    return seek_offset;
}

int DVDFileSeekForce(dvd_file_t *dvd_file, int seek_offset, int force_size)
{
    dvd_file->offset = seek_offset;
    return seek_offset;
}

ssize_t DVDReadBytes(dvd_file_t *dvd_file, void *data, size_t size)
{
    if (g_ifo_entries.size() <= dvd_file->vts_id) return -1;

    ifo_entry_t* p_ifo = &g_ifo_entries[dvd_file->vts_id];

    if (NULL == p_ifo->data) return -1;

    if ((dvd_file->offset + size) > p_ifo->size) return -1;
    memcpy(data, p_ifo->data + dvd_file->offset, size);
    dvd_file->offset += size;
    return size;
}

static unsigned int g_read_count = 0, g_access_count = 0;

const unsigned char * DVDReadBlock(dvd_file_t *dvd_file, int offset, unsigned char *data)
{
    uint32_t key;
    data_map_t* p_map = GetDataMap(&key,dvd_file->vts_id,offset);

    data_map_t::iterator it = p_map->find(key);
    if (p_map->end() != it)
    {
        g_access_count++;
        return it->second;
    }

    IDvdNavBase* base = (IDvdNavBase*)dvd_file->dvd->rd;

    if (false==base->DvdNavReadVob(dvd_file->vts_id, offset, data))
    {
        return NULL;
    }

    g_read_count++;

    DvdNavAddVob(dvd_file->vts_id, offset, data);

    return data;
}

void DvdNavStat(uint32_t* p_read, uint32_t* p_access)
{
    *p_read = g_read_count;
    *p_access = g_access_count;
}

dvdnav_t* IDvdNavBase::DvdNavOpen(bool EnableLog)
{
    dvdnav_logger_cb logcb;
    dvdnav_stream_cb strcb;
    dvdnav_t* dvdnav;

    bzero(&logcb, sizeof(logcb));
    logcb.pf_log = IDvdNavBase::CbLog;

    bzero(&strcb, sizeof(strcb));
    strcb.pf_read = IDvdNavBase::CbRead;

    if (DVDNAV_STATUS_OK != dvdnav_open_stream2(&dvdnav, this, EnableLog?&logcb:NULL, &strcb))
    {
        return NULL;
    }
    dvdnav_set_readahead_flag(dvdnav, 0);
    dvdnav_set_nav_only_flag(dvdnav, 1);

    return dvdnav;
}

/*static*/ void IDvdNavBase::CbLog(void *ctx, dvdnav_logger_level_t level, const char *str, va_list lst)
{
    IDvdNavBase* base = (IDvdNavBase*)ctx;

    base->DvdNavLog(level, str, lst);
}

/*static*/ int IDvdNavBase::CbRead(void *p_stream, void* buffer, int i_read)
{
    if (i_read != 0x13) return false;
    memcpy(buffer, &p_stream, sizeof(void*));
    return 0x15;
}

/*static*/ IDvdNavBase* IDvdNavBase::GetBase(void* ctx, const dvdnav_stream_cb* strcb)
{
    void* buf[8];

    if (0x15 != (*strcb->pf_read)(ctx, buf, 0x13)) return NULL;

    return (IDvdNavBase*)buf[0];
}

void IDvdNavBase::Log(const char* fmt, ...)
{
    va_list lst;
    va_start(lst, fmt);

    this->DvdNavLog(DVDNAV_LOGGER_LEVEL_INFO, fmt, lst);

    va_end(lst);
}

static const unsigned int BigPageSize = (16*1024*1024) - (DVD_VIDEO_LB_LEN/2);

static uint8_t*     g_page_data = NULL;
static unsigned int g_page_rest = 0;

static uint8_t* data_malloc(unsigned int size)
{
    if (0 == g_page_rest)
    {
        g_page_data = (uint8_t*)malloc(BigPageSize);
        if (NULL != g_page_data)
        {
            g_page_rest = BigPageSize;
            uintptr_t off = ((uintptr_t)g_page_data) & (DVD_VIDEO_LB_LEN - 1);
            if (0 != off)
            {
                off = DVD_VIDEO_LB_LEN - off;
                g_page_data += off;
                g_page_rest -= off;
            }
            g_page_rest -= (g_page_rest&(DVD_VIDEO_LB_LEN - 1));
        }
    }

    if ((NULL == g_page_data) || (size > g_page_rest) || (0 != (size&(DVD_VIDEO_LB_LEN - 1))))
    {
        return (uint8_t*)malloc(size);
    }

    uint8_t* p = g_page_data;

    g_page_data += size;
    g_page_rest -= size;

    return p;
}

extern void dvdnav_critical_failure(void)
{
    fprintf(stderr, "\n\ndvdnav_critical_failure\n\n");
    fflush(stderr);
    exit(1);
}

