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
#include "toolbuttonp.h"
#include "qtapp.h"

// barbarian magic
void QToolButtonP::setButtonSize(const QSize& size, int scale)
{
    unsigned int h2 = (size.height()*scale*102) / 16384;

    QSize isz = getImageGoodSize(h2, false);

    unsigned int h3 = (isz.height()*160) / 128;

    setIconSize(QSize(h3, h3));

    int h4 = sizeHint().height();

    setFixedSize(QSize(h4,h4));
    setIconSize(isz);
}

