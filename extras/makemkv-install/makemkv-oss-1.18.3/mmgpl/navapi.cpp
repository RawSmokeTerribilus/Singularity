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
#include <dvdnav/dvdnav.h>
#include <strings.h>
#include <stdio.h>

bool DvdNavSetParam(dvdnav_t* ctx, int id, uint32_t value)
{
    dvdnav_status_t st;
    uint8_t sbuf[5];

    sbuf[0] = (uint8_t)(value >> (0 * 8));
    sbuf[1] = (uint8_t)(value >> (1 * 8));
    sbuf[2] = (uint8_t)(value >> (2 * 8));
    sbuf[3] = (uint8_t)(value >> (3 * 8));
    sbuf[4] = 0;

    switch (id)
    {
    case dvdnav_region_mask: st = dvdnav_set_region_mask(ctx, value); break;
    case dvdnav_menu_language: st = dvdnav_menu_language_select(ctx, (char*)sbuf); break;
    case dvdnav_audio_language: st = dvdnav_audio_language_select(ctx, (char*)sbuf); break;
    case dvdnav_spu_language: st = dvdnav_spu_language_select(ctx, (char*)sbuf); break;
    case dvdnav_angle: st = dvdnav_angle_change(ctx, value); break;
    case dvdnav_button: st = dvdnav_button_select_and_activate(ctx, dvdnav_get_current_nav_pci(ctx), value); break;
    case dvdnav_title: st = dvdnav_title_play(ctx, value); break;
    case dvdnav_program: st = dvdnav_program_play(ctx, (value>>16),(value>>8)&0xff,(value&0xff)); break;
    case dvdnav_highlight: st = dvdnav_button_select(ctx, dvdnav_get_current_nav_pci(ctx), value); break;
    default: st = DVDNAV_STATUS_ERR; break;
    }
    return (DVDNAV_STATUS_OK == st);
}

static void fill_position_info(dvdnav_t* ctx, dvdnav_event_t* p_event)
{
    int32_t title, vtsn, pgcn, pgn, celln;
    if (DVDNAV_STATUS_OK != dvdnav_current_title_program2(ctx, &title, &vtsn, &pgcn, &pgn, &celln))
    {
        p_event->title_id = 0xffff;
    } else {
        p_event->vtsn = (uint8_t)vtsn;
        p_event->pgc_id = (uint16_t)pgcn;
        p_event->cell_id = (uint8_t)celln;
        if (title >= 0)
        {
            p_event->title_id = (uint16_t)title;
        } else {
            p_event->title_id = 0xffff;
        }
    }

    pci_t* pci = dvdnav_get_current_nav_pci(ctx);
    if (NULL != pci)
    {
        p_event->vobu = pci->pci_gi.nv_pck_lbn;
    }
}

bool DvdNavRun(dvdnav_t* ctx, dvdnav_event_t* p_event)
{
    uint8_t data[DVD_VIDEO_LB_LEN];
    int len = DVD_VIDEO_LB_LEN;
    dvdnav_status_t st;

    int32_t code;

    bzero(p_event, sizeof(*p_event));

    st = dvdnav_get_next_block(ctx, data, &code, &len);
    p_event->time = (uint32_t)(dvdnav_get_absolute_time(ctx)/90);
    p_event->sprm_flags = dvdnav_get_prm(ctx,3,0);
    p_event->highlight = (uint8_t)(dvdnav_get_prm(ctx, 1, 8) >> 10);
    if (DVDNAV_STATUS_OK != st)
    {
        p_event->type = dvdnav_evt_error;
        p_event->code = st;
        return true;
    }

    p_event->type = dvdnav_evt_libdvdnav;
    p_event->code = code;

    switch (code)
    {
    case DVDNAV_STILL_FRAME:
        p_event->still_time = (uint8_t) ((dvdnav_still_event_t *)data)->length;
        fill_position_info(ctx, p_event);
        if (0xff != p_event->still_time)
        {
            dvdnav_still_skip(ctx);
        }
        break;
    case DVDNAV_WAIT:
        dvdnav_wait_skip(ctx);
        break;
    case DVDNAV_NAV_PACKET:
        fill_position_info(ctx, p_event);
        break;
    case DVDNAV_CELL_CHANGE:
        fill_position_info(ctx, p_event);
        break;
    default:
        break;
    }

    return true;
}
