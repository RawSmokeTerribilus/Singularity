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
#include <lgpl/aproxy.h>
#include <lgpl/stl.h>
#include <alloca.h>
#include <strings.h>
#include <dvdnav/dvdnav.h>
#include <dvdnav/navbase.h>
#include <lgpl/posixio.h>

class CSrvTransport : public CPipeTransport , public IDvdNavBase
{
    uint64_t        m_PipeIn;
    uint64_t        m_PipeOut;
    stl::vector<dvdnav_t*>  m_nav;
    int             m_log_fd;
    uint8_t*        m_log_page;
    unsigned int    m_log_size;
    AP_SHMEM        m_mem;
private:
    static const unsigned int LogPageSize = (1 * 1024 * 1024) - 0x80;
public:
    CSrvTransport(uint64_t pipein, uint64_t pipeout, const char* logfile)
        : m_PipeIn(pipein)
        , m_PipeOut(pipeout)
        , m_log_fd(0)
        , m_log_page(NULL)
        , m_log_size(0)
    {
        bzero(&m_mem, sizeof(m_mem));
        if (NULL != logfile)
        {
            InitLog(logfile);
        }
    }
    ~CSrvTransport();
    bool RunServer();
private:
    bool SendEvent(dvdnav_event_type_t type, unsigned int arg_count, const uint32_t* args, const uint8_t* data, unsigned int data_size);
    bool RecvCommand(dvdnav_cmd_type_t* p_cmd, unsigned int arg_count, uint32_t* args, unsigned int* p_data_size);
    inline const uint8_t* RecvData() { return m_mem.strbuf; }
    bool SendData(const void* Buffer, unsigned int Size) override;
    bool RecvData(void* Buffer, unsigned int Size, unsigned int *p_Received) override;
    void DvdNavLog(dvdnav_logger_level_t level, const char *str, va_list lst) override;
    bool DvdNavReadVob(unsigned int id, uint32_t sector, uint8_t* data) override;
    bool DoSendEvent(const dvdnav_event_t& evt);
    bool DoClone(unsigned int ndx);
    bool InitLog(const char* FileName);
    bool FlushLog();
    void AddLogData(const uint8_t* data, unsigned int size);
public:
    inline bool SendStatus(uint32_t value)
    {
        return SendEvent(dvdnav_evt_status, 1, &value, NULL, 0);
    }
    inline bool SendError(uint32_t value)
    {
        return SendEvent(dvdnav_evt_error, 1, &value, NULL, 0);
    }
};

CSrvTransport::~CSrvTransport()
{
    if (0 != m_PipeIn) ApClosePipe(m_PipeIn);
    if (0 != m_PipeOut) ApClosePipe(m_PipeOut);

    {
        unsigned int all_read, all_access;
        DvdNavStat(&all_read, &all_access);

        this->Log("\nblocks_read=%u (%umb), accessed=%u\n", all_read, all_read/512, all_access);
    }

    FlushLog();
    if (0 != m_log_fd)
    {
        close(m_log_fd);
    }
    free(m_log_page);
}

bool CSrvTransport::SendData(const void* Buffer, unsigned int Size)
{
    return (Size == (unsigned int)ApWritePipe(m_PipeOut, Buffer, Size));
}

bool CSrvTransport::RecvData(void* Buffer, unsigned int Size, unsigned int *p_Received)
{
    int r = ApReadPipe(m_PipeIn, Buffer, Size, AP_SEM_TIMEOUT);
    if (r <= 0) return false;
    *p_Received = r;
    return true;
}

bool CSrvTransport::SendEvent(dvdnav_event_type_t type, unsigned int arg_count, const uint32_t* args, const uint8_t* data, unsigned int data_size)
{
    m_mem.cmd = (( ((uint32_t)type) | 0x80) << 24) | (arg_count << 16) | data_size;
    m_mem.flags = 0;
    memcpy(m_mem.args, args, arg_count * sizeof(uint32_t));
    memcpy(m_mem.strbuf, data, data_size);

    return SendCmd(&m_mem);
}

bool CSrvTransport::RecvCommand(dvdnav_cmd_type_t* p_cmd, unsigned int arg_count, uint32_t* args, unsigned int* p_data_size)
{
    if (false == RecvCmd(&m_mem)) return false;
    *p_cmd = (dvdnav_cmd_type_t)((m_mem.cmd >> 24) & 0x7f);
    *p_data_size = m_mem.cmd & 0xffff;

    memcpy(args,m_mem.args, arg_count * sizeof(uint32_t));

    return true;
}

bool CSrvTransport::DoSendEvent(const dvdnav_event_t& evt)
{
    uint32_t args[8];

    args[0] = evt.code;
    args[1] = evt.time;
    args[2] = (((uint32_t)evt.title_id) << 16) | evt.pgc_id;
    args[3] = (((uint32_t)evt.vtsn) << 24) |
        (((uint32_t)evt.cell_id) << 16) |
        (((uint32_t)evt.still_time) << 8) |
        (((uint32_t)evt.highlight) << 0);
    args[4] = evt.vobu;
    args[5] = evt.sprm_flags;
    args[6] = 0;
    args[7] = 0;

    return SendEvent(evt.type, 8, args, NULL, 0);
}

bool CSrvTransport::DoClone(unsigned int ndx)
{
    dvdnav_t *dvdnav;

    dvdnav_status_t st = dvdnav_dup(&dvdnav, m_nav[ndx]);
    if (DVDNAV_STATUS_OK != st)
    {
        return false;
    }

    if (m_nav.capacity() == m_nav.size())
    {
        m_nav.reserve(m_nav.capacity() + 512);
    }
    m_nav.push_back(dvdnav);

    return SendStatus((uint32_t)(m_nav.size() - 1));
}

bool DvdNavRunServer(uint64_t pipein, uint64_t pipeout)
{
    const char* log_name = getenv("MMDVDNAVLOG");

    CSrvTransport* trans = new CSrvTransport(pipein, pipeout, log_name);
    bool r = trans->RunServer();
    delete trans;
    return r;
}

bool CSrvTransport::RunServer()
{
    uint32_t args[4];
    bool do_exit = false;

    if (false==SendStatus(0xDA000000))
    {
        return false;
    }

    while (false==do_exit)
    {
        dvdnav_cmd_type_t cmd;
        dvdnav_event_t evt;
        unsigned int data_size;

        if (false == RecvCommand(&cmd, 4, args, &data_size))
        {
            return false;
        }

        switch (cmd)
        {
        case dvdnav_cmd_add_ifo:
            if (false == DvdNavAddIfo(args[0],args[1],args[2],RecvData(),data_size)) return false;
            if (false == SendStatus(0)) return false;
            break;
        case dvdnav_cmd_set_ifo:
            if (false == DvdNavSetIfo(args[0], args[1], RecvData(), data_size)) return false;
            if (false == SendStatus(0)) return false;
            break;
        case dvdnav_cmd_set_param:
            if (args[0] >= m_nav.size()) return false;
            if (false == DvdNavSetParam(m_nav[args[0]], args[1], args[2])) return false;
            if (false == SendStatus(0)) return false;
            break;
        case dvdnav_cmd_run:
            if (args[0] >= m_nav.size()) return false;
            if (false == DvdNavRun(m_nav[args[0]], &evt)) return false;
            if (false == DoSendEvent(evt)) return false;
            break;
        case dvdnav_cmd_clone:
            if (true == m_nav.empty())
            {
                dvdnav_t* nav = DvdNavOpen(0 != m_log_fd);
                if (NULL == nav) return false;

                m_nav.reserve(512);
                m_nav.push_back(nav);
            }
            if (args[0] >= m_nav.size()) return false;
            if (false == DoClone(args[0])) return false;
            break;
        case dvdnav_cmd_die:
            if (false == SendStatus(0)) return false;
            do_exit = true;
            break;
        case dvdnav_cmd_log:
            AddLogData(RecvData(), data_size);
            if (false == SendStatus(0)) return false;
            break;
        default:
            return false;
            break;
        }
    }
    return true;
}

bool CSrvTransport::DvdNavReadVob(unsigned int id, uint32_t sector, uint8_t* data)
{
    uint32_t args[2];

    args[0] = id;
    args[1] = sector;
    if (false == SendEvent(dvdnav_evt_read, 2, args, NULL, 0)) return false;

    dvdnav_cmd_type_t cmd;
    unsigned int data_size;

    if (false == RecvCommand(&cmd, 0, NULL, &data_size)) return false;
    if (dvdnav_cmd_add_vob != cmd) return false;
    if (data_size != DVD_VIDEO_LB_LEN) return false;

    memcpy(data, RecvData(), DVD_VIDEO_LB_LEN);

    return true;
}

bool CSrvTransport::InitLog(const char* FileName)
{
    int fd;

    fd = open(FileName, O_CREAT | O_WRONLY | O_TRUNC, S_IREAD| S_IWRITE);
    if (fd <= 0) return false;

    m_log_page = (uint8_t*)malloc(LogPageSize);
    if (NULL == m_log_page)
    {
        close(fd);
        return false;
    }

    m_log_fd = fd;
    m_log_size = 0;

    return true;
}

void CSrvTransport::DvdNavLog(dvdnav_logger_level_t level, const char *str, va_list lst)
{
    static const unsigned int MaxStrLen = 1024;

    if ((NULL == m_log_page) || (0 == m_log_fd)) return;

    if ((m_log_size + MaxStrLen + 2) >= LogPageSize)
    {
        FlushLog();
    }

    unsigned int rest = LogPageSize - m_log_size;

    int r = vsnprintf((char*)(m_log_page + m_log_size), rest, str, lst);

    if ((r < 0) || (((size_t)r) >= rest))
    {
        r = 0;
    }

    m_log_size += ((unsigned int)r);

    m_log_page[m_log_size] = '\n';
    m_log_size += 1;
}

bool CSrvTransport::FlushLog()
{
    if ( (0 != m_log_size) && (0 != m_log_fd))
    {
        int len = m_log_size;
        m_log_size = 0;

        if (write(m_log_fd, m_log_page, len) != len)
        {
            return false;
        }
    }

    return true;
}

void CSrvTransport::AddLogData(const uint8_t* data, unsigned int size)
{
    if ((NULL == m_log_page) || (0 == m_log_fd)) return;

    if ((m_log_size + size) >= LogPageSize)
    {
        FlushLog();
    }

    memcpy(m_log_page + m_log_size, data, size);
    m_log_size += size;
}

