from loguru import logger
import time

def execute(bot):
    """
    具体任务：额外活跃 (仅作为独立任务入口，实际逻辑在前置步骤中已完成)
    此函数保留作为兼容性接口，虽然不再作为独立任务被调度
    """
    logger.info("【额外活跃】已到达目标页面，任务完成")
    return True

def navigate(bot):
    """
    公共步骤：点击头像 -> 等级 -> 更多任务 -> 额外活跃
    返回 True 表示成功进入，False 表示失败
    此逻辑原在 bot_core.py 中，现移至此处统一管理
    """
    prefix = "【额外活跃】"
    # logger.info(f"开始执行公共步骤:{prefix}")

    # 0. 检查是否已在目标页面
    # 通过检测是否存在该页面特有的任务入口文本来判断
    # 注意：由于页面可能发生滚动，需要检查多个位置的标志性文本
    indicators = [
        "额外活跃", # 页面标题或tab
        "发布一条空间说说", 
        "使用AI妙绘", 
        "福利社", 
        "盲盒签", 
        "点赞一条好友动态", 
        "浏览十条空间好友动态", 
        "登录经典农场小游戏", 
        "去日签卡打一次卡", 
        "去天天领福利", 
        "免费小说", 
        "去QQ音乐简洁版听歌", 
        "使用金币兑换等级加速"
    ]
    
    is_already_on_page = False
    for indicator in indicators:
        if bot.d(textContains=indicator).exists:
            # logger.info(f"{prefix} 检测到页面包含 '{indicator}'，判断已在额外活跃页面")
            is_already_on_page = True
            break
            
    if is_already_on_page:
        # logger.info(f"{prefix}检测到已在额外活跃页面，跳过导航")
        return True
    
    # 1. 点击左上角头像 (带重试机制)
    logger.info(f"{prefix} 点击左上角头像")
    
    # 强制等待主页加载完成
    try:
        bot.d(resourceId="com.tencent.mobileqq:id/conversation_head").wait(timeout=10)
    except Exception:
        if not bot.check_alive(): return False

    sidebar_opened = False
    # 尝试最多3次点击头像以打开侧边栏
    for attempt in range(3):
        # 执行点击
        if bot.d(resourceId="com.tencent.mobileqq:id/conversation_head").exists:
            bot.d(resourceId="com.tencent.mobileqq:id/conversation_head").click()
        elif bot.d(descriptionContains="帐户及设置").exists:
            bot.d(descriptionContains="帐户及设置").click()
        else:
            # 盲点
            bot.d.click(50, 100)
        
        # 等待侧边栏动画
        time.sleep(2.0)
        
        # 检查侧边栏是否已打开 (检测等级图标)
        # 快速检测，不需要等待太久
        if bot.d(textContains="LV").exists or bot.d(descriptionContains="等级").exists or bot.d(resourceId="com.tencent.mobileqq:id/my_level").exists:
            sidebar_opened = True
            logger.info(f"{prefix} 侧边栏已打开")
            break
        
        logger.warning(f"{prefix} 侧边栏似乎未打开 (第 {attempt+1} 次尝试)，尝试重新点击头像")
        
    if not sidebar_opened:
            if not bot.check_alive(): return False
            logger.error(f"{prefix} 多次尝试后无法打开侧边栏")
            # 尝试截图保存现场 (可选)
            return False
    
    # 2. 点击等级图标
    logger.info(f"{prefix} 点击等级图标")
    if not bot.click_element(text_contains="LV", fallback_id="com.tencent.mobileqq:id/my_level", desc_contains="等级", prefix=prefix):
            if not bot.check_alive(): return False
            logger.error(f"{prefix} 无法找到侧边栏等级图标")
            return False

    # 3. 再次点击等级图标 (进入我的等级页)
    logger.info(f"{prefix} 再次点击等级图标")
    if bot.d(text="更多任务").wait(timeout=5):
        logger.info(f"{prefix} 已直接检测到'更多任务'，跳过二次点击检测")
    else:
        if not bot.check_alive(): return False
        bot.click_element(text_contains="LV", desc_contains="等级", prefix=prefix)


    if not bot.check_alive(): return False

    # 4. 点击'更多任务' (含重试机制)
    logger.info(f"{prefix} 点击'更多任务'")
    
    max_retries = 5
    for i in range(max_retries):
        if not bot.check_alive(): return False
        
        # 尝试点击
        if bot.click_image_template("更多任务.png", threshold=0.7, prefix=prefix):
            pass # 点击成功，继续检测
        else:
            logger.warning(f"{prefix} 未找到 '更多任务' 按钮 (尝试 {i+1}/{max_retries})")
            # 即使没找到图片，也可能是已经点过了或者图片识别失败，尝试后续检测
        
        # 智能等待页面加载 (替代死等)
        check_timeout = 15
        check_start = time.time()
        detected = False
        while time.time() - check_start < check_timeout:
            if bot.d(textContains="额外活跃").exists:
                detected = True
                break
            time.sleep(1)
        
        if detected:
            logger.info(f"{prefix} 页面加载完成 (耗时 {time.time() - check_start:.1f}s)")
            break # 成功找到目标，跳出重试循环
        else:
            logger.warning(f"{prefix} 页面加载超时，未检测到 '额外活跃' (尝试 {i+1}/{max_retries})")
            
            if i < max_retries - 1:
                logger.info(f"{prefix} 尝试后退并重试...")
                bot.d.press("back")
                time.sleep(2)
                # 后退后可能回到了等级页，需要确保在等级页，这里假设后退一次能回到等级页
                # 再次点击等级页的逻辑可能不需要，因为'更多任务'就在等级页
            else:
                logger.error(f"{prefix} 重试 {max_retries} 次后仍未找到 '额外活跃'，流程失败")
                # 此时不立即返回 False，尝试最后一次直接点击（原有逻辑的兜底），或者直接失败
                # 根据用户要求 "点击一个后退，然后重试"，这里最后一次失败后，可能真的失败了
    
    if not detected:
        # 如果重试完还没检测到，尝试最后一次死马当活马医，或者直接返回
        # 考虑到上面的逻辑已经很充分，这里如果没有 detected，大概率是进不去了
        # 但为了兼容原有逻辑的后续步骤（虽然大概率会失败），我们保留原有结构，
        # 或者直接在这里 return False
        pass 
        # 这里不直接 return False，让它走到第5步，如果第5步也找不到那就真的结束了
        # 但通常第5步也是依赖 detected 的结果的（页面没加载出来，点击多半失败）
    
    if not bot.check_alive(): return False

    # 5. 点击 '额外活跃'
    logger.info(f"{prefix} 点击 '额外活跃'")
    if bot.click_element(text_contains="额外活跃", timeout=10, prefix=prefix):
        logger.info(f"{prefix} 成功点击 '额外活跃'")
        return True
    else:
        if not bot.check_alive(): return False
        logger.error(f"{prefix} 未找到 '额外活跃' 入口")
        return False
