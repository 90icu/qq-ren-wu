from loguru import logger
import time

def execute(bot):
    """
    具体任务：发布说说
    """
    logger.info("【发布说说】开始执行具体任务逻辑")
    
    # 1. 查找 '发布一条空间说说' 并点击
    logger.info("【发布说说】查找 '发布一条空间说说'")
    if bot.scroll_and_find(text_contains="发布一条空间说说", prefix="【发布说说】"):
         # 检查是否已完成
         if bot.is_task_completed("发布一条空间说说"):
             logger.info("【发布说说】检测到任务已完成，跳过")
             return True

         if not bot.check_alive(): return False
         logger.info("【发布说说】找到入口，点击")
         bot.click_element(text_contains="发布一条空间说说", prefix="【发布说说】")
    else:
         if not bot.check_alive(): return False
         logger.warning("【发布说说】未找到 '发布一条空间说说' 入口")
         return False
    
    # 2. 调用通用发表流程
    logger.info("【发布说说】调用通用发表流程")
    return bot.publish_comment(content=",", prefix="【发布说说】")
