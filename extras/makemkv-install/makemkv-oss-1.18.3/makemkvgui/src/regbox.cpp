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
#include "regbox.h"

CRegBox::CRegBox(MainWnd *mainWnd,QIcon* icon) : QDialog(mainWnd)
{
    setWindowIcon(*icon);
    setWindowTitle(UI_QSTRING(APP_IFACE_REGISTER_TEXT));
    m_MainWnd = mainWnd;
    m_HaveValidator = ((*mainWnd->app()->GetAppString(AP_vastr_KeyString, 1)) == 'y');

    this->setAcceptDrops(true);

    QGridLayout* lay = new QGridLayout();
    lay->setSizeConstraint(QLayout::SetFixedSize);

    lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_KEY_TEXT)), 0, 1, 1, 1, Qt::AlignLeft);

    lay->addWidget(createHLine(),1,0,1,2);

    m_Key = new QLineEdit();
    QFont f = m_Key->font();
    f.setFamily(QFontDatabase::systemFont(QFontDatabase::FixedFont).family());
    m_Key->setFont(f);
    m_Key->setMinimumWidth(m_Key->fontMetrics().averageCharWidth() * (AP_KEY_STRING_LEN+2));

    lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_KEY_NAME)), 2, 0, Qt::AlignRight);
    lay->addWidget(m_Key, 2, 1);

    lay->addWidget(createHLine(), 3, 0, 1, 2);

    m_KeyType = createLabel(QString());
    lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_KEY_TYPE)),4,0,Qt::AlignRight);
    lay->addWidget(m_KeyType, 4, 1, Qt::AlignLeft);

    m_KeyDate = createLabel(QString());
    lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_KEY_DATE)), 5, 0, Qt::AlignRight);
    lay->addWidget(m_KeyDate, 5, 1, Qt::AlignLeft);

    lay->addWidget(createHLine(),6,0,1,2);

    QDialogButtonBox* btn_box = new QDialogButtonBox(
        QDialogButtonBox::Open| QDialogButtonBox::Ok| QDialogButtonBox::Cancel,Qt::Horizontal);

    m_ButtonOk = btn_box->button(QDialogButtonBox::Ok);

    QPushButton* bpurchase = new QPushButton(UI_QSTRING(APP_IFACE_ACT_PURCHASE_NAME), this);
    QPushButton *bopen = btn_box->button(QDialogButtonBox::Open);

    if (false == m_HaveValidator)
    {
        bopen->setDisabled(true);
    }

    btn_box->addButton(bpurchase, QDialogButtonBox::ActionRole);

    lay->addWidget(btn_box,7,1);

    setLayout(lay);

    check(connect(m_Key, &QLineEdit::textChanged, this, &CRegBox::RefreshKey));

    check(connect(bpurchase, &QPushButton::clicked, this, &CRegBox::SlotPurchase));
    check(connect(bopen, &QPushButton::clicked, this, &CRegBox::SlotLoadFile));
    check(connect(btn_box, &QDialogButtonBox::rejected, this, &CRegBox::reject));
    check(connect(m_ButtonOk, &QPushButton::clicked, this, &CRegBox::accept));

    QString key_string = QStringFromUtf8(m_MainWnd->app()->GetSettingString(apset_app_Key));
    m_Key->setText(key_string);
}

void CRegBox::SlotPurchase()
{
    if (m_MainWnd->purchaseAct->isEnabled())
    {
        m_MainWnd->purchaseAct->trigger();
    }
    reject();
}

void CRegBox::SlotLoadFile()
{
    QString filter = QLatin1String("*.txt *.eml *.msg *.pdf *.html *.htm");

    QString fileName = QFileDialog::getOpenFileName(this,
        UI_QSTRING(APP_IFACE_OPENFILE_TITLE),
        QString(),
        filter);

    if (fileName.isEmpty())
    {
        return;
    }

    LoadFromFile(fileName);
}

void CRegBox::RefreshKey(const QString& )
{
    QString key = m_Key->text();

    if (KeyIsValid(key))
    {
        if (key != m_Key->text())
        {
            m_Key->setText(key);
            return;
        }
        m_KeyType->setText(QStringFromUtf8(m_MainWnd->app()->GetAppString(AP_vastr_KeyString, 4)));
        m_KeyDate->setText(QStringFromUtf8(m_MainWnd->app()->GetAppString(AP_vastr_KeyString, 5)));
        m_ButtonOk->setEnabled(true);
    } else {
        if (key.isEmpty())
        {
            m_KeyType->setText(QString());
        } else {
            m_KeyType->setText(UI_QSTRING(APP_KEYTYPE_INVALID));
        }
        m_KeyDate->setText(QString());
        m_ButtonOk->setEnabled(false);
    }
}

bool CRegBox::KeyIsValid(QString& key)
{
    if (m_HaveValidator && (key.length()>=(AP_KEY_STRING_LEN-2)))
    {
        m_MainWnd->app()->SetAppString(AP_vastr_KeyString, key.utf16());
        const utf8_t* r = m_MainWnd->app()->GetAppString(AP_vastr_KeyString, 2);
        if (r[0] == '-') return false;
        if (r[0] != 0)
        {
            key = QStringFromUtf8(r);
        }
    }

    if (key.length() != AP_KEY_STRING_LEN) return false;
    if (false == KeyCheckStringCrc(key.utf16())) return false;

    return true;
}

static bool acceptFileName(const QString name)
{
    if (name.endsWith(QLatin1String(".txt"))) return true;
    if (name.endsWith(QLatin1String(".htm"))) return true;
    if (name.endsWith(QLatin1String(".html"))) return true;
    if (name.endsWith(QLatin1String(".eml"))) return true;
    if (name.endsWith(QLatin1String(".msg"))) return true;
    if (name.endsWith(QLatin1String(".pdf"))) return true;
    return false;
}

static QString extractFileName(const QMimeData& md)
{
    QByteArray ba;

    ba = md.data(QLatin1String("application/x-qt-windows-mime;value=\"FileNameW\""));
    if (ba.size()>(1*sizeof(uint16_t)))
    {
        unsigned int sz = ba.size() / sizeof(uint16_t);
        const uint16_t* src = (const uint16_t*)ba.data();
        while ((sz != 0) && (src[sz - 1] == 0)) sz--;
        return QString::fromUtf16(src,sz);
    }

    if (md.hasUrls())
    {
        for (auto url : md.urls())
        {
            if (url.isLocalFile())
            {
                return url.toLocalFile();
            }
        }
    }

    return QString();
}

static inline bool isText(const QMimeData& md)
{
    if (md.hasHtml()) return true;
    if (md.hasText()) return true;
    return false;
}

static QByteArray getText(const QMimeData& md)
{
    QByteArray ba;

    ba = md.data(QLatin1String("application/x-qt-windows-mime;value=\"RTF As Text\""));
    if (ba.size() < 1)
    {
        ba = md.data(QLatin1String("text/plain;charset=utf-8"));
    }
    if (ba.size() < 1)
    {
        ba = md.data(QLatin1String("text/unicode"));
    }
    if (ba.size() < 1)
    {
        ba = md.data(QLatin1String("text/html"));
    }
    if (ba.size() < 1)
    {
        ba = md.data(QLatin1String("text/plain"));
    }
    return ba;
}


void CRegBox::dragEnterEvent(QDragEnterEvent *e)
{
    const QMimeData* md = e->mimeData();

    if (false == m_HaveValidator) return;

    QString fn = extractFileName(*md);
    if ((false == fn.isEmpty()) && acceptFileName(fn))
    {
        e->acceptProposedAction();
        return;
    }

    if (true == isText(*md))
    {
        e->acceptProposedAction();
        return;
    }
}

void CRegBox::dropEvent(QDropEvent *e)
{
    const QMimeData* md = e->mimeData();

    if (false == m_HaveValidator) return;

    QString fn = extractFileName(*md);
    if ((false == fn.isEmpty()) && acceptFileName(fn))
    {
        LoadFromFile(fn);
        e->acceptProposedAction();
        return;
    }

    if (true == isText(*md))
    {
        LoadFromBuffer(getText(*md));
        e->acceptProposedAction();
        return;
    }
}

void CRegBox::LoadFromFile(const QString& fileName)
{
    if (false == m_HaveValidator) return;
    m_MainWnd->app()->SetAppString(AP_vastr_KeyString, fileName.utf16(), 1);
    LoadCommon();
}

void CRegBox::LoadFromBuffer(const QByteArray& data)
{
    if (false == m_HaveValidator) return;
    m_MainWnd->app()->SetAppString(AP_vastr_KeyString, data.size(), data.data(), 0);
    LoadCommon();
}

void CRegBox::LoadCommon()
{
    const utf8_t* r = m_MainWnd->app()->GetAppString(AP_vastr_KeyString, 2);
    if (r[0] == '-') return;
    if (r[0] != 0)
    {
        m_Key->setText(QStringFromUtf8(r));
    }
}

