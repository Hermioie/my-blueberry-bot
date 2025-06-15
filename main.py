import discord
from discord.ext import commands
import os
import asyncio
from flask import Flask
from threading import Thread

# --- 网站设置 (保持在线) ---
app = Flask('')
@app.route('/')
def home():
    return "I'm alive"
def run_flask():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- 机器人核心设置 ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

bot.remove_command('help')

@bot.event
async def on_ready():
    print(f'机器人 {bot.user} (蓝莓) 已成功登录并准备就绪！')
    try:
        synced = await bot.tree.sync()
        print(f'已成功同步 {len(synced)} 条斜杠指令。')
    except Exception as e:
        print(f'同步斜杠指令失败: {e}')
    
    print('------------------------------------')
    await bot.change_presence(activity=discord.Game(name="使用 /决斗 /轮盘 /速配"))

async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'已加载模组: {filename}')
            except Exception as e:
                print(f'加载模组 {filename} 失败: {e}')

async def main():
    async with bot:
        await load_cogs()
        TOKEN = os.getenv('DISCORD_TOKEN')
        if TOKEN is None:
            print('错误：在 Secrets 中未找到名为 DISCORD_TOKEN 的机密。')
        else:
            keep_alive()
            await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"启动时发生致命错误: {e}")
