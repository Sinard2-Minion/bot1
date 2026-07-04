import discord
from discord.ext import commands
from discord import app_commands
import os  # Импортируем системную библиотеку для чтения ключей
from tickets import DropdownView
from economy import setup_economy_commands
from keep_alive import keep_alive

class RPCorporateBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        setup_economy_commands(self.tree)
        await self.tree.sync()

bot = RPCorporateBot()

@bot.tree.command(name="настройка_меню", description="Отправить главное меню подачи заявлений")
@app_commands.checks.has_permissions(administrator=True)
async def setup_menu(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️",
        description="Приветствуем вас в едином центре обработки заявлений граждан!\n\n👇 **Выберите необходимый тип заявления в меню ниже:**",
        color=discord.Color.gold()
    )
    await interaction.response.send_message("Меню создано!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=DropdownView())

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        time_left = f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
        await interaction.response.send_message(f"⏱️ Команда на перезарядке! Подождите еще **{time_left}**.", ephemeral=True)
    else:
        raise error

@bot.event
async def on_ready():
    print(f"🤖 Бот {bot.user.name} успешно запущен в безопасном модульном режиме!")

# Запускаем веб-сервер для Render
keep_alive()

# Вытаскиваем секретный ключ под именем "BOT_TOKEN". На компьютере или хостинге он должен быть настроен.
TOKEN = os.environ.get("BOT_TOKEN")

if TOKEN is None:
    print("❌ ОШИБКА: Секретный ключ 'BOT_TOKEN' не найден в переменных окружения!")
else:
    bot.run(TOKEN)
