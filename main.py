import discord
from discord.ext import commands
import os
from keep_alive import keep_alive # Импортируем наш веб-сервер

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')

@bot.command()
async def ping(ctx):
    await ctx.send('Понг!')

# Запускаем фоновый веб-сервер для Render
keep_alive()

# Получаем токен из переменных окружения (настроим это в Render)
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
