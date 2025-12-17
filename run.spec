# run.spec
block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('credentials.json', '.'),
        ('token.json', '.')  # Si NO existe, puedes quitar esta línea
    ],
    hiddenimports=[
        "googleapiclient",
        "googleapiclient.discovery",
        "google.oauth2",
        "google.auth.transport.requests",
        "googleapiclient.http",
        "fastapi",
        "uvicorn",
        "requests",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[]
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='run',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True
)
