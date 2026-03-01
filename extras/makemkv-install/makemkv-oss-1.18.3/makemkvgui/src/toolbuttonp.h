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
#ifndef APP_TOOLBUTTONP_H
#define APP_TOOLBUTTONP_H

#include "qtgui.h"

class QToolButtonP : public QToolButton
{
    Q_OBJECT

public:
    void setButtonSize(const QSize& size, int scale);

private:
};

#endif
