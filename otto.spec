# Build on Windows from the repository root. Persistent files are external.
a = Analysis(['main.py'], pathex=[], binaries=[], datas=[],
             hiddenimports=['uvicorn.logging', 'uvicorn.loops.auto',
                            'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
                            'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on'],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Otto',
          debug=False, strip=False, upx=False, console=True)
