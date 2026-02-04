from loguru import logger
import time

def execute(bot):
    """
    具体任务：AI妙绘
    """
    logger.info("【AI妙绘】开始执行具体任务逻辑")
    
    # 1. 查找 '使用AI妙绘' 并点击
    logger.info("【AI妙绘】查找 '使用AI妙绘'")
    if bot.scroll_and_find(text_contains="使用AI妙绘", prefix="【AI妙绘】"):
         # 检查是否已完成
         if bot.is_task_completed("使用AI妙绘"):
             logger.info("【AI妙绘】检测到任务已完成，跳过")
             return True
             
         if not bot.check_alive(): return False
         logger.info("【AI妙绘】找到入口，点击")
         bot.click_element(text_contains="使用AI妙绘", prefix="【AI妙绘】")
    else:
         if not bot.check_alive(): return False
         logger.warning("【AI妙绘】未找到 '使用AI妙绘' 入口")
         return False
         
    time.sleep(5) # 等待网页/小程序加载

    # 2. 点击 '免费使用'
    logger.info("【AI妙绘】点击 '免费使用'")
    if bot.click_element(text_contains="免费使用", timeout=10, prefix="【AI妙绘】"):
         logger.info("【AI妙绘】已点击 '免费使用'")
    else:
         logger.warning("【AI妙绘】未找到 '免费使用'，尝试继续")

    # 2.1 检查 'AI妙绘用户协议' 弹窗
    time.sleep(1) # 稍作等待弹窗出现
    if bot.d(textContains="AI妙绘用户协议").exists:
         logger.info("【AI妙绘】检测到用户协议弹窗，尝试点击 '同意并接受'")
         try:
             # 优先尝试精确匹配 (避免匹配到正文内容)
             if bot.d(text="同意并接受").exists:
                 bot.d(text="同意并接受").click()
                 logger.info("【AI妙绘】已点击 '同意并接受' (精确匹配)")
             else:
                 # 如果精确匹配失败，尝试查找包含文本的所有元素，并点击位置最靠下的一个
                 # 因为正文通常在上方，按钮在下方
                 eles = bot.d(textContains="同意并接受")
                 if eles.exists:
                     count = eles.count
                     best_ele = None
                     max_bottom = 0
                     for i in range(count):
                         try:
                             ele = eles[i]
                             bounds = ele.info['bounds']
                             if bounds['bottom'] > max_bottom:
                                 max_bottom = bounds['bottom']
                                 best_ele = ele
                         except:
                             continue
                     
                     if best_ele:
                         best_ele.click()
                         logger.info("【AI妙绘】已点击位置最靠下的 '同意并接受'")
                     else:
                         logger.warning("【AI妙绘】未找到有效的 '同意并接受' 元素")
                 else:
                     logger.warning("【AI妙绘】未找到 '同意并接受' 文本")
         except Exception as e:
             logger.error(f"【AI妙绘】点击协议按钮异常: {e}")
         
         time.sleep(1) # 点击后稍作等待

    # 3. 选择第一张图片
    logger.info("【AI妙绘】选择第一张图片")
    time.sleep(2)
    # 盲点相册第一张图的位置 (根据用户经验值 15%, 20%)
    w, h = bot.d.window_size()
    x = int(w * 0.15)
    y = int(h * 0.20)
    logger.info(f"【AI妙绘】尝试点击相册第一张图片 (坐标: {x}, {y})")
    bot.d.click(x, y)
         
    # 4. 页面跳转后等待 '去发布'
    logger.info("【AI妙绘】等待 '去发布'")
    # 使用颜色检测替代单纯的 wait，并将检测间隔调整为 5 秒
    if bot.wait_for_active_button(text="去发布", timeout=60, check_interval=5.0, prefix="【AI妙绘】"):
         logger.info("【AI妙绘】检测到 '去发布' 且已激活")
    else:
         logger.error("【AI妙绘】等待 '去发布' 激活超时")
         return False

    # 5. 点击 '去发布'
    logger.info("【AI妙绘】点击 '去发布'")
    if bot.click_element(text="去发布", timeout=10, prefix="【AI妙绘】"):
         logger.info("【AI妙绘】已点击 '去发布'")
    else:
         logger.error("【AI妙绘】未找到 '去发布' 按钮")
         return False
    
    # 5.1 调用通用发表流程
    logger.info("【AI妙绘】调用通用发表流程")
    return bot.publish_comment(content=",", prefix="【AI妙绘】")
