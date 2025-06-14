import discord
import os
import random
import time
import datetime
import asyncio
from flask import Flask
from threading import Thread

# --- 决斗功能的状态变量 ---
duel_initiator = None
duel_channel = None
duel_timestamp = 0
DUEL_TIMEOUT_SECONDS = 120

# --- 俄罗斯轮盘功能的状态变量 ---
roulette_active = False
roulette_channel = None
roulette_timestamp = 0
roulette_chamber_count = 6
roulette_bullet_position = 0
roulette_current_pulls = 0
roulette_participants = []
ROULETTE_TIMEOUT_SECONDS = 300
ROULETTE_MUTE_SECONDS = 480

# --- 西部枪战决斗结果随机池 ---
duel_outcomes = [
    {"winner_text": "是镇上最快的枪手！在{loser}的手指碰到枪托之前，子弹已经呼啸而出！", "loser_text": "甚至没来得及拔枪，就缓缓倒在了尘土中。", "mute_seconds": 180, "weight": 30},
    {"winner_text": "在枪响的瞬间侧身翻滚，精准的子弹命中了{loser}持枪的手臂！", "loser_text": "的手枪被打飞，只能痛苦地捂住伤口。", "mute_seconds": 120, "weight": 20},
    {"winner_text": "的子弹击中了{loser}脚边的威士忌酒瓶，飞溅的玻璃碎片让其阵脚大乱！", "loser_text": "被吓了一跳，狼狈地放弃了抵抗。", "mute_seconds": 60, "weight": 15},
    {"winner_text": "在最关键的时刻，{loser}的左轮手枪居然卡壳了！真是天意！", "loser_text": "绝望地看着卡壳的枪，迎接了命运的审判。", "mute_seconds": 240, "weight": 10},
    {"is_draw": True, "draw_text": "黄沙漫天，两人同时拔枪！两声枪响合为一声，子弹在空中碰撞，擦出耀眼的火花！这场对决，不分胜负！", "mute_seconds": 10, "weight": 5},
    {"reversal": True, "winner_text": "的手速快如鬼魅，但就在子弹即将命中眉心的千钧一发之际，{loser}的眼神变了！他竟然用两根手指稳稳地夹住了那颗致命的子弹！", "loser_text": "露出了难以置信的表情，在这位深藏不露的高手面前，他已经输了。", "reversal_text": "“你的速度很快，” {loser}缓缓开口，指尖的子弹冒着青烟，“但还不够快。” 说罢，屈指一弹，子弹以更快的速度飞了回去！", "mute_seconds": 600, "weight": 3}
]

# --- 禁言失败时的随机台词 ---
timeout_failure_messages = [
    "警长正要上前铐住 **{loser}**，但突然看清了对方的脸，吓得立马收回了手，敬了个礼！‘哎呀！原来是大人您！小的有眼不识泰山，您当然不需要进禁闭室！’",
    "**{loser}** 突然从口袋里掏出一袋沉甸甸的金币，悄悄塞给了警长。警长掂了掂，然后假装什么都没看见，吹着口哨走开了。看来，有钱真的可以为所欲为...",
    "当警长试图靠近 **{loser}** 时，一股无形的气场将他弹开！‘我...我的身体动不了！’ 警长惊恐地发现，有些大人物，是规则无法束缚的！",
    "**{loser}** 只是冷冷地瞥了警长一眼，警长便冷汗直流，默默地退下了。有些眼神，是惹不起的。",
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
    global duel_initiator, duel_channel, duel_timestamp
    global roulette_active, roulette_channel, roulette_timestamp, roulette_bullet_position, roulette_current_pulls, roulette_participants

    if message.author == client.user:
        return

    # --- 决斗功能逻辑 ---
    if "决斗" in message.content:
        if duel_initiator is None:
            duel_initiator = message.author
            duel_channel = message.channel
            duel_timestamp = time.time()
            await message.channel.send(
                f"🤠 **正午的钟声敲响...**\n"
                f"枪手 **{duel_initiator.display_name}** 推开酒馆摇晃的木门，缓缓走到小镇中央。他的手，已经悬停在腰间的枪套上。\n"
                f"“这里有谁敢与我一较高下？” 他低沉的声音在风中回荡。\n"
                f"*(应战者，请同样宣告「决斗」。若 {int(DUEL_TIMEOUT_SECONDS/60)} 分钟内无人回应，他将失望地离去...)*"
            )
            return
        else:
            if time.time() - duel_timestamp > DUEL_TIMEOUT_SECONDS:
                await duel_channel.send(f"⏳ **夕阳西下...**\n等了太久，**{duel_initiator.display_name}** 哼了一声，将口中的草根吐掉，转身没入了阴影之中。")
                duel_initiator = None
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
            mute_duration = datetime.timedelta(seconds=chosen_outcome["mute_seconds"])

            if chosen_outcome.get("is_draw"):
                await message.channel.send(f"**{chosen_outcome['draw_text']}**")
                try:
                    await duel_initiator.timeout(mute_duration, reason="枪战平局")
                    await challenger.timeout(mute_duration, reason="枪战平局")
                    await message.channel.send(f"根据古老的法则，双方都将进入冥想室反思 **{chosen_outcome['mute_seconds']}** 秒。")
                except Exception as e:
                    print(f"无法禁言平局玩家: {e}")
                    await message.channel.send("…等等！时空乱流似乎受到了某种更高力量的干扰，无法将两位强者完全吞噬！")

            elif chosen_outcome.get("reversal"):
                winner, loser = duel_initiator, challenger
                win_text = chosen_outcome["winner_text"].format(loser=loser.display_name)
                lose_text = chosen_outcome["loser_text"]
                reversal_text = chosen_outcome["reversal_text"].format(loser=winner.display_name)

                await message.channel.send(f"⚡ **{win_text}**\n**{lose_text}**\n\n...但是！\n\n**{reversal_text}**")
                await asyncio.sleep(2)
                try:
                    await loser.timeout(mute_duration, reason="决斗被反杀")
                    await message.channel.send(f"最终的胜利者是 **{winner.display_name}**！**{loser.display_name}** 因为轻敌而被禁言 **{chosen_outcome['mute_seconds']}** 秒！")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(timeout_failure_messages).format(loser=loser.display_name)
                    await message.channel.send(f"\n…等等，情况有变！\n{failure_message}")

            else:
                participants = [duel_initiator, challenger]
                random.shuffle(participants)
                winner, loser = participants[0], participants[1]

                win_text = chosen_outcome["winner_text"].format(loser=loser.display_name)
                lose_text = chosen_outcome["loser_text"]

                await message.channel.send(f"💨 **{winner.display_name}** {win_text}\n**{loser.display_name}** {lose_text}")
                await asyncio.sleep(1)
                try:
                    await loser.timeout(mute_duration, reason="枪战落败")
                    await message.channel.send(f"胜利者是 **{winner.display_name}**！失败者 **{loser.display_name}** 将被警长带走关禁闭 **{chosen_outcome['mute_seconds']}** 秒。")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(timeout_failure_messages).format(loser=loser.display_name)
                    await message.channel.send(f"\n…等等，情况有变！\n{failure_message}")

            duel_initiator = None
            duel_channel = None
            duel_timestamp = 0
            return

    # --- 俄罗斯轮盘功能逻辑 ---
    if "轮盘" in message.content:
        if not roulette_active:
            roulette_active = True
            roulette_channel = message.channel
            roulette_timestamp = time.time()
            roulette_bullet_position = random.randint(1, roulette_chamber_count)
            roulette_current_pulls = 0
            roulette_participants = []

            await message.channel.send(
                f"嘻嘻~ 我叫蓝莓哦！(o´▽`o)ﾉ\n"
                f"要来玩个心跳加速的幸运游戏吗？我这里有一把非常漂亮的左轮手枪，**{roulette_chamber_count}**个弹巢中，我已经悄悄填入了**一颗子弹**！\n"
                f"接下来，谁敢对我说出「轮盘」二字，就是勇敢的挑战者！\n"
                f"中弹的“幸运儿”，奖励是和我一起在小黑屋里待上 **{int(ROULETTE_MUTE_SECONDS/60)}** 分钟哦！\n"
                f"*(如果 {int(ROULETTE_TIMEOUT_SECONDS/60)} 分钟内游戏还没结束，蓝莓可就要失去耐心了...)*"
            )
            return

        else:
            if time.time() - roulette_timestamp > ROULETTE_TIMEOUT_SECONDS:
                await roulette_channel.send("唉...等了这么久，游戏都冷场了啦！真无聊~ 蓝莓把枪收起来咯！下次再来找我玩吧！")
                roulette_active = False
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
                try:
                    mute_duration = datetime.timedelta(seconds=ROULETTE_MUTE_SECONDS)
                    await loser.timeout(mute_duration, reason="俄罗斯轮盘中弹")
                    await message.channel.send(f"恭喜！作为奖励，你要陪蓝莓一起在小黑屋里待上 **{int(ROULETTE_MUTE_SECONDS/60)}** 分钟哦！\n"
                                               f"游戏结束，谢谢大家！蓝莓爱你们~")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(timeout_failure_messages).format(loser=loser.display_name)
                    await message.channel.send(f"\n…哎呀！蓝莓本来想把你关起来的，但是...\n{failure_message}")

                roulette_active = False

            else:
                await message.channel.send(f"咔哒...\n**{message.author.display_name}** 松了一口气，是空膛哦！真好运呢~\n"
                                           f"现在，这把左轮手枪还剩下 **{remaining_chambers}** 个弹巢，下一位勇敢的人是谁呀？")
            return

    # --- 随机问号功能 ---
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
