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
#include "dvdbox.h"
#include "qtgui.h"
#include "qtapp.h"

CDVDBox::CDVDBox(MainWnd *mainWnd,QIcon* icon,unsigned int Code, const unsigned int Codes[], const utf8_t* Text[]) : QDialog(mainWnd)
{
    setWindowIcon(*icon);
    setWindowTitle(UI_QSTRING(Code));
    m_MainWnd = mainWnd;

    QGroupBox* box1 = new QGroupBox(QStringFromCodeUtf8(Codes[0],Text[0]));
    QBoxLayout *lay1 = new QVBoxLayout();
    QGrayTextViewer* tview = new QGrayTextViewer();
    tview->setHtmlBody(QStringFromCodeUtf8(Codes[2],Text[2]));
    lay1->addWidget(tview);
    box1->setLayout(lay1);

    QGroupBox* box2 = new QGroupBox(QStringFromCodeUtf8(Codes[1],Text[1]));
    QBoxLayout *lay2 = new QVBoxLayout();
    QLabel *text = new QLabel();
    text->setTextFormat(Qt::RichText);
    text->setText(QStringFromCodeUtf8(Codes[3],Text[3]));
    check(connect(text, &QLabel::linkActivated, mainWnd, &MainWnd::SlotLaunchUrl));
    m_Line = new QLineEdit();
    lay2->addWidget(text);
    lay2->addWidget(m_Line);
    box2->setLayout(lay2);

    QDialogButtonBox* btn_box = new QDialogButtonBox(QDialogButtonBox::Ok|QDialogButtonBox::Cancel,Qt::Horizontal);

    QBoxLayout *lay = new QVBoxLayout();
    lay->addWidget(box1);
    lay->addWidget(box2);
    lay->addWidget(btn_box);
    setLayout(lay);

    check(connect(btn_box, &QDialogButtonBox::rejected, this, &CDVDBox::reject));
    check(connect(btn_box, &QDialogButtonBox::accepted, this, &CDVDBox::accept));
}

