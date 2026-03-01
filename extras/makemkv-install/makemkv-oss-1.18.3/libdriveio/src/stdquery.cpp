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
#include <stddef.h>
#include <stdint.h>
#include <driveio/scsicmd.h>
#include <driveio/driveio.h>
#include <driveio/scsihlp.h>
#include <driveio/error.h>
#include <lgpl/byteorder.h>
#include <errno.h>
#include <string.h>

//
// Queries all standard drive info
//
static int QueryDriveInfo(ISimpleScsiTarget* ScsiTarget,DIO_INFOLIST List)
{
    int err;
    unsigned int len,slen;
    uint8_t data_buffer[256+32];

    //
    // Inquiry
    //
    err=QueryInquiryInfo(ScsiTarget,data_buffer,&slen);
    if (err) return err;
    if (DriveInfoList_AddItem(List,diid_InquiryData,data_buffer,slen)) return DRIVEIO_ERR_NO_MEMORY;
    if ((data_buffer[0]&0x1f)!=5) return DRIVEIO_ERROR_BAD_DATA; // not a MMC drive

    //
    // All feature descriptors
    //
    unsigned int current_feature = 0, first_feature;
    while(current_feature<0x10000)
    {
        uint8_t cdb_get_configuration[10];
        ScsiCmdResponse res;

        memset(cdb_get_configuration,0,sizeof(cdb_get_configuration));
        cdb_get_configuration[0]=0x46;
        cdb_get_configuration[2]=(uint8_t)(current_feature>>8);
        cdb_get_configuration[3]=(uint8_t)(current_feature>>0);

        len = sizeof(data_buffer);
        err=ExecuteReadScsiCommand(ScsiTarget,cdb_get_configuration,10,data_buffer,len,&res);
        if (err) return err;

        if (res.Status!=0) break;
        len = res.Transferred;

        slen = rd32be(data_buffer);

        slen +=4;
        if (slen > len) slen = len;

        if (slen==8) break; // empty feature header

        if (slen < 12) return DRIVEIO_ERROR_BAD_DATA;

        const uint8_t *dptr=data_buffer+8;
        slen-=8;

        first_feature = current_feature;

        while(slen>=4)
        {
            unsigned int feature_code, feature_len;

            feature_code = rd16be(dptr);

            if ((feature_code < first_feature) ||
                ((current_feature !=0) && (feature_code == 0)))
            {
                // drive is supposed to return empty feature header
                // but returned the last feature descriptor (or garbage)
                current_feature = 0x10000;
                break;
            }

            feature_len = 4 + ((unsigned int)dptr[3]);

            if (feature_len > slen)
            {
                if (feature_code >= current_feature) current_feature = (feature_code + 1);
                break;
            }

            if (DriveInfoList_AddItem(List,(DriveInfoId)(diid_FeatureDescriptor + feature_code),dptr,feature_len)) return DRIVEIO_ERR_NO_MEMORY;

            if (feature_code >= current_feature) current_feature = (feature_code + 1);
            dptr += feature_len;
            slen -= feature_len;
        }
    }

    return 0;
}

//
// BD DI structure is huge (4+4096 bytes) but only small part is usually filled.
// This function reduces amount of zeroes to store :)
//
static unsigned int CalculateRealBDDISize(const uint8_t* Buffer,unsigned int Len)
{
    // very little public information on BD DI structures is available, going with the most conservative way

    const uint8_t* ptr=Buffer+4;
    unsigned int rest = Len-4;
    unsigned int size = 0;
    while(rest>12)
    {
        unsigned int struct_size;

        if(0!=memcmp(ptr,"DI",2)) break;

        struct_size=0;
        if (0==memcmp(ptr+8,"BDO",3)) struct_size=64;
        if (0==memcmp(ptr+8,"BDW",3)) struct_size=112;
        if (0==memcmp(ptr+8,"BDR",3)) struct_size=112;
        if (0==memcmp(ptr+8,"BDU",3)) struct_size=64;
        if (0==struct_size) break;
        if (struct_size>rest)
        {
            break;
        }

        ptr+=struct_size;
        rest-=struct_size;
        size+=struct_size;
    }
    if (size!=0)
    {
        size+=4;
    }
    return size;
}

static int QueryDiscStructure(ISimpleScsiTarget* ScsiTarget,uint16_t Code,uint8_t* Buffer,uint16_t Length,unsigned int *StructureLength)
{
    int err;
    ScsiCmd cmd;
    ScsiCmdResponse res;

    memset(&cmd,0,sizeof(cmd));
    cmd.CdbLen=12;
    cmd.Cdb[0]=0xAD;
    cmd.Cdb[1]=(uint8_t)(Code>>8);
    cmd.Cdb[7]=(uint8_t)(Code);
    cmd.Cdb[8]=(uint8_t)(Length>>8);
    cmd.Cdb[9]=(uint8_t)(Length>>0);

    cmd.OutputBuffer = Buffer;
    cmd.OutputLen = Length;
    cmd.Timeout = 10;

    memset(Buffer,0xee,Length);

    err = ScsiTarget->Exec(&cmd,&res);
    if (err) return err;

    if ( (res.Status!=0) || (res.Transferred<4) )
    {
        *StructureLength = 0;
    } else {
        if (rd16be(Buffer+2)==0)
        {
            *StructureLength = rd16be(Buffer) + 2;
        } else {
            *StructureLength = 0;
        }
    }

    return 0;
}

//
// Queries all standard disc info
//
static int QueryStandardDiscInfo(ISimpleScsiTarget* ScsiTarget,DIO_INFOLIST List)
{
    int err;
    unsigned int len,slen;
    uint8_t data_buffer[4096+16];

    //
    // Current profile
    //
    {
        static const uint8_t cdb_get_configuration[10]={0x46,0,0,0,0,0,0,0,0,0};
        ScsiCmdResponse res;

        len = 32;
        err=ExecuteReadScsiCommand(ScsiTarget,cdb_get_configuration,10,data_buffer,len,&res);
        if (err) return err;
        if (res.Status==0)
        {
            len = res.Transferred;
            slen = rd32be(data_buffer);
            slen +=4;
            if (slen > len) slen = len;
            if (slen<8) return DRIVEIO_ERROR_BAD_DATA;
            if (DriveInfoList_AddItem(List,diid_CurrentProfile,data_buffer+6,2)) return DRIVEIO_ERR_NO_MEMORY;
        }
    }

    //
    // Disc structures
    //

    // type, code, size
    static const uint16_t disc_struct_ids[]={
        0x0000,0x03f0, // DVD Physical Format Information
        0x0001,0x0008, // DVD Copyright Information
        0x0003,0x00f0, // DVD BCA Information
        0x000e,0x00f0, // DVD Pre-recorded Information in Lead-in
        0x000f,0x00f0, // DVD Unique Disc Identifier
        0x0100,0x03f0, // BD Disc Information (DI)
        0,0
    };


    for (unsigned int disc_struct_id=0;disc_struct_ids[disc_struct_id+1]!=0;disc_struct_id+=2)
    {
        uint16_t code;
        unsigned int maxlen;

        code = disc_struct_ids[disc_struct_id];
        len = disc_struct_ids[disc_struct_id+1];

        err=QueryDiscStructure(ScsiTarget,code,data_buffer,len,&slen);
        if (err!=0) return err;

        if (slen<4) continue;

        // limit the size of some structures
        switch(code)
        {
        case 0x0000: // DVD Physical Format Information
            maxlen = (4+17);
            break;
        case 0x0100: // BD Disc Information (DI)
            maxlen = CalculateRealBDDISize(data_buffer,slen);
            break;
        default:
            maxlen=len;
            break;
        }

        if (slen>maxlen) slen=maxlen;

        if (DriveInfoList_AddItem(List, (DriveInfoId) (((unsigned int)diid_DiscStructure) + code),data_buffer,slen)) return DRIVEIO_ERR_NO_MEMORY;
    }

    //
    // TOC
    //
    for (unsigned int layer_id=0;layer_id<=1;layer_id++)
    {
        uint8_t cdb_read_toc[10];
        ScsiCmdResponse res;

        memset(cdb_read_toc,0,sizeof(cdb_read_toc));
        cdb_read_toc[0]=0x43;
        cdb_read_toc[2]=(uint8_t)layer_id;
        len = 0x3f0;
        err=ExecuteReadScsiCommand(ScsiTarget,cdb_read_toc,10,data_buffer,len,&res);
        if (err) return err;
        if (res.Status==0)
        {
            len = res.Transferred;
            slen = rd16be(data_buffer)+2;
            if (slen>len) continue;
            if (DriveInfoList_AddItem(List, (DriveInfoId) (((unsigned int)diid_TOC) + layer_id),data_buffer,slen)) return DRIVEIO_ERR_NO_MEMORY;
        }
    }

    //
    // Disc information
    //
    for (unsigned int layer_id=0;layer_id<=1;layer_id++)
    {
        ScsiCmd cmd;
        ScsiCmdResponse res;

        len = 0x3f0;

        memset(&cmd,0,sizeof(cmd));
        cmd.CdbLen=10;
        cmd.Cdb[0]=0x51;
        cmd.Cdb[1]=(uint8_t)layer_id;
        cmd.Cdb[7]=(uint8_t)(len>>8);
        cmd.Cdb[8]=(uint8_t)(len>>0);

        cmd.OutputBuffer = data_buffer;
        cmd.OutputLen = len;
        cmd.Timeout = 10;

        err = ScsiTarget->Exec(&cmd,&res);
        if (err) return err;

        if (res.Status==0)
        {
            len = res.Transferred;
            slen = rd16be(data_buffer)+2;

            if ( (layer_id==0) && (slen>34) )
            {
                slen=34; // do not read OPC entries
            }

            if (slen>len) continue;
            if (DriveInfoList_AddItem(List, (DriveInfoId) (((unsigned int)diid_DiscInformation) + layer_id),data_buffer,slen)) return DRIVEIO_ERR_NO_MEMORY;
        }
    }

    //
    // Capacity
    //
    {
        ScsiCmd cmd;
        ScsiCmdResponse res;

        memset(&cmd,0,sizeof(cmd));
        cmd.CdbLen=10;
        cmd.Cdb[0]=0x25;

        cmd.OutputBuffer = data_buffer;
        cmd.OutputLen = 8;
        cmd.Timeout = 10;

        err = ScsiTarget->Exec(&cmd,&res);
        if (err) return err;
        if (res.Status!=0)
        {
            return DRIVEIO_ERR_SCSI_STATUS(res.Status);
        }
        if (res.Transferred!=8)
        {
            return DRIVEIO_ERROR_BAD_DATA;
        }
        if (DriveInfoList_AddItem(List, diid_DiscCapacity,data_buffer,8)) return DRIVEIO_ERR_NO_MEMORY;
    }

    return 0;
}

static int QueryDiscInfo(ISimpleScsiTarget* ScsiTarget,DIO_INFOLIST List,bool FailIfNotReady)
{
    int err;
    bool ready;

    if (0!=(err=TestUnitReady(ScsiTarget,&ready))) return err;
    if (false==ready)
    {
        return FailIfNotReady?DRIVEIO_ERR_NOT_READY:0;
    }

    if (0!=(err=QueryStandardDiscInfo(ScsiTarget,List))) return err;

    return 0;
}

namespace LibDriveIo
{

static int DriveIoQuery(ISimpleScsiTarget* ScsiTarget,DriveIoQueryType QueryType,DIO_INFOLIST list)
{
    int err;

    switch(QueryType)
    {
    case diq_QueryAllInfo:
        if (0!=(err = QueryDriveInfo(ScsiTarget,list))) break;
        if (0!=(err = QueryDiscInfo(ScsiTarget,list,false))) break;
        break;
    case diq_QueryDriveInfo:
        err = QueryDriveInfo(ScsiTarget,list);
        break;
    case diq_QueryDiscInfo:
        err = QueryDiscInfo(ScsiTarget,list,true);
        break;
    default:
        err = DRIVEIO_ERROR_INVALID_ARG;
        break;
    }
    return err;
}

static int DriveIoQuery(ISimpleScsiTarget* ScsiTarget, DriveIoQueryType QueryType, DIO_INFOLIST* InfoList)
{
    DIO_INFOLIST list;
    int err;

    list = DriveInfoList_Create();
    if (NULL == list)
    {
        return DRIVEIO_ERR_NO_MEMORY;
    }

    err = DriveIoQuery(ScsiTarget, QueryType, list);

    if (err)
    {
        DriveInfoList_Destroy(list);
        return err;
    }

    *InfoList = list;
    return 0;
}

class CFwdScsiTarget : public ISimpleScsiTarget
{
private:
    DriveIoExecScsiCmdFunc  m_Func;
    void*                   m_Context;
public:
    CFwdScsiTarget(DriveIoExecScsiCmdFunc f,void *c) :
        m_Func(f) ,
        m_Context(c)
    {
    }
    int Exec(const ScsiCmd* Cmd,ScsiCmdResponse *CmdResult);
};

int CFwdScsiTarget::Exec(const ScsiCmd* Cmd,ScsiCmdResponse *CmdResult)
{
    if (NULL==m_Func) return -1;
    return (*m_Func)(m_Context,Cmd,CmdResult);
}

}; // namespace LibDriveIo

//
// API
//

extern "C" int DIO_CDECL DriveIoQueryCreate(DriveIoExecScsiCmdFunc ScsiProc,void* ScsiContext,DriveIoQueryType QueryType,DIO_INFOLIST* InfoList)
{
    CFwdScsiTarget t(ScsiProc,ScsiContext);
    return LibDriveIo::DriveIoQuery(&t,QueryType,InfoList);
}

extern "C" int DIO_CDECL DriveIoQueryAdd(DriveIoExecScsiCmdFunc ScsiProc,void* ScsiContext,DriveIoQueryType QueryType,DIO_INFOLIST InfoList)
{
    CFwdScsiTarget t(ScsiProc,ScsiContext);
    return LibDriveIo::DriveIoQuery(&t,QueryType,InfoList);
}

extern "C" int DIO_CDECL DriveIoGetInquiryData(ScsiInquiryData *InquiryData,DriveIoExecScsiCmdFunc ScsiProc,void* ScsiContext,DIO_INFOLIST InfoList)
{
    CFwdScsiTarget t(ScsiProc,ScsiContext);
    return LibDriveIo::BuildInquiryData(&t,InfoList,InquiryData);
}

extern "C" int DIO_CDECL DriveIoGetDriveInfo(ScsiDriveInfo *DriveInfo,DriveIoExecScsiCmdFunc ScsiProc,void* ScsiContext,DIO_INFOLIST InfoList)
{
    CFwdScsiTarget t(ScsiProc,ScsiContext);
    return LibDriveIo::BuildDriveInfo(&t,InfoList,DriveInfo);
}

extern "C" int DIO_CDECL DriveIoGetDriveId(ScsiDriveId *DriveId,DriveIoExecScsiCmdFunc ScsiProc,void* ScsiContext,DIO_INFOLIST InfoList)
{
    int err;
    ScsiDriveInfo info;
    CFwdScsiTarget t(ScsiProc,ScsiContext);

    err = LibDriveIo::BuildDriveInfo(&t,InfoList,&info);
    if (0!=err) return err;

    LibDriveIo::BuildDriveId(DriveId,&info);

    return 0;
}

