/*
    Written by GuinpinSoft inc <oss@makemkv.com>

    This file is hereby placed into public domain,
    no copyright is claimed.

*/
#ifndef LGPL_BYTEORDER_H_INCLUDED
#define LGPL_BYTEORDER_H_INCLUDED

#include <string.h>
#include <stdint.h>

#if defined(_MSC_VER)

#include <stdlib.h>
#pragma intrinsic(_byteswap_ulong, _byteswap_uint64, _byteswap_ushort)

#define _LITTLE_ENDIAN  1234
#define _BIG_ENDIAN     4321
#define _PDP_ENDIAN     3412

#define _BYTE_ORDER     _LITTLE_ENDIAN

#define __bswap16(x)    _byteswap_ushort(x)
#define __bswap32(x)    _byteswap_ulong(x)
#define __bswap64(x)    _byteswap_uint64(x)

#if defined(_M_IX86) || defined (_M_X64)
#define BYTEORDER_ARCH_ALLOWS_UNALIGNED_ACCESS 1
#endif

#elif defined(_linux_)

#ifndef __USE_MISC
#define __USE_MISC 1	// for __bswap_xx
#endif

#include <endian.h>

#define __bswap64(x)    __bswap_64(x)
#define __bswap32(x)    __bswap_32(x)
#define __bswap16(x)    __bswap_16(x)

#define _LITTLE_ENDIAN  __LITTLE_ENDIAN
#define _BIG_ENDIAN     __BIG_ENDIAN
#define _PDP_ENDIAN     __PDP_ENDIAN
#define _BYTE_ORDER     __BYTE_ORDER

#elif defined(_darwin_)

#include <machine/endian.h>

#define __bswap64(x)    __builtin_bswap64(x)
#define __bswap32(x)    __builtin_bswap32(x)
#define __bswap16(x)    __builtin_bswap16(x)

#define _LITTLE_ENDIAN  __DARWIN_LITTLE_ENDIAN
#define _BIG_ENDIAN     __DARWIN_BIG_ENDIAN
#define _PDP_ENDIAN     __DARWIN_PDP_ENDIAN
#define _BYTE_ORDER     __DARWIN_BYTE_ORDER

#elif defined(__BSD_VISIBLE)

#include <machine/endian.h>

#else

#error "Unknown platform"

#endif

#if ( (defined(__GNUC__) || defined (__clang__)) && ((defined(__i386__) || defined(__x86_64))) )
#define BYTEORDER_ARCH_ALLOWS_UNALIGNED_ACCESS 1
#endif

#if _BYTE_ORDER == _LITTLE_ENDIAN

#define bswap_cpu_to_le64(x) (x)
#define bswap_cpu_to_le32(x) (x)
#define bswap_cpu_to_le16(x) (x)

#define bswap_cpu_to_be64(x) __bswap64(x)
#define bswap_cpu_to_be32(x) __bswap32(x)
#define bswap_cpu_to_be16(x) __bswap16(x)

#else

#define bswap_cpu_to_be64(x) (x)
#define bswap_cpu_to_be32(x) (x)
#define bswap_cpu_to_be16(x) (x)

#define bswap_cpu_to_le64(x) __bswap64(x)
#define bswap_cpu_to_le32(x) __bswap32(x)
#define bswap_cpu_to_le16(x) __bswap16(x)

#endif

#define bswap_le64_to_cpu bswap_cpu_to_le64
#define bswap_le32_to_cpu bswap_cpu_to_le32
#define bswap_le16_to_cpu bswap_cpu_to_le16

#define bswap_be64_to_cpu bswap_cpu_to_be64
#define bswap_be32_to_cpu bswap_cpu_to_be32
#define bswap_be16_to_cpu bswap_cpu_to_be16

#ifdef BYTEORDER_ARCH_ALLOWS_UNALIGNED_ACCESS

// arch allows unaligned access

static inline uint16_t rd16ua(const uint8_t* Data)
{
    return *(const uint16_t*)Data;
}

static inline uint32_t rd32ua(const uint8_t* Data)
{
    return *(const uint32_t*)Data;
}

static inline uint64_t rd64ua(const uint8_t* Data)
{
    return *(const uint64_t*)Data;
}

static inline void wr16ua(uint8_t* Data, uint16_t Value)
{
    *((uint16_t*)Data) = Value;
}

static inline void wr32ua(uint8_t* Data, uint32_t Value)
{
    *((uint32_t*)Data) = Value;
}

static inline void wr64ua(uint8_t* Data, uint64_t Value)
{
    *((uint64_t*)Data) = Value;
}

// inline big-endian access macros

static inline uint16_t rd16be(const uint8_t* Data)
{
    return bswap_cpu_to_be16(rd16ua(Data));
}

static inline uint32_t rd32be(const uint8_t* Data)
{
    return bswap_cpu_to_be32(rd32ua(Data));
}

static inline uint64_t rd64be(const uint8_t* Data)
{
    return bswap_cpu_to_be64(rd64ua(Data));
}

static inline void wr16be(uint8_t* Data,uint16_t Value)
{
    wr16ua(Data, bswap_cpu_to_be16(Value));
}

static inline void wr32be(uint8_t* Data,uint32_t Value)
{
    wr32ua(Data, bswap_cpu_to_be32(Value));
}

static inline void wr64be(uint8_t* Data,uint64_t Value)
{
    wr64ua(Data, bswap_cpu_to_be64(Value));
}

// inline little-endian access macros

static inline uint16_t rd16le(const uint8_t* Data)
{
    return bswap_cpu_to_le16(rd16ua(Data));
}

static inline uint32_t rd32le(const uint8_t* Data)
{
    return bswap_cpu_to_le32(rd32ua(Data));
}

static inline uint64_t rd64le(const uint8_t* Data)
{
    return bswap_cpu_to_le64(rd64ua(Data));
}

static inline void wr16le(uint8_t* Data,uint16_t Value)
{
    wr16ua(Data, bswap_cpu_to_le16(Value));
}

static inline void wr32le(uint8_t* Data,uint32_t Value)
{
    wr32ua(Data, bswap_cpu_to_le32(Value));
}

static inline void wr64le(uint8_t* Data,uint64_t Value)
{
    wr64ua(Data, bswap_cpu_to_le64(Value));
}

#else // BYTEORDER_ARCH_ALLOWS_UNALIGNED_ACCESS

// inline big-endian access macros

static inline uint16_t rd16be(const uint8_t* Data)
{
    uint16_t v;
    v  = ((uint16_t)Data[0]) << (1 * 8);
    v |= ((uint16_t)Data[1]) << (0 * 8);
    return v;
}

static inline uint32_t rd32be(const uint8_t* Data)
{
    uint32_t v;
    v  = ((uint32_t)Data[0]) << (3 * 8);
    v |= ((uint32_t)Data[1]) << (2 * 8);
    v |= ((uint32_t)Data[2]) << (1 * 8);
    v |= ((uint32_t)Data[3]) << (0 * 8);
    return v;
}

static inline uint64_t rd64be(const uint8_t* Data)
{
    uint64_t v;
    v  = ((uint64_t)Data[0]) << (7 * 8);
    v |= ((uint64_t)Data[1]) << (6 * 8);
    v |= ((uint64_t)Data[2]) << (5 * 8);
    v |= ((uint64_t)Data[3]) << (4 * 8);
    v |= ((uint64_t)Data[4]) << (3 * 8);
    v |= ((uint64_t)Data[5]) << (2 * 8);
    v |= ((uint64_t)Data[6]) << (1 * 8);
    v |= ((uint64_t)Data[7]) << (0 * 8);
    return v;
}

static inline void wr16be(uint8_t* Data, uint16_t Value)
{
    Data[0] = (uint8_t)(Value >> (1 * 8));
    Data[1] = (uint8_t)(Value >> (0 * 8));
}

static inline void wr32be(uint8_t* Data, uint32_t Value)
{
    Data[0] = (uint8_t)(Value >> (3 * 8));
    Data[1] = (uint8_t)(Value >> (2 * 8));
    Data[2] = (uint8_t)(Value >> (1 * 8));
    Data[3] = (uint8_t)(Value >> (0 * 8));
}

static inline void wr64be(uint8_t* Data, uint64_t Value)
{
    Data[0] = (uint8_t)(Value >> (7 * 8));
    Data[1] = (uint8_t)(Value >> (6 * 8));
    Data[2] = (uint8_t)(Value >> (5 * 8));
    Data[3] = (uint8_t)(Value >> (4 * 8));
    Data[4] = (uint8_t)(Value >> (3 * 8));
    Data[5] = (uint8_t)(Value >> (2 * 8));
    Data[6] = (uint8_t)(Value >> (1 * 8));
    Data[7] = (uint8_t)(Value >> (0 * 8));
}

// inline little-endian access macros

static inline uint16_t rd16le(const uint8_t* Data)
{
    uint16_t v;
    v  = ((uint16_t)Data[0]) << (0 * 8);
    v |= ((uint16_t)Data[1]) << (1 * 8);
    return v;
}

static inline uint32_t rd32le(const uint8_t* Data)
{
    uint32_t v;
    v  = ((uint32_t)Data[0]) << (0 * 8);
    v |= ((uint32_t)Data[1]) << (1 * 8);
    v |= ((uint32_t)Data[2]) << (2 * 8);
    v |= ((uint32_t)Data[3]) << (3 * 8);
    return v;
}

static inline uint64_t rd64le(const uint8_t* Data)
{
    uint64_t v;
    v  = ((uint64_t)Data[0]) << (0 * 8);
    v |= ((uint64_t)Data[1]) << (1 * 8);
    v |= ((uint64_t)Data[2]) << (2 * 8);
    v |= ((uint64_t)Data[3]) << (3 * 8);
    v |= ((uint64_t)Data[4]) << (4 * 8);
    v |= ((uint64_t)Data[5]) << (5 * 8);
    v |= ((uint64_t)Data[6]) << (6 * 8);
    v |= ((uint64_t)Data[7]) << (7 * 8);
    return v;
}

static inline void wr16le(uint8_t* Data, uint16_t Value)
{
    Data[0] = (uint8_t)(Value >> (0 * 8));
    Data[1] = (uint8_t)(Value >> (1 * 8));
}

static inline void wr32le(uint8_t* Data, uint32_t Value)
{
    Data[0] = (uint8_t)(Value >> (0 * 8));
    Data[1] = (uint8_t)(Value >> (1 * 8));
    Data[2] = (uint8_t)(Value >> (2 * 8));
    Data[3] = (uint8_t)(Value >> (3 * 8));
}

static inline void wr64le(uint8_t* Data, uint64_t Value)
{
    Data[0] = (uint8_t)(Value >> (0 * 8));
    Data[1] = (uint8_t)(Value >> (1 * 8));
    Data[2] = (uint8_t)(Value >> (2 * 8));
    Data[3] = (uint8_t)(Value >> (3 * 8));
    Data[4] = (uint8_t)(Value >> (4 * 8));
    Data[5] = (uint8_t)(Value >> (5 * 8));
    Data[6] = (uint8_t)(Value >> (6 * 8));
    Data[7] = (uint8_t)(Value >> (7 * 8));
}

#endif // BYTEORDER_ARCH_ALLOWS_UNALIGNED_ACCESS

#endif // LGPL_BYTEORDER_H_INCLUDED

