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
#include "settingdlg.h"
#include "mainwnd.h"
#include <lgpl/sstring.h>

CSettingDialog::CSettingDialog(MainWnd* mainwnd, QIcon* icon, QWidget *parent) : QDialog(parent)
{
    client = mainwnd->app();

    setWindowIcon(*icon);
    setWindowTitle(UI_QSTRING(APP_SETTINGDLG_TITLE));

    tabWidget = new QTabWidget();
    tabWidget->setUsesScrollButtons(false);
    buttonBox = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel | QDialogButtonBox::Apply , Qt::Horizontal);

    // dvd
    dvdTab = new CDVDTab(client);
    tabWidget->addTab(dvdTab, UI_QSTRING(APP_TTREE_VIDEO));

    // general
    generalTab = new CGeneralTab();
    tabWidget->addTab(generalTab,UI_QSTRING(APP_IFACE_SETTINGS_TAB_GENERAL));
    check(connect(generalTab->check_ExpertMode, &QCheckBox::stateChanged, this, &CSettingDialog::SlotExpertStateChanged));

    // IO
    ioTab = new CIOTab();
    tabWidget->addTab(ioTab,UI_QSTRING(APP_IFACE_SETTINGS_TAB_IO));

    // Language
    languageTab = new CLanguageTab(client);
    tabWidget->addTab(languageTab,UI_QSTRING(APP_IFACE_SETTINGS_TAB_LANGUAGE));

    // prot
    protTab = new CProtTab();
    tabWidget->addTab(protTab, UI_QSTRING(APP_IFACE_SETTINGS_TAB_PROT));

    decryptTab = new CDecryptTab(mainwnd);
    tabWidget->addTab(decryptTab, UI_QSTRING(APP_IFACE_SETTINGS_TAB_INTEGRATION));

    advancedTab = new CAdvancedTab(client);
    advancedTabVisible = false;

    QBoxLayout *lay = new QVBoxLayout();
    lay->addWidget(tabWidget);
    lay->addWidget(buttonBox);
    this->setLayout(lay);

    check(connect(buttonBox, &QDialogButtonBox::accepted, this, &CSettingDialog::accept));
    check(connect(buttonBox, &QDialogButtonBox::rejected, this, &CSettingDialog::reject));
    check(connect(buttonBox->button(QDialogButtonBox::Apply), &QPushButton::clicked, this, &CSettingDialog::SlotApply));

    check(connect(this, &CSettingDialog::accepted, this, &CSettingDialog::SlotApply));

    ReadSettings(true);
};

CSettingDialog::~CSettingDialog()
{
    if (!advancedTabVisible)
    {
        delete advancedTab;
    }
}

void CSettingDialog::SlotApply()
{
    bool restartRequired=false;

    if (false==WriteSettings(restartRequired))
    {
        QMessageBox::critical(this,UI_QSTRING(APP_CAPTION_MSG),UI_QSTRING(APP_IFACE_SETTINGS_MSG_FAILED));
    }
    ReadSettings(false);

    if (restartRequired)
    {
        QMessageBox::information(this,UI_QSTRING(APP_CAPTION_MSG),
            UI_QSTRING(APP_IFACE_SETTINGS_MSG_RESTART));
    }
}

void CSettingDialog::ReadSettings(bool first)
{
    // general
    const utf8_t *datapath = client->GetSettingString(apset_app_DataDir);
    generalTab->dataDir->setText(QStringFromUtf8(datapath));

    int show_debug = client->GetSettingInt(apset_app_ShowDebug);
    generalTab->check_DebugLog->setCheckState( (show_debug==0) ? Qt::Unchecked : Qt::Checked );

    int site_access = client->GetSettingInt(apset_app_UpdateEnable);
    generalTab->check_SiteAccess->setCheckState( (site_access==0) ? Qt::Unchecked : Qt::Checked );

    int expert_mode = client->GetSettingInt(apset_app_ExpertMode);
    generalTab->check_ExpertMode->setCheckState( (expert_mode==0) ? Qt::Unchecked : Qt::Checked );

    int show_av = client->GetSettingInt(apset_app_ShowAVSyncMessages);
    generalTab->check_ShowAV->setCheckState( (show_av==0) ? Qt::Unchecked : Qt::Checked );

    const utf8_t *app_proxy = client->GetSettingString(apset_app_Proxy);
    generalTab->lineEditProxy->setText(QStringFromUtf8(app_proxy));

    // language
    languageTab->setValue(languageTab->comboBoxInterfaceLanguage,client->GetSettingString(apset_app_InterfaceLanguage));
    languageTab->setValue(languageTab->comboBoxPreferredLanguage,client->GetSettingString(apset_app_PreferredLanguage));

    // io
    int retry_count = client->GetSettingInt(apset_io_ErrorRetryCount);
    ioTab->spinBoxRetryCount->setValue(retry_count);
    int buf_size = client->GetSettingInt(apset_io_RBufSizeMB);
    int darwin_workaround = client->GetSettingInt(apset_io_DarwinK2Workaround);
    int single_drive = client->GetSettingInt(apset_io_SingleDrive);

    if (0==buf_size)
    {
        ioTab->comboBoxRBufSize->setCurrentIndex(0);
    } else {
        char sbuf[32];
        sprintf_s(sbuf,32,"%u",buf_size);
        QString sstr=QLatin1String(sbuf);
        if (ioTab->comboBoxRBufSize->findText(sstr)<0)
        {
            ioTab->comboBoxRBufSize->addItem(sstr);
        }
        ioTab->comboBoxRBufSize->setCurrentIndex(ioTab->comboBoxRBufSize->findText(sstr));
    }
    ioTab->comboBoxDarwinK2Workaround->setCurrentIndex(darwin_workaround);
    ioTab->checkSingleDrive->setCheckState( (single_drive==0) ? Qt::Unchecked : Qt::Checked );

    // dvd
    const utf8_t *dest_path = client->GetSettingString(apset_app_DestinationDir);
    if (NULL==dest_path) dest_path="";
    dvdTab->destinationDir->setText(QStringFromUtf8(dest_path),true);
    dvdTab->destinationDir->setMRU(client->GetSettingString(apset_path_DestDirMRU));

    int dest_type = client->GetSettingInt(apset_app_DestinationType);
    dvdTab->destinationDir->setIndexValue(dest_type);

    int MinimumTitleLength = client->GetSettingInt(apset_dvd_MinimumTitleLength);
    dvdTab->spinBoxMinimumTitleLength->setValue(MinimumTitleLength);

    // prot
    int SpRemoveMethod = client->GetSettingInt(apset_dvd_SPRemoveMethod);
    protTab->comboBoxSpRemoveMethod->setCurrentIndex(SpRemoveMethod);
    protTab->javaDir->setText(QStringFromUtf8( client->GetSettingString(apset_app_Java)));

    int dump_always = client->GetSettingInt(apset_bdplus_DumpAlways);
    protTab->check_DumpAlways->setCheckState( (dump_always==0) ? Qt::Unchecked : Qt::Checked );

    decryptTab->LoadSettings(client);

    // advanced
    const utf8_t *defaultProfile = client->GetSettingString(apset_app_DefaultProfileName);
    if (NULL==defaultProfile) defaultProfile="";
    int profileIndex = 0;
    for (int index=1;index<advancedTab->comboProfile->count();++index)
    {
        if (defaultProfile[0]==0) break;
        if (advancedTab->comboProfile->itemText(index) == QStringFromUtf8(defaultProfile))
        {
            profileIndex = index;
            break;
        }
    }
    advancedTab->comboProfile->setCurrentIndex(profileIndex);

    const utf8_t *defaultSelection = client->GetSettingString(apset_app_DefaultSelectionString);
    if (NULL==defaultSelection) defaultSelection="";
    if (defaultSelection[0]==0)
    {
        defaultSelection = client->GetAppString(AP_vastr_DefaultSelectionString);
    }
    advancedTab->lineEditSelection->setText(QStringFromUtf8(defaultSelection));

    const utf8_t *defaultOutputFileName = client->GetSettingString(apset_app_DefaultOutputFileName);
    if (NULL==defaultOutputFileName) defaultOutputFileName="";
    if (defaultOutputFileName[0]==0)
    {
        defaultOutputFileName = client->GetAppString(AP_vastr_DefaultOutputFileName);
    }
    advancedTab->lineEditOutputFileName->setText(QStringFromUtf8(defaultOutputFileName));

    advancedTab->ccextractorDir->setText(QStringFromUtf8(client->GetSettingString(apset_app_ccextractor)));

    toggleAdvanced(expert_mode!=0);

    if (first)
    {
        newSettings = false;
        oldExpertMode = (expert_mode!=0);
        oldOutputFileName = advancedTab->lineEditOutputFileName->text();
    }
}

bool CSettingDialog::WriteSettings(bool& restartRequired)
{
    QString string;

    // general
    client->SetSettingString(apset_app_DataDir,Utf16FromQString(generalTab->dataDir->text()));
    client->SetSettingInt( apset_app_ShowDebug , (generalTab->check_DebugLog->checkState() == Qt::Checked) ? 1 : 0 );
    client->SetSettingInt( apset_app_UpdateEnable , (generalTab->check_SiteAccess->checkState() == Qt::Checked) ? 1 : 0 );
    client->SetSettingInt( apset_app_ExpertMode , (generalTab->check_ExpertMode->checkState() == Qt::Checked) ? 1 : 0 );
    client->SetSettingInt( apset_app_ShowAVSyncMessages , (generalTab->check_ShowAV->checkState() == Qt::Checked) ? 1 : 0 );
    client->SetSettingString(apset_app_Proxy, Utf16FromQString(generalTab->lineEditProxy->text()));

    // language
    client->SetSettingString(apset_app_InterfaceLanguage,languageTab->getValue(languageTab->comboBoxInterfaceLanguage,string));
    client->SetSettingString(apset_app_PreferredLanguage,languageTab->getValue(languageTab->comboBoxPreferredLanguage,string));

    // io
    client->SetSettingInt(apset_io_ErrorRetryCount,ioTab->spinBoxRetryCount->value());
    int rbuf_size;
    if (ioTab->comboBoxRBufSize->currentIndex()==0)
    {
        rbuf_size=0;
    } else {
        rbuf_size=ioTab->comboBoxRBufSize->currentText().toInt();
    }
    client->SetSettingInt(apset_io_RBufSizeMB,rbuf_size);
    client->SetSettingInt(apset_io_DarwinK2Workaround,ioTab->comboBoxDarwinK2Workaround->currentIndex());
    client->SetSettingInt(apset_io_SingleDrive,(ioTab->checkSingleDrive->checkState() == Qt::Checked) ? 1 : 0 );

    // dvd
    client->SetSettingString(apset_app_DestinationDir,Utf16FromQString(dvdTab->destinationDir->text()));
    client->SetSettingInt(apset_app_DestinationType,dvdTab->destinationDir->getIndexValue());

    client->SetSettingInt(apset_dvd_MinimumTitleLength,dvdTab->spinBoxMinimumTitleLength->value());

    //prot
    client->SetSettingInt(apset_dvd_SPRemoveMethod,protTab->comboBoxSpRemoveMethod->currentIndex());
    client->SetSettingInt( apset_bdplus_DumpAlways , (protTab->check_DumpAlways->checkState() == Qt::Checked) ? 1 : 0 );
    client->SetSettingString(apset_app_Java,Utf16FromQString(protTab->javaDir->text()));

    // advanced
    if (advancedTab->comboProfile->currentIndex())
    {
        client->SetSettingString(apset_app_DefaultProfileName,Utf16FromQString(advancedTab->comboProfile->currentText()));
    } else {
        client->SetSettingString(apset_app_DefaultProfileName,(const utf16_t*)NULL);
    }
    if (advancedTab->lineEditSelection->text() == QStringFromUtf8(client->GetAppString(AP_vastr_DefaultSelectionString)))
    {
        client->SetSettingString(apset_app_DefaultSelectionString, (const utf16_t*)NULL);
    } else {
        client->SetSettingString(apset_app_DefaultSelectionString,Utf16FromQString(advancedTab->lineEditSelection->text()));
    }
    if (advancedTab->lineEditOutputFileName->text() == QStringFromUtf8(client->GetAppString(AP_vastr_DefaultOutputFileName)))
    {
        client->SetSettingString(apset_app_DefaultOutputFileName, (const utf16_t*)NULL);
    } else {
        client->SetSettingString(apset_app_DefaultOutputFileName,Utf16FromQString(advancedTab->lineEditOutputFileName->text()));
    }
    client->SetSettingString(apset_app_ccextractor,Utf16FromQString(advancedTab->ccextractorDir->text()));

    restartRequired = (NULL!=client->GetAppString(AP_vastr_RestartRequired));

    newSettings = true;
    newExpertMode = (generalTab->check_ExpertMode->checkState() == Qt::Checked);
    newOutputFileName = advancedTab->lineEditOutputFileName->text();

    // flush
    if (false==client->SaveSettings()) return false;
    if (false==decryptTab->SaveSettings(client)) return false;

    return true;
}

bool CSettingDialog::redrawRequired()
{
    if (newSettings)
    {
        if (oldExpertMode!=newExpertMode) return true;
        if (oldOutputFileName!=newOutputFileName) return true;
    }
    return false;
}


CIOTab::CIOTab(QWidget *parent) : QWidget(parent)
{
    QGroupBox* box = new QGroupBox(UI_QSTRING(APP_IFACE_SETTINGS_IO_OPTIONS));

    spinBoxRetryCount = new QSpinBox();
    comboBoxRBufSize = new QComboBox();
    comboBoxRBufSize->addItem(QString(UI_QSTRING(APP_IFACE_SETTINGS_IO_AUTO)));
    comboBoxRBufSize->addItem(QLatin1String("64"));
    comboBoxRBufSize->addItem(QLatin1String("256"));
    comboBoxRBufSize->addItem(QLatin1String("512"));
    comboBoxRBufSize->addItem(QLatin1String("768"));
    comboBoxRBufSize->addItem(QLatin1String("1024"));
    comboBoxDarwinK2Workaround = new QComboBox();
    comboBoxDarwinK2Workaround->addItem(QLatin1String("0"));
    comboBoxDarwinK2Workaround->addItem(QLatin1String("1"));
    comboBoxDarwinK2Workaround->addItem(QLatin1String("2"));
    checkSingleDrive = new QCheckBox();

    QGridLayout *b_lay = new QGridLayout();
    b_lay->setColumnStretch(0,2);

    bool osx_k2bug_affected = false;

#ifdef Q_OS_DARWIN
    osx_k2bug_affected = true;
#endif

    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_IO_READ_RETRY)),0,0,Qt::AlignRight);
    b_lay->addWidget(spinBoxRetryCount,0,1);
    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_IO_READ_BUFFER)),1,0,Qt::AlignRight);
    b_lay->addWidget(comboBoxRBufSize,1,1);
    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_IO_SINGLE_DRIVE)),2,0,Qt::AlignRight);
    b_lay->addWidget(checkSingleDrive,2,1);
    if (osx_k2bug_affected)
    {
        b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_IO_DARWIN_K2_WORKAROUND)),3,0,Qt::AlignRight);
        b_lay->addWidget(comboBoxDarwinK2Workaround,3,1);
    }

    box->setLayout(b_lay);

    QBoxLayout *lay = new QVBoxLayout();
    lay->addWidget(box);

    lay->addStretch(2);
    this->setLayout(lay);
}

CDVDTab::CDVDTab(CApClient* client,QWidget *parent) : QWidget(parent)
{
    radio_None = new QRadioButton(UI_QSTRING(APP_IFACE_SETTINGS_DEST_TYPE_NONE));
    radio_Auto = new QRadioButton(UI_QSTRING(APP_IFACE_SETTINGS_DEST_TYPE_AUTO));
    radio_SemiAuto = new QRadioButton(UI_QSTRING(APP_IFACE_SETTINGS_DEST_TYPE_SEMIAUTO));
    radio_Custom = new QRadioButton(UI_QSTRING(APP_IFACE_SETTINGS_DEST_TYPE_CUSTOM));

    QWidgetList lst;
    lst.append(radio_None);
    lst.append(radio_Auto);
    lst.append(radio_SemiAuto);
    lst.append(radio_Custom);

    destinationDir = new CDirSelectBox(client,CDirSelectBox::DirBoxOutDirMKV,UI_QSTRING(APP_IFACE_SETTINGS_DESTDIR),lst);

    check(connect(destinationDir, &CDirSelectBox::SignalIndexChanged, this, &CDVDTab::SlotIndexChanged));

    QGroupBox* box = new QGroupBox(UI_QSTRING(APP_IFACE_SETTINGS_IO_OPTIONS));

    spinBoxMinimumTitleLength = new QSpinBox();
    spinBoxMinimumTitleLength->setMaximum(9999);

    QGridLayout *b_lay = new QGridLayout();
    b_lay->setColumnStretch(0,2);

    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_DVD_MIN_LENGTH)),0,0,Qt::AlignRight);
    b_lay->addWidget(spinBoxMinimumTitleLength,0,1);

    box->setLayout(b_lay);
    QBoxLayout *lay = new QVBoxLayout();
    lay->addWidget(destinationDir);
    lay->addWidget(box);
    lay->addStretch(2);
    this->setLayout(lay);
}

CProtTab::CProtTab(QWidget *parent) : QWidget(parent)
{
    QGroupBox* dvdBox = new QGroupBox(QLatin1String("DVD"));

    comboBoxSpRemoveMethod = new QComboBox();
    comboBoxSpRemoveMethod->addItem(UI_QSTRING(APP_IFACE_SETTINGS_DVD_AUTO));
    comboBoxSpRemoveMethod->addItem(QLatin1String("CellWalk"));
    comboBoxSpRemoveMethod->addItem(QLatin1String("CellTrim"));
    comboBoxSpRemoveMethod->addItem(QLatin1String("CellFull"));

    QGridLayout *b_lay = new QGridLayout();
    b_lay->setColumnStretch(0,2);

    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_DVD_SP_REMOVE)),0,0,Qt::AlignRight);
    b_lay->addWidget(comboBoxSpRemoveMethod,0,1);
    dvdBox->setLayout(b_lay);

    QGroupBox* miscBox = new QGroupBox(QLatin1String("BD+"));
    QGridLayout *m_lay = new QGridLayout();
    m_lay->setColumnStretch(0,2);

    check_DumpAlways = new QCheckBox();
    m_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_BDP_DUMP_ALWAYS)),0,0,Qt::AlignRight);
    m_lay->addWidget(check_DumpAlways,0,1);
    miscBox->setLayout(m_lay);

    javaDir = new CDirSelectBox(NULL,CDirSelectBox::DirBoxFile,UI_QSTRING(APP_IFACE_SETTINGS_PROT_JAVA_PATH));

    QBoxLayout *lay = new QVBoxLayout();

    lay->addWidget(dvdBox);
    lay->addWidget(miscBox);
    lay->addWidget(javaDir);

    lay->addStretch(2);
    this->setLayout(lay);
}

CGeneralTab::CGeneralTab(QWidget *parent) : QWidget(parent)
{
    dataDir = new CDirSelectBox(NULL,CDirSelectBox::DirBoxDir,UI_QSTRING(APP_IFACE_SETTINGS_DATA_DIR));

    QGroupBox* miscBox = new QGroupBox(UI_QSTRING(APP_IFACE_SETTINGS_GENERAL_MISC));
    QGridLayout *m_lay = new QGridLayout();
    m_lay->setColumnStretch(0,2);

    check_DebugLog = new QCheckBox();
    m_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_LOG_DEBUG_MSG)),0,0,Qt::AlignRight);
    m_lay->addWidget(check_DebugLog,0,1);
    check_ExpertMode = new QCheckBox();
    m_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_EXPERT_MODE)),1,0,Qt::AlignRight);
    m_lay->addWidget(check_ExpertMode,1,1);
    check_ShowAV = new QCheckBox();
    m_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_SHOW_AVSYNC)),2,0,Qt::AlignRight);
    m_lay->addWidget(check_ShowAV,2,1);
    miscBox->setLayout(m_lay);


    QGroupBox* netBox = new QGroupBox(UI_QSTRING(APP_IFACE_SETTINGS_GENERAL_ONLINE_UPDATES));
    QGridLayout *net_lay = new QGridLayout();

    check_SiteAccess = new QCheckBox();
    net_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_ENABLE_INTERNET_ACCESS)), 0, 0, Qt::AlignRight);
    net_lay->addWidget(check_SiteAccess, 0, 1);
    lineEditProxy = new QLineEdit();
    net_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_PROXY_SERVER)), 1, 0, Qt::AlignRight);
    net_lay->addWidget(lineEditProxy,1,1);
    netBox->setLayout(net_lay);

    QBoxLayout *lay = new QVBoxLayout();
    lay->addWidget(dataDir);
    lay->addWidget(miscBox);
    lay->addWidget(netBox);

    lay->addStretch(2);

    this->setLayout(lay);
}

void CDVDTab::SlotIndexChanged()
{
    int index = destinationDir->getIndexValue();
    if ( (index==0) || (index==1) )
    {
        destinationDir->setDirEnabled(false);
    }
    if ( (index==2) || (index==3) )
    {
        destinationDir->setDirEnabled(true);
    }
}

typedef struct _lang_info_t
{
    const char* code;
    const char* a1;
    const char* a2;
    const char* name;
} lang_info_t;

#include <lgpl/iso639tbl.h>


CLanguageTab::CLanguageTab(CGUIApClient* ap_client,QWidget *parent) : QWidget(parent)
{
    QGroupBox* box = new QGroupBox(UI_QSTRING(APP_IFACE_SETTINGS_IO_OPTIONS));

    comboBoxInterfaceLanguage = new QComboBox();
    comboBoxInterfaceLanguage->addItem(QString(UI_QSTRING(APP_IFACE_SETTINGS_LANGUAGE_AUTO)));

    for (unsigned int i=0;i<AP_APP_LOC_MAX;i++)
    {
        const utf8_t* name;
        QString qstrName;

        name = ap_client->GetAppString(AP_vastr_InterfaceLanguage, i, 0);
        if (NULL == name) break;

        qstrName.clear();
        qstrName.reserve(10+strlen(name));
        qstrName.append(QStringFromUtf8(name,3));
        qstrName.append(QString::fromLatin1(" : "));
        qstrName.append(QStringFromUtf8(name+4));

        comboBoxInterfaceLanguage->addItem(qstrName);
    }


    comboBoxPreferredLanguage = new QComboBox();
    comboBoxPreferredLanguage->addItem(QString(UI_QSTRING(APP_IFACE_SETTINGS_LANGUAGE_NONE)));

    for (size_t i=0;i<(sizeof(lang_table)/sizeof(lang_table[0]));i++)
    {
        QString langString;

        if (!lang_table[i].a1) continue;

        langString.clear();
        langString.reserve(8+strlen(lang_table[i].name));

        langString.append(QString::fromLatin1(lang_table[i].code));
        langString.append(QString::fromLatin1(" : "));
        langString.append(QString::fromUtf8(lang_table[i].name));

        comboBoxPreferredLanguage->addItem(QString(langString));
    }

    QGridLayout *b_lay = new QGridLayout();
    b_lay->setColumnStretch(0,2);

    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_LANG_INTERFACE)),0,0,Qt::AlignRight);
    b_lay->addWidget(comboBoxInterfaceLanguage,0,1);
    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_LANG_PREFERRED)),1,0,Qt::AlignRight);
    b_lay->addWidget(comboBoxPreferredLanguage,1,1);

    box->setLayout(b_lay);

    QBoxLayout *lay = new QVBoxLayout();
    lay->addWidget(box);

    lay->addStretch(2);
    this->setLayout(lay);
}

void CLanguageTab::setValue(QComboBox*  comboBox,const utf8_t *value)
{
    comboBox->setCurrentIndex(0);
    if (!value)
    {
        return;
    }
    if (!value[0])
    {
        return;
    }

    QString valueStr = QStringFromUtf8(value);

    for (int i=1;i<comboBox->count();i++)
    {
        if (comboBox->itemText(i).startsWith(valueStr))
        {
            comboBox->setCurrentIndex(i);
            break;
        }
    }
}

const utf16_t* CLanguageTab::getValue(QComboBox*  comboBox,QString &buffer)
{
    if (comboBox->currentIndex()==0) return NULL;

    buffer.clear();
    buffer.append(comboBox->currentText().mid(0,3));

    return Utf16FromQString(buffer);
}

void CSettingDialog::toggleAdvanced(bool expert_mode)
{
    if (expert_mode && !advancedTabVisible)
    {
        tabWidget->addTab(advancedTab , UI_QSTRING(APP_IFACE_SETTINGS_TAB_ADVANCED));
        advancedTabVisible = true;
    }
    if (!expert_mode && advancedTabVisible)
    {
        tabWidget->removeTab(tabWidget->indexOf(advancedTab));
        advancedTabVisible = false;
    }
}

void CSettingDialog::SlotExpertStateChanged(int state)
{
    toggleAdvanced(state==Qt::Checked);
}

CAdvancedTab::CAdvancedTab(CGUIApClient* ap_client,QWidget *parent) : QWidget(parent)
{
    QGroupBox* box = new QGroupBox(UI_QSTRING(APP_IFACE_SETTINGS_IO_OPTIONS));

    comboProfile = new QComboBox();
    comboProfile->addItem(QString(UI_QSTRING(PROFILE_NAME_DEFAULT)));
    comboProfile->setEditable(false);

    unsigned int profile_count = (unsigned int)strtoul(ap_client->GetAppString(AP_vastr_ProfileCount),0,10);
    for (unsigned int i=1;i<profile_count;i++)
    {
        comboProfile->addItem(QStringFromUtf8(ap_client->GetAppString(AP_vastr_ProfileString,i,0)));
    }

    lineEditSelection = new QLineEdit();
    lineEditOutputFileName = new QLineEdit();

    QGridLayout *b_lay = new QGridLayout();

    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_ADV_DEFAULT_PROFILE)),0,0,Qt::AlignRight);
    b_lay->addWidget(comboProfile,0,1);
    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_ADV_DEFAULT_SELECTION)),1,0,Qt::AlignRight);
    b_lay->addWidget(lineEditSelection,1,1);
    b_lay->addWidget(createLabel(UI_QSTRING(APP_IFACE_SETTINGS_ADV_OUTPUT_FILE_NAME_TEMPLATE)),2,0,Qt::AlignRight);
    b_lay->addWidget(lineEditOutputFileName,2,1);
    box->setLayout(b_lay);

    QString titleExternExe = UI_QSTRING(APP_IFACE_SETTINGS_ADV_EXTERN_EXEC_PATH);
    ccextractorDir = new CDirSelectBox(ap_client,CDirSelectBox::DirBoxFile,
        titleExternExe.arg(QLatin1String("ccextractor")));

    QBoxLayout *lay = new QVBoxLayout();

    lay->addWidget(box);
    lay->addWidget(ccextractorDir);

    lay->addStretch(2);
    this->setLayout(lay);
}

CDecryptTab::CDecryptTab(MainWnd* mainwnd, QWidget *parent) : QWidget(parent)
{
    QGroupBox* box = new QGroupBox(UI_QSTRING(APP_IFACE_BACKUPDLG_TEXT_CAPTION));

    QLabel* labelText = new QLabel();
    labelText->setTextFormat(Qt::RichText);
    labelText->setWordWrap(true);
    labelText->setText(UI_QSTRING(APP_IFACE_SETTINGS_INT_TEXT).arg(mainwnd->formatURL("libmmbd")));
    check(connect(labelText, &QLabel::linkActivated, mainwnd, &MainWnd::SlotLaunchUrl));

    QBoxLayout *blay = new QVBoxLayout();
    blay->addWidget(labelText);
    box->setLayout(blay);

    viewItems = new QTreeWidget();
    viewItems->setRootIsDecorated(false);
    viewItems->setSelectionMode(QAbstractItemView::NoSelection);

    {
        QStringList hdr_labels;
        hdr_labels += UI_QSTRING(VITEM_NAME);
        hdr_labels += UI_QSTRING(APP_IFACE_SETTINGS_INT_HDR_PATH);
        viewItems->setHeaderLabels(hdr_labels);
    }

    QBoxLayout *lay = new QVBoxLayout();

    lay->addWidget(box);
    lay->addWidget(viewItems);

    //lay->addStretch(2);
    this->setLayout(lay);
}

void CDecryptTab::LoadSettings(CGUIApClient* client)
{
    viewItems->clear();
    for (unsigned int i=0; i<128; i++)
    {
        QTreeWidgetItem* item;
        const utf8_t *itemStr;
        unsigned int itemStatus;

        itemStr = client->GetAppString(AP_vastr_ExternalAppItem, i, 0);
        if (NULL==itemStr) break;
        if (itemStr[0]==':') break;
        if ((itemStr[0]=='x') && (itemStr[1]==0)) break;

        itemStatus = itemStr[0]-'a';

        item = new QTreeWidgetItem();
        item->setFlags(Qt::ItemIsSelectable | Qt::ItemIsUserCheckable | (((itemStatus&1)!=0)?Qt::ItemIsEnabled:Qt::NoItemFlags));
        item->setCheckState(0, (((itemStatus&2)!=0)?Qt::Checked:Qt::Unchecked));

        itemStr = client->GetAppString(AP_vastr_ExternalAppItem, i, 1);
        item->setText(0, QStringFromUtf8(itemStr));

        itemStr = client->GetAppString(AP_vastr_ExternalAppItem, i, 2);
        item->setText(1, QStringFromUtf8(itemStr));

        viewItems->addTopLevelItem(item);
    }
    viewItems->resizeColumnToContents(0);
    viewItems->resizeColumnToContents(1);
}

bool CDecryptTab::SaveSettings(CGUIApClient* client)
{
    unsigned int count = viewItems->topLevelItemCount();
    if (0==count) return true;
    if (count>256) count=256;

    uint32_t bits[8]={0};

    for (unsigned int i=0; i<count; i++)
    {
        if (Qt::Checked==viewItems->topLevelItem(i)->checkState(0))
        {
            bits[i>>5] |= (((uint32_t)1) << (i&31));
        }
    }
    return (0==client->SetExternAppFlags(bits,8));
}

