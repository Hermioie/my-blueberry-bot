import discord
from discord import app_commands
from discord.ext import commands
import random

class SocialCog(commands.Cog, name="社交"):
    """包含CP匹配等社交功能"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="速配", description="让蓝莓来占卜一下两位成员的CP匹配度！")
    @app_commands.describe(成员1="选择第一位成员", 成员2="选择第二位成员")
    async def ship(self, interaction: discord.Interaction, 成员1: discord.Member, 成员2: discord.Member):
        """测试两位成员的CP匹配度！"""
        if 成员1 == 成员2:
            await interaction.response.send_message("蓝莓提示：自己和自己是100%匹配的啦，换个其他人试试看吧！", ephemeral=True)
            return
            
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
            description=f"蓝莓开始为 **{成员1.display_name}** 和 **{成员2.display_name}** 进行缘分占卜...",
            color=color
        )
        embed.add_field(name="匹配指数", value=f"**{score}%**", inline=False)
        embed.add_field(name="缘分进度条", value=bar, inline=False)
        embed.add_field(name="蓝莓的悄悄话", value=comment, inline=False)
        embed.set_thumbnail(url="https://i.imgur.com/3V51Y2u.png")

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        # 这是一个简单的检查，确保不会在游戏频道发问号
        # 注意: 如果有多个Cog，获取其他Cog可能需要更健壮的方式，但对于此结构是可行的
        games_cog = self.bot.get_cog("游戏")
        if games_cog:
            if message.channel.id in games_cog.active_duels or message.channel.id in games_cog.active_roulettes:
                return
        
        # 检查消息是否是指令调用，如果是，则不发问号
        # 斜杠指令是 interaction, 普通消息是 message, message.interaction 不为 None 代表是斜杠指令的响应
        if message.interaction:
            return

        if random.randint(1, 100) == 1:
            await message.channel.send('？')

async def setup(bot):
    await bot.add_cog(SocialCog(bot))
