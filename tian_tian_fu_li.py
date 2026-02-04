from loguru import logger
import time
import random

def execute(bot):
    """
    具体任务：天天福利
    步骤：
    1. 找到“去天天领福利，赚金豆兑好礼”
    2. 点击进入
    3. 上下滑动20秒
    4. 返回
    """
    logger.info("【天天福利】开始执行具体任务逻辑")

    # 1. 查找入口
    target_text = "去天天领福利，赚金豆兑好礼"
    logger.info(f"【天天福利】查找 '{target_text}'")
    
    # 使用 scroll_and_find 查找入口
    # 注意：这里的 text 可能很长，建议使用 contains 或者只匹配前半部分，
    # 但用户给出了完整文本，先尝试完整匹配或部分关键匹配。
    # 为了稳妥，使用 textContains 匹配关键部分 "去天天领福利"
    
    if bot.scroll_and_find(text_contains="去天天领福利", prefix="【天天福利】"):
         # 检查是否已完成
         if bot.is_task_completed("去天天领福利"):
             logger.info("【天天福利】检测到任务已完成，跳过")
             return True

         if not bot.check_alive(): return False
         logger.info("【天天福利】找到入口，点击进入")
         bot.click_element(text_contains="去天天领福利", prefix="【天天福利】")
    else:
         if not bot.check_alive(): return False
         logger.warning(f"【天天福利】未找到 '{target_text}' 入口")
         return False

    logger.info("【天天福利】等待页面加载...")
    time.sleep(5)

    # 2. 上下滑动20秒
    logger.info("【天天福利】开始滑动浏览 (20秒)...")
    start_time = time.time()
    duration = 20
    
    while time.time() - start_time < duration:
        if not bot.check_alive(): return False
        
        # 每次滑动前检查是否有 "立即签到.png"
        if bot.click_image_template("立即签到.png", prefix="【天天福利】"):
            logger.info("【天天福利】识别到并点击了 '立即签到.png'")
        
        # 随机上滑或下滑，模拟浏览
        # 通常是上滑(查看下方内容)多一些
        if random.random() < 0.7:
            logger.info("【天天福利】上滑查看更多...")
            bot.d.swipe(0.5, 0.8, 0.5, 0.3, duration=0.5)
        else:
            logger.info("【天天福利】下滑回顾...")
            bot.d.swipe(0.5, 0.3, 0.5, 0.8, duration=0.5)
            
        time.sleep(random.uniform(1, 3))
        
        remaining = duration - (time.time() - start_time)
        if remaining > 0:
            logger.info(f"【天天福利】剩余时间: {int(remaining)}秒")

    # 3. 任务结束
    logger.info("【天天福利】任务完成")
    
    return True
