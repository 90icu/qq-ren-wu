from loguru import logger
import time

def execute(bot):
    """
    具体任务：盲盒签
    """
    logger.info("【盲盒签】开始执行具体任务逻辑")
    
    # 1. 查找 '参与盲盒签并成功发布至空间' 并点击
    logger.info("【盲盒签】查找 '参与盲盒签并成功发布至空间'")
    if bot.scroll_and_find(text_contains="参与盲盒签并成功发布至空间", prefix="【盲盒签】"):
         # 检查是否已完成
         if bot.is_task_completed("参与盲盒签并成功发布至空间"):
             logger.info("【盲盒签】检测到任务已完成，跳过")
             return True

         if not bot.check_alive(): return False
         logger.info("【盲盒签】找到入口，点击")
         bot.click_element(text_contains="参与盲盒签并成功发布至空间", prefix="【盲盒签】")
    else:
         if not bot.check_alive(): return False
         logger.warning("【盲盒签】未找到 '参与盲盒签并成功发布至空间' 入口")
         return False
    
    # 2. 等待并点击 '保存并发布'
    # 页面会加载，需要每秒检测一次
    logger.info("【盲盒签】等待并点击 '保存并发布'")
    # wait_and_click_image 内部就是循环检测 (默认每秒 sleep 1s)
    if bot.wait_and_click_image("保存并发布.png", timeout=30, prefix="【盲盒签】"):
         logger.info("【盲盒签】已点击 '保存并发布'")
    else:
         logger.error("【盲盒签】未找到 '保存并发布' 按钮")
         return False
         
    # 3. 调用通用发表流程
    logger.info("【盲盒签】调用通用发表流程")
    return bot.publish_comment(content=",", prefix="【盲盒签】")
