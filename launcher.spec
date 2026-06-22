# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    # Bundle the static web files only.
    # We do NOT bundle .battle files because:
    #   1. It may contain stale tournament data from build time
    #   2. DB_FILE is always resolved relative to sys.executable (the exe), not
    #      the PyInstaller temp extraction dir (sys._MEIPASS), so the bundled
    #      file was never actually used anyway.
    # A fresh .battle file will be created next to the exe on first run if none exists.
    datas=[('static', 'static')],
    hiddenimports=[
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BattleBotsManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
