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
#include <stdint.h>
#include <string.h>
#include <strings.h>

#include "rand.h"

static const unsigned int NUM_WORDS = 9;
static const unsigned int MAX_BOUND = NUM_WORDS * 32;
static_assert(MAX_BOUND > 257, "Max PG count per PGC");

uint32_t rand_next(uint32_t *rand)
{
    uint64_t product = ((uint64_t)(*rand)) * 48271;
    uint32_t x = (uint32_t)( (product & 0x7fffffff) + (product >> 31) );

    x = (x & 0x7fffffff) + (x >> 31);
    *rand = x;
    return x;
}

void rand_seed(uint32_t* rand, uint32_t value)
{
    uint32_t ns = (*rand + value);
    ns |= 0x8000;
    ns &= 0x7fffffff;
    *rand = rand_next(&ns);
}

inline static uint32_t peek_next(uint32_t rand)
{
    uint32_t r = rand;
    return rand_next(&r);
}

inline static bool getbit(uint32_t* bits, unsigned int index)
{
    unsigned int n = index / 32;
    unsigned int s = index % 32;
    return (0 != (bits[n] & (1 << s)));
}

inline static void setbit(uint32_t* bits, unsigned int index)
{
    unsigned int n = index / 32;
    unsigned int s = index % 32;
    bits[n] |= (1 << s);
}

unsigned int rand_shuffle(uint32_t* rand, unsigned int bound, unsigned int step)
{
    uint32_t bits[NUM_WORDS];
    uint32_t r = *rand;

    bzero(bits, sizeof(bits));

    if (bound >= MAX_BOUND) return 0;

    while (step >= bound)
    {
        step -= bound;
        rand_next(&r);
    }

    if (bound >= 4)
    {
        while (0 == (peek_next(r) % bound))
        {
            rand_next(&r);
        }
    }

    unsigned int n,v;
    for (unsigned int s = 0; s <= step; s++)
    {
        n = (rand_next(&r) % (bound-s));
        v = 0;

        while (getbit(bits, v))
        {
            v++;
        }

        for (unsigned int i = 0; i < n; i++)
        {
            v++;
            while (getbit(bits, v))
            {
                v++;
            }
        }
        setbit(bits, v);
    }

    return v;
}

