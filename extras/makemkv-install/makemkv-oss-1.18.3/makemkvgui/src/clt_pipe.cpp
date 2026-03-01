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
#include <lgpl/byteorder.h>

bool CPipeTransport::SendCmd(AP_SHMEM* p_mem)
{
    uint32_t cmd = p_mem->cmd;
    unsigned int arg_count = (cmd >> 16) & 0xff;
    unsigned int data_size = cmd & 0xffff;
    unsigned int all_size = (1 + arg_count) * sizeof(uint32_t) + data_size;
    uint32_t* data;

    if (0 == data_size)
    {
        data = (p_mem->args - 1);

        if ((0 == arg_count) && (cmd < 0x10000000))
        {
            cmd |= ((cmd >> 24) | 0xf00000f0);
            all_size = 1;
        } else {
#if (_BYTE_ORDER != _LITTLE_ENDIAN)
            for (unsigned int i = 0; i < arg_count; i++)
            {
                p_mem->args[i] = bswap_cpu_to_le32(p_mem->args[i]);
            }
#endif
        }
    } else {
        data = ((uint32_t*)p_mem->strbuf) - (1 + arg_count);

        for (unsigned int i = 0; i < arg_count; i++)
        {
            data[arg_count-i] = bswap_cpu_to_le32(p_mem->args[(arg_count-1)-i]);
        }
    }
    data[0] = bswap_cpu_to_le32(cmd);

    bool r;


    r = this->SendData(data, all_size);


    return r;
}

bool CPipeTransport::RecvCmd(AP_SHMEM* p_mem)
{
    unsigned int rd;

    uint32_t* data = (p_mem->args - 1);

    static const unsigned int data_buffer_size = (sizeof(AP_SHMEM) - offsetof(AP_SHMEM, args)) + 1*sizeof(uint32_t);


    unsigned int have = 0;

    while (have < 4)
    {
        if (false == RecvData( ((uint8_t*)data)+have, data_buffer_size-have, &rd))
        {
            return false;
        }
        have += rd;

        if (have == 1)
        {
            uint8_t v = *((uint8_t*)data);
            if (v >= 0xf0)
            {
                data[0] = bswap_cpu_to_le32( ((uint32_t)(v - 0xf0)) << 24);
                have = 4;
            }
        }
    }

    uint32_t cmd = bswap_le32_to_cpu(data[0]);
    unsigned int arg_count = (cmd >> 16) & 0xff;
    unsigned int data_size = cmd & 0xffff;
    unsigned int hdr_size = (1 + arg_count) * sizeof(uint32_t);
    unsigned int all_size = hdr_size + data_size;

    while (have < all_size)
    {
        if (false == RecvData( ((uint8_t*)data) + have, all_size - have, &rd))
        {
            return false;
        }
        have += rd;
    }

    if (have != all_size)
    {
        return false;
    }


    p_mem->cmd = cmd;

#if (_BYTE_ORDER != _LITTLE_ENDIAN)
    for (unsigned int i = 0; i < arg_count; i++)
    {
        p_mem->args[i] = bswap_le32_to_cpu(p_mem->args[i]);
    }
#endif

    if (0 != data_size)
    {
        memmove(p_mem->strbuf, data + 1 + arg_count, data_size);
    }

    return true;
}

