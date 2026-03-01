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
#ifndef APP_REGBOX_H
#define APP_REGBOX_H

#include <lgpl/aproxy.h>
#include "mainwnd.h"
#include "qtgui.h"

class CRegBox : public QDialog
{
    Q_OBJECT

public:
    CRegBox(MainWnd *MainWnd,QIcon* icon);

private:
    MainWnd*        m_MainWnd;
    bool            m_HaveValidator;
    QLineEdit*      m_Key;
    QLabel*         m_KeyType;
    QLabel*         m_KeyDate;
    QPushButton*    m_ButtonOk;

public:
    inline QString key()
    {
        return m_Key->text();
    }

private:
    void dragEnterEvent(QDragEnterEvent *e) override;
    void dropEvent(QDropEvent *e) override;

private:
    void RefreshKey(const QString& key);
    bool KeyIsValid(QString& key);
    void LoadFromFile(const QString& fileName);
    void LoadFromBuffer(const QByteArray& data);
    void LoadCommon();

private slots:
    void SlotPurchase();
    void SlotLoadFile();
};

static inline char KeyBitsToChar(uint8_t c)
{
    if (c==0) return '_';
    if (c<11) return '0' + (c-1);
    if (c<38) return '@'+(c-11);
    return 'a'+(c-38);
}

static inline uint8_t KeyIsValidChar(utf16_t c)
{
    if (c=='_') return true;
    if ( (c>='0') && (c<='9') ) return true;
    if ( (c>='@') && (c<='Z') ) return true;
    if ( (c>='a') && (c<='z') ) return true;
    return false;
}

static const unsigned int AP_KEY_STRING_LEN = 68;

// PLEASE, do not copy&paste this function into keygen code :)
static inline bool KeyCheckStringCrc(const utf16_t* str)
{
    size_t len = utf16len(str);

    if (len != AP_KEY_STRING_LEN )
    {
        return false;
    }

    uint16_t crc=0;

    for (unsigned int i=0;i<(AP_KEY_STRING_LEN-2);i++)
    {
        if ( (i>=2) && (KeyIsValidChar(str[i])==false)) return false;

        crc += ((uint8_t)str[i]) & 0x7f;

        crc = (uint16_t) (((crc*(11+i)))%4093);
    }

    if (KeyBitsToChar( (uint8_t) (crc&0x3f) ) != str[AP_KEY_STRING_LEN-2]) return false;
    if (KeyBitsToChar( (uint8_t) ((crc>>6)&0x3f)) != str[AP_KEY_STRING_LEN-1]) return false;

    return true;
}


#endif
