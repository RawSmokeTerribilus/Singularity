/*
    libDriveIo - MMC drive interrogation library

    Copyright (C) 2007-2025 GuinpinSoft inc <libdriveio@makemkv.com>

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

*/
#include <driveio/scsicmd.h>
#include <driveio/driveio.h>

namespace LibDriveIo
{

int ExecuteReadScsiCommand(ISimpleScsiTarget* ScsiTarget,const uint8_t* Cdb,unsigned int CdbLen,void *Buffer,unsigned int BufferSize,ScsiCmdResponse* Response);
int ExecuteReadScsiCommand(ISimpleScsiTarget* ScsiTarget,const uint8_t* Cdb,unsigned int CdbLen,void *Buffer,unsigned int* BufferSize);
int ExecuteWriteScsiCommand(ISimpleScsiTarget* ScsiTarget,const uint8_t* Cdb,unsigned int CdbLen,const void *Buffer,unsigned int BufferSize,ScsiCmdResponse* Response);
int ExecuteWriteScsiCommand(ISimpleScsiTarget* ScsiTarget,const uint8_t* Cdb,unsigned int CdbLen,const void *Buffer,unsigned int BufferSize);
int TestUnitReady(ISimpleScsiTarget* ScsiTarget, bool* Ready);
int BuildInquiryData(ISimpleScsiTarget* ScsiTarget,DIO_INFOLIST List,ScsiInquiryData *InquiryData);
int BuildDriveInfo(ISimpleScsiTarget* ScsiTarget,DIO_INFOLIST List,ScsiDriveInfo *DriveInfo);
int QueryInquiryInfo(ISimpleScsiTarget* ScsiTarget,uint8_t *Buffer,unsigned int *BufferSize);
void BuildDriveId(ScsiDriveId* DriveId,const ScsiDriveInfo *DriveInfo);
int IsScsiMmcDeviceNonBlacklisted(ISimpleScsiTarget* Target);
int ScsiErrorFromResult(const ScsiCmdResponse *CmdResult);

}
using namespace LibDriveIo;
