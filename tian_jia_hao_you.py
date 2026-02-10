from loguru import logger
import time
import json

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
            logger.info("【添加好友】配置中无friend_qq，跳过任务")
            return True
            
        # 解析QQ号列表
        friend_qq_str = friend_qq_str.replace("，", ",") # 兼容中文逗号
        qq_list = [x.strip() for x in friend_qq_str.split(",") if x.strip()]
        
        if not qq_list:
            logger.info("【添加好友】解析后无有效QQ号，跳过任务")
            return True

        target_qqs = qq_list[:3]
        logger.info(f"【添加好友】将执行以下QQ号: {target_qqs}")
        
    except Exception as e:
        logger.error(f"【添加好友】读取配置失败: {e}")
        return False

    # 2. 循环执行
    # 定义内部辅助函数：搜索并点击QQ
    def step_search_qq(target_qq):
        logger.info("【添加好友】查找 '搜索.png'")
        if not bot.click_image_template("搜索.png", threshold=0.8, prefix="【添加好友】"):
            logger.warning("【添加好友】未识别到 '搜索.png'，尝试使用文本查找")
            if bot.d(description="搜索").exists:
                bot.d(description="搜索").click()
            elif bot.d(resourceId="com.tencent.mobileqq:id/et_search_keyword").exists:
                bot.d(resourceId="com.tencent.mobileqq:id/et_search_keyword").click()
            else:
                raise Exception("无法找到搜索入口")
        
        logger.info("【添加好友】等待搜索页加载...")
        time.sleep(2)
        
        # 输入QQ号
        logger.info(f"【添加好友】输入QQ号: {target_qq}")
        input_box = None
        if bot.d(className="android.widget.EditText").exists:
            input_box = bot.d(className="android.widget.EditText")
        elif bot.d(resourceId="com.tencent.mobileqq:id/3en").exists:
            input_box = bot.d(resourceId="com.tencent.mobileqq:id/3en")

        if input_box:
            input_box.click()
            time.sleep(1)
            logger.info(f"【添加好友】执行 ADB input text {target_qq}")
            for char in str(target_qq):
                bot.d.shell(f"input text {char}")
                time.sleep(0.2)
            time.sleep(1)
        else:
            logger.warning("【添加好友】未找到输入框，尝试盲输")
            for char in str(target_qq):
                bot.d.shell(f"input text {char}")
                time.sleep(0.2)
            time.sleep(1)
        
        logger.info("【添加好友】等待搜索结果加载(5秒)...")
        time.sleep(5)
        
        # 点击搜索结果
        logger.info(f"【添加好友】查找包含QQ号 {target_qq} 的搜索结果")
        target_el = bot.d(textContains=target_qq)
        if target_el.exists:
            target_el.click()
        else:
            target_el_backup = bot.d(resourceId="com.tencent.mobileqq:id/j64", textContains=target_qq)
            if target_el_backup.exists:
                target_el_backup.click()
            else:
                raise Exception(f"无法找到包含 {target_qq} 的搜索结果")
        
        logger.info("【添加好友】已点击搜索结果，等待跳转...")
        time.sleep(3)

    # 定义内部辅助函数：执行添加操作
    def step_perform_add():
        logger.info("【添加好友】执行添加/发送逻辑")
        add_btn = None
        if bot.d(resourceId="com.tencent.mobileqq:id/6mq").exists:
            add_btn = bot.d(resourceId="com.tencent.mobileqq:id/6mq")
        
        send_btn = None
        if bot.d(text="发送").exists:
            send_btn = bot.d(text="发送")
        elif bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText").exists:
            send_btn = bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText")
        
        if add_btn:
            logger.info("【添加好友】点击“添加”按钮...")
            add_btn.click()
            time.sleep(3)
            # 点击添加后，查找发送
            real_send_btn = None
            if bot.d(text="发送").exists:
                real_send_btn = bot.d(text="发送")
            elif bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText").exists:
                real_send_btn = bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText")
            
            if not real_send_btn:
                # 尝试加好友作为跳板
                if bot.d(text="加好友").exists:
                    bot.d(text="加好友").click()
                    time.sleep(2)
                    if bot.d(text="发送").exists:
                        real_send_btn = bot.d(text="发送")
                    elif bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText").exists:
                        real_send_btn = bot.d(resourceId="com.tencent.mobileqq:id/ivTitleBtnRightText")
            
            if real_send_btn:
                real_send_btn.click()
                logger.info("【添加好友】已点击发送按钮")
                time.sleep(2)
            else:
                raise Exception("点击添加后未找到发送按钮")
                
        elif send_btn:
            logger.info("【添加好友】直接找到“发送”按钮，点击...")
            send_btn.click()
            time.sleep(2)
        else:
            raise Exception("未找到“添加”或“发送”按钮")

    # 定义内部辅助函数：删除好友
    def step_delete_friend():
        logger.info("【添加好友】执行删除好友流程")
        more_btn = None
        if bot.d(resourceId="com.tencent.mobileqq:id/5p9").exists:
            more_btn = bot.d(resourceId="com.tencent.mobileqq:id/5p9")
        elif bot.d(description="聊天设置").exists:
            more_btn = bot.d(description="聊天设置")
        elif bot.d(description="更多功能").exists:
            more_btn = bot.d(description="更多功能")
            
        if more_btn:
            more_btn.click()
            time.sleep(2)
        else:
            raise Exception("未找到右上角更多/设置按钮")
            
        # 查找设置按钮
        setting_btn = None
        if bot.d(resourceId="com.tencent.mobileqq.profilecard_feature_impl:id/p42").exists:
            setting_btn = bot.d(resourceId="com.tencent.mobileqq.profilecard_feature_impl:id/p42")
        elif bot.d(description="设置").exists:
            setting_btn = bot.d(description="设置")
        
        if setting_btn:
            setting_btn.click()
        
        logger.info("【添加好友】等待“删除好友”选项...")
        time.sleep(2)
        
        # 上滑
        try:
            bot.d.swipe(0.5, 0.8, 0.5, 0.2, duration=0.5)
            time.sleep(1)
            bot.d.swipe(0.5, 0.8, 0.5, 0.2, duration=0.5)
            time.sleep(1)
        except:
            pass
            
        # 点击删除
        del_btn_found = False
        if bot.d(text="删除好友").exists:
            bot.d(text="删除好友").click()
            del_btn_found = True
        elif bot.d(text="删除").exists:
            bot.d(text="删除").click()
            del_btn_found = True
            
        if not del_btn_found:
            raise Exception("未找到“删除好友”选项")
            
        time.sleep(2)
        # 确认删除
        confirm_clicked = False
        if bot.d(text="确定").exists:
            bot.d(text="确定").click()
            confirm_clicked = True
        elif bot.d(resourceId="com.tencent.mobileqq:id/dialogRightBtn").exists:
            bot.d(resourceId="com.tencent.mobileqq:id/dialogRightBtn").click()
            confirm_clicked = True
        elif bot.d(text="删除好友", className="android.widget.TextView").exists:
            bot.d(text="删除好友", className="android.widget.TextView").click()
            confirm_clicked = True
            
        if confirm_clicked:
            logger.info("【添加好友】已确认删除")
            time.sleep(3)
        else:
            raise Exception("未找到删除确认按钮")

    # 主循环
    for i, qq in enumerate(target_qqs):
        if not bot.check_alive(): return False
        
        # 错误隔离
        try:
            # 1. 更新状态：执行中
            if hasattr(bot, "gui_callback") and bot.gui_callback:
                bot.gui_callback(qq, "执行中...", "processing")
            
            logger.info(f"【添加好友】============== 开始处理QQ: {qq} ==============")
            
            # 2. 重启QQ (确保环境纯净，且在主页方便搜索)
            bot.reset_app_state(prefix=f"【添加好友-QQ{qq}】")
            
            # 3. 搜索QQ
            step_search_qq(qq)
            
            # 4. 判断是否好友
            is_friend = False
            if bot.d(resourceId="com.tencent.mobileqq:id/5p9").exists or \
               bot.d(description="聊天设置").exists or \
               bot.d(description="更多功能").exists:
                is_friend = True
            
            if is_friend:
                logger.info(f"【添加好友】QQ {qq} 已经是好友")
                # 5. 如果是好友：删除 -> 重启 -> 搜索 -> 添加
                step_delete_friend()
                
                logger.info("【添加好友】删除完成，重启QQ...")
                bot.reset_app_state(prefix=f"【添加好友-QQ{qq}-重加】")
                
                step_search_qq(qq)
                step_perform_add()
                
            else:
                logger.info(f"【添加好友】QQ {qq} 不是好友，直接添加")
                # 6. 如果不是好友：直接添加
                step_perform_add()
            
            # 7. 更新状态：成功
            logger.info(f"【添加好友】QQ {qq} 处理成功")
            if hasattr(bot, "gui_callback") and bot.gui_callback:
                bot.gui_callback(qq, "执行成功", "success")
                
        except Exception as e:
            logger.error(f"【添加好友】QQ {qq} 处理失败: {e}")
            # 8. 失败处理：更新状态，继续下一个
            if hasattr(bot, "gui_callback") and bot.gui_callback:
                bot.gui_callback(qq, "执行失败", "failed")
            continue
            
    logger.info("【添加好友】所有QQ处理完毕")
    return True
