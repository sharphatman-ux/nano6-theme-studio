# -*- mode: python ; coding: utf-8 -*-
# Slim build: QtCore/QtGui/QtWidgets only; drop QtNetwork/QtSvg/QtQml/opengl32sw,
# translations, and every imageformat plugin except the ones Pillow can't cover.
import os
ROOT = os.path.abspath('.')
QT_MODS = ['Qt3DAnimation','Qt3DCore','Qt3DExtras','Qt3DInput','Qt3DLogic','Qt3DRender',
  'QtBluetooth','QtCharts','QtConcurrent','QtDBus','QtDataVisualization','QtDesigner','QtGraphs',
  'QtHelp','QtHttpServer','QtLocation','QtMultimedia','QtMultimediaWidgets','QtNetwork',
  'QtNetworkAuth','QtNfc','QtOpenGL','QtOpenGLWidgets','QtPositioning','QtPrintSupport','QtQml',
  'QtQuick','QtQuick3D','QtQuickControls2','QtQuickWidgets','QtRemoteObjects','QtScxml',
  'QtSensors','QtSerialBus','QtSerialPort','QtSpatialAudio','QtSql','QtStateMachine','QtSvg',
  'QtSvgWidgets','QtTest','QtTextToSpeech','QtUiTools','QtWebChannel','QtWebEngine',
  'QtWebEngineCore','QtWebEngineWidgets','QtWebSockets','QtXml','QtPdf','QtPdfWidgets','QtAxContainer']
a = Analysis(
    ['src/nano6studio/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'CREDITS.md'), '.'),
        (os.path.join(ROOT, 'LICENSE'), '.'),
        (os.path.join(ROOT, 'THIRD_PARTY_LICENSES.md'), '.'),
        (os.path.join(ROOT, 'third_party'), 'third_party'),
    ],
    hiddenimports=['PIL.ImageQt'],
    excludes=['numpy','matplotlib','scipy','tkinter','_tkinter','pyfatfs','fs','pkg_resources',
              'setuptools','unittest','pydoc','doctest','xmlrpc','http.server','email','sqlite3',
              'lib2to3','pdb','multiprocessing','asyncio','ssl','_ssl','_hashlib','ctypes.test',
              'PIL.ImageTk','PIL._avif','PIL._webp','PIL._imagingcms','PIL._imagingmath',
              'PIL._imagingmorph','shiboken6.Shiboken.QtNetwork']
             + ['PySide6.' + m for m in QT_MODS],
    noarchive=False,
)
DROP = ('opengl32sw', 'qt6network', 'qt6svg', 'qt6qml', 'qt6quick', 'qt6pdf', 'qt6opengl',
        'qt6virtualkeyboard', 'qt6dbus', 'd3dcompiler', 'qt6printsupport', 'libcrypto', 'libssl',
        'qsvg', 'qtiff', 'qwebp', 'qicns', 'qtga', 'qwbmp', 'qpdf', 'qgif', 'qjpeg', 'qico',
        'qnetworklistmanager', 'qtuiotouch', 'qdirect2d', 'qoffscreen', 'qminimal',
        '_avif', '_webp', '_imagingcms', '_ssl', '_hashlib', 'libffi', '_ctypes_test',
        'msvcp140_1', 'msvcp140_2', 'qmodernwindowsstyle', 'qcertonly', 'qschannel', 'qopensslbackend')
def keep(entry):
    n = entry[0].replace('\\', '/').lower()
    if '/translations/' in n or n.endswith('.qm'):
        return False
    base = n.rsplit('/', 1)[-1]
    return not any(base.startswith(d) or ('/' + d) in n for d in DROP)
a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='Nano6ThemeStudio',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    upx_exclude=['qwindows.dll'], runtime_tmpdir=None, console=False,
)
