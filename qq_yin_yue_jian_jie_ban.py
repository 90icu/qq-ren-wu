import time
from loguru import logger
import e_wai_huo_yue

def execute(bot):
    """
    QQ音乐简洁任务
    入口文本：去QQ音乐简洁版听歌
    """
    logger.info("【QQ音乐简洁】开始执行任务逻辑")

    # 1. 查找入口
    logger.info("【QQ音乐简洁】查找 '去QQ音乐简洁版听歌'")
    
    if bot.scroll_and_find(text="去QQ音乐简洁版听歌", prefix="【QQ音乐简洁】"):
        # 检查是否已完成
        if bot.is_task_completed("去QQ音乐简洁版听歌"):
            logger.info("【QQ音乐简洁】检测到任务已完成，跳过")
            return True

        logger.info("【QQ音乐简洁】找到入口，点击进入")
        bot.click_element(text="去QQ音乐简洁版听歌", prefix="【QQ音乐简洁】")
        time.sleep(5) # 等待页面加载

        
        logger.info("【QQ音乐简洁】查找 '去简洁版听歌领奖励.png'")
        if bot.click_image_template("去简洁版听歌领奖励.png", threshold=0.8, prefix="【QQ音乐简洁】"):
             logger.info("【QQ音乐简洁】成功点击 '去简洁版听歌领奖励.png'")
        else:
             logger.warning("【QQ音乐简洁】未找到 '去简洁版听歌领奖励.png'")

        time.sleep(5)
        # 检查是否有 "打开.png"
        if bot.click_image_template("打开.png", threshold=0.8, prefix="【QQ音乐简洁】"):
             logger.info("【QQ音乐简洁】成功点击 '打开.png'")
        else:
             logger.info("【QQ音乐简洁】未找到 '打开.png'")

        # 定义需要循环识别的图片列表（按顺序）
        # 每次循环只要识别到其中一个，就点击并重新开始新一轮循环
        # 如果一轮循环下来所有图片都没识别到，就结束循环
        loop_images = [
            ("允许-黑字白底.png", 0.8),
            ("同意！开始听歌.png", 0.6),
            ("进入全功能模式.png", 0.6),
            ("QQ登录.png", 0.8),
            ("单选-白圈黑底.png", 0.8),
            ("QQ登录-黑字蓝底.png", 0.8),
            ("同意.png", 0.8),
            ("打开QQ查看.png", 0.8)  # 特殊处理：点击后直接重启执行额外活跃
        ]
        
        max_loops = 20 # 防止死循环，最大尝试次数
        consecutive_failures = 0 # 连续失败次数
        
        for loop_idx in range(max_loops):
            logger.info(f"【QQ音乐简洁】开始第 {loop_idx + 1} 轮循环识别...")
            found_any = False
            
            for img_name, threshold in loop_images:
                time.sleep(1) # 稍微等待一下
                logger.info(f"【QQ音乐简洁】查找 '{img_name}'")
                
                if bot.click_image_template(img_name, threshold=threshold, prefix="【QQ音乐简洁】"):
                    logger.info(f"【QQ音乐简洁】成功点击 '{img_name}'")
                    found_any = True
                    
                    # 特殊逻辑：如果是 "打开QQ查看.png"，点击后直接结束任务流程
                    if img_name == "打开QQ查看.png":
                        logger.info("【QQ音乐简洁】识别到 '打开QQ查看.png'，等待 10 秒...")
                        time.sleep(10)
                        
                        # 尝试识别 "打开.png"
                        if bot.click_image_template("打开.png", threshold=0.8, prefix="【QQ音乐简洁】"):
                             logger.info("【QQ音乐简洁】成功点击 '打开.png'")
                        else:
                             logger.info("【QQ音乐简洁】未找到 '打开.png'")
                        
                        logger.info("【QQ音乐简洁】特殊流程结束，退出循环")
                        break 
                    
                    # 识别到一个后，跳出当前图片列表循环，重新开始下一轮（从头开始识别）
                    break
            
            # 如果是 "打开QQ查看.png" 触发的 break，外层也要 break
            if found_any:
                 consecutive_failures = 0 # 重置连续失败次数
                 # 检查是否是特殊图片，如果是则直接退出大循环
                 if img_name == "打开QQ查看.png":
                     break
                 
                 time.sleep(10) # 点击后等待页面响应，再进行下一轮
                 continue
            else:
                consecutive_failures += 1
                logger.info(f"【QQ音乐简洁】本轮未识别到任何目标图片 (连续失败 {consecutive_failures}/5)")
                if consecutive_failures >= 5:
                    logger.info("【QQ音乐简洁】连续 5 轮未识别到目标，结束循环")
                    break
                else:
                    time.sleep(10) # 稍微等待后继续下一轮
                    continue

        logger.info("【QQ音乐简洁】任务循环结束")
        
        return True
    else:
        logger.error("【QQ音乐简洁】未找到任务入口")
        return False
