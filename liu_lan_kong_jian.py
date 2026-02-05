from loguru import logger
import time

def execute(bot):
    """
    具体任务：浏览空间
    步骤：
    1. 找到“浏览十条空间好友动态”
    2. 检测是否出现“前往领取查看.png” (任务完成标志)
       - 如果出现：直接返回 True，跳过任务
    3. 如果未出现：点击进入，往下一直快速滚动，持续20秒
    4. 等待两秒，然后返回
    """
    logger.info("【浏览空间】开始执行具体任务逻辑")

    # 1. 查找 '浏览十条空间好友动态'
    logger.info("【浏览空间】查找 '浏览十条空间好友动态'")
    if bot.scroll_and_find(text_contains="浏览十条空间好友动态", prefix="【浏览空间】"):
         # 检查是否已完成
         if bot.is_task_completed("浏览十条空间好友动态"):
             logger.info("【浏览空间】检测到任务已完成，跳过")
             return True

         if not bot.check_alive(): return False
         
         logger.info("【浏览空间】找到入口，点击进入")
         bot.click_element(text_contains="浏览十条空间好友动态", prefix="【浏览空间】")
    else:
         if not bot.check_alive(): return False
         logger.warning("【浏览空间】未找到 '浏览十条空间好友动态' 入口")
         return False

    logger.info("【浏览空间】等待5秒加载页面...")
    time.sleep(5) 
    
    # 2. 检测“前往领取查看.png” (只检测不点击)
    # logger.info("【浏览空间】检测是否已完成 (前往领取查看.png)")
    # success, _ = bot.click_image_template("前往领取查看.png", threshold=0.8, prefix="【浏览空间】", return_details=True, action="check")
    
    # if success:
    #     logger.info("【浏览空间】检测到 '前往领取查看'，任务已完成，跳过执行")
    #     return True
        
    # logger.info("【浏览空间】未检测到完成标志，开始执行任务")

    # 3. 往下一直快速滚动，持续20秒
    logger.info("【浏览空间】开始快速滚动 (持续20秒)")
    
    start_time = time.time()
    duration = 20
    
    while time.time() - start_time < duration:
        if not bot.check_alive(): return False
        
        # 快速滑动
        try:
            w, h = bot.d.window_size()
            bot.d.swipe(w // 2, h * 0.8, w // 2, h * 0.2, duration=0.1)
        except Exception as e:
            logger.warning(f"滑动失败: {e}")
            
        time.sleep(0.5) 
        
    logger.info("【浏览空间】滚动结束")
    
    # 4. 等两秒
    logger.info("【浏览空间】等待2秒")
    time.sleep(2)
    
    return True
