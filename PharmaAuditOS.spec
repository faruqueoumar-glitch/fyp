# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ("app", "app"),
    ("src", "src"),
]
binaries = []
hiddenimports = [
    "waitress",
    "webview",
    "zeroconf",
    "whitenoise",
    "app.apps",
    "app.sync_engine",
    "app.sync_views",
    "src.settings.dev",
    "src.settings.base",
    "src.urls",
    "src.wsgi",
] + collect_submodules("django") + collect_submodules("whitenoise") + collect_submodules("zeroconf") + collect_submodules("app") + collect_submodules("src")

for pkg in ("webview", "waitress"):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ["desktop_app.py"],
    pathex=[".", "src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PharmaAuditOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="PharmaAuditOS",
)
