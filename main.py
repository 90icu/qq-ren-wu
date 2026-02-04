import json
import time
import threading
from loguru import logger
from emulator_manager import EmulatorManager
from bot_core import BotCore
import os

def load_config(path="config.json"):
    if not os.path.exists(path):
        logger.error(f"配置文件不存在: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_emulator_task(account_config, ld_path, pkg_name):
    """
    单个模拟器的任务流程
    """
    index = account_config.get("emulator_index", 0)
    username = account_config.get("username")
    password = account_config.get("password")
    
    logger.info(f"启动任务线程: 模拟器[{index}] - 账号: {username}")
    
    # 1. 初始化模拟器管理器
    emu_mgr = EmulatorManager(ld_path)
    
    # 2. 启动模拟器
    if not emu_mgr.launch(index):
        logger.error(f"模拟器[{index}] 启动失败，任务终止")
        return

    # 等待安卓系统完全启动 (adb 可连)
    time.sleep(20) # 这里的等待时间可能需要根据机器性能调整
    
    # 3. 获取 ADB Serial
    serial = emu_mgr.get_adb_serial(index)
    
    # 4. 初始化 Bot
    bot = BotCore(serial, pkg_name)
    
    if bot.connect():
        # 5. 启动 APP
        bot.start_app()
        
        # 6. 处理弹窗
        bot.handle_popup()
        
        # 7. 登录
        bot.login_qq(username, password)
        
        # 8. 执行任务
        bot.perform_task()
        
        logger.info(f"模拟器[{index}] 任务完成")
        
        # 9. 关闭模拟器 (可选，看是否需要挂机)
        # emu_mgr.quit(index)
    else:
        logger.error(f"无法连接到模拟器[{index}]")

def main():
    # 1. 读取配置
    config = load_config()
    if not config:
        return

    ld_path = config.get("ldplayer_path")
    pkg_name = "com.tencent.mobileqq"
    accounts = config.get("accounts", [])

    if not accounts:
        logger.warning("没有配置账号任务")
        return

    threads = []
    
    # 2. 为每个账号启动一个线程
    for account in accounts:
        t = threading.Thread(target=run_emulator_task, args=(account, ld_path, pkg_name))
        threads.append(t)
        t.start()
        # 错开启动时间，避免瞬间占用过高 CPU
        time.sleep(10)

    # 等待所有线程结束
    for t in threads:
        t.join()

    logger.info("所有任务已结束")

if __name__ == "__main__":
    main()
