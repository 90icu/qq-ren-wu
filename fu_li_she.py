from loguru import logger
import time

def execute(bot):
    """
    具体任务：福利社
    """
    logger.info("【福利社】开始执行具体任务逻辑")
    
    # 1. 查找 '福利社' 并点击
    logger.info("【福利社】查找 '福利社'")
    if bot.scroll_and_find(text_contains="福利社", prefix="【福利社】"):
         # 检查是否已完成
         if bot.is_task_completed("福利社"):
             logger.info("【福利社】检测到任务已完成，跳过")
             return True

         if not bot.check_alive(): return False
         logger.info("【福利社】找到福利社区域，尝试点击入口")
         bot.click_element(text_contains="去QQ会员福利社", prefix="【福利社】")
    else:
         if not bot.check_alive(): return False
         logger.warning("【福利社】未找到 '福利社' 区域")
         return False
    
    time.sleep(2)
    if not bot.check_alive(): return False
    
    # 2. 在福利社页面点击 '立即领取'
    logger.info("【福利社】等待 '立即领取'")
    # 优先尝试图像识别
    if bot.click_image_template("福利社-立即领取.png", threshold=0.8, prefix="【福利社】"):
         logger.info("【福利社】成功点击 '立即领取' (图像识别)")
    elif bot.click_element(text_contains="立即领取", timeout=5, prefix="【福利社】"):
         logger.info("【福利社】成功点击 '立即领取' (文本识别)")
    else:
         if not bot.check_alive(): return False
         logger.warning("【福利社】超时未找到 '立即领取'")
         return False

    if not bot.check_alive(): return False
    
    # 3. 点击 '获取手机号'
    logger.info("【福利社】等待并点击 '获取手机号'")
    if not bot.wait_and_click_image("获取手机号.png", timeout=10, prefix="【福利社】"):
         if not bot.check_alive(): return False
         logger.warning("【福利社】未找到 '获取手机号'")
         return False
         
    # 4. 点击 '允许'
    logger.info("【福利社】等待并点击 '允许'")
    if not bot.wait_and_click_image("允许.png", timeout=10, prefix="【福利社】"):
         if not bot.check_alive(): return False
         logger.warning("【福利社】未找到 '允许'")
         return False
         
    # 5. 点击 '单选'
    logger.info("【福利社】等待并点击 '单选'")
    if not bot.wait_and_click_image("单选.png", timeout=10, prefix="【福利社】"):
         if not bot.check_alive(): return False
         logger.warning("【福利社】未找到 '单选'")
         return False
         
    # 6. 点击 '确认领取'
    logger.info("【福利社】等待并点击 '确认领取'")
    if not bot.wait_and_click_image("确认领取.png", timeout=10, prefix="【福利社】"):
         if not bot.check_alive(): return False
         logger.warning("【福利社】未找到 '确认领取'")
         return False
         
    # 7. 任务结束
    logger.info("【福利社】任务完成")
    
    return True
