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
#ifndef APP_QTGUI_H
#define APP_QTGUI_H

#include <QtCore/qglobal.h>
#include <QtCore/QFileInfo>
#include <QtCore/QTime>
#include <QtCore/QBitArray>
#include <QtCore/QTimer>
#include <QtCore/QElapsedTimer>
#include <QtCore/QUrl>
#include <QtCore/QMimeData>

#include <QtGui/QImage>
#include <QtGui/QPixmap>
#include <QtGui/QIcon>
#include <QtGui/QKeyEvent>
#include <QtGui/QDesktopServices>
#include <QtGui/QScreen>
#include <QtGui/QFontDatabase>

#include <QtWidgets/QApplication>
#include <QtWidgets/QMessageBox>
#include <QtWidgets/QDialog>
#include <QtWidgets/QInputDialog>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QTextEdit>
#include <QtWidgets/QGroupBox>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QTreeWidgetItem>
#include <QtWidgets/QToolButton>
#include <QtWidgets/QProgressBar>
#include <QtWidgets/QStackedWidget>
#include <QtWidgets/QComboBox>
#include <QtWidgets/QAction>
#include <QtWidgets/QCheckBox>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QBoxLayout>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QDialogButtonBox>
#include <QtWidgets/QSpinBox>
#include <QtWidgets/QRadioButton>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QScrollBar>
#include <QtWidgets/QMenu>
#include <QtWidgets/QMenuBar>
#include <QtWidgets/QToolBar>
#include <QtWidgets/QStatusBar>
#include <QtWidgets/QSplitter>
#include <QtWidgets/QFileDialog>

inline static QString qt_html_escape(const QString &plain)
{
    return plain.toHtmlEscaped();
}

#endif // APP_QTGUI_H

