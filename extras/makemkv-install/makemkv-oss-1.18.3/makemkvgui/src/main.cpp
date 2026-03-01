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
#include "qtgui.h"
#include <lgpl/aproxy.h>

#include "mainwnd.h"

#if !defined(_MSC_VER) && !defined(__cdecl)
#define __cdecl
#endif

#define aversion aversion002
extern "C" const unsigned int __cdecl aversion();

#ifdef Q_OS_WIN
#include <objbase.h>
static void PlatformInitBeforeApp()
{
    CoInitializeEx(NULL,COINIT_APARTMENTTHREADED|COINIT_DISABLE_OLE1DDE);
}
void AppWait();
#else
#define PlatformInitBeforeApp()
#endif

int qMain(int argc, char **argv)
{
    PlatformInitBeforeApp();

    static CGUIApClient apc;
    QApplication app(argc, argv);

    char* appname = argv[0];

    argv++; argc--;

    if (argc>=2)
    {
        if (strcmp(argv[0],"debug")==0)
        {
            apc.EnableDebug(argv[1]);
            argv += 2; argc -= 2;
        }
#ifdef Q_OS_WIN
        if (strcmp(argv[0], "break")==0)
        {
            __debugbreak();
            argv += 2; argc -= 2;
        }
#endif
    }

#if (QT_VERSION > 0x050000)
    QCoreApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
#endif

    CApClient::ITransport*  p_trans = NULL;

    CShMemTransport     shmt;
    CStdPipeTransport   stdt;
    if ( (argc >= 1) && (strcmp(argv[0], "-std") == 0) )
    {
        p_trans = &stdt;
        argv++; argc--;
    }
#if 0
    if ((argc >= 2) && (strcmp(argv[0], "-net") == 0))
    {
        if (!nett.Init(argv[1]))
        {
            fprintf(stderr, "Network failed\n");
            return 1;
        }
        p_trans = &nett;
        argv+=2; argc-=2;
    }
#endif
    if (NULL == p_trans)
    {
        p_trans = &shmt;
    }

    unsigned int errcode;
    if (false==apc.Init(p_trans,"makemkvcon",&errcode))
    {
        QString msg = UI_QSTRING(APP_INIT_FAILED);

        const char* err;
        switch (errcode)
        {
        case 1:  err = "CANT_LOCATE_MAKEMKVCON"; break;
        case 2:  err = "VERSION_MISMATCH"; break;
        case 3:  err = "COMMUNICATION_FAILURE"; break;
        case 4:  err = "NO_ANSWER_FROM_MAKEMKVCON"; break;
        default: err = NULL; break;
        }
        if (err)
        {
            msg.append(QLatin1String("\n"));
            msg.append(QLatin1String(err));
        }
        QMessageBox::critical(NULL,UI_QSTRING(APP_CAPTION_MSG),msg);
        return 1;
    }

    AppGetInterfaceLanguageData(&apc);

    const char* appdir;
    char *aend = strrchr(appname,'/');
    if (!aend)
    {
        aend = strrchr(appname,'\\');
    }
    if (aend)
    {
        *aend =0;
        appdir = appname;
    } else {
        appdir = ".";
    }

    MainWnd mainWin(&apc,appdir);
    mainWin.show();
    int r = app.exec();

#ifdef APP_DEBUG_INPROC
    AppWait();
#endif

    apc.AppExiting();

#if defined(Q_OS_DARWIN) || defined(Q_OS_WIN)
    aversion();
#endif

    return r;
}

#if !defined(QT_NEEDS_QMAIN)
extern "C" int main(int argc, char **argv)
{
    return qMain(argc,argv);
}
#endif

