import sys
import uiautomator2 as u2
import time
import cv2
import numpy as np
from loguru import logger
import os
import importlib
import e_wai_huo_yue


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

import subprocess

class BotCore:
    def __init__(self, serial, package_name="com.tencent.mobileqq", image_callback=None):
        self.serial = serial
        self.package_name = package_name
        self.d = None
        self.stop_event = None
        self.image_callback = image_callback
        self.current_task_skipped = False # 标记当前任务是否因已完成而跳过

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
            # 等待主页某个特征元素出现，例如 "消息" 标签
            # 这样比固定 sleep 更快
            if self.d(text="消息").wait(timeout=20):
                logger.info("应用主页已加载")
                return True
            else:
                logger.warning("应用启动可能超时，未检测到主页")
                return False
        else:
            logger.error("设备未连接")
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
            logger.info(f"{prefix} 正在关闭 波点音乐...")
            self.d.app_stop("cn.wenyu.bodian")
            logger.info(f"{prefix} 正在关闭 QQ音乐...")
            self.d.app_stop("com.tencent.qqmusic")
            
            time.sleep(2)
            
            # 启动 QQ
            logger.info(f"{prefix} 正在启动 QQ...")
            self.d.app_start("com.tencent.mobileqq")
            
            # 等待启动完成
            time.sleep(10)
            self.handle_popup()
            return True
        except Exception as e:
            logger.error(f"{prefix} 重置应用状态失败: {e}")
            return False

    def login_qq(self, username, password):
        logger.info("假设已登录，跳过登录步骤")
        pass

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
            # ("额外活跃", "e_wai_huo_yue"), # 移除：作为公共模块，不作为独立任务显示
            ("福利社", "fu_li_she"),
            ("发布说说", "fa_bu_shuo_shuo"),
            ("AI妙绘", "ai_miao_hui"),
            ("盲盒签", "mang_he_qian"),
            ("点赞说说", "dian_zan_shuo_shuo"),
            ("浏览空间", "liu_lan_kong_jian"),
            ("登陆农场", "deng_lu_nong_chang"),
            ("日签打卡", "ri_qian_da_ka"),
            ("天天福利", "tian_tian_fu_li"),
            ("免费小说", "mian_fei_xiao_shuo"),
            ("QQ音乐简洁", "qq_yin_yue_jian_jie_ban"),
            ("金币加速", "jin_bi_jia_su")
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

        last_task_name = None
        last_task_skipped = False

        # 定义额外活跃任务集合
        extra_active_subtasks = [
            "福利社", "发布说说", "AI妙绘", "盲盒签", "点赞说说", 
            "浏览空间", "登陆农场", "日签打卡", "天天福利", 
            "免费小说", "QQ音乐简洁", "金币加速"
        ]
        
        for module, task_name in tasks_to_run:
            if not self.check_alive(): break
            
            # 判断是否需要重置应用状态
            should_reset = True
            
            # 智能重置逻辑：只有当上一个任务是“已完成跳过”状态，且都在额外活跃系列时，才不重启
            if last_task_skipped and last_task_name in extra_active_subtasks and task_name in extra_active_subtasks:
                should_reset = False
                logger.info(f"任务【{last_task_name}】已跳过，保持当前页面状态继续执行【{task_name}】")
            
            if should_reset:
                # 每个任务执行前重置应用状态
                if not self.reset_app_state():
                    logger.error(f"【{task_name}】重置应用状态失败，跳过此任务")
                    continue
            
            # 使用 lambda 包装，以便在 run_task_with_retry 中调用
            task_func = lambda: module.execute(self)
            
            # 重置当前任务的跳过状态
            self.current_task_skipped = False
            
            self.run_task_with_retry(task_func, task_name)
            
            last_task_name = task_name
            last_task_skipped = self.current_task_skipped
            
        logger.info("所有任务流程结束")

    def run_task_with_retry(self, task_func, task_name):
        """
        执行单个任务，包含公共步骤和重试机制
        """
        # 尝试执行公共步骤
        if not self.navigate_to_extra_active():
            logger.warning(f"【{task_name}】执行失败，尝试重启 QQ")
            self.restart_qq()
            if not self.navigate_to_extra_active():
                logger.error(f"重启后公共步骤依然失败，跳过任务【{task_name}】")
                return

        logger.info(f"准备执行任务:【{task_name}】")

        # 尝试执行具体任务
        if task_func():
            # logger.info(f"【{task_name}】任务完成") # 避免重复打印，具体任务脚本中已包含
            pass
        else:
            logger.warning(f"【{task_name}】任务执行失败，尝试重启 QQ")
            self.restart_qq()
            
            # 重启后再次执行公共步骤
            if self.navigate_to_extra_active():
                logger.info("重启后公共步骤执行成功，但不重试任务，继续下一个任务")
                # 原来的重试逻辑已移除
                # if task_func():
                #     logger.info(f"【{task_name}】任务重试完成")
                # else:
                #     logger.error(f"【{task_name}】任务重试依然失败")
            else:
                logger.error(f"重启后公共步骤执行失败，无法继续")


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
                            logger.info(f"检测到任务【{task_text_contains}】已完成")
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
                            # logger.debug("颜色未达标，继续等待...")
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
                return False
            
            # 使用 return_details=True 获取相似度，同时 suppress_warning=True 禁止内部打印
            success, similarity = self.click_image_template(template_name, threshold=threshold, prefix=prefix, suppress_warning=True, return_details=True)
            
            if success:
                return True
            
            # 每5秒打印一次警告日志
            if time.time() - last_log_time >= 5.0:
                # logger.warning(f"{prefix} 图像识别未找到目标 | 模板: {template_name} | 最高相似度: {similarity:.2f} (阈值: {threshold})")
                last_log_time = time.time()
                
            time.sleep(1)
        return False

    def click_element(self, text=None, text_contains=None, desc_contains=None, text_matches=None, fallback_id=None, timeout=5, prefix=""):
        """
        智能点击函数：尝试多种定位方式，只要一种成功即返回
        """
        if not self.check_alive():
             logger.error(f"{prefix} 设备连接已断开，停止操作")
             return False

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
            # logger.info(f"点击元素 | 依据: {method}") # 移除详细日志
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

    def click_image_template(self, template_name, threshold=0.7, prefix="", suppress_warning=False, return_details=False, action="click"):
        """
        基于图像识别点击元素 (OpenCV)，支持多尺度匹配
        template_name: 图片文件名 (位于 assets 目录下)
        action: "click" (默认), "check" (只检测), "get_rect" (返回 (x,y,w,h))
        """
        if not self.check_alive():
            logger.error("设备连接已断开，停止图像识别")
            return False

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
                
                if max_val >= threshold:
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
                        logger.warning(f"图像识别未找到目标 | 模板: {template_name} | 最高相似度: {max_val:.2f} (阈值: {threshold})")
                    if return_details: return False, max_val
            else:
                # 调用图像识别回调更新 UI (未找到情况)
                if self.image_callback:
                    try:
                         self.image_callback(template_path, img_bgr, 0.0, None, threshold)
                    except Exception as e:
                        logger.error(f"图像识别回调异常: {e}")

                if not suppress_warning:
                    logger.warning(f"图像识别完全失败")
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
        if self.click_element(text_contains="分享新鲜事", timeout=5, prefix=prefix):
             found_edit = True
        elif self.d(className="android.widget.EditText").exists:
             self.d(className="android.widget.EditText").click()
             found_edit = True
        
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

    def scroll_and_find(self, text=None, text_contains=None, max_swipes=10, prefix=""):
        """
        快速滚动查找，到底自动停止
        """
        logger.info(f"{prefix} 滚动查找: {text or text_contains}")
        # 禁用隐式等待以提高滚动检测速度
        self.d.implicitly_wait(0.1)
        
        last_hierarchy = None

        for i in range(max_swipes):
            if not self.check_alive():
                logger.error("设备连接已断开，停止滚动")
                self.d.implicitly_wait(10.0)
                return False

            if text and self.d(text=text).exists:
                self.d.implicitly_wait(10.0)
                return True
            if text_contains and self.d(textContains=text_contains).exists:
                self.d.implicitly_wait(10.0)
                return True
            
            # 记录当前页面结构（简易版：只对比dump内容，虽然慢但准确）
            # 为了性能，也可以只对比屏幕上所有 TextView 的内容集合
            # 这里先尝试 dump，如果太慢再优化
            current_hierarchy = self.d.dump_hierarchy()
            
            if last_hierarchy and current_hierarchy == last_hierarchy:
                logger.warning("页面未发生变化，可能已到底部")
                break
                
            last_hierarchy = current_hierarchy

            # 快速滑动
            self.d.swipe_ext("up", scale=0.6)
            # 短暂 sleep 等待滚动动画结束
            time.sleep(0.8)
            
        self.d.implicitly_wait(10.0)
        return False
