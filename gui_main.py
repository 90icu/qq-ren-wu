import json
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from loguru import logger
from emulator_manager import EmulatorManager
from bot_core import BotCore
import os
import sys
import subprocess
import cv2
from PIL import Image, ImageTk
import numpy as np

# 重定向 logger 到 UI，支持颜色
class GuiLogSink:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        
        # 配置颜色标签
        # 级别样式 (粗体)
        self.text_widget.tag_config("LEVEL_INFO", foreground="#006400", font=("Consolas", 9, "bold"))     # DarkGreen
        self.text_widget.tag_config("LEVEL_WARNING", foreground="#FF8C00", font=("Consolas", 9, "bold"))  # DarkOrange
        self.text_widget.tag_config("LEVEL_ERROR", foreground="#FF0000", font=("Consolas", 9, "bold"))    # Red
        self.text_widget.tag_config("LEVEL_DEBUG", foreground="#808080", font=("Consolas", 9, "bold"))    # Gray
        self.text_widget.tag_config("LEVEL_CRITICAL", foreground="#8B0000", background="#FFB6C1", font=("Consolas", 9, "bold"))
        
        # 内容颜色
        self.text_widget.tag_config("MSG_TASK", foreground="#0000FF")    # Blue (带【】的任务日志)
        self.text_widget.tag_config("MSG_COMMON", foreground="#008000")  # Green (公共步骤等普通日志)
        self.text_widget.tag_config("MSG_ERROR", foreground="#FF0000")   # Red (错误信息)
        self.text_widget.tag_config("MSG_WARNING", foreground="#FF8C00") # Orange (警告信息)

    def __call__(self, message):
        try:
            record = message.record
            level_name = record["level"].name
            time_str = record["time"].strftime("%H:%M:%S")
            msg_content = record["message"]
            
            self.text_widget.config(state=tk.NORMAL)
            
            # 1. 插入时间 (默认黑色)
            self.text_widget.insert(tk.END, f"{time_str} ")
            
            # 2. 插入级别 (加粗, 无额外空格，依靠前后文本的空格)
            # level_name[0] 取首字母 (I, W, E...)
            level_tag = f"LEVEL_{level_name}"
            self.text_widget.insert(tk.END, f"{level_name[0]}", level_tag)
            
            # 3. 插入消息内容 (根据内容着色)
            # 简单判断规则：
            # - ERROR 级别 -> 红色
            # - WARNING 级别 -> 橙色
            # - 带【】 -> 蓝色 (任务)
            # - 其他 -> 绿色 (公共)
            
            msg_tag = "MSG_COMMON"
            if level_name == "ERROR":
                msg_tag = "MSG_ERROR"
            elif level_name == "WARNING":
                msg_tag = "MSG_WARNING"
            elif "【" in msg_content and "】" in msg_content:
                msg_tag = "MSG_TASK"
            elif "【额外活跃】" in msg_content: # 确保包含这个前缀的也用蓝色
                msg_tag = "MSG_TASK"
            
            self.text_widget.insert(tk.END, f" {msg_content}\n", msg_tag)
            
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
        except Exception:
            pass

def load_config(path="config.json"):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        return {}

class AutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("雷电模拟器多开控制器")
        
        # 设定固定窗口大小
        window_width = 1000
        window_height = 700

        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 计算居中位置
        x_cordinate = int((screen_width/2) - (window_width/2))
        y_cordinate = int((screen_height/2) - (window_height/2))

        # 设置窗口大小并居中
        self.root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        
        # 禁止调整大小（同时会禁用/隐藏最大化按钮）
        self.root.resizable(False, False)
        
        # 加载配置
        self.config = load_config()
        self.ld_path = self.config.get("ldplayer_path", "")
        self.pkg_name = "com.tencent.mobileqq"
        
        # 初始化管理器
        self.emu_mgr = None
        if self.ld_path:
            try:
                self.emu_mgr = EmulatorManager(self.ld_path)
            except Exception as e:
                messagebox.showerror("错误", f"初始化雷电管理器失败: {e}\n请检查配置文件中的路径。")

        # 布局
        main_paned = ttk.PanedWindow(root, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 上半部分：控制区和列表 (权重 1)
        top_frame = ttk.Frame(main_paned)
        main_paned.add(top_frame, weight=1)
        
        # 工具栏
        toolbar = ttk.Frame(top_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        self.btn_launch = ttk.Button(toolbar, text="启动模拟器", command=self.launch_only_selected, state=tk.DISABLED)
        self.btn_launch.pack(side=tk.LEFT, padx=5)

        self.btn_refresh = ttk.Button(toolbar, text="刷新任务进度", command=self.refresh_task_progress_click, state=tk.DISABLED)
        self.btn_refresh.pack(side=tk.LEFT, padx=5)

        self.btn_start = ttk.Button(toolbar, text="执行全部任务", command=self.start_selected, state=tk.DISABLED)
        self.btn_start.pack(side=tk.LEFT, padx=5, ipadx=20)
        
        # 任务进度展示区域
        self.setup_progress_ui(top_frame)
        
        # 列表区域
        tree_frame = ttk.Frame(top_frame)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        columns = ("index", "title", "status", "pid")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        
        self.tree.heading("index", text="索引")
        self.tree.heading("title", text="模拟器标题")
        self.tree.heading("status", text="运行状态")
        self.tree.heading("pid", text="PID")
        
        self.tree.column("index", width=50, anchor="center")
        self.tree.column("title", width=150)
        self.tree.column("status", width=100, anchor="center")
        self.tree.column("pid", width=80, anchor="center")
        
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 中间部分：图像识别显示 (权重 3)
        self.image_frame = ttk.LabelFrame(main_paned, text="图像识别")
        main_paned.add(self.image_frame, weight=3)
        
        self.setup_image_recognition_ui(self.image_frame)

        # 下半部分：日志 (权重 4)
        log_frame = ttk.LabelFrame(main_paned, text="运行日志")
        main_paned.add(log_frame, weight=4)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志
        logger.remove()
        # 1. 输出到 GUI 文本框 (使用自定义 Sink 处理颜色和格式)
        logger.add(GuiLogSink(self.log_text), format="{message}")
        # 2. 输出到控制台 (保持带颜色，方便调试)
        if sys.stderr:
            logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")

        self.running_tasks = {} # index -> thread
        self.stop_events = {}   # index -> event
        self.restarting_tasks = set() # index -> bool, 防止重复触发重启

        # 初始刷新
        if self.emu_mgr:
            self.refresh_list_loop()

    def setup_progress_ui(self, parent):
        """
        初始化任务进度展示区域
        """
        # 使用 LabelFrame 容器
        progress_group = ttk.LabelFrame(parent, text="任务执行进度")
        progress_group.pack(side=tk.TOP, fill=tk.X, pady=5, padx=5)
        
        # 内部使用 grid 布局
        self.task_status_widgets = {} # task_name -> status_label
        
        try:
            # 获取任务列表
            temp_bot = BotCore(None)
            task_list = temp_bot.get_task_list()
            
            # 样式配置
            style = ttk.Style()
            style.configure("Status.TLabel", font=("微软雅黑", 9))
            style.configure("Pending.Status.TLabel", foreground="#808080") # 灰色
            style.configure("Running.Status.TLabel", foreground="#0000FF") # 蓝色
            style.configure("Success.Status.TLabel", foreground="#008000") # 绿色
            style.configure("Failed.Status.TLabel", foreground="#FF0000")  # 红色
            
            # 创建网格
            # 每行显示 6 个任务，每个任务占用一格 (TaskName: Status)
            cols_per_row = 6
            
            # 过滤掉额外活跃(虽然 BotCore 已过滤，再保险一次)
            filtered_list = [item for item in task_list if item[0] != "额外活跃"]
            
            for i, (task_name, _) in enumerate(filtered_list):
                row = i // cols_per_row
                col = i % cols_per_row
                
                # 每个单元格是一个小 Frame
                cell_frame = ttk.Frame(progress_group, padding=2)
                cell_frame.grid(row=row, column=col, sticky="w", padx=10, pady=2)
                
                # 任务名
                lbl_name = ttk.Label(cell_frame, text=f"{task_name}:", font=("微软雅黑", 9, "bold"))
                lbl_name.pack(side=tk.LEFT)
                
                # 状态
                lbl_status = ttk.Label(cell_frame, text="未执行", style="Pending.Status.TLabel")
                lbl_status.pack(side=tk.LEFT, padx=(5, 0))
                
                self.task_status_widgets[task_name] = lbl_status
                
        except Exception as e:
            logger.error(f"初始化进度UI失败: {e}")
            ttk.Label(progress_group, text="加载任务列表失败").pack()

    def update_task_status_ui(self, task_name, status_code):
        """
        更新任务状态 UI (线程安全)
        status_code: pending, running, success, failed
        """
        def _update():
            if task_name not in self.task_status_widgets:
                return
                
            lbl = self.task_status_widgets[task_name]
            
            if status_code == "pending":
                lbl.config(text="未执行", style="Pending.Status.TLabel")
            elif status_code == "running":
                lbl.config(text="执行中...", style="Running.Status.TLabel")
            elif status_code == "success":
                lbl.config(text="执行成功", style="Success.Status.TLabel")
            elif status_code == "failed":
                lbl.config(text="执行失败", style="Failed.Status.TLabel")
        
        self.root.after(0, _update)

    def setup_image_recognition_ui(self, parent):
        """
        初始化图像识别 UI
        """
        # 左右分栏
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左边显示模板图片
        self.panel_template = ttk.LabelFrame(paned, text="寻找目标")
        paned.add(self.panel_template, weight=1)
        
        self.lbl_template_img = ttk.Label(self.panel_template, text="无图片", anchor="center")
        self.lbl_template_img.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 右边显示实时扫描和结果
        self.panel_scan = ttk.LabelFrame(paned, text="实时扫描")
        paned.add(self.panel_scan, weight=1)
        
        # 上方显示相似度
        self.lbl_similarity = ttk.Label(self.panel_scan, text="相似度: 0.00", font=("Arial", 10, "bold"))
        self.lbl_similarity.pack(side=tk.TOP, pady=2)
        
        # 下方显示扫描图片
        self.lbl_scan_img = ttk.Label(self.panel_scan, text="等待扫描...", anchor="center")
        self.lbl_scan_img.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def update_image_recognition(self, template_path, scanned_img_bgr, similarity, match_rect, threshold=None):
        """
        更新图像识别 UI，需在主线程执行
        """
        # 使用 after 确保在主线程更新 UI
        self.root.after(0, self._update_image_recognition_ui_thread_safe, template_path, scanned_img_bgr, similarity, match_rect, threshold)

    def _update_image_recognition_ui_thread_safe(self, template_path, scanned_img_bgr, similarity, match_rect, threshold=None):
        try:
            # 1. 更新相似度标签
            color = "green" if similarity > (threshold if threshold else 0.7) else "red" 
            text = f"相似度: {similarity:.2f}"
            if threshold is not None:
                text += f"   阈值: {threshold:.2f}"
            self.lbl_similarity.config(text=text, foreground=color)
            
            # 2. 更新模板图片
            if template_path and os.path.exists(template_path):
                # 限制显示大小 (尽可能大)
                # 获取容器大小
                w_container = self.panel_template.winfo_width()
                h_container = self.panel_template.winfo_height()
                
                # 如果容器还没渲染出来，给个较大的默认值
                if w_container < 10: w_container = 300
                if h_container < 10: h_container = 300
                
                # 留一点边距
                max_size = (w_container - 10, h_container - 10)
                
                # 读取模板
                template_arr = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if template_arr is not None:
                    template_rgb = cv2.cvtColor(template_arr, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(template_rgb)
                    pil_img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(pil_img)
                    
                    self.lbl_template_img.config(image=tk_img, text="")
                    self.lbl_template_img.image = tk_img # 保持引用
                else:
                    self.lbl_template_img.config(image="", text="无法读取图片")
            
            # 3. 更新扫描图片
            if scanned_img_bgr is not None:
                # 如果有匹配区域，则裁剪显示该区域
                display_img = scanned_img_bgr
                if match_rect:
                    x, y, w, h = match_rect
                    # 确保坐标在图像范围内
                    h_img, w_img = scanned_img_bgr.shape[:2]
                    x = max(0, int(x))
                    y = max(0, int(y))
                    w = min(w_img - x, int(w))
                    h = min(h_img - y, int(h))
                    
                    if w > 0 and h > 0:
                        # 裁剪出匹配区域
                        display_img = scanned_img_bgr[y:y+h, x:x+w].copy()
                        # 不画红框，保持原图
                
                # 转 RGB
                scan_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
                pil_scan = Image.fromarray(scan_rgb)
                
                # 缩放以适应 Label
                # 获取 Label 当前大小，如果太小则给默认值
                w_label = self.lbl_scan_img.winfo_width()
                h_label = self.lbl_scan_img.winfo_height()
                
                # 尝试获取父容器大小，因为 label 可能因为图片小而变小
                w_container = self.panel_scan.winfo_width()
                h_container = self.panel_scan.winfo_height() - 30 # 减去相似度标签高度
                
                # 使用较大的那个尺寸，确保尽量填满空间
                target_w = max(w_label, w_container)
                target_h = max(h_label, h_container)

                if target_w < 10: target_w = 400
                if target_h < 10: target_h = 300
                
                # 保持比例缩放，尽可能填满
                pil_scan.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                tk_scan = ImageTk.PhotoImage(pil_scan)
                
                self.lbl_scan_img.config(image=tk_scan, text="")
                self.lbl_scan_img.image = tk_scan # 保持引用
                
        except Exception as e:
            logger.error(f"更新图像识别 UI 失败: {e}")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_refresh.config(state=tk.NORMAL)
            
            # 检查选中的模拟器状态
            has_stopped = False
            for item in selected_items:
                values = self.tree.item(item, "values")
                # values[2] is status ("运行中" or "已停止")
                if values[2] != "运行中":
                    has_stopped = True
                    break
            
            if has_stopped:
                self.btn_launch.config(state=tk.NORMAL)
            else:
                self.btn_launch.config(state=tk.DISABLED)
        else:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_launch.config(state=tk.DISABLED)
            self.btn_refresh.config(state=tk.DISABLED)

    def refresh_list_loop(self):
        """
        自动刷新循环
        """
        self.refresh_list()
        # 10秒后再次调用
        self.root.after(10000, self.refresh_list_loop)

    def refresh_list(self):
        if not self.emu_mgr:
            logger.error("未初始化模拟器管理器，无法刷新列表")
            return
            
        # 记录当前选中项，以便刷新后恢复 (如果还在)
        selected_indices = []
        for item in self.tree.selection():
             selected_indices.append(self.tree.item(item, "values")[0])
             
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            emulators = self.emu_mgr.list_emulators()
            
            for em in emulators:
                idx = em['index']
                status = "运行中" if em['is_running'] else "已停止"
                
                item = self.tree.insert("", tk.END, values=(
                    idx,
                    em['title'],
                    status,
                    em['pid']
                ))
                
                # 尝试恢复选中
                if str(idx) in selected_indices:
                    self.tree.selection_add(item)
                    
        except Exception as e:
            logger.error(f"刷新列表失败: {e}")
        
        # 如果没有选中任何项，且列表不为空，默认选中第一个
        if not self.tree.selection():
            children = self.tree.get_children()
            if children:
                self.tree.selection_set(children[0])

        # 触发一次选择事件检查按钮状态
        self.on_tree_select(None)

    def refresh_task_progress_click(self):
        """
        刷新任务进度按钮点击事件
        """
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择模拟器")
            return
            
        for item in selected_items:
            values = self.tree.item(item, "values")
            index = values[0]
            
            if index in self.running_tasks and self.running_tasks[index].is_alive():
                logger.warning(f"模拟器 [{index}] 正在运行任务，请先停止或等待完成")
                continue
                
            threading.Thread(target=self.run_refresh_wrapper, args=(index,), daemon=True).start()

    def run_refresh_wrapper(self, index):
        """
        刷新任务进度的线程逻辑
        """
        stop_event = threading.Event()
        self.stop_events[index] = stop_event
        self.running_tasks[index] = threading.current_thread()
        
        try:
            logger.info(f"刷新进度线程启动: 模拟器 [{index}]")
            
            # 1. 启动模拟器 (复用逻辑)
            timeout = self.config.get("emulator_timeout", 30)
            if not self.emu_mgr.launch(index, timeout=timeout):
                logger.error(f"模拟器 [{index}] 启动失败")
                return

            if stop_event.is_set(): return
            
            # 2. 等待 Android 就绪
            logger.info(f"[{index}] 等待 ADB 连接...")
            serial = self.emu_mgr.get_adb_serial(index)
            
            connected = False
            max_adb_retries = int(timeout / 2)
            if max_adb_retries < 1: max_adb_retries = 1
            
            for _ in range(max_adb_retries):
                if stop_event.is_set(): return
                output = self.emu_mgr.execute_cmd(["adb", "--index", str(index), "--command", "get-state"])
                if output and "device" in output:
                    connected = True
                    break
                time.sleep(2)
            
            if not connected:
                logger.error(f"[{index}] 无法连接 ADB")
                return

            # 3. 执行 Refresh 逻辑
            def status_callback(t_name, status):
                self.update_task_status_ui(t_name, status)
            
            bot = BotCore(serial, self.pkg_name, image_callback=self.update_image_recognition, task_status_callback=status_callback)
            bot.register_stop_event(stop_event)
            
            if bot.connect():
                if stop_event.is_set(): return
                bot.refresh_task_progress()
                logger.info(f"[{index}] 刷新任务进度完成")
            
        except Exception as e:
            logger.error(f"[{index}] 刷新任务异常: {e}")
        finally:
            if index in self.running_tasks:
                del self.running_tasks[index]
            if index in self.stop_events:
                del self.stop_events[index]

    def run_specific_task_click(self, task_name):
        """
        点击具体任务按钮的处理函数
        """
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择要执行任务的模拟器")
            return
            
        for item in selected_items:
            values = self.tree.item(item, "values")
            index = values[0]
            
            # 检查是否正在重启中
            if index in self.restarting_tasks:
                logger.warning(f"模拟器 [{index}] 正在重启切换任务中，请勿重复点击")
                continue

            # 如果已有任务在运行，先停止，再重启
            if index in self.running_tasks and self.running_tasks[index].is_alive():
                logger.info(f"模拟器 [{index}] 正在运行其他任务，正在停止并切换到任务: {task_name}")
                
                # 标记正在重启
                self.restarting_tasks.add(index)

                # 发送停止信号
                if index in self.stop_events:
                    self.stop_events[index].set()
                
                # 启动一个协调线程来处理等待和重启，避免阻塞 UI
                def restart_handler(idx, t_name):
                    try:
                        # 等待旧线程退出
                        old_thread = self.running_tasks.get(idx)
                        if old_thread:
                            old_thread.join(timeout=10) # 最多等10秒
                            if old_thread.is_alive():
                                logger.warning(f"[{idx}] 旧任务线程未能在10秒内正常退出，强制启动新任务")
                        
                        # 启动新任务
                        self._start_task_thread(idx, t_name)
                    finally:
                        if idx in self.restarting_tasks:
                            self.restarting_tasks.remove(idx)

                threading.Thread(target=restart_handler, args=(index, task_name), daemon=True).start()
                continue

            # 如果没有运行，直接启动
            self._start_task_thread(index, task_name)

    def _start_task_thread(self, index, task_name=None):
        """
        内部启动任务线程的逻辑
        """
        # 创建停止事件
        stop_event = threading.Event()
        self.stop_events[index] = stop_event
        
        # 启动线程
        t = threading.Thread(
            target=self.run_task_wrapper,
            args=(index, None, stop_event, task_name)
        )
        t.daemon = True
        self.running_tasks[index] = t
        t.start()

    def start_selected(self):
        """
        启动按钮：执行默认全部流程
        """
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        for item in selected_items:
            values = self.tree.item(item, "values")
            index = values[0]
            
            # 检查是否正在重启中
            if index in self.restarting_tasks:
                logger.warning(f"模拟器 [{index}] 正在重启中，请稍候")
                continue

            # 如果已有任务在运行，强制停止并重启
            if index in self.running_tasks and self.running_tasks[index].is_alive():
                logger.info(f"模拟器 [{index}] 正在运行任务，强制停止并重新执行全部任务")
                
                # 标记正在重启
                self.restarting_tasks.add(index)

                # 发送停止信号
                if index in self.stop_events:
                    self.stop_events[index].set()
                
                # 启动协调线程
                def restart_handler(idx):
                    try:
                        old_thread = self.running_tasks.get(idx)
                        if old_thread:
                            old_thread.join(timeout=10)
                        self._start_task_thread(idx, None) # None for all tasks
                    finally:
                        if idx in self.restarting_tasks:
                            self.restarting_tasks.remove(idx)

                threading.Thread(target=restart_handler, args=(index,), daemon=True).start()
                continue
            
            self._start_task_thread(index, None) # None 表示全部任务

    def launch_only_selected(self):
        """
        只启动模拟器
        """
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        for item in selected_items:
            values = self.tree.item(item, "values")
            index = values[0]
            
            # 使用 threading 启动，避免卡住 UI
            threading.Thread(target=self._launch_emulator_thread, args=(index,), daemon=True).start()

    def _launch_emulator_thread(self, index):
        try:
            # 尝试获取标题
            title = f"[{index}]"
            try:
                # 从 treeview 中查找标题 (如果在主线程可能更安全，但这里是只读)
                # 或者调用 emu_mgr 获取
                # 为了简单，直接调用 list2 获取最新标题
                output = self.emu_mgr.execute_cmd(["dnconsole", "list2"])
                if output:
                    for line in output.strip().split('\n'):
                        parts = line.split(',')
                        if len(parts) > 1 and str(parts[0]) == str(index):
                            title = f"[{index}:{parts[1]}]"
                            break
            except:
                pass

            logger.info(f"正在启动模拟器 {title}...")
            if self.emu_mgr.launch_emulator(index):
                logger.info(f"模拟器 {title} 启动指令已发送")
            else:
                logger.error(f"模拟器 {title} 启动失败")
        except Exception as e:
            logger.error(f"启动模拟器 [{index}] 异常: {e}")



        
    def stop_single_task(self, index):
        if index in self.stop_events:
            self.stop_events[index].set()
            logger.info(f"已发送停止信号给模拟器 [{index}]")
        
    def run_task_wrapper(self, index, account_config, stop_event, specific_task_name=None):
        try:
            logger.info(f"任务线程启动: 模拟器 [{index}] {f'| 目标任务: {specific_task_name}' if specific_task_name else ''}")
            
            # 1. 启动模拟器
            # check if running
            is_running_before = False
            # 简单检查一下状态（其实 launch 内部也会检查，但我们需要知道之前的状态来决定是否重启QQ）
            # 注意：这里调用 list_emulators 可能会慢，而且我们是在线程里。
            # 暂时假设：如果 emu_mgr.launch 返回 True 且极快，说明已经在运行。
            # 或者我们可以通过 execute_cmd 检查 pid
            
            # 但最靠谱的是根据用户指示：
            # "如果未启动点击，就自动启动然后完成对应的任务"
            # "如果已启动就在模拟器里结束QQ进程然后重启QQ自行执行对应任务"
            
            # 我们先尝试 launch，如果它本来就在运行，launch 会直接返回 True
            # 但是我们需要知道它"本来"是否在运行。
            # 我们可以利用 self.emu_mgr.list_emulators() 的结果，但那个是定时的。
            # 直接查询一次状态吧
            
            check_running = self.emu_mgr.execute_cmd(["dnconsole", "list2"])
            # list2 format: index,title,top_hwnd,bind_hwnd,android_running,pid,vbox_pid
            # 简单解析一下
            if check_running:
                lines = check_running.strip().split('\n')
                for line in lines:
                    parts = line.split(',')
                    if len(parts) > 4 and str(parts[0]) == str(index):
                         if parts[4] == "1":
                             is_running_before = True
                         break
            
            # 获取超时配置
            timeout = self.config.get("emulator_timeout", 30)

            if not self.emu_mgr.launch(index, timeout=timeout):
                logger.error(f"模拟器 [{index}] 启动失败")
                return

            if stop_event.is_set(): return
            
            # 2. 等待 Android 就绪
            logger.info(f"[{index}] 等待 ADB 连接 (超时: {timeout}s)...")
            serial = self.emu_mgr.get_adb_serial(index)
            
            connected = False
            max_adb_retries = int(timeout / 2)
            if max_adb_retries < 1: max_adb_retries = 1
            
            for _ in range(max_adb_retries):
                if stop_event.is_set(): return
                output = self.emu_mgr.execute_cmd(["adb", "--index", str(index), "--command", "get-state"])
                if output and "device" in output:
                    connected = True
                    break
                time.sleep(2)
            
            if not connected:
                logger.error(f"[{index}] 无法连接 ADB")
                return

            # 3. 执行 Bot 逻辑
            
            # 定义状态回调
            def status_callback(t_name, status):
                self.update_task_status_ui(t_name, status)
            
            bot = BotCore(serial, self.pkg_name, image_callback=self.update_image_recognition, task_status_callback=status_callback)
            bot.register_stop_event(stop_event)
            
            if bot.connect():
                if stop_event.is_set(): return
                
                if stop_event.is_set(): return
                
                if stop_event.is_set(): return
                
                if stop_event.is_set(): return
                # 传入特定任务名称
                bot.perform_task(target_task_name=specific_task_name)
                
                logger.info(f"[{index}] 自动化任务完成")

                # 如果是执行全部任务，完成后自动刷新进度
                if specific_task_name is None and not stop_event.is_set():
                     logger.info(f"[{index}] 全任务流程结束，开始自动刷新进度...")
                     bot.refresh_task_progress()
            
        except Exception as e:
            logger.error(f"[{index}] 任务异常: {e}")
        finally:
            # 清理
            if index in self.running_tasks:
                del self.running_tasks[index]
            if index in self.stop_events:
                del self.stop_events[index]

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationGUI(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("程序已停止")
        sys.exit(0)
