import PyInstaller.__main__
import os
import uiautomator2

# 任务模块列表 (这些模块是动态加载的，PyInstaller 无法自动检测，需要手动添加)
task_modules = [
    "e_wai_huo_yue",
    "fu_li_she",
    "fa_bu_shuo_shuo",
    "ai_miao_hui",
    "mang_he_qian",
    "dian_zan_shuo_shuo",
    "liu_lan_kong_jian",
    "deng_lu_nong_chang", "ri_qian_da_ka",
    "tian_tian_fu_li", "mian_fei_xiao_shuo",
    "qq_yin_yue_jian_jie_ban", "jin_bi_jia_su"
]

# 构建 hidden imports 参数
hidden_imports = []
for module in task_modules:
    hidden_imports.extend(['--hidden-import', module])

# 添加其他可能需要的隐式依赖
hidden_imports.extend(['--hidden-import', 'uiautomator2'])
hidden_imports.extend(['--hidden-import', 'PIL'])
hidden_imports.extend(['--hidden-import', 'loguru'])
hidden_imports.extend(['--hidden-import', 'cv2'])
hidden_imports.extend(['--hidden-import', 'numpy'])

# 主入口文件
entry_point = 'gui_main.py'

# 输出文件名
name = 'QQBotController'

# PyInstaller 参数
u2_assets_path = os.path.join(os.path.dirname(uiautomator2.__file__), 'assets')
args = [
    entry_point,
    '--onefile',       # 打包成单个 exe 文件
    '--windowed',      # 不显示控制台窗口 (GUI 程序)
    '--name', name,    # 输出文件名
    '--clean',         # 清理临时文件
    '--noconfirm',     # 不询问确认
    '--add-data', 'assets;assets', # 打包图片资源
    '--add-data', f'{u2_assets_path};uiautomator2/assets', # 打包 uiautomator2 资源
] + hidden_imports

print("正在开始打包...")
print(f"包含的隐藏模块: {task_modules}")

import shutil

try:
    PyInstaller.__main__.run(args)
    
    # 复制 config.json 到 dist 目录
    if os.path.exists("config.json"):
        shutil.copy("config.json", os.path.join("dist", "config.json"))
        print(f"已复制 config.json 到 dist 目录")
        
    print("\n" + "="*50)
    print("打包完成！")
    print(f"可执行文件位置: {os.path.join(os.getcwd(), 'dist', name + '.exe')}")
    print("="*50)
except Exception as e:
    print(f"打包过程中发生错误: {e}")
