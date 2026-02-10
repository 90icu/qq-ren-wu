from loguru import logger
import time
import json
import os

def execute(bot):
    """
    具体任务：添加好友
    逻辑：
    1. 读取 config.json 中的 friend_qq
    2. 依次搜索QQ号
    3. 如果已存在：删除 -> 添加
    4. 如果不存在：添加
    """
    logger.info("【添加好友】开始执行任务逻辑")

    # 1. 读取配置
    try:
        config_path = "config.json"
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        friend_qq_str = config.get("friend_qq", "")
        if not friend_qq_str:
            logger.info("【添加好友】配置中无 friend_qq，跳过任务")
            return True
            
        # 解析QQ号列表
        qq_list = [x.strip() for x in friend_qq_str.split(",") if x.strip()]
        # 过滤非数字
        qq_list = [x for x in qq_list if x.isdigit()]
        
        if not qq_list:
            logger.info("【添加好友】解析后无有效QQ号，跳过任务")
            return True
            
        # 最多取前3个
        target_qqs = qq_list[:3]
        logger.info(f"【添加好友】将执行以下QQ号: {target_qqs}")
        
    except Exception as e:
        logger.error(f"【添加好友】读取配置失败: {e}")
        return False

    # 2. 循环执行
    for qq in target_qqs:
        if not bot.check_alive(): return False
        
        logger.info(f"【添加好友】开始处理QQ: {qq}")
        
        # 定义重试机制：如果删除了好友，需要重启QQ并重新搜索添加
        # 最多重试1次 (共2次执行)
        max_attempts = 2
        for attempt in range(max_attempts):
            logger.info(f"【添加好友】执行轮次: {attempt + 1}/{max_attempts}")
            should_restart_and_retry = False
            
            # 1. 识别“搜索.png”并点击
            logger.info("【添加好友】查找 '搜索.png'")
            # 尝试识别搜索图标，如果识别不到则尝试文本
            if not bot.click_image_template("搜索.png", threshold=0.8, prefix="【添加好友】"):
                logger.warning("【添加好友】未识别到 '搜索.png'，尝试使用文本查找")
                if bot.d(description="搜索").exists:
                    bot.d(description="搜索").click()
                elif bot.d(resourceId="com.tencent.mobileqq:id/et_search_keyword").exists:
                    bot.d(resourceId="com.tencent.mobileqq:id/et_search_keyword").click()
                else:
                    logger.error("【添加好友】无法找到搜索入口")
                    return False
            
            logger.info("【添加好友】等待搜索页加载...")
            time.sleep(2)
            
            # 2. 输入QQ号
            logger.info(f"【添加好友】输入QQ号: {qq}")
            
            # 尝试找到输入框 (用于 set_text)
            # 优先找 EditText，其次找 id/3en (搜索框)
            input_box = None
            if bot.d(className="android.widget.EditText").exists:
                input_box = bot.d(className="android.widget.EditText")
            elif bot.d(resourceId="com.tencent.mobileqq:id/3en").exists:
                input_box = bot.d(resourceId="com.tencent.mobileqq:id/3en")
    
            if input_box:
                logger.info(f"【添加好友】找到输入框对象: {input_box.info.get('className', 'Unknown')}")
                input_box.click() # 确保获取焦点
                time.sleep(1)
                
                # 使用 ADB input text 逐个输入数字，间隔0.5秒
                logger.info(f"【添加好友】执行 ADB input text {qq} (逐字输入)")
                for char in str(qq):
                    bot.d.shell(f"input text {char}")
                    time.sleep(0.5)
                time.sleep(1)
            else:
                logger.warning("【添加好友】未找到输入框对象 (EditText/3en)，尝试盲输")
                # 盲输兜底
                for char in str(qq):
                    bot.d.shell(f"input text {char}")
                    time.sleep(0.5)
                time.sleep(1)
            
            # 3. 等待5秒
            logger.info("【添加好友】等待搜索结果加载(5秒)...")
            time.sleep(5)
            
            # 4. 识别搜索结果并点击
            # 日志显示: Element: Text=' (583651957)', Id='com.tencent.mobileqq:id/j64'
            logger.info(f"【添加好友】查找包含QQ号 {qq} 的搜索结果")
            
            # 优先查找文本匹配的，因为 id 可能变化
            target_el = bot.d(textContains=qq)
            search_clicked = False
            
            if target_el.exists:
                logger.info(f"【添加好友】找到目标 (textContains): {target_el.get_text()}")
                target_el.click()
                search_clicked = True
            else:
                # 备用策略：尝试 resourceId 
                target_el_backup = bot.d(resourceId="com.tencent.mobileqq:id/j64", textContains=qq)
                if target_el_backup.exists:
                    logger.info(f"【添加好友】找到目标 (id/j64): {target_el_backup.get_text()}")
                    target_el_backup.click()
                    search_clicked = True
                else:
                    logger.error(f"【添加好友】无法找到包含 {qq} 的搜索结果，任务可能失败")
    
            if search_clicked:
                logger.info("【添加好友】已点击搜索结果，等待跳转...")
                time.sleep(3)
                # 打印跳转后的页面，方便下一步确认
                # bot.dump_ui_info()
                
                # 5. 优先判断是否已是好友，然后查找“添加”和“发送”按钮
                logger.info("【添加好友】判断页面状态(好友/添加/发送)")
                
                # 优先检查是否已是好友 (通过左上角昵称 id/5p9 判断)
                is_friend = False
                more_btn = None
                
                if bot.d(resourceId="com.tencent.mobileqq:id/5p9").exists:
                    logger.info("【添加好友】检测到左上角昵称(id/5p9)，判断为已是好友")
                    is_friend = True
                    more_btn = bot.d(resourceId="com.tencent.mobileqq:id/5p9")
                elif bot.d(description="聊天设置").exists:
                    logger.info("【添加好友】检测到“聊天设置”按钮，判断为已是好友")
                    is_friend = True
                    more_btn = bot.d(description="聊天设置")
                elif bot.d(description="更多功能").exists:
                    logger.info("【添加好友】检测到“更多功能”按钮，判断为已是好友")
                    is_friend = True
                    more_btn = bot.d(description="更多功能")
                    
                if is_friend:
                    logger.info("【添加好友】开始删除好友流程")
                    if more_btn:
                        more_btn.click()
                        
                        # 点击左上角昵称后，进入资料设置页，需要点击“设置”按钮 (id/p42)
                        logger.info("【添加好友】等待“设置”按钮(id/p42)出现...")
                        time.sleep(2)
                        
                        setting_btn = None
                        if bot.d(resourceId="com.tencent.mobileqq.profilecard_feature_impl:id/p42").exists:
                            setting_btn = bot.d(resourceId="com.tencent.mobileqq.profilecard_feature_impl:id/p42")
                        elif bot.d(description="设置").exists:
                            setting_btn = bot.d(description="设置")
                        
                        if setting_btn:
                            logger.info("【添加好友】点击“设置”按钮...")
                            setting_btn.click()
                        else:
                            logger.warning("【添加好友】未找到“设置”按钮(id/p42)，尝试直接查找删除选项")
                        
                        # 等待跳转，间隔1秒持续10秒，静默识别删除好友
                        logger.info("【添加好友】等待“删除好友”选项出现(10s)...")
                        
                        # 先尝试上滑页面到底部，防止按钮被遮挡
                        try:
                            logger.info("【添加好友】尝试上滑页面...")
                            # 从屏幕下部滑到上部，增加 duration 防止滑动过快无效
                            bot.d.swipe(0.5, 0.8, 0.5, 0.2, duration=0.5)
                            time.sleep(1)
                            # 再滑一次，确保到底
                            bot.d.swipe(0.5, 0.8, 0.5, 0.2, duration=0.5)
                            time.sleep(1)
                        except Exception as e:
                            logger.warning(f"【添加好友】上滑页面失败: {e}")
                        
                        del_btn_found = False
                        for _ in range(10):
                            if bot.d(text="删除好友").exists:
                                bot.d(text="删除好友").click()
                                del_btn_found = True
                                break
                            # 兼容 "删除" (不同版本可能显示不同)
                            if bot.d(text="删除").exists:
                                bot.d(text="删除").click()
                                del_btn_found = True
                                break
                            time.sleep(1)
                        
                        if del_btn_found:
                            logger.info("【添加好友】已点击“删除好友”，等待确认...")
                            time.sleep(2) # 等待2秒
                            
                            # 静默识别“确定”按钮，点击
                            confirm_clicked = False
                            for _ in range(10):
                                # 优先找“确定”，也兼容“删除好友”确认键
                                if bot.d(text="确定").exists:
                                    bot.d(text="确定").click()
                                    confirm_clicked = True
                                    break
                                # 兼容 id/dialogRightBtn
                                if bot.d(resourceId="com.tencent.mobileqq:id/dialogRightBtn").exists:
                                    bot.d(resourceId="com.tencent.mobileqq:id/dialogRightBtn").click()
                                    confirm_clicked = True
                                    break
                                # 兼容 text="删除好友"
                                if bot.d(text="删除好友", className="android.widget.TextView").exists:
                                    bot.d(text="删除好友", className="android.widget.TextView").click()
                                    confirm_clicked = True
                                    break
                                time.sleep(1)
    
                            if confirm_clicked:
                                logger.info("【添加好友】已确认删除")
                                time.sleep(3)
                                
                                # 修改逻辑：删除完成后，重启QQ并重新执行添加逻辑
                                logger.info("【添加好友】删除完成，准备重启QQ并重新执行添加逻辑...")
                                bot.reset_app_state(prefix="【添加好友】")
                                should_restart_and_retry = True
                                
                            else:
                                logger.error("【添加好友】未找到删除确认按钮")
                        else:
                            logger.error("【添加好友】设置页未找到“删除好友”选项")
                    else:
                        logger.error("【添加好友】未找到右上角更多设置按钮")
                
                else:
                    # 未发现好友特征，执行添加/发送逻辑
                    logger.info("【添加好友】未发现已是好友特征，查找“添加”或“发送”按钮")
                    
                    # 定义查找逻辑
                    add_btn = None
                    add_btn_name = ""
                    
                    # 只识别 com.tencent.mobileqq:id/6mq
                    if bot.d(resourceId="com.tencent.mobileqq:id/6mq").exists:
                        add_btn = bot.d(resourceId="com.tencent.mobileqq:id/6mq")
                        try:
                            btn_text = add_btn.get_text()
                            # 仅在点击时打印
                            add_btn_name = f"id/6mq(Text={btn_text})"
                        except Exception as e:
                            logger.warning(f"【添加好友】获取 id/6mq 文本失败: {e}")
                            add_btn_name = "id/6mq"
                        
                    send_btn = None
                    send_btn_name = ""
                    if bot.d(text="发送").exists:
                        send_btn = bot.d(text="发送")
                        send_btn_name = "text=发送"
                    elif bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText").exists:
                        send_btn = bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText")
                        send_btn_name = "id/ivTitleBtnRightText"
                    
                    # 逻辑分支
                    if add_btn:
                        logger.info(f"【添加好友】找到“{add_btn_name}”按钮，点击...")
                        add_btn.click()
                        logger.info("【添加好友】等待验证申请页面加载...")
                        time.sleep(3)
                        
                        # 点击添加后，再次查找发送按钮
                        logger.info("【添加好友】查找“发送”或“加好友”按钮")
                        # bot.dump_ui_info()
                        
                        # 定义发送逻辑
                        real_send_btn = None
                        
                        if bot.d(text="发送").exists:
                            real_send_btn = bot.d(text="发送")
                            logger.info("【添加好友】直接找到“text=发送”按钮")
                        elif bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText").exists:
                            real_send_btn = bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText")
                            logger.info("【添加好友】直接找到“id/ivTitleBtnRightText”按钮")
                        
                        # 如果没找到发送按钮，尝试再次找加好友按钮（可能是因为第一次点添加只是展开了输入框或者页面刷新了）
                        if not real_send_btn:
                            logger.info("【添加好友】未找到“发送”按钮，尝试查找“加好友”按钮作为跳板")
                            if bot.d(text="加好友").exists:
                                logger.info("【添加好友】找到“text=加好友”按钮，点击...")
                                bot.d(text="加好友").click()
                                time.sleep(2)
                                
                                # 点击加好友后，再次查找发送按钮
                                if bot.d(text="发送").exists:
                                    real_send_btn = bot.d(text="发送")
                                    logger.info("【添加好友】点击加好友后找到“text=发送”按钮")
                                elif bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText").exists:
                                    real_send_btn = bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText")
                                    logger.info("【添加好友】点击加好友后找到“id/ivTitleBtnRightText”按钮")
                        
                        # 最终点击发送
                        if real_send_btn:
                            real_send_btn.click()
                            logger.info("【添加好友】已点击发送按钮，请求已发送")
                            time.sleep(2)
                        else:
                            logger.warning("【添加好友】流程结束仍未找到“发送”按钮")
                            
                    elif send_btn:
                        logger.info(f"【添加好友】直接找到“{send_btn_name}”按钮，点击...")
                        send_btn.click()
                        logger.info("【添加好友】请求已发送")
                        time.sleep(2)
                        
                    else:
                        logger.warning("【添加好友】未找到“添加”按钮、发送按钮，也未检测到是好友")
            
            # 检查是否需要重试
            if should_restart_and_retry:
                continue # 进入下一次循环 (attempt + 1)
            else:
                break # 不需要重试，结束当前QQ的处理，进入下一个QQ
        
    logger.info("【添加好友】所有QQ处理完毕")
    return True
