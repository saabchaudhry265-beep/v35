# PyInstaller spec: pyinstaller --noconfirm --clean tropy_eldorii.spec
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("pygame")
datas += [("assets", "assets")]

a = Analysis(["game.py"], pathex=["."], datas=datas, binaries=binaries, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Tropy Eldorii", console=False,
    icon="assets/icon.ico", version="version_info.txt", upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Tropy Eldorii", upx=False)
