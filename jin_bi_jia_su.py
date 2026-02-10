import time
from loguru import logger

def execute(bot):
    """
    金币加速任务
    入口文本：使用金币兑换等级加速
    """
    logger.info("【金币加速】开始执行任务逻辑")

    # 1. 查找入口
    logger.info("【金币加速】查找 '使用金币兑换等级加速'")
    
    if bot.scroll_and_find(text="使用金币兑换等级加速", prefix="【金币加速】"):
        # 检查是否已完成
        if bot.is_task_completed("使用金币兑换等级加速"):
            logger.info("【金币加速】检测到任务已完成，跳过")
            return True

        logger.info("【金币加速】找到入口，点击进入")
        bot.click_element(text="使用金币兑换等级加速", prefix="【金币加速】")
        time.sleep(5) # 等待页面加载
        
        # 标记是否成功点击了允许
        clicked_allow = False

        # 优先识别 "允许-黑字白底.png"
        logger.info("【金币加速】尝试识别 '允许-黑字白底.png'")
        if bot.click_image_template("允许-黑字白底.png", threshold=0.8, prefix="【金币加速】"):
             logger.info("【金币加速】成功点击 '允许-黑字白底.png'")
             clicked_allow = True
        
        # 识别不到再识别 "允许-蓝字白底.png"
        if not clicked_allow:
            logger.info("【金币加速】未找到黑字版，尝试识别 '允许-蓝字白底.png'")
            if bot.click_image_template("允许-蓝字白底.png", threshold=0.8, prefix="【金币加速】"):
                 logger.info("【金币加速】成功点击 '允许-蓝字白底.png'")
                 clicked_allow = True
        
        if clicked_allow:
            logger.info("【金币加速】进入等待阶段，持续检测 '跳过.png' 或 '立即兑换.png' (限时30秒)...")
            
            start_wait = time.time()
            clicked_skip = False
            clicked_exchange = False
            clicked_ad = False
            
            while time.time() - start_wait < 30:
                # 1. 检测跳过
                is_found_skip, sim_skip = bot.click_image_template("跳过.png", threshold=0.8, prefix="【金币加速】", suppress_warning=True, return_details=True)
                if is_found_skip:
                     logger.info(f"【金币加速】检测到并点击了 '跳过.png' (相似度: {sim_skip:.2f})，提前结束等待")
                     clicked_skip = True
                     break

                # 2. 检测立即兑换
                is_found_exchange, sim_exchange = bot.click_image_template("立即兑换.png", threshold=0.8, prefix="【金币加速】", suppress_warning=True, return_details=True)
                if is_found_exchange:
                     logger.info(f"【金币加速】检测到并点击了 '立即兑换.png' (相似度: {sim_exchange:.2f})，提前结束等待")
                     time.sleep(2) # 点击立即兑换之后等待2秒再结束
                     clicked_skip = True
                     clicked_exchange = True
                     break

                # 3. 检测观看广告领金币
                is_found_ad, sim_ad = bot.click_image_template("观看广告领金币.png", threshold=0.8, prefix="【金币加速】", suppress_warning=True, return_details=True)
                if is_found_ad:
                     logger.info(f"【金币加速】检测到并点击了 '观看广告领金币.png' (相似度: {sim_ad:.2f})，提前结束等待")
                     clicked_skip = True
                     clicked_ad = True
                     break

                # 4. 检测 确认.png
                is_found_confirm, sim_confirm = bot.click_image_template("确认.png", threshold=0.8, prefix="【金币加速】", suppress_warning=True, return_details=True)
                if is_found_confirm:
                     logger.info(f"【金币加速】检测到并点击了 '确认.png' (相似度: {sim_confirm:.2f})，提前结束等待")
                     clicked_skip = True
                     break

                # 5. 检测 QQ登录-企鹅图标-2.png
                # 如果识别到，先识别点击“单选-方形.png”，再点击“QQ登录-企鹅图标-2.png”
                is_found_login, sim_login = bot.click_image_template("QQ登录-企鹅图标-2.png", threshold=0.8, prefix="【金币加速】", suppress_warning=True, return_details=True, action="check")
                
                if is_found_login:
                     logger.info(f"【金币加速】检测到 'QQ登录-企鹅图标-2.png' (相似度: {sim_login:.2f})")
                     
                     # 1. 识别并点击 单选-方形.png
                     if bot.click_image_template("单选-方形.png", threshold=0.8, prefix="【金币加速】"):
                         logger.info("【金币加速】已点击 '单选-方形.png'")
                         time.sleep(1)
                     
                     # 2. 点击 QQ登录-企鹅图标-2.png
                     if bot.click_image_template("QQ登录-企鹅图标-2.png", threshold=0.8, prefix="【金币加速】"):
                         logger.info("【金币加速】已点击 'QQ登录-企鹅图标-2.png'")
                         time.sleep(1)

                     # 3. 识别并点击 同意.png (重试 5 次，每次间隔 2 秒)
                     for _ in range(5):
                         if bot.click_image_template("同意.png", threshold=0.8, prefix="【金币加速】", suppress_warning=True):
                             logger.info("【金币加速】已点击 '同意.png'")
                             time.sleep(1)
                             break
                         time.sleep(2)
                    
                     # 继续循环，不跳出
                     continue
                
                # 每隔 3 秒打印一次正在检测的日志
                elapsed = time.time() - start_wait
                if int(elapsed) % 3 == 0 and int(elapsed) > 0:
                     logger.info(f"【金币加速】监测中: 跳过/{sim_skip:.2f} 兑换/{sim_exchange:.2f} 广告/{sim_ad:.2f} 确认/{sim_confirm:.2f} 登录/{sim_login:.2f}")
                     
                time.sleep(1)
            
            if clicked_ad:
                logger.info("【金币加速】已进入广告播放，等待 35 秒...")
                time.sleep(35)
                # 尝试点击关闭广告（如果有）
                # 通常广告结束会有关闭按钮，这里可以尝试通用的关闭逻辑，或者留给后续步骤
                # 暂时先等待，不执行额外关闭操作，除非用户要求
            
            if not clicked_skip:
                logger.info("【金币加速】30秒内未检测到目标图片，等待结束")
            
            
            logger.info("【金币加速】任务完成")
            return True
        
        else:
            logger.warning("【金币加速】未找到任何'允许'按钮")
            # 任务虽然没点到按钮，但流程走完了，是否算成功？
            # 这里保持原逻辑返回 False
            return False

    else:
        logger.error("【金币加速】未找到任务入口")
        return False
