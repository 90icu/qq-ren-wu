from loguru import logger
import time

def execute(bot):
    """
    具体任务：登陆农场
    步骤：
    1. 找到“登陆经典农场小游戏”
    2. 点击进入
    3. 等待一分钟
    4. 返回
    """
    logger.info("【登陆农场】开始执行具体任务逻辑")

    # 1. 查找 '登录经典农场小游戏'
    logger.info("【登陆农场】查找 '登录经典农场小游戏'")
    if bot.scroll_and_find(text_contains="登录经典农场小游戏", prefix="【登陆农场】"):
         # 检查是否已完成
         if bot.is_task_completed("登录经典农场小游戏"):
             logger.info("【登陆农场】检测到任务已完成，跳过")
             return True
             
         if not bot.check_alive(): return False
         logger.info("【登陆农场】找到入口，点击进入")
         bot.click_element(text_contains="登录经典农场小游戏", prefix="【登陆农场】")
    else:
         if not bot.check_alive(): return False
         logger.warning("【登陆农场】未找到 '登录经典农场小游戏' 入口")
         return False

    # 2. 等待加载完成 (识别 'QQ农场-加载中.png')
    logger.info("【登陆农场】等待页面加载，等待 20 秒...")
    time.sleep(20)
    
    start_time = time.time()
    max_wait = 300 # 5分钟
    
    while time.time() - start_time < max_wait:
        if not bot.check_alive(): return False
        
        # 识别图片，如果存在说明还在加载
        is_loading, _ = bot.click_image_template("QQ农场-加载中.png", action="check", suppress_warning=True, return_details=True, prefix="【登陆农场】")
        
        if not is_loading:
            logger.info("【登陆农场】加载图片消失，认为加载完成")
            break
            
        elapsed = time.time() - start_time
        if int(elapsed) > 0 and int(elapsed) % 30 == 0:
            logger.info(f"【登陆农场】正在加载中... (已等待 {int(elapsed)} 秒)")
            
        time.sleep(1)
        
    if time.time() - start_time >= max_wait:
        logger.warning("【登陆农场】等待加载超时 (5分钟)")

    # 任务完成
    logger.info("【登陆农场】任务流程结束")
    
    return True
