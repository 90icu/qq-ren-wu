from loguru import logger
import time

def execute(bot):
    """
    具体任务：免费小说
    步骤：
    1. 找到“去免费小说看任一本书”
    2. 点击进入
    3. 找到“猜你喜欢”标题下面的列表，点击列表第一个进去
    4. 返回返回两次
    """
    logger.info("【免费小说】开始执行具体任务逻辑")

    # 1. 查找入口
    target_text = "去免费小说看任一本书"
    logger.info(f"【免费小说】查找 '{target_text}'")
    
    if bot.scroll_and_find(text_contains=target_text, prefix="【免费小说】"):
         # 检查是否已完成
         if bot.is_task_completed(target_text):
             logger.info("【免费小说】检测到任务已完成，跳过")
             return True

         if not bot.check_alive(): return False
         logger.info("【免费小说】找到入口，点击进入")
         bot.click_element(text_contains=target_text, prefix="【免费小说】")
    else:
         # 尝试模糊匹配
         if bot.scroll_and_find(text_contains="免费小说", prefix="【免费小说】"):
             # 检查是否已完成
             if bot.is_task_completed("免费小说"):
                 logger.info("【免费小说】检测到任务已完成(模糊匹配)，跳过")
                 return True

             if not bot.check_alive(): return False
             logger.info("【免费小说】找到入口(模糊匹配)，点击进入")
             bot.click_element(text_contains="免费小说", prefix="【免费小说】")
         else:
             if not bot.check_alive(): return False
             logger.warning(f"【免费小说】未找到 '{target_text}' 入口")
             return False

    logger.info("【免费小说】等待页面加载...")
    time.sleep(5)

    # 2. 找到“猜你喜欢”并点击下方列表第一个
    logger.info("【免费小说】查找 '猜你喜欢'...")
    
    # 使用图像识别定位
    # 获取“猜你喜欢.png”的位置 (左上角 x, y, 宽, 高)
    rect = bot.click_image_template("猜你喜欢.png", action="get_rect", threshold=0.7, prefix="【免费小说】")
    
    if rect:
        x, y, w, h = rect
        logger.info(f"【免费小说】图像识别成功，位置: ({x}, {y}), 宽: {w}, 高: {h}")
        
        # 策略：以图片左上角为基准
        # 点击中间靠下一点的位置
        # 为了防止点击到边缘触发侧滑或点击位置不对，X轴取屏幕中间
        # Y轴偏移量减小，防止点太远
        
        screen_w, screen_h = bot.d.window_size()
        click_x = screen_w * 0.5
        click_y = int(y + h + 80) # 偏移量改为 80 像素
        
        logger.info(f"【免费小说】点击计算坐标 ({click_x}, {click_y})")
        bot.d.click(click_x, click_y)
        time.sleep(5) # 等待进入书籍
        
    else:
        logger.warning("【免费小说】未找到 '猜你喜欢.png' 图像 (请确保图片存在于 assets 目录)")
        logger.info("【免费小说】启用备用方案：坐标盲点")
        
        try:
            # 获取屏幕大小
            w, h = bot.d.window_size()
            
            # 策略：点击屏幕中下部 (约 60% 高度位置)，通常这里是列表第一项
            click_x = w * 0.5
            click_y = h * 0.6
            
            logger.info(f"【免费小说】点击屏幕坐标 ({click_x}, {click_y})")
            bot.d.click(click_x, click_y)
            time.sleep(5) # 等待进入书籍
            
        except Exception as e:
            logger.error(f"【免费小说】盲点失败: {e}")

    # 3. 返回两次

    # 3. 任务结束
    logger.info("【免费小说】任务完成")

    return True
