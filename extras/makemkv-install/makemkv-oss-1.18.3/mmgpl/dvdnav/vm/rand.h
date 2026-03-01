/*
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
#ifndef LIBDVDNAV_RAND_H
#define LIBDVDNAV_RAND_H

void     rand_seed(uint32_t* rand,uint32_t value);
uint32_t rand_next(uint32_t* rand);

unsigned int rand_shuffle(uint32_t* rand, unsigned int bound, unsigned int step);

#endif /* LIBDVDNAV_RAND_H */
