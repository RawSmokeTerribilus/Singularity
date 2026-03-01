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
#ifndef APP_SETTINGDLG_H
#define APP_SETTINGDLG_H

#include "qtgui.h"
#include <lgpl/aproxy.h>
#include "dirselectbox.h"

class MainWnd;

class CGeneralTab : public QWidget
{
    Q_OBJECT

public:
    CDirSelectBox*   dataDir;

    QCheckBox*      check_DebugLog;
    QCheckBox*      check_SiteAccess;
    QCheckBox*      check_ExpertMode;
    QCheckBox*      check_ShowAV;
    QLineEdit*      lineEditProxy;

public:
    CGeneralTab(QWidget *parent = 0);
};

class CLanguageTab : public QWidget
{
    Q_OBJECT

public:
    QComboBox*  comboBoxInterfaceLanguage;
    QComboBox*  comboBoxPreferredLanguage;

public:
    CLanguageTab(CGUIApClient* ap_client,QWidget *parent = 0);
    static void setValue(QComboBox*  comboBox,const utf8_t *value);
    static const utf16_t* getValue(QComboBox*  comboBox,QString &buffer);
};


class CIOTab : public QWidget
{
    Q_OBJECT

public:
    QSpinBox*   spinBoxRetryCount;
    QComboBox*  comboBoxRBufSize;
    QComboBox*  comboBoxDarwinK2Workaround;
    QCheckBox*  checkSingleDrive;

public:
    CIOTab(QWidget *parent = 0);
};

class CDVDTab : public QWidget
{
    Q_OBJECT

public:
    CDirSelectBox*   destinationDir;
    QRadioButton*   radio_None;
    QRadioButton*   radio_Auto;
    QRadioButton*   radio_SemiAuto;
    QRadioButton*   radio_Custom;

    QSpinBox*    spinBoxMinimumTitleLength;


public:
    CDVDTab(CApClient* ap_client,QWidget *parent = 0);
private slots:
    void SlotIndexChanged();
};

class CProtTab : public QWidget
{
    Q_OBJECT

public:
    QComboBox*   comboBoxSpRemoveMethod;
    QCheckBox*      check_DumpAlways;
    CDirSelectBox*  javaDir;

public:
    CProtTab(QWidget *parent = 0);
};

class CDecryptTab : public QWidget
{
    Q_OBJECT

public:
    QTreeWidget*      viewItems;

public:
    CDecryptTab(MainWnd* mainwnd, QWidget *parent = 0);
    void LoadSettings(CGUIApClient* ap_client);
    bool SaveSettings(CGUIApClient* ap_client);
};


class CAdvancedTab : public QWidget
{
    Q_OBJECT

public:
    QComboBox*      comboProfile;
    QLineEdit*      lineEditSelection;
    QLineEdit*      lineEditOutputFileName;
    CDirSelectBox*  ccextractorDir;

public:
    CAdvancedTab(CGUIApClient* ap_client,QWidget *parent = 0);
};

class CSettingDialog : public QDialog
{
    Q_OBJECT

public:
    CSettingDialog(MainWnd* mainwnd, QIcon* icon, QWidget *parent = 0);
    ~CSettingDialog();

private:
    CGUIApClient* client;
    QTabWidget *tabWidget;
    QDialogButtonBox *buttonBox;

public: // tabs
    CGeneralTab* generalTab;
    CLanguageTab* languageTab;
    CIOTab* ioTab;
    CDVDTab* dvdTab;
    CProtTab* protTab;
    CDecryptTab* decryptTab;
    CAdvancedTab* advancedTab;
    bool advancedTabVisible;
private:
    bool newSettings;
    bool oldExpertMode;
    bool newExpertMode;
    QString oldOutputFileName;
    QString newOutputFileName;

private:
    void toggleAdvanced(bool expert_mode);
private slots:
    void SlotApply();
    void SlotExpertStateChanged(int state);
private:
    void ReadSettings(bool first);
    bool WriteSettings(bool& restartRequired);
public:
    bool redrawRequired();
};


#endif // APP_SETTINGDLG_H
