import sys
import uiautomator2 as u2
import time
from loguru import logger
import os
import importlib
import e_wai_huo_yue
import cv2
import numpy as np


# 配置 Loguru 格式
# 注意：如果在 gui_main.py 中运行，这里的配置会被覆盖
# 仅保留用于单独测试 bot_core.py
if __name__ == "__main__":
    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )

class DeviceDisconnectedError(Exception):
    """设备断开连接异常"""
    pass

class BotCore:
    def __init__(self, serial, package_name="com.tencent.mobileqq", image_callback=None, task_status_callback=None):
        self.serial = serial
        self.package_name = package_name
        self.d = None
        self.stop_event = None
        self.image_callback = image_callback
        self.task_status_callback = task_status_callback
        self.current_task_skipped = False # 标记当前任务是否因已完成而跳过

        # 定义额外活跃任务集合及对应的任务文本 (用于检测是否已完成)
        self.extra_active_tasks_map = {
            "福利社": "福利社",
            "发布说说": "发布一条空间说说",
            "AI妙绘": "使用AI妙绘",
            "盲盒签": "参与盲盒签并成功发布至空间",
            "点赞说说": "点赞一条好友动态",
            "浏览空间": "浏览十条空间好友动态",
            "登陆农场": "登录经典农场小游戏",
            "日签打卡": "去日签卡打一次卡",
            "天天福利": "去天天领福利",
            "免费小说": "去免费小说看任一本书",
            "QQ音乐简洁": "去QQ音乐简洁版听歌",
            "金币加速": "使用金币兑换等级加速"
        }

    def update_task_status(self, task_name, status):
        """
        更新任务状态
        status: pending, running, success, failed
        """
        if self.task_status_callback:
            try:
                self.task_status_callback(task_name, status)
            except Exception as e:
                logger.error(f"更新任务状态回调失败: {e}")

    def register_stop_event(self, event):
        """
        注册外部停止事件，用于在任务执行中途响应停止信号
        """
        self.stop_event = event

    def get_resource_path(self, relative_path):
        """
        获取资源绝对路径，适配 PyInstaller 打包
        """
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def connect(self):
        try:
            logger.info(f"正在连接设备 {self.serial}")
            self.d = u2.connect(self.serial)
            logger.info(f"设备 {self.serial} 连接成功")
            # 设置全局隐式等待，默认查找元素等待 10s
            self.d.implicitly_wait(10.0)
            return True
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            return False

    def start_app(self):
        if self.d:
            logger.info(f"启动应用 {self.package_name}")
            self.d.app_start(self.package_name)
            # 优化：每秒检查，超时20秒，不打印日志
            for _ in range(20):
                if self.d(text="消息").exists:
                    logger.info("应用主页已加载")
                    return True
                time.sleep(1)
            
            logger.warning("应用启动可能超时，未检测到主页")
            return False
        else:
            logger.error("设备未连接")
            return False

    def ensure_app_started(self):
        """
        确保应用已启动（如果未在前台则拉起，不强制等待主页）
        """
        try:
            current = self.d.app_current()
            if current['package'] == self.package_name:
                return True
            
            logger.info(f"应用不在前台 (当前: {current.get('package')})，正在拉起...")
            self.d.app_start(self.package_name)
            time.sleep(5)
            return True
        except Exception as e:
            logger.warning(f"检查应用状态失败: {e}")
            # 尝试盲启动
            try:
                self.d.app_start(self.package_name)
                time.sleep(5)
                return True
            except:
                return False

    def handle_popup(self):
        logger.info("检查弹窗")
        allow_texts = ["允许", "同意", "确定", "始终允许", "仅在使用中允许"]
        # 快速检查，不等待
        self.d.implicitly_wait(1.0)
        for text in allow_texts:
            if self.d(text=text).exists:
                logger.info(f"点击弹窗按钮: {text}")
                self.d(text=text).click()
        # 恢复默认等待
        self.d.implicitly_wait(10.0)

    def reset_app_state(self, prefix=""):
        """
        强制杀掉 QQ、波点音乐、QQ音乐进程，并重新启动 QQ
        """
        logger.info(f"{prefix} 重置应用状态：关闭所有相关进程并重启 QQ")
        try:
            # 杀掉相关进程
            logger.info(f"{prefix} 正在关闭 QQ...")
            self.d.app_stop("com.tencent.mobileqq")
            time.sleep(2)
            logger.info(f"{prefix} 正在关闭 波点音乐...")
            self.d.app_stop("cn.wenyu.bodian")
            time.sleep(2)
            logger.info(f"{prefix} 正在关闭 QQ音乐...")
            self.d.app_stop("com.tencent.qqmusic")
            time.sleep(2)
            
            # 增加等待时间，避免立即启动导致黑屏
            time.sleep(5)
            
            # 启动 QQ
            logger.info(f"{prefix} 正在启动 QQ...")
            self.d.app_start("com.tencent.mobileqq")
            
            # 确保屏幕是亮着的
            try:
                self.d.screen_on()
            except:
                pass
            
            # 等待启动完成
            # 优化为轮询检测
            # time.sleep(20)
            for _ in range(20):
                if self.d(text="消息").exists:
                    logger.info(f"{prefix} QQ主页已加载")
                    break
                time.sleep(1)
            
            self.handle_popup()
            return True
        except Exception as e:
            logger.error(f"{prefix} 重置应用状态失败: {e}")
            return False

    def login_qq(self, username, password):
        logger.info("假设已登录，跳过登录步骤")
        return True

    def restart_qq(self, prefix=""):
        """
        重启 QQ 应用，尝试最多5次
        """
        logger.info(f"{prefix} 正在重启 QQ")
        if not self.d:
            return False

        max_retries = 5
        for i in range(max_retries):
            try:
                logger.info(f"{prefix} 重启 QQ 第 {i+1}/{max_retries} 次尝试")
                self.d.app_stop(self.package_name)
                time.sleep(2)
                
                # 启动应用
                if self.start_app():
                    time.sleep(5) # 等待启动
                    self.handle_popup()
                    return True
                
                # 如果启动失败，尝试返回桌面清理环境
                logger.warning(f"{prefix} 第 {i+1} 次启动超时，尝试清理环境后重试")
                self.d.press("home")
                time.sleep(1)
                self.d.app_stop(self.package_name)
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"{prefix} 重启 QQ 异常: {e}")
                time.sleep(1)

        logger.error(f"{prefix} 重启 QQ 失败，已达到最大重试次数")
        return False

    def navigate_to_extra_active(self):
        """
        公共步骤：点击头像 -> 等级 -> 更多任务 -> 额外活跃
        返回 True 表示成功进入，False 表示失败
        逻辑已移至 e_wai_huo_yue.navigate
        """
        return e_wai_huo_yue.navigate(self)

    def get_task_list(self):
        """
        获取可用任务列表，用于 GUI 生成按钮
        返回: list of (task_name, module_name)
        """
        return [
            ("福利社", "fu_li_she"),
            ("发布说说", "fa_bu_shuo_shuo"),
            ("AI妙绘", "ai_miao_hui"),
            ("盲盒签", "mang_he_qian"),
            ("点赞说说", "dian_zan_shuo_shuo"),
            ("浏览空间", "liu_lan_kong_jian"),
            ("登陆农场", "deng_lu_nong_chang"),
            ("日签打卡", "ri_qian_da_ka"),
            ("金币加速", "jin_bi_jia_su"),
            ("天天福利", "tian_tian_fu_li"),
            ("免费小说", "mian_fei_xiao_shuo"),
            ("QQ音乐简洁", "qq_yin_yue_jian_jie_ban"),
            ("添加好友", "tian_jia_hao_you")
        ]

    def perform_task(self, target_task_name=None):
        logger.info(f"开始执行任务流程 {f'[{target_task_name}]' if target_task_name else '[全部]'}")
        if not self.check_alive():
            logger.error("设备未连接，无法执行任务")
            return

        # 获取任务列表
        task_definitions = self.get_task_list()
        
        # 转换为 (module, name) 列表
        tasks_to_run = []
        for name, module_name in task_definitions:
             # 如果指定了目标任务，只添加该任务
             if target_task_name and name != target_task_name:
                 continue
             
             try:
                 module = importlib.import_module(module_name)
                 tasks_to_run.append((module, name))
             except ImportError as e:
                 logger.error(f"无法加载任务模块 {module_name}: {e}")

        if not tasks_to_run:
            logger.warning("没有可执行的任务")
            return

        last_task_skipped = False
        just_restarted = False # 标记是否刚刚重启过 QQ
        any_task_failed = False # 标记是否有任务执行失败（用于决定是否需要刷新进度）

        try:
            for module, task_name in tasks_to_run:
                # 如果是执行全部任务，且即将执行“添加好友”
                if target_task_name is None and task_name == "添加好友":
                    # 根据用户需求：如果每个任务都执行成功，就不要再执行刷新任务进度的功能了
                    if any_task_failed:
                        logger.info("检测到之前有任务执行失败，在执行【添加好友】前刷新任务进度...")
                        self.refresh_task_progress()
                    else:
                        logger.info("所有前置任务均执行成功，跳过刷新任务进度，直接执行【添加好友】")

                if not self.check_alive(): 
                    self.update_task_status(task_name, "failed")
                    any_task_failed = True
                    raise DeviceDisconnectedError("设备连接已断开")
                
                # 标记为执行中
                self.update_task_status(task_name, "running")
                
                should_reset = True
                current_task_is_completed = False

                # 1. 尝试检测任务是否已完成 (仅针对额外活跃系列)
                # 策略：如果上一个任务已跳过（意味着我们在列表页），则尝试直接检查当前任务是否也已完成
                # 避免在上一个任务刚执行完（状态未重置）的情况下强行导航导致错误
                if last_task_skipped and task_name in self.extra_active_tasks_map:
                    task_text = self.extra_active_tasks_map[task_name]
                    
                    # 确保应用已启动，否则无法导航
                    self.ensure_app_started()

                    # 尝试进入额外活跃页面 (如果已经在页面上，navigate 会很快返回 True)
                    # 注意：navigate_to_extra_active 可能会因为找不到入口而返回 False，此时需要重置
                    if self.navigate_to_extra_active():
                        # 滚动查找任务文本，并在滚动过程中检查是否已完成
                        if self.scroll_and_check_completed(task_text):
                            logger.info(f"【{task_name}】检测到已完成，跳过执行且不重启")
                            current_task_is_completed = True
                            should_reset = False
                
                # 2. 如果任务已完成，直接跳过本次循环的后续步骤
                if current_task_is_completed:
                    self.update_task_status(task_name, "success")
                    last_task_skipped = True
                    just_restarted = False # 任务完成了，重置标记
                    continue

                # 3. 如果未完成，决定是否重置
                # 如果上一个任务是跳过的（说明我们在列表页），且当前任务也是额外活跃系列，则不重置
                if last_task_skipped and task_name in self.extra_active_tasks_map:
                    should_reset = False
                    logger.info(f"因上一个任务已跳过，保持当前状态执行【{task_name}】")
                
                # 如果刚刚重启过 QQ 且处于额外活跃页面（由 run_task_with_retry 保证），则不重置
                if just_restarted:
                     should_reset = False
                     logger.info(f"因刚刚重启过 QQ 并完成了前一个任务，保持当前状态执行【{task_name}】")
                     just_restarted = False # 使用一次后重置

                if should_reset:
                    # 每个任务执行前重置应用状态
                    if not self.reset_app_state():
                        logger.error(f"【{task_name}】重置应用状态失败，跳过此任务")
                        self.update_task_status(task_name, "failed")
                        any_task_failed = True
                        last_task_skipped = False
                        just_restarted = False
                        continue
                
                # 使用 lambda 包装，以便在 run_task_with_retry 中调用
                task_func = lambda: module.execute(self)
                
                # 重置当前任务的跳过状态
                self.current_task_skipped = False
                
                success, restarted = self.run_task_with_retry(task_func, task_name)
                if success:
                     self.update_task_status(task_name, "success")
                else:
                     self.update_task_status(task_name, "failed")
                     any_task_failed = True
                
                # 更新 last_task_skipped 状态，依据任务执行过程中是否标记了 skipped
                last_task_skipped = self.current_task_skipped
                
                # 更新 just_restarted 状态，供下一个任务判断是否需要重置
                if restarted:
                    just_restarted = True
                else:
                    just_restarted = False
                
            logger.info("所有任务流程结束")
            
        except DeviceDisconnectedError:
            logger.error("任务流程因设备断开而终止")
            return

    def run_task_with_retry(self, task_func, task_name):
        """
        执行单个任务，包含公共步骤和重试机制
        返回 (success, restarted) 元组
        success: True 表示成功，False 表示失败
        restarted: True 表示在执行过程中发生了重启 QQ 的操作（且最后处于可用状态）
        """
        restarted = False
        
        # 判断是否需要进入额外活跃页面
        is_extra_active_task = task_name in self.extra_active_tasks_map

        # 尝试执行公共步骤 (仅针对额外活跃任务)
        if is_extra_active_task:
            if not self.navigate_to_extra_active():
                logger.warning(f"【{task_name}】执行失败，尝试重启 QQ")
                self.restart_qq()
                restarted = True
                if not self.navigate_to_extra_active():
                    logger.error(f"重启后公共步骤依然失败，跳过任务【{task_name}】")
                    return False, restarted
        else:
            logger.info(f"【{task_name}】非额外活跃任务，跳过公共导航步骤")

        logger.info(f"准备执行任务:【{task_name}】")

        # 尝试执行具体任务
        if task_func():
            return True, restarted
        else:
            logger.warning(f"【{task_name}】任务执行失败，尝试重启 QQ")
            self.restart_qq()
            restarted = True
            
            # 重启后再次执行公共步骤 (如果需要)
            if is_extra_active_task:
                if self.navigate_to_extra_active():
                    logger.info(f"重启后公共步骤执行成功，正在重试任务【{task_name}】...")
                    
                    # 重试任务
                    if task_func():
                        logger.info(f"【{task_name}】任务重试成功")
                        return True, restarted
                    else:
                        logger.error(f"【{task_name}】任务重试依然失败，继续下一个任务")
                        return False, restarted
                else:
                    logger.error(f"重启后公共步骤执行失败，无法继续")
                    return False, restarted
            else:
                # 非额外活跃任务，重启后直接重试
                logger.info(f"重启后正在重试任务【{task_name}】...")
                if task_func():
                    logger.info(f"【{task_name}】任务重试成功")
                    return True, restarted
                else:
                    logger.error(f"【{task_name}】任务重试依然失败，继续下一个任务")
                    return False, restarted


    def refresh_task_progress(self):
        """
        清理环境，重启QQ，进入额外活跃，检查所有任务状态并更新UI
        """
        logger.info("【刷新进度】开始刷新任务进度...")
        
        # 1. 重置环境并导航
        if not self.reset_app_state(prefix="【刷新进度】"):
             logger.error("【刷新进度】重置应用状态失败")
             return
             
        if not self.navigate_to_extra_active():
             logger.error("【刷新进度】无法进入额外活跃页面")
             return
             
        # 2. 扫描检查所有任务
        # 记录已找到并更新状态的任务，避免重复处理，默认为 pending
        pending_tasks = self.extra_active_tasks_map.copy()
        
        for name in pending_tasks:
            self.update_task_status(name, "pending")
            
        max_scrolls = 15
        last_source = None
        
        for i in range(max_scrolls):
            if not self.check_alive(): break
            
            logger.info(f"【刷新进度】扫描第 {i+1} 页...")
            
            # 检查当前页面的所有剩余任务
            current_checking_names = list(pending_tasks.keys())
            
            for name in current_checking_names:
                text = pending_tasks[name]
                
                # 检查任务文本是否存在
                if self.d(textContains=text).exists:
                    # 检查是否已完成
                    if self.is_task_completed(text):
                        self.update_task_status(name, "success")
                        logger.info(f"【刷新进度】任务【{name}】: 已完成")
                    else:
                        self.update_task_status(name, "pending")
                        logger.info(f"【刷新进度】任务【{name}】: 未完成")
                        
                    # 无论是否完成，既然找到了，就可以从待寻找列表中移除
                    del pending_tasks[name]
            
            if not pending_tasks:
                logger.info("【刷新进度】所有任务状态已确认")
                break
                
            # 滚动
            source = self.d.dump_hierarchy()
            if last_source and source == last_source:
                logger.info("【刷新进度】已到达底部")
                break
            last_source = source
            
            self.d.swipe_ext("up", scale=0.6) # 向上滑，内容向下滚
            time.sleep(1.0)
            
        # 结束后，剩余在 pending_tasks 里的就是没找到的
        for name in pending_tasks:
            logger.warning(f"【刷新进度】未找到任务【{name}】，标记为未执行")
            self.update_task_status(name, "pending")
            
        logger.info("【刷新进度】刷新完成")

    def is_task_completed(self, task_text_contains):
        """
        检查指定任务是否标记为“已完成”
        规则：在任务文本的同一行右侧（或附近）检测到“已完成”文本
        """
        if not self.check_alive(): return False
        
        # 1. 找到任务元素
        # 注意：调用此方法前通常已经 scroll_and_find 过了，所以应该是可见的
        # 但为了稳健，如果不可见可能需要重新查找（这里假设已在屏幕上）
        task_ele = self.d(textContains=task_text_contains)
        if not task_ele.exists:
            return False
            
        try:
            # 获取任务元素坐标 (取第一个匹配的)
            task_bounds = task_ele.info['bounds']
            task_cy = (task_bounds['top'] + task_bounds['bottom']) / 2
            
            # 查找页面上所有的“已完成”元素
            completed_eles = self.d(text="已完成")
            count = completed_eles.count
            
            for i in range(count):
                try:
                    ele = completed_eles[i]
                    bounds = ele.info['bounds']
                    cy = (bounds['top'] + bounds['bottom']) / 2
                    
                    # 判定规则：
                    # 1. Y轴中心差值在一定范围内 (说明在同一行)，设为 60 像素
                    # 2. “已完成”在任务文本的右侧 (left >= task_right - buffer)
                    if abs(cy - task_cy) < 60: 
                        if bounds['left'] >= task_bounds['right'] - 50: 
                            logger.info(f"======== 检测到任务【{task_text_contains}】已完成 ========")
                            self.current_task_skipped = True # 标记任务已跳过
                            return True
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"检查任务完成状态时出错: {e}")
            
        return False

    def check_alive(self):
        """
        检查设备连接是否存活，且未收到停止信号
        """
        if self.stop_event and self.stop_event.is_set():
            logger.info("收到停止信号，停止当前操作")
            return False

        if not self.d:
            return False
        try:
            # 简单调用一个轻量级命令检查连接
            return self.d.info.get('screenOn') is not None
        except:
            return False

    def wait_for_active_button(self, text, timeout=60, check_interval=1.0, prefix=""):
        """
        等待文本按钮出现，并循环检测其颜色是否为“正蓝色”(Active)
        用于解决 '去发布' 按钮虽然存在但处于禁用(暗色)状态的问题
        """
        logger.info(f"{prefix} 等待按钮 '{text}' 变为激活状态(正蓝色)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.check_alive():
                return False
                
            # 1. 查找元素
            ele = self.d(text=text)
            if ele.exists:
                try:
                    # 2. 获取坐标
                    bounds = ele.info['bounds']
                    left, top, right, bottom = bounds['left'], bounds['top'], bounds['right'], bounds['bottom']
                    
                    # 3. 截图并裁剪区域
                    # 注意：uiautomator2 的 screenshot(format='opencv') 返回 BGR
                    img = self.d.screenshot(format='opencv')
                    
                    # 简单的越界检查
                    h_img, w_img = img.shape[:2]
                    left = max(0, left)
                    top = max(0, top)
                    right = min(w_img, right)
                    bottom = min(h_img, bottom)
                    
                    if right > left and bottom > top:
                        roi = img[top:bottom, left:right]
                        
                        # 4. 计算平均颜色 (BGR)
                        mean_color = np.mean(roi, axis=(0, 1))
                        b, g, r = mean_color[0], mean_color[1], mean_color[2]
                        
                        # 5. 判断是否为“正蓝”
                        # 规则：蓝色分量明显高于红绿，且蓝色分量足够亮
                        # 暗蓝(禁用): B可能在 100-150 左右，且整体较暗
                        # 浅蓝(等待/不可点): B很高(>200)，但G也高(>180)，导致 B-G 较小 (<50)
                        # 正蓝(激活): B通常 > 160 (甚至200+)，且 B >> R, B >> G (diff > 60)
                        
                        logger.debug(f"{prefix} 按钮 '{text}' 颜色均值: B={b:.1f}, G={g:.1f}, R={r:.1f}")
                        
                        # 阈值设定：
                        # B > 150 (亮度)
                        # B - R > 60 (色相偏蓝)
                        # B - G > 60 (排除浅蓝/天蓝)
                        if b > 150 and (b - r > 60) and (b - g > 60):
                            logger.info(f"{prefix} 检测到按钮 '{text}' 已激活 (颜色 B:{b:.1f}, Diff_G:{b-g:.1f})")
                            return True
                        else:
                            pass
                except Exception as e:
                    logger.warning(f"{prefix} 颜色检测异常: {e}")
            
            time.sleep(check_interval)
            
        logger.warning(f"{prefix} 等待按钮 '{text}' 激活超时")
        return False

    def wait_and_click_image(self, template_name, timeout=10, threshold=0.8, prefix=""):
        """
        循环等待并点击图片，用于处理页面加载延迟
        """
        start_time = time.time()
        last_log_time = 0
        while time.time() - start_time < timeout:
            if not self.check_alive():
                logger.error(f"{prefix} 设备连接已断开，停止等待")
                raise DeviceDisconnectedError("设备连接已断开")
            
            # 使用 return_details=True 获取相似度，同时 suppress_warning=True 禁止内部打印
            success, similarity = self.click_image_template(template_name, threshold=threshold, prefix=prefix, suppress_warning=True, return_details=True)
            
            if success:
                return True
            
            # 每5秒打印一次警告日志
            if time.time() - last_log_time >= 5.0:
                last_log_time = time.time()
                
            time.sleep(1)
        return False

    def click_element(self, text=None, text_contains=None, desc_contains=None, text_matches=None, fallback_id=None, timeout=5, prefix=""):
        """
        智能点击函数：尝试多种定位方式，只要一种成功即返回
        """
        if not self.check_alive():
             logger.error(f"{prefix} 设备连接已断开，停止操作")
             raise DeviceDisconnectedError("设备连接已断开")

        # 临时调整隐式等待，避免每个判断都等很久
        self.d.implicitly_wait(0.5)
        found_ele = None
        method = ""
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if text and self.d(text=text).exists:
                found_ele = self.d(text=text)
                method = f"text='{text}'"
                break
            if text_contains and self.d(textContains=text_contains).exists:
                found_ele = self.d(textContains=text_contains)
                method = f"textContains='{text_contains}'"
                break
            if text_matches and self.d(textMatches=text_matches).exists:
                found_ele = self.d(textMatches=text_matches)
                method = f"textMatches='{text_matches}'"
                break
            if desc_contains and self.d(descriptionContains=desc_contains).exists:
                found_ele = self.d(descriptionContains=desc_contains)
                method = f"descContains='{desc_contains}'"
                break
            if fallback_id and self.d(resourceId=fallback_id).exists:
                found_ele = self.d(resourceId=fallback_id)
                method = f"resourceId='{fallback_id}'"
                break
            time.sleep(0.5)
            
        # 恢复默认等待
        self.d.implicitly_wait(10.0)
        
        if found_ele:
            # 找到元素后，等待一小段时间再点击，确保动画结束
            time.sleep(1.0)
            found_ele.click()
            # 点击后也稍微等待一下
            time.sleep(1.0)
            return True
        return False

    def read_image_safe(self, path, flags=cv2.IMREAD_COLOR):
        """
        安全读取图片，支持中文路径
        """
        try:
            # OpenCV imread 不支持 Windows 中文路径，需用 np.fromfile 读取
            return cv2.imdecode(np.fromfile(path, dtype=np.uint8), flags)
        except Exception as e:
            logger.error(f"读取图片失败 {path}: {e}")
            return None

    def click_image_template(self, template_name, threshold=0.7, prefix="", suppress_warning=False, return_details=False, action="click", ignore_color=False):
        """
        基于图像识别点击元素 (OpenCV)，支持多尺度匹配
        template_name: 图片文件名 (位于 assets 目录下)
        action: "click" (默认), "check" (只检测), "get_rect" (返回 (x,y,w,h))
        ignore_color: 是否忽略颜色校验 (默认为 False)
        """
        if not self.check_alive():
            logger.error("设备连接已断开，停止图像识别")
            raise DeviceDisconnectedError("设备连接已断开")

        # 确保路径正确，适配 PyInstaller
        template_path = self.get_resource_path(os.path.join("assets", template_name))
             
        if not os.path.exists(template_path):
            if not suppress_warning:
                logger.warning(f"图片模板未找到: {template_path}")
            return False
            
        try:
            # 1. 截图 (直接获取内存数据，不保存文件)
            # uiautomator2 screenshot(format='opencv') 返回的是 BGR 格式的 numpy 数组
            img_bgr = self.d.screenshot(format='opencv')
            
            if img_bgr is None:
                 logger.error("无法获取屏幕截图")
                 return False

            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            
            # 使用支持中文路径的方式读取模板
            template = self.read_image_safe(template_path, cv2.IMREAD_GRAYSCALE)
            
            if template is None:
                logger.error(f"无法读取模板图片: {template_path}")
                return False
                
            template_h, template_w = template.shape[:2]
            
            found = None
            
            # 3. 多尺度匹配 (0.6 到 1.4 倍)
            # 这里的 scale 是相对于模板原始大小的比例
            for scale in np.linspace(0.6, 1.4, 20):
                # 计算缩放后的模板尺寸
                resized_w = int(template_w * scale)
                resized_h = int(template_h * scale)
                
                # 如果缩放后的模板比屏幕还大，就跳过
                if resized_w > img_gray.shape[1] or resized_h > img_gray.shape[0]:
                    continue
                    
                resized_template = cv2.resize(template, (resized_w, resized_h))
                
                # 模板匹配
                res = cv2.matchTemplate(img_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                
                # 记录最佳匹配
                if found is None or max_val > found[0]:
                    found = (max_val, max_loc, scale, resized_w, resized_h)
            
            # 4. 判断结果
            if found:
                max_val, max_loc, best_scale, best_w, best_h = found
                top_left_x = max_loc[0]
                top_left_y = max_loc[1]
                center_x = int(top_left_x + best_w/2)
                center_y = int(top_left_y + best_h/2)
                
                # --- 颜色校验 (全局优化) ---
                # 如果匹配度达标，进一步检查颜色是否匹配
                # 防止“形状一样但颜色不一样”被误识别
                color_match = True
                color_diff = 0.0
                
                if max_val >= threshold and not ignore_color:
                    try:
                        # 读取彩色模板
                        template_color = self.read_image_safe(template_path, cv2.IMREAD_COLOR)
                        if template_color is not None:
                            # 缩放彩色模板
                            resized_template_color = cv2.resize(template_color, (best_w, best_h))
                            
                            # 获取截图中的对应区域 (ROI)
                            # 也就是最佳匹配位置的图像
                            # img_bgr 是原始彩色截图
                            roi_color = img_bgr[top_left_y:top_left_y+best_h, top_left_x:top_left_x+best_w]
                            
                            # 确保尺寸一致 (处理边界情况)
                            if roi_color.shape == resized_template_color.shape:
                                # 计算均值颜色差异 (欧氏距离)
                                mean_template = np.mean(resized_template_color, axis=(0, 1))
                                mean_roi = np.mean(roi_color, axis=(0, 1))
                                color_diff = np.linalg.norm(mean_template - mean_roi)
                                
                                # 设定颜色阈值
                                # 经验值：30-50 表示轻微色差，>60 通常是不同颜色
                                # 这里设定 65 作为阈值，严格区分颜色
                                if color_diff > 65:
                                    color_match = False
                                    logger.warning(f"{prefix} 形状匹配但颜色不符 | 模板: {template_name} | 差异: {color_diff:.2f} (>65)")
                    except Exception as e:
                        logger.warning(f"颜色校验异常: {e}")

                # 调用图像识别回调更新 UI
                if self.image_callback:
                    try:
                        # 传入 color_diff 供 UI 显示 (可选)
                        self.image_callback(template_path, img_bgr, max_val, (top_left_x, top_left_y, best_w, best_h), threshold)
                    except Exception as e:
                        logger.error(f"图像识别回调异常: {e}")

                if max_val >= threshold:
                    if not color_match:
                         # 颜色不匹配，视为识别失败
                         if not suppress_warning:
                             logger.warning(f"{prefix} 图像识别失败 (颜色不匹配) | 模板: {template_name} | 相似度: {max_val:.2f}")
                         if return_details: return False, max_val
                         return False

                    logger.info(f"{prefix} 图像识别成功 | 模板: {template_name} | 相似度: {max_val:.2f} | 颜色差: {color_diff:.1f} | 坐标: ({center_x}, {center_y})")
                    
                    if action == "click":
                        self.d.click(center_x, center_y)
                        time.sleep(2.0) # 点击后等待
                    elif action == "get_rect":
                        # 返回左上角坐标和宽高
                        return (top_left_x, top_left_y, best_w, best_h)
                    
                    if return_details: return True, max_val
                    return True
                else:
                    if not suppress_warning:
                         pass
                    if return_details: return False, max_val
            else:
                # 调用图像识别回调更新 UI (未找到情况)
                if self.image_callback:
                    try:
                         self.image_callback(template_path, img_bgr, 0.0, None, threshold)
                    except Exception as e:
                        logger.error(f"图像识别回调异常: {e}")

                if not suppress_warning:
                    pass
                if return_details: return False, 0.0

        except Exception as e:
            logger.error(f"图像识别出错: {e}")
            
        if return_details: return False, 0.0
        return False

    def dump_ui_info(self):
        """
        导出当前页面的元素信息，辅助定位
        """
        try:
            logger.info("正在获取当前页面 UI 结构...")
            xml = self.d.dump_hierarchy()
            # 简单解析一下，打印出所有可见文本
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            
            logger.info("--- 当前页面可见元素 (Text / Desc / ResourceId) ---")
            count = 0
            for node in root.iter('node'):
                text = node.get("text", "")
                desc = node.get("content-desc", "")
                rid = node.get("resource-id", "")
                
                if text or desc or rid:
                    # 过滤掉一些无用信息，只打印关键的
                    if "layout" in rid and not text and not desc:
                        continue
                        
                    msg = []
                    if text: msg.append(f"Text='{text}'")
                    if desc: msg.append(f"Desc='{desc}'")
                    if rid: msg.append(f"Id='{rid}'")
                    
                    if msg:
                        logger.info(f"Element: {', '.join(msg)}")
                        count += 1
                        
            if count == 0:
                logger.warning("当前页面似乎没有检测到任何有效文本或ID")
            else:
                logger.info("------------------------------------------------")
                
        except Exception as e:
            logger.error(f"Dump UI 失败: {e}")

    def publish_comment(self, content=",", prefix=""):
        """
        公共逻辑：在说说发布页面输入内容并点击发表
        包含查找文本框、输入内容、点击发表按钮的完整流程
        """
        logger.info(f"{prefix} 开始执行通用发表流程")
        
        # 1. 查找并点击文本框
        logger.info(f"{prefix} 等待文本框")
        found_edit = False
        
        # 重试 10 次，每次 2 秒
        for i in range(10):
            # 不打印日志的查找
            if self.d(textContains="分享新鲜事").exists:
                 self.d(textContains="分享新鲜事").click()
                 found_edit = True
                 break
            elif self.d(className="android.widget.EditText").exists:
                 self.d(className="android.widget.EditText").click()
                 found_edit = True
                 break
            
            # 如果没找到，等待 2 秒
            time.sleep(2)
        
        if found_edit:
             time.sleep(1)
             try:
                 self.d.send_keys(content)
                 logger.info(f"{prefix} 已输入内容: {content}")
                 time.sleep(1)
             except Exception as e:
                 logger.error(f"{prefix} 输入失败: {e}")
        else:
             logger.warning(f"{prefix} 未找到文本框，尝试直接点击发表")

        # 2. 点击 '发表' (右上角)
        logger.info(f"{prefix} 点击 '发表'")
        # 优先尝试图像识别
        if self.wait_and_click_image("发表.png", timeout=10, prefix=prefix):
             logger.info(f"{prefix} 已点击 '发表' (图像)")
             time.sleep(3) # 等待发布完成
             return True
        
        # 其次尝试文本点击
        if self.click_element(text="发表", timeout=5, prefix=prefix):
             logger.info(f"{prefix} 已点击 '发表' (文本)")
             time.sleep(3)
             return True
             
        # 最后尝试右上角盲点 (备用方案)
        logger.warning(f"{prefix} 未识别到发表按钮，尝试点击右上角")
        try:
            w, h = self.d.window_size()
            # 右上角大概位置
            self.d.click(w - 50, 100)
            logger.info(f"{prefix} 已盲点右上角")
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"{prefix} 点击右上角失败: {e}")
            return False

    def scroll_and_check_completed(self, task_text, max_swipes=10):
        """
        滚动查找指定任务，并检查是否标记为“已完成”
        如果在任意位置找到任务且已完成，返回 True
        """
        logger.info(f"滚动检查任务状态: {task_text}")
        self.d.implicitly_wait(0.1)
        
        last_hierarchy = None
        found_completed = False

        for i in range(max_swipes):
            if not self.check_alive():
                raise DeviceDisconnectedError("设备连接已断开")

            # 检查当前页面是否有该任务且已完成
            if self.is_task_completed(task_text):
                found_completed = True
                break
            
            # 如果没找到任务文本，或者找到了但没完成（is_task_completed 返回 False）
            # 我们需要决定是否继续滚动。
            # 只有当屏幕上完全没有该任务文本时，才需要滚动去寻找。
            # 如果屏幕上有任务文本但未显示完成，说明还没做，直接返回 False 即可（不需要再往下找了，通常任务只出现一次）
            
            if self.d(textContains=task_text).exists:
                # 任务在屏幕上，但 is_task_completed 返回 False，说明未完成
                # 双重确认：有时 OCR 或 UI 树更新滞后，稍微等一下再查一次
                logger.info(f"找到任务【{task_text}】但未显示完成")
                break
            
            # 记录页面结构
            current_hierarchy = self.d.dump_hierarchy()
            if last_hierarchy and current_hierarchy == last_hierarchy:
                break
            last_hierarchy = current_hierarchy

            # 向上滑动
            self.d.swipe_ext("up", scale=0.6)
            time.sleep(0.8)
            
        self.d.implicitly_wait(10.0)
        return found_completed

    def scroll_and_find(self, text=None, text_contains=None, max_swipes=10, prefix=""):
        """
        双向滚动查找：先向下查找，如果到底未找到，则向上回滚查找
        """
        target = text or text_contains
        logger.info(f"{prefix} 滚动查找: {target}")
        # 禁用隐式等待以提高滚动检测速度
        self.d.implicitly_wait(0.1)
        
        # 内部函数：检查是否存在
        def check_exists():
            if text and self.d(text=text).exists: return True
            if text_contains and self.d(textContains=text_contains).exists: return True
            return False

        if check_exists():
            self.d.implicitly_wait(10.0)
            return True

        # Phase 1: 向下查找 (Swipe Up)
        logger.info(f"{prefix} 尝试向下查找...")
        last_hierarchy = None
        swiped_down_count = 0
        
        for i in range(max_swipes):
            if not self.check_alive():
                self.d.implicitly_wait(10.0)
                raise DeviceDisconnectedError("设备连接已断开")

            current_hierarchy = self.d.dump_hierarchy()
            if last_hierarchy and current_hierarchy == last_hierarchy:
                logger.warning("页面未发生变化，可能已到底部")
                break
            last_hierarchy = current_hierarchy

            self.d.swipe_ext("up", scale=0.6)
            swiped_down_count += 1
            time.sleep(0.8)
            
            if check_exists():
                self.d.implicitly_wait(10.0)
                return True
            
        # Phase 2: 如果向下没找到，尝试向上回滚查找 (Swipe Down)
        # 尤其适用于列表已经滚动到底部，而目标在顶部的情况
        logger.info(f"{prefix} 向下未找到，尝试向上回滚查找...")
        last_hierarchy = None
        
        # 向上滑动的次数：至少 max_swipes，或者更多以确保能回到顶部
        up_swipes = max_swipes + 5
        
        for i in range(up_swipes):
            if not self.check_alive():
                self.d.implicitly_wait(10.0)
                raise DeviceDisconnectedError("设备连接已断开")
                
            current_hierarchy = self.d.dump_hierarchy()
            if last_hierarchy and current_hierarchy == last_hierarchy:
                logger.info("页面未发生变化，可能已到顶部")
                break
            last_hierarchy = current_hierarchy
            
            self.d.swipe_ext("down", scale=0.6)
            time.sleep(0.8)
            
            if check_exists():
                self.d.implicitly_wait(10.0)
                return True
            
        self.d.implicitly_wait(10.0)
        return False
