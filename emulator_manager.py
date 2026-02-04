import subprocess
import os
import time
from loguru import logger

class EmulatorManager:
    def __init__(self, install_path):
        """
        初始化模拟器管理器
        :param install_path: 雷电模拟器安装路径 (包含 dnconsole.exe 的文件夹)
        """
        self.install_path = install_path
        self.console_exe = os.path.join(install_path, "dnconsole.exe")
        
        if not os.path.exists(self.console_exe):
            logger.error(f"未找到 dnconsole.exe，请检查路径: {self.console_exe}")
            raise FileNotFoundError(f"dnconsole.exe not found in {install_path}")

    def execute_cmd(self, args, retries=3):
        """执行 dnconsole 命令，带重试机制"""
        cmd = [self.console_exe] + args
        
        last_error = None
        for attempt in range(retries):
            try:
                # hide console window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='gbk', # 雷电控制台通常输出 gbk 编码
                    startupinfo=startupinfo
                )
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    last_error = stderr if stderr else f"Return code: {process.returncode}"
                    if attempt < retries - 1:
                        time.sleep(1) # 失败等待1秒后重试
                        continue
                    logger.error(f"命令执行失败 (已重试{retries}次): {cmd}, 错误: {last_error}")
                else:
                    return stdout.strip()
                    
            except Exception as e:
                last_error = str(e)
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                logger.error(f"执行命令异常 (已重试{retries}次): {e}")
                return None
        
        return None

    def list_emulators(self):
        """
        获取模拟器列表
        返回格式: list of dict, e.g. [{'index': '0', 'title': '雷电模拟器', ...}]
        dnconsole list2 返回: 索引,标题,顶层句柄,绑定句柄,是否进入安卓,PID,VBoxPID
        """
        output = self.execute_cmd(["list2"])
        emulators = []
        if output:
            lines = output.split('\n')
            for line in lines:
                parts = line.split(',')
                if len(parts) >= 7:
                    emulators.append({
                        "index": parts[0],
                        "title": parts[1],
                        "is_running": parts[4] == "1",
                        "pid": parts[5]
                    })
        return emulators

    def set_resolution(self, index, width, height, dpi=240):
        """
        设置模拟器分辨率
        dnconsole modify --index 0 --resolution 591,1000,240
        注意：修改分辨率通常需要重启模拟器才能生效，建议在 launch 之前调用
        """
        logger.info(f"设置模拟器 [{index}] 分辨率: {width}x{height} (DPI: {dpi})")
        # 如果模拟器正在运行，修改可能不会立即生效或者需要重启
        # 这里只负责下发命令
        self.execute_cmd(["modify", "--index", str(index), "--resolution", f"{width},{height},{dpi}"])

    def launch(self, index):
        """启动指定索引的模拟器"""
        logger.info(f"正在启动模拟器 [{index}]...")
        
        # 启动前强制设置分辨率
        self.set_resolution(index, 504, 955, 240)
        
        self.execute_cmd(["launch", "--index", str(index)])
        
        # 简单的等待逻辑，实际可能需要轮询 check running 状态
        # 这里为了演示简单，循环检查状态直到运行
        for _ in range(30):
            if self.is_running(index):
                logger.info(f"模拟器 [{index}] 已启动")
                return True
            time.sleep(2)
        
        logger.warning(f"模拟器 [{index}] 启动超时")
        return False

    def launch_emulator(self, index):
        """
        GUI 调用的启动接口 (别名)
        """
        # 为了不阻塞 UI 线程太久，这里只发送指令，不等待启动完成
        # 或者快速检查一次
        
        # 启动前强制设置分辨率
        self.set_resolution(index, 504, 955, 240)
        
        logger.info(f"发送启动指令: 模拟器 [{index}]")
        self.execute_cmd(["launch", "--index", str(index)])
        return True

    def quit(self, index):
        """关闭指定索引的模拟器"""
        logger.info(f"正在关闭模拟器 [{index}]...")
        self.execute_cmd(["quit", "--index", str(index)])

    def is_running(self, index):
        """检查指定索引是否在运行"""
        emulators = self.list_emulators()
        for em in emulators:
            if str(em['index']) == str(index):
                return em['is_running']
        return False

    def get_adb_serial(self, index):
        """
        获取模拟器的 ADB 序列号 (serial)
        雷电模拟器通常是 127.0.0.1:5555 + (index * 2)
        或者可以用 adb devices 查看
        这里简单推算
        """
        port = 5555 + (int(index) * 2)
        return f"127.0.0.1:{port}"
