# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata
import os

block_cipher = None

datas = [
    ('mastui/app.css', 'mastui'),
    ('mastui/app.css', '.'),
    ('pyproject.toml', '.'),
    ('assets', 'assets'),
    ('LICENSE', '.'),
]

# Collect metadata and data files for dynamic packages
for pkg in ['mastui', 'textual', 'textual_image', 'mastodon.py', 'beautifulsoup4']:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

hiddenimports = [
    'textual',
    'textual._context',
    'textual.widgets',
    'textual.containers',
    'textual.binding',
    'textual.screen',
    'textual.events',
    'textual.message',
    'textual_image',
    'textual_image.renderable',
    'textual_image.widget.sixel',
    'PIL',
    'PIL.Image',
    'bs4',
    'requests',
    'httpx',
    'dotenv',
    'clipman',
    'clipman.exceptions',
    'dateutil',
    'dateutil.parser',
    'html2text',
    'toml',
    'mastui.web',
]

# Collect all resources from textual and textual_image
for pkg in ['textual', 'textual_image', 'rich', 'mastui']:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        hiddenimports += pkg_hidden
    except Exception:
        pass

icon_path = 'assets/mastui-logo.ico' if os.path.exists('assets/mastui-logo.ico') else 'assets/mastui-logo.png'
if not os.path.exists(icon_path):
    icon_path = None

a = Analysis(
    ['mastui/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mastui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
