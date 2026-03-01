/*
    libDriveIo - MMC drive interrogation library

    Written by GuinpinSoft inc <libdriveio@makemkv.com>

    This file is hereby placed into public domain,
    no copyright is claimed.

*/
#include <stddef.h>
#include <stdint.h>
#include <lgpl/byteorder.h>

#ifndef LIBDRIVEIO_NO_CPP
#define LIBDRIVEIO_NO_CPP 1
#endif
#include <driveio/driveio.h>

extern "C" size_t DIO_CDECL DriveInfoList_GetSerializedChunkSize(const void* Buffer)
{
    uint32_t sz = rd32be(((const uint8_t*)Buffer) + 4);
    sz += 8;
    if (sz >= 0x40000000)
    {
        sz = 0x40000000;
    }
    return sz;
}

extern "C" void DIO_CDECL DriveInfoList_GetSerializedChunkInfo(const void* Buffer,DriveInfoItem *Item)
{
    Item->Data = ((const uint8_t*)Buffer) + 8;
    Item->Id = (DriveInfoId)rd32be(((const uint8_t*)Buffer) + 0);
    Item->Size = rd32be(((const uint8_t*)Buffer) + 4);
}

