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
#ifndef LGPL_MMDVDNAV_H_INCLUDED
#define LGPL_MMDVDNAV_H_INCLUDED

#include <stddef.h>
#include <stdint.h>

typedef enum _dvdnav_event_type_t
{
    dvdnav_evt_error=0,
    dvdnav_evt_libdvdnav = 1,
    dvdnav_evt_read = 2,
    dvdnav_evt_status = 3,
} dvdnav_event_type_t;

typedef enum _dvdnav_cmd_type_t
{
    dvdnav_cmd_add_ifo = 0,
    dvdnav_cmd_set_ifo = 1,
    dvdnav_cmd_add_vob = 2,
    dvdnav_cmd_set_param = 3,
    dvdnav_cmd_run = 4,
    dvdnav_cmd_clone = 5,
    dvdnav_cmd_die = 6,
    dvdnav_cmd_log = 7,
} dvdnav_cmd_type_t;

typedef struct _dvdnav_event_t
{
    dvdnav_event_type_t type;
    uint32_t            code;
    uint32_t            time;
    uint32_t            vobu;
    uint32_t            sprm_flags;
    uint16_t            title_id;
    uint16_t            pgc_id;
    uint8_t             vtsn;
    uint8_t             cell_id;
    uint8_t             still_time;
    uint8_t             highlight;
} dvdnav_event_t;

typedef enum _dvdnav_lib_code_t
{
    dvdnav_lib_block_ok = 0,
    dvdnav_lib_nop = 1,
    dvdnav_lib_still_frame = 2,
    dvdnav_lib_spu_change = 3,
    dvdnav_lib_audio_change = 4,
    dvdnav_lib_vts_change = 5,
    dvdnav_lib_cell_change = 6,
    dvdnav_lib_nav_packet = 7,
    dvdnav_lib_stop = 8,
    dvdnav_lib_highlight = 9,
    dvdnav_lib_clut = 10,
    dvdnav_lib_hop = 12,
    dvdnav_lib_wait = 13,
} dvdnav_lib_code_t;

typedef enum _dvdnav_param_t
{
    dvdnav_region_mask = 0,
    dvdnav_menu_language = 1,
    dvdnav_audio_language = 2,
    dvdnav_spu_language = 3,
    dvdnav_angle = 4,
    dvdnav_button = 5,
    dvdnav_title = 6,
    dvdnav_program = 7,
    dvdnav_highlight = 8,
} dvdnav_param_t;

typedef struct dvdnav_s dvdnav_t;

#define FLAG_MENU_VOB 0x100
#define VTS_ID_MASK   0x0ff

bool DvdNavAddIfo(unsigned int id,unsigned int size, uint32_t tvob_offset, const uint8_t* data,unsigned int data_size);
bool DvdNavSetIfo(unsigned int id,unsigned int offset,const uint8_t* data,unsigned int data_size);
bool DvdNavAddVob(unsigned int id, uint32_t sector, const uint8_t* data);
void DvdNavStat(uint32_t* p_read, uint32_t* p_access);
bool DvdNavSetParam(dvdnav_t* ctx, int id, uint32_t value);
bool DvdNavRun(dvdnav_t* ctx, dvdnav_event_t* p_event);

bool DvdNavRunServer(uint64_t pipein, uint64_t pipeout);

#endif // LGPL_MMDVDNAV_H_INCLUDED

