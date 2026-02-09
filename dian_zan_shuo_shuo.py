from loguru import logger
import time

def execute(bot):
    """
    具体任务：点赞说说 (图像识别版)
    """
    logger.info("【点赞说说】开始执行具体任务逻辑")

    # 1. 查找 '点赞一条好友动态' 并点击
    logger.info("【点赞说说】查找 '点赞一条好友动态'")
    if bot.scroll_and_find(text_contains="点赞一条好友动态", prefix="【点赞说说】"):
         # 检查是否已完成
         if bot.is_task_completed("点赞一条好友动态"):
             logger.info("【点赞说说】检测到任务已完成，跳过")
             return True

         if not bot.check_alive(): return False
         logger.info("【点赞说说】找到入口，点击")
         bot.click_element(text_contains="点赞一条好友动态", prefix="【点赞说说】")
    else:
         if not bot.check_alive(): return False
         logger.warning("【点赞说说】未找到 '点赞一条好友动态' 入口")
         return False

    time.sleep(3) # 等待加载好友动态页面

    # 2. 循环点赞 (目标: 3次, 超时: 30秒)
    logger.info("【点赞说说】开始寻找并点赞 (目标: 3个)")
    
    like_count = 0
    target_count = 3
    timeout = 30
    start_time = time.time()
    
    while like_count < target_count:
        if not bot.check_alive(): return False
        
        # 检查是否超时
        if time.time() - start_time > timeout:
            logger.warning(f"【点赞说说】任务超时 (已点赞 {like_count}/{target_count})")
            break
            
        # 尝试点击 "未点赞.png"
        # 注意：click_image_template 会点击匹配度最高的一个
        # 点击后，图标通常会变成 "已点赞"，下次就不会再匹配到这个了
        if bot.click_image_template("未点赞.png", threshold=0.9, prefix="【点赞说说】"):
            like_count += 1
            logger.info(f"【点赞说说】成功点赞 ({like_count}/{target_count})")
            time.sleep(1) # 等待UI刷新
        else:
            # 当前屏幕没找到，滑动
            logger.info("【点赞说说】当前屏未找到'未点赞'图标，向下滑动")
            bot.d.swipe_ext("up", scale=0.9)
            time.sleep(1.5) # 等待加载

    logger.info(f"【点赞说说】点赞流程结束，共点赞 {like_count} 个")
    
    return True
