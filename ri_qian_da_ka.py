from loguru import logger
import time

def execute(bot):
    """
    具体任务：日签打卡
    步骤：
    1. 找到“去日签打卡一次”
    2. 点击进入
    3. 识别“立即打卡”并点击
    4. 返回
    """
    logger.info("【日签打卡】开始执行具体任务逻辑")

    # 1. 查找 '去日签卡打一次卡'
    logger.info("【日签打卡】查找 '去日签卡打一次卡'")
    if bot.scroll_and_find(text_contains="去日签卡打一次卡", prefix="【日签打卡】"):
         # 检查是否已完成
         if bot.is_task_completed("去日签卡打一次卡"):
             logger.info("【日签打卡】检测到任务已完成，跳过")
             return True

         if not bot.check_alive(): return False
         logger.info("【日签打卡】找到入口，点击进入")
         bot.click_element(text_contains="去日签卡打一次卡", prefix="【日签打卡】")
    else:
         if not bot.check_alive(): return False
         logger.warning("【日签打卡】未找到 '去日签卡打一次卡' 入口")
         return False

    logger.info("【日签打卡】等待页面加载...")
    time.sleep(5)

    # 2. 识别“立即打卡”
    logger.info("【日签打卡】查找 '立即打卡' 按钮")
    # 优先尝试文本查找
    found = False
    if bot.d(textContains="立即打卡").exists:
        logger.info("【日签打卡】发现 '立即打卡' 文本，点击...")
        bot.click_element(text_contains="立即打卡", prefix="【日签打卡】")
        found = True
    elif bot.d(descriptionContains="立即打卡").exists:
        logger.info("【日签打卡】发现 '立即打卡' 描述，点击...")
        bot.click_element(desc_contains="立即打卡", prefix="【日签打卡】")
        found = True
    
    if found:
        logger.info("【日签打卡】点击成功，等待响应...")
        time.sleep(3)
    else:
        logger.warning("【日签打卡】未找到 '立即打卡' 按钮 (文本或描述)")
        # 即使没找到，也继续执行返回操作，防止卡在页面

    # 3. 任务结束
    logger.info("【日签打卡】任务完成")

    return True
