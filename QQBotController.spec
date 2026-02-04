# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('G:\\aaa\\qq\\.venv\\Lib\\site-packages\\uiautomator2\\assets', 'uiautomator2/assets')],
    hiddenimports=['e_wai_huo_yue', 'fu_li_she', 'fa_bu_shuo_shuo', 'ai_miao_hui', 'mang_he_qian', 'dian_zan_shuo_shuo', 'liu_lan_kong_jian', 'deng_lu_nong_chang', 'ri_qian_da_ka', 'tian_tian_fu_li', 'mian_fei_xiao_shuo', 'qq_yin_yue_jian_jie_ban', 'jin_bi_jia_su', 'uiautomator2', 'PIL', 'loguru', 'cv2', 'numpy'],
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
    name='QQBotController',
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
