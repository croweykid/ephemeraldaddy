# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

pyside_datas, pyside_binaries, pyside_hidden = collect_all("PySide6")
shiboken_datas, shiboken_binaries, shiboken_hidden = collect_all("shiboken6")

datas = [('tools/cities15000.txt', 'tools'),
 ('de421.bsp', '.'),
 ('ephemeraldaddy/graphics', 'ephemeraldaddy/graphics'),
 ('ephemeraldaddy/gui/fonts', 'ephemeraldaddy/gui/fonts'),
 ('ephemeraldaddy/data/compiled', 'ephemeraldaddy/data/compiled')] + pyside_datas + shiboken_datas
binaries = pyside_binaries + shiboken_binaries
hiddenimports = ['PySide6', 'shiboken6', 'swisseph', 'geopy.geocoders.nominatim'] + pyside_hidden + shiboken_hidden
excludes = ['pytest', 'pandas.tests', 'numpy.tests', 'numpy.f2py.tests', 'matplotlib.tests', 'skyfield.tests']

a = Analysis(
    ["ephemeraldaddy/gui/bootstrap.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EphemeralDaddy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EphemeralDaddy',
)
