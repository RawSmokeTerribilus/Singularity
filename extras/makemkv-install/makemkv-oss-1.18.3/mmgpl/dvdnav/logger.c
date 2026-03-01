/*
* This file is part of libdvdnav, a DVD navigation library.
*
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation; either version 2.1 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.
*/

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
#include <stdio.h>
#include <stdarg.h>

#include "dvdnav/dvdnav.h"
#include "logger.h"

void dvdnav_log( void *priv, const dvdnav_logger_cb *logcb,
                 dvdnav_logger_level_t level, const char *fmt, ... )
{
    va_list list;
    va_start(list, fmt);
    if(logcb && logcb->pf_log)
        logcb->pf_log(priv, level, fmt, list);
#if 0
    else
    {
        FILE *stream = (level == DVDNAV_LOGGER_LEVEL_ERROR) ? stderr : stdout;
        fprintf(stream, "libdvdnav: ");
        vfprintf(stream, fmt, list);
        fprintf(stream, "\n");
    }
#endif
    va_end(list);
}

int dvdnav_assert_worker(void *priv, const dvdnav_logger_cb *logcb, const char* expression)
{
    dvdnav_log(priv, logcb, DVDNAV_LOGGER_LEVEL_ERROR, "libdvdnav assertion failure: %s\n", expression);
    dvdnav_critical_failure();
    return 0;
}


