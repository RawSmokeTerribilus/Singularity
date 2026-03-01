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
#include "qtapp.h"
#include "notify.h"
#include <QtDBus/QDBusInterface>
#include <lgpl/sysabi.h>

static QDBusInterface*  notifyInterface = NULL;

void notifyInit()
{
    QDBusMessage msgServerInformation;

    notifyInterface = new QDBusInterface(
        QLatin1String("org.freedesktop.Notifications"),
        QLatin1String("/org/freedesktop/Notifications"),
        QLatin1String("org.freedesktop.Notifications")
        );

    if (!notifyInterface->isValid())
    {
        notifyCleanup();
        return;
    }

    msgServerInformation = notifyInterface->call(QDBus::Block,QLatin1String("GetServerInformation"));

    if (msgServerInformation.type()!=QDBusMessage::ReplyMessage)
    {
        notifyCleanup();
        return;
    }

    if (msgServerInformation.arguments().size()<3)
    {
        notifyCleanup();
        return;
    }
}

void notifyStart(QMainWindow* mainWindow,unsigned long Id,const QString &Name)
{
}

void notifyUpdate(QMainWindow* mainWindow,unsigned int Value,unsigned int MaxValue,unsigned int TimeElapsed)
{
}

void notifyFinish(QMainWindow* mainWindow)
{
}

void notifyEvent(QMainWindow* mainWindow,unsigned long Id,const char* IdName,const QString &Text,const QString &Name)
{
    if (notifyInterface)
    {
        notifyInterface->call(
            QDBus::BlockWithGui,
            QLatin1String("Notify"),
            QLatin1String("makemkv"),
            QVariant((uint)0),
            QLatin1String(""),
            Name,
            Text,
            QStringList(),
            QMap<QString, QVariant>(),
            QVariant((int)3)
            );
    }
}

void notifyCleanup()
{
    delete notifyInterface;
    notifyInterface = NULL;
}

void desktopShowFile(const QString &FileName)
{
    char*       argv[6];
    QByteArray  name;
    SYS_stat    st;

    name = FileName.toUtf8();
    argv[0] = NULL;

    static const char* nautilus = "/usr/bin/nautilus";
    if (SYS_nstat(nautilus,&st)==0)
    {
        argv[0]=(char*)nautilus;
        argv[1]=(char*)"-w";
        argv[2]=(char*)"-s";
        argv[3]=name.data();
        argv[4]=NULL;
    }
    if (NULL!=argv[0])
    {
        SYS_posix_launch(argv,0,0,0,SYS_posix_envp());
    }
}

