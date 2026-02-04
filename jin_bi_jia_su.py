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
            logger.info("【金币加速】进入等待阶段，持续检测 '跳过.png' 或 '立即兑换.png' (限时20秒)...")
            
            start_wait = time.time()
            clicked_skip = False
            clicked_exchange = False
            
            while time.time() - start_wait < 20:
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
                     clicked_skip = True
                     clicked_exchange = True
                     break
                
                # 每隔 3 秒打印一次正在检测的日志
                elapsed = time.time() - start_wait
                if int(elapsed) % 3 == 0 and int(elapsed) > 0:
                     logger.info(f"【金币加速】正在后台监测 '跳过.png'/{sim_skip:.2f} 或 '立即兑换.png'/{sim_exchange:.2f} ...")
                     
                time.sleep(1)
            
            if not clicked_skip:
                logger.info("【金币加速】20秒内未检测到目标图片，等待结束")
            
            
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
