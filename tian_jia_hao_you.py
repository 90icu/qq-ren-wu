from loguru import logger
import time
import json
import os

def execute(bot):
    """
    具体任务：添加好友
    逻辑：
    1. 读取 config.json 中的 friend_qq
    2. 依次搜索QQ号
    3. 如果已存在：删除 -> 添加
    4. 如果不存在：添加
    """
    logger.info("【添加好友】开始执行任务逻辑")

    # 1. 读取配置
    try:
        config_path = "config.json"
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        friend_qq_str = config.get("friend_qq", "")
        if not friend_qq_str:
            logger.info("【添加好友】配置中无 friend_qq，跳过任务")
            return True
            
        # 解析QQ号列表
        qq_list = [x.strip() for x in friend_qq_str.split(",") if x.strip()]
        # 过滤非数字
        qq_list = [x for x in qq_list if x.isdigit()]
        
        if not qq_list:
            logger.info("【添加好友】解析后无有效QQ号，跳过任务")
            return True
            
        # 最多取前3个
        target_qqs = qq_list[:3]
        logger.info(f"【添加好友】将执行以下QQ号: {target_qqs}")
        
    except Exception as e:
        logger.error(f"【添加好友】读取配置失败: {e}")
        return False

    # 2. 循环执行
    for qq in target_qqs:
        if not bot.check_alive(): return False
        
        logger.info(f"【添加好友】开始处理QQ: {qq}")
        
        # 1. 重启QQ
        bot.restart_qq()
        
        # 2. 识别“搜索.png”并点击
        logger.info("【添加好友】查找 '搜索.png'")
        # 尝试识别搜索图标，如果识别不到则尝试文本
        if not bot.click_image_template("搜索.png", threshold=0.8, prefix="【添加好友】"):
            logger.warning("【添加好友】未识别到 '搜索.png'，尝试使用文本查找")
            if bot.d(description="搜索").exists:
                bot.d(description="搜索").click()
            elif bot.d(resourceId="com.tencent.mobileqq:id/et_search_keyword").exists:
                 bot.d(resourceId="com.tencent.mobileqq:id/et_search_keyword").click()
            else:
                logger.error("【添加好友】无法找到搜索入口")
                return False
        
        time.sleep(1)
        
        # 3. 粘贴QQ号
        logger.info(f"【添加好友】输入QQ号: {qq}")
        # 尝试找到输入框
        input_box = bot.d(className="android.widget.EditText")
        if input_box.exists:
             input_box.set_text(qq)
        else:
             # 如果之前点击的是搜索图标，可能需要再次确认输入框是否获得焦点
             # 有时候点击搜索后会进入搜索页，有一个输入框
             pass
             
        # 4. 等待5秒
        logger.info("【添加好友】等待5秒...")
        time.sleep(5)
        
        # 5. 打印页面元素
        logger.info("【添加好友】打印当前页面元素结构 (Dump UI)")
        bot.dump_ui_info()
        
        # 调试模式，暂时只执行第一个
        logger.info("【添加好友】调试模式：已完成第一个QQ的处理和Dump，结束任务")
        break
        
    return True
        
    logger.info("【添加好友】所有QQ处理完毕")
    return True
