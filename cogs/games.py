import discord
from discord import app_commands
from discord.ext import commands
import json
import random
import time
import datetime
import asyncio
import re

MIN_MUTE_SECONDS = 10
MAX_MUTE_SECONDS = 3600

def parse_duration(time_str: str):
    if not time_str: return None
    match = re.match(r"(\d+)\s*(s|秒|m|分|分钟|h|时|小时)", time_str, re.I)
    if not match: return None
    value, unit = int(match.group(1)), match.group(2).lower()
    if unit in ("s", "秒"): seconds = value
    elif unit in ("m", "分", "分钟"): seconds = value * 60
    elif unit in ("h", "时", "小时"): seconds = value * 3600
    else: return None
    if MIN_MUTE_SECONDS <= seconds <= MAX_MUTE_SECONDS: return seconds
    else: return None

def format_seconds(seconds):
    if seconds < 60: return f"{seconds}秒"
    elif seconds < 3600: return f"{int(seconds / 60)}分钟"
    else: return f"{int(seconds / 3600)}小时"

class GamesCog(commands.Cog, name="游戏"):
    """包含决斗和轮盘等游戏功能"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        with open('config/duel_outcomes.json', 'r', encoding='utf-8') as f:
            self.duel_outcomes = json.load(f)
        with open('config/failure_messages.json', 'r', encoding='utf-8') as f:
            self.timeout_failure_messages = json.load(f)
        
        self.active_duels = {} 
        self.active_roulettes = {} 

    @app_commands.command(name="决斗", description="向全频道发起一场西部枪战对决！")
    @app_commands.describe(时长="设定惩罚时长,如 '5m', '30s' (可选, 默认随机)")
    async def duel(self, interaction: discord.Interaction, 时长: str = None):
        channel_id = interaction.channel.id
        
        if channel_id not in self.active_duels:
            parsed_seconds = parse_duration(时长)
            if 时长 and not parsed_seconds:
                await interaction.response.send_message(f"蓝莓提示：时间格式不正确或超出范围了哦！请输入一个 {format_seconds(MIN_MUTE_SECONDS)} 到 {format_seconds(MAX_MUTE_SECONDS)} 之间的时间。", ephemeral=True)
                return
            
            duration_text = f"**本次决斗的赌注是：{format_seconds(parsed_seconds)}的禁闭时间！**\n" if parsed_seconds else ""
            
            self.active_duels[channel_id] = {'initiator': interaction.user, 'timestamp': time.time(), 'custom_duration': parsed_seconds}

            await interaction.response.send_message(
                f"🤠 **正午的钟声敲响...**\n"
                f"枪手 **{interaction.user.display_name}** 推开酒馆摇晃的木门，缓缓走到小镇中央。他的手，已经悬停在腰间的枪套上。\n"
                f"{duration_text}"
                f"“这里有谁敢与我一较高下？” 他低沉的声音在风中回荡。\n"
                f"*(应战者，请同样使用 `/决斗` 指令。若 2 分钟内无人回应，他将失望地离去...)*"
            )
        else:
            duel_data = self.active_duels[channel_id]
            
            if time.time() - duel_data['timestamp'] > 120:
                await interaction.response.send_message(f"⏳ **夕阳西下...**\n等了太久，**{duel_data['initiator'].display_name}** 哼了一声，将口中的草根吐掉，转身没入了阴影之中。")
                del self.active_duels[channel_id]
                return

            if interaction.user == duel_data['initiator']:
                await interaction.response.send_message("和镜子里的自己比快，可算不上真正的枪手。", ephemeral=True)
                return

            challenger = interaction.user
            initiator = duel_data['initiator']
            await interaction.response.send_message(f"💥 **“很好。”**\n另一位枪手 **{challenger.display_name}** 从街角的阴影中走出，接受了这场生死对决！空气瞬间凝固了...")
            
            await asyncio.sleep(3)

            chosen_outcome = random.choices(self.duel_outcomes, weights=[d['weight'] for d in self.duel_outcomes], k=1)[0]
            final_mute_seconds = duel_data['custom_duration'] if duel_data['custom_duration'] is not None else chosen_outcome["mute_seconds"]
            mute_duration = datetime.timedelta(seconds=final_mute_seconds)

            if chosen_outcome.get("is_draw"):
                await interaction.followup.send(f"**{chosen_outcome['draw_text']}**")
                try:
                    await initiator.timeout(mute_duration, reason="枪战平局")
                    await challenger.timeout(mute_duration, reason="枪战平局")
                    await interaction.followup.send(f"根据古老的法则，双方都将进入冥想室反思 **{format_seconds(final_mute_seconds)}**。")
                except Exception as e:
                    print(f"无法禁言平局玩家: {e}")
                    await interaction.followup.send("…等等！时空乱流似乎受到了某种更高力量的干扰，无法将两位强者完全吞噬！")
            
            elif chosen_outcome.get("reversal"):
                winner, loser = initiator, challenger
                win_text = chosen_outcome["winner_text"].format(loser=loser.display_name)
                lose_text = chosen_outcome["loser_text"]
                reversal_text = chosen_outcome["reversal_text"].format(loser=winner.display_name)
                loser_reaction = chosen_outcome["loser_reaction"].format(original_winner=loser.display_name)
                
                await interaction.followup.send(f"⚡ **{win_text}**\n**{lose_text}**\n\n...但是！\n\n**{reversal_text}**")
                await asyncio.sleep(2)
                await interaction.followup.send(loser_reaction)
                await asyncio.sleep(2)
                try:
                    await loser.timeout(mute_duration, reason="决斗被反杀")
                    await interaction.followup.send(f"最终的胜利者是 **{winner.display_name}**！**{loser.display_name}** 因为轻敌，付出了被禁言 **{format_seconds(final_mute_seconds)}** 的代价！")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(self.timeout_failure_messages).format(loser=loser.display_name)
                    await interaction.followup.send(failure_message)
            else:
                participants = [initiator, challenger]
                random.shuffle(participants)
                winner, loser = participants[0], participants[1]
                
                win_text = chosen_outcome["winner_text"].format(loser=loser.display_name)
                lose_text = chosen_outcome["loser_text"]
                
                await interaction.followup.send(f"💨 **{winner.display_name}** {win_text}\n**{loser.display_name}** {lose_text}")
                await asyncio.sleep(1)

                if chosen_outcome.get("loser_reaction"):
                    loser_reaction = chosen_outcome["loser_reaction"].format(loser=loser.display_name)
                    await interaction.followup.send(loser_reaction)
                    await asyncio.sleep(2)
                
                try:
                    await loser.timeout(mute_duration, reason="枪战落败")
                    await interaction.followup.send(f"胜利者是 **{winner.display_name}**！失败者 **{loser.display_name}** 将被警长带走关禁闭 **{format_seconds(final_mute_seconds)}**。")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(self.timeout_failure_messages).format(loser=loser.display_name)
                    await interaction.followup.send(failure_message)
            
            del self.active_duels[channel_id]

    @app_commands.command(name="轮盘", description="开始一局紧张刺激的俄罗斯轮盘赌！")
    @app_commands.describe(时长="设定本次轮盘的惩罚时长 (可选)")
    async def roulette(self, interaction: discord.Interaction, 时长: str = None):
        channel_id = interaction.channel.id
        
        if channel_id not in self.active_roulettes:
            parsed_seconds = parse_duration(时长)
            if 时长 and not parsed_seconds:
                await interaction.response.send_message(f"蓝莓提示：时间格式不正确或超出范围了哦！请输入一个 {format_seconds(MIN_MUTE_SECONDS)} 到 {format_seconds(MAX_MUTE_SECONDS)} 之间的时间。", ephemeral=True)
                return

            duration_text = f"这次的赌注有点大...中弹的人要陪蓝莓在小黑屋里待上整整 **{format_seconds(parsed_seconds)}**！" if parsed_seconds else f"中弹的“幸运儿”，奖励是和我一起在小黑屋里待上 **{int(480/60)}** 分钟哦！"
            
            self.active_roulettes[channel_id] = {
                'timestamp': time.time(),
                'custom_duration': parsed_seconds,
                'participants': [],
                'bullet_position': random.randint(1, 6),
                'current_pulls': 0
            }
            await interaction.response.send_message(
                f"嘻嘻~ 我叫蓝莓哦！(o´▽`o)ﾉ\n"
                f"要来玩个心跳加速的幸运游戏吗？我这里有一把非常漂亮的左轮手枪，**6**个弹巢中，我已经悄悄填入了**一颗子弹**！\n"
                f"接下来，谁敢使用 `/轮盘` 指令，就是勇敢的挑战者！\n"
                f"{duration_text}\n"
                f"*(如果 5 分钟内游戏还没结束，蓝莓可就要失去耐心了...)*"
            )
        else:
            roulette_data = self.active_roulettes[channel_id]
            
            if time.time() - roulette_data['timestamp'] > 300:
                # Use followup because an interaction may already be in progress
                await interaction.response.send_message("唉...等了这么久，游戏都冷场了啦！真无聊~ 蓝莓把枪收起来咯！下次再来找我玩吧！", ephemeral=True)
                del self.active_roulettes[channel_id]
                return

            if interaction.user in roulette_data['participants']:
                await interaction.response.send_message(f"**{interaction.user.display_name}**，你已经试过一次运气啦，把机会让给别人吧！", ephemeral=True)
                return
            
            await interaction.response.defer() # Defer response to think
            
            roulette_data['current_pulls'] += 1
            roulette_data['participants'].append(interaction.user)
            
            if roulette_data['current_pulls'] == roulette_data['bullet_position']:
                loser = interaction.user
                await interaction.followup.send(f"**砰！**\n随着一声巨响，**{loser.display_name}** 的眼前出现了好多旋转的小星星... 看来你就是那个独一无二的幸运儿啦！")
                await asyncio.sleep(2)
                
                final_mute_seconds = roulette_data['custom_duration'] if roulette_data['custom_duration'] is not None else 480
                mute_duration = datetime.timedelta(seconds=final_mute_seconds)

                try:
                    await loser.timeout(mute_duration, reason="俄罗斯轮盘中弹")
                    await interaction.followup.send(f"恭喜！作为奖励，你要陪蓝莓一起在小黑屋里待上 **{format_seconds(final_mute_seconds)}** 哦！\n"
                                   f"游戏结束，谢谢大家！蓝莓爱你们~")
                except Exception as e:
                    print(f"无法禁言 {loser.display_name}: {e}")
                    failure_message = random.choice(self.timeout_failure_messages).format(loser=loser.display_name)
                    await interaction.followup.send(f"\n…哎呀！蓝莓本来想把你关起来的，但是...\n{failure_message}")
                
                del self.active_roulettes[channel_id]
            else:
                remaining_chambers = 6 - roulette_data['current_pulls']
                await interaction.followup.send(f"咔哒...\n**{interaction.user.display_name}** 松了一口气，是空膛哦！真好运呢~\n"
                               f"现在，这把左轮手枪还剩下 **{remaining_chambers}** 个弹巢，下一位勇敢的人是谁呀？")

async def setup(bot):
    await bot.add_cog(GamesCog(bot))
