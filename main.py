# ------------------ 所有 import 语句都集中在顶部 ------------------
import discord
import os
import random
import time
import datetime
import asyncio
import re
from flask import Flask
from threading import Thread

# --- 网站设置 (用于 UptimeRobot 保持在线) ---
app = Flask('')
@app.route('/')
def home():
    return "I'm alive"
def run_flask():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- 时间解析函数及限制 ---
MIN_MUTE_SECONDS = 10
MAX_MUTE_SECONDS = 3600 # 1小时

def parse_duration(time_str):
    """解析用户输入的时间字符串 (如 '10m', '1h', '30秒')，返回总秒数"""
    match = re.match(r"(\d+)\s*(s|秒|m|分|分钟|h|时|小时)", time_str, re.I)
    if not match:
        return None

    value, unit = int(match.group(1)), match.group(2).lower()
    
    if unit in ("s", "秒"):
        seconds = value
    elif unit in ("m", "分", "分钟"):
        seconds = value * 60
    elif unit in ("h", "时", "小时"):
        seconds = value * 3600
    else:
        return None
    
    if MIN_MUTE_SECONDS <= seconds <= MAX_MUTE_SECONDS:
        return seconds
    else:
        return None

def format_seconds(seconds):
    """将秒数格式化为易读的字符串 (如 '5分钟', '1小时')"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{int(seconds / 60)}分钟"
    else:
        return f"{int(seconds / 3600)}小时"

# --- 游戏功能的状态变量 ---
duel_initiator = None
duel_channel = None
duel_timestamp = 0
duel_custom_duration = None
DUEL_TIMEOUT_SECONDS = 120

roulette_active = False
roulette_channel = None
roulette_timestamp = 0
roulette_custom_duration = None
roulette_chamber_count = 6
roulette_bullet_position = 0
roulette_current_pulls = 0
roulette_participants = []
ROULETTE_TIMEOUT_SECONDS = 300
ROULETTE_MUTE_SECONDS = 480

# --- 西部枪战决斗结果随机池 (新增 "loser_reaction" 字段) ---
duel_outcomes = [
    {"winner_text": "是镇上最快的枪手！在{loser}的手指碰到枪托之前，子弹已经呼啸而出！", "loser_text": "甚至没来得及拔枪，就缓缓倒在了尘土中。", "loser_reaction": "一切都发生得太快了，{loser}的脸上还保持着错愕的表情。", "mute_seconds": 180, "weight": 30},
    {"winner_text": "在枪响的瞬间侧身翻滚，精准的子弹命中了{loser}持枪的手臂！", "loser_text": "的手枪被打飞，只能痛苦地捂住伤口。", "loser_reaction": "剧痛让{loser}单膝跪地，他知道这场对决已经结束了。", "mute_seconds": 120, "weight": 20},
    {"winner_text": "的子弹击中了{loser}脚边的威士忌酒瓶，飞溅的玻璃碎片让其阵脚大乱！", "loser_text": "被吓了一跳，狼狈地放弃了抵抗。", "loser_reaction": "{loser}心有余悸地看着脚边的碎片，庆幸子弹没有打中自己。", "mute_seconds": 60, "weight": 15},
    {"winner_text": "在最关键的时刻，{loser}的左轮手枪居然卡壳了！真是天意！", "loser_text": "绝望地看着卡壳的枪，迎接了命运的审判。", "loser_reaction": "“不...不应该是这样的！” {loser}愤怒地将卡壳的枪扔在地上。", "mute_seconds": 240, "weight": 10},
    {"is_draw": True, "draw_text": "黄沙漫天，两人同时拔枪！两声枪响合为一声，子弹在空中碰撞，擦出耀眼的火花！这场对决，不分胜负！", "mute_seconds": 10, "weight": 5},
    {"reversal": True, "winner_text": "的手速快如鬼魅，但就在子弹即将命中眉心的千钧一发之际，{loser}的眼神变了！他竟然用两根手指稳稳地夹住了那颗致命的子弹！", "loser_text": "露出了难以置信的表情，在这位深藏不露的高手面前，他已经输了。", "reversal_text": "“你的速度很快，” {loser}缓缓开口，指尖的子弹冒着青烟，“但还不够快。” 说罢，屈指一弹，子弹以更快的速度飞了回去！", "loser_reaction": "面对这超乎常理的一幕，**{original_winner}** 愣在了原地，冷汗浸湿了他的衣背，他知道，这次他踢到铁板了。", "mute_seconds": 600, "weight": 3}
]

# --- 禁言失败时的随机台词 (优化了衔接) ---
timeout_failure_messages = [
    "然而，正当警长准备将 **{loser}** 带走时，他突然看清了对方的脸，吓得立马收回了手，敬了个礼！‘哎呀！原来是大人您！小的有眼不识泰山，您当然不需要进禁闭室！’",
    "然而，正当警长掏出手铐时，**{loser}** 突然从口袋里掏出一袋沉甸甸的金币，悄悄塞了过去。警长掂了掂，然后假装什么都没看见，吹着口哨走开了。看来，有钱真的可以为所欲为...",
    "然而，当警长试图靠近 **{loser}** 时，一股无形的气场将他弹开！‘我...我的身体动不了！’ 警长惊恐地发现，有些大人物，是规则无法束缚的！",
    "然而，**{loser}** 只是冷冷地瞥了警长一眼，警长便冷汗直流，默默地退下了。有些眼神，是惹不起的。",
]

# --- 机器人设置 ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'机器人 {client.user} (蓝莓) 已成功登录并准备就绪！')
    print('------------------------------------')

@client.event
async def on_message(message):
    global duel_initiator, duel_channel, duel_timestamp, duel_custom_duration
    global roulette_active, roulette_channel, roulette_timestamp, roulette_custom_duration, roulette_bullet_position, roulette_current_pulls, roulette_participants

    if message.author == client.user:
        return
    
    clean_content = message.content.strip()

    # --- 决斗功能逻辑 ---
    if clean_content.startswith("决斗"):
        if duel_initiator is None:
            parts = clean_content.split()
            duration_text = ""
            temp_custom_duration = None
            
            if len(parts) > 1:
                parsed_seconds = parse_duration(parts[1])
                if parsed_seconds:
                    temp_custom_duration = parsed_seconds
                    duration_text = f"**本次决斗的赌注是：{format_seconds(temp_custom_duration)}的禁闭时间！**\n"
                else:
                    await message.channel.send(f"蓝莓提示：时间格式不正确或超出范围了哦！请输入一个 {format_seconds(MIN_MUTE_SECONDS)} 到 {format_seconds(MAX_MUTE_SECONDS)} 之间的时间，例如 `决斗 5分钟`。")
                    return
            
            duel_initiator = message.author
            duel_channel = message.channel
            duel_timestamp = time.time()
            duel_custom_duration = temp_custom_duration

            await message.channel.send(
                f"🤠 **正午的钟声敲响...**\n"
                f"枪手 **{duel_initiator.display_name}** 推开酒馆摇晃的木门，缓缓走到小镇中央。他的手，已经悬停在腰间的枪套上。\n"
                f"{duration_text}"
                f"“这里有谁敢与我一较高下？” 他低沉的声音在风中回荡。\n"
                f"*(应战者，请同样宣告「决斗」。若 {int(DUEL_TIMEOUT_SECONDS/60)} 分钟内无人回应，他将失望地离去...)*"
            )
            return
        else:
            if time.time() - duel_timestamp > DUEL_TIMEOUT_SECONDS:
                await duel_channel.send(f"⏳ **夕阳西下...**\n等了太久，**{duel_initiator.display_name}** 哼了一声，将口中的草根吐掉，转身没入了阴影之中。")
                duel_initiator = None
                duel_custom_duration = None
                return

            if message.author == duel_initiator:
                await message.channel.send("和镜子里的自己比快，可算不上真正的枪手。")
                return
            
            if message.channel != duel_channel:
                return

            challenger = message.author
            await message.channel.send(f"💥 **“很好。”**\n另一位枪手 **{challenger.display_name}** 从街角的阴影中走出，接受了这场生死对决！空气瞬间凝固了...")
            
            await asyncio.sleep(3)

            chosen_outcome = random.choices(duel_outcomes, weights=[d['weight'] for d in duel_outcomes], k=1)[0]
            final_mute_seconds = duel_custom_duration if duel_custom_duration is not None else chosen_outcome["mute_seconds"]
            mute_duration = datetime.timedelta(seconds=final_mute_seconds)

            if chosen_outcome.get("is_draw"):
                await message.channel.send(f"**{chosen_outcome['draw_text']}**")
                try:
                    await duel_initiator.timeout(mute_duration, reason="枪战平局")
                    await challenger.timeout(mute_duration, reason="枪战平局")
                    await message.channel.send(f"根据古老的法则，双方都将进入冥想室反思 **{format_seconds(final_mute_seconds)}**。")
                except Exception as e:
                    print(f"无法禁言平局玩家: {e}")
                    await message.channel.send("…等等！时空乱流似乎受到了某种更高力量的干扰，无法将两位强者完全吞噬！")

            elif chosen_outcome.get("reversal"):
                winner, loser = duel_initiator, challenger
                win_text = chosen_outcome["winner_text"].format(loser=loser.display_name)
                lose_text = chosen_outcome["loser_text"]
                reversal_text = chosen_outcome["reversal_text"].format(loser=winner.display_name)
                loser_reaction = chosen_outcome["loser_reaction"].format(original_winner=loser.display_name)
                
                await message.channel.send(f"⚡ **{win_text}**\n**{lose_text}**\n\n...但是！\n\n**{reversal_text}**")
                await asyncio.sleep(2)
                await message.channel.send(loser_reaction)
                await asyncio.sleep(2)
                
                try:
                    await loser.timeout(mute_duration, reason="决斗被反杀")
                    await message.channel.send(f"最终的胜利者是 **{winner.display_name}**！**{loser.display_name}** 因为轻敌，付出了被禁言 **{format_seconds(final_mute_seconds)}** 的代价！")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(timeout_failure_messages).format(loser=loser.display_name)
                    await message.channel.send(failure_message)

            else:
                participants = [duel_initiator, challenger]
                random.shuffle(participants)
                winner, loser = participants[0], participants[1]
                
                win_text = chosen_outcome["winner_text"].format(loser=loser.display_name)
                lose_text = chosen_outcome["loser_text"]
                
                await message.channel.send(f"💨 **{winner.display_name}** {win_text}\n**{loser.display_name}** {lose_text}")
                await asyncio.sleep(1)

                if chosen_outcome.get("loser_reaction"):
                    loser_reaction = chosen_outcome["loser_reaction"].format(loser=loser.display_name)
                    await message.channel.send(loser_reaction)
                    await asyncio.sleep(2)
                
                try:
                    await loser.timeout(mute_duration, reason="枪战落败")
                    await message.channel.send(f"胜利者是 **{winner.display_name}**！失败者 **{loser.display_name}** 将被警长带走关禁闭 **{format_seconds(final_mute_seconds)}**。")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(timeout_failure_messages).format(loser=loser.display_name)
                    await message.channel.send(failure_message)
            
            duel_initiator = None
            duel_channel = None
            duel_timestamp = 0
            duel_custom_duration = None
            return

    # --- 俄罗斯轮盘功能逻辑 ---
    elif clean_content.startswith("轮盘"):
        if not roulette_active:
            parts = clean_content.split()
            temp_custom_duration = None
            
            if len(parts) > 1:
                parsed_seconds = parse_duration(parts[1])
                if parsed_seconds:
                    temp_custom_duration = parsed_seconds
                    duration_text = f"这次的赌注有点大...中弹的人要陪蓝莓在小黑屋里待上整整 **{format_seconds(temp_custom_duration)}**！"
                else:
                    await message.channel.send(f"蓝莓提示：时间格式不正确或超出范围了哦！请输入一个 {format_seconds(MIN_MUTE_SECONDS)} 到 {format_seconds(MAX_MUTE_SECONDS)} 之间的时间，例如 `轮盘 5分钟`。")
                    return
            else:
                duration_text = f"中弹的“幸运儿”，奖励是和我一起在小黑屋里待上 **{int(ROULETTE_MUTE_SECONDS/60)}** 分钟哦！"
                
            roulette_active = True
            roulette_channel = message.channel
            roulette_timestamp = time.time()
            roulette_bullet_position = random.randint(1, roulette_chamber_count)
            roulette_current_pulls = 0
            roulette_participants = []
            roulette_custom_duration = temp_custom_duration
            
            await message.channel.send(
                f"嘻嘻~ 我叫蓝莓哦！(o´▽`o)ﾉ\n"
                f"要来玩个心跳加速的幸运游戏吗？我这里有一把非常漂亮的左轮手枪，**{roulette_chamber_count}**个弹巢中，我已经悄悄填入了**一颗子弹**！\n"
                f"接下来，谁敢对我说出「轮盘」二字，就是勇敢的挑战者！\n"
                f"{duration_text}\n"
                f"*(如果 {int(ROULETTE_TIMEOUT_SECONDS/60)} 分钟内游戏还没结束，蓝莓可就要失去耐心了...)*"
            )
            return

        else:
            if time.time() - roulette_timestamp > ROULETTE_TIMEOUT_SECONDS:
                await roulette_channel.send("唉...等了这么久，游戏都冷场了啦！真无聊~ 蓝莓把枪收起来咯！下次再来找我玩吧！")
                roulette_active = False
                roulette_custom_duration = None
                return

            if message.channel != roulette_channel:
                return

            if message.author in roulette_participants:
                await message.channel.send(f"**{message.author.display_name}**，你已经试过一次运气啦，把机会让给别人吧！")
                return

            roulette_current_pulls += 1
            roulette_participants.append(message.author)
            remaining_chambers = roulette_chamber_count - roulette_current_pulls

            if roulette_current_pulls == roulette_bullet_position:
                loser = message.author
                await message.channel.send(f"**砰！**\n随着一声巨响，**{loser.display_name}** 的眼前出现了好多旋转的小星星... 看来你就是那个独一无二的幸运儿啦！")
                await asyncio.sleep(2)
                
                final_mute_seconds = roulette_custom_duration if roulette_custom_duration is not None else ROULETTE_MUTE_SECONDS
                mute_duration = datetime.timedelta(seconds=final_mute_seconds)

                try:
                    await loser.timeout(mute_duration, reason="俄罗斯轮盘中弹")
                    await message.channel.send(f"恭喜！作为奖励，你要陪蓝莓一起在小黑屋里待上 **{format_seconds(final_mute_seconds)}** 哦！\n"
                                               f"游戏结束，谢谢大家！蓝莓爱你们~")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(timeout_failure_messages).format(loser=loser.display_name)
                    await message.channel.send(f"\n…哎呀！蓝莓本来想把你关起来的，但是...\n{failure_message}")
                
                roulette_active = False
                roulette_custom_duration = None

            else:
                await message.channel.send(f"咔哒...\n**{message.author.display_name}** 松了一口气，是空膛哦！真好运呢~\n"
                                           f"现在，这把左轮手枪还剩下 **{remaining_chambers}** 个弹巢，下一位勇敢的人是谁呀？")
            return
    
    # --- CP 匹配度功能 ---
    elif clean_content.startswith("速配"):
        if len(message.mentions) != 2:
            await message.channel.send("蓝莓提示：请同时 @ 两位你想匹配的人哦！像这样：`速配 @张三 @李四`")
            return

        user1 = message.mentions[0]
        user2 = message.mentions[1]
        
        score = random.randint(0, 100)
        
        if score == 0:
            comment = "呃... 你们俩的缘分可能比陌生人还浅，八字不合，建议保持安全距离！"
            color = 0x5865F2
        elif 1 <= score <= 20:
            comment = "就像两条平行线，虽然在同一个世界，但似乎永远不会相交。还是做普通朋友吧！"
            color = 0x99AAB5
        elif 21 <= score <= 40:
            comment = "是能一起聊天打游戏的朋友关系！但要更进一步？嗯...似乎还缺点什么。"
            color = 0x7289DA
        elif 41 <= score <= 60:
            comment = "有点暧昧的火花哦！如果有人再勇敢一点点，故事可能就不一样了~"
            color = 0xE91E63
        elif 61 <= score <= 80:
            comment = "相当登对！你们在一起时，周围的空气都变得甜甜的，很有发展潜力！"
            color = 0xFEE75C
        elif 81 <= score <= 99:
            comment = "天生一对！你们的默契和磁场，简直就是天造地设，请快点在一起！"
            color = 0xEB459E
        else: # score == 100
            comment = "灵魂伴侣！你们的相遇是宇宙级别的奇迹！请不要犹豫，立即原地结婚！"
            color = 0xED4245

        filled_blocks = int(score / 10)
        empty_blocks = 10 - filled_blocks
        bar = '❤️' * filled_blocks + '🖤' * empty_blocks

        embed = discord.Embed(
            title="💖 蓝莓のCP匹配占卜 💖",
            description=f"蓝莓开始为 **{user1.display_name}** 和 **{user2.display_name}** 进行缘分占卜...",
            color=color
        )
        embed.add_field(name="匹配指数", value=f"**{score}%**", inline=False)
        embed.add_field(name="缘分进度条", value=bar, inline=False)
        embed.add_field(name="蓝莓的悄悄话", value=comment, inline=False)
        embed.set_thumbnail(url="https://i.imgur.com/3V51Y2u.png")

        await message.channel.send(embed=embed)
        return

    # --- 随机问号功能 (在其他功能都未触发时) ---
    if random.randint(1, 10) == 1:
        await message.channel.send('？')

# --- 运行机器人 ---
try:
    TOKEN = os.getenv('DISCORD_TOKEN')
    if TOKEN is None:
        print('错误：在 Secrets 中未找到名为 DISCORD_TOKEN 的机密。')
    else:
        keep_alive()
        client.run(TOKEN)
except Exception as e:
    print(f"启动时发生错误: {e}")
