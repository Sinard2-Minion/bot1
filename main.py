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

# --- ОБЫЧНЫЕ ТЕКСТОВЫЕ КОМАНДЫ (ЧЕРЕЗ ПРЕФИКС !) ---

from database import get_user_data, update_balance
import random

@bot.command(name="баланс", aliases=["bal", "money"])
async def txt_balance(ctx, member: discord.Member = None):
    target = member or ctx.author
    u_data = get_user_data(target.id)
    embed = discord.Embed(title=f"💰 Баланс {target.display_name}", color=discord.Color.green())
    embed.add_field(name="💵 Наличные:", value=f"${u_data['cash']}", inline=False)
    embed.add_field(name="🏦 В банке:", value=f"${u_data['bank']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="депозит", aliases=["dep"])
async def txt_deposit(ctx, amount: int):
    u_data = get_user_data(ctx.author.id)
    if amount <= 0 or u_data["cash"] < amount:
        await ctx.send("❌ Недостаточно наличных или неверная сумма!")
        return
    update_balance(ctx.author.id, -amount, "cash")
    update_balance(ctx.author.id, amount, "bank")
    await ctx.send(f"🏦 Вы положили **${amount}** в банк.")

@bot.command(name="снять", aliases=["with"])
async def txt_withdraw(ctx, amount: int):
    u_data = get_user_data(ctx.author.id)
    if amount <= 0 or u_data["bank"] < amount:
        await ctx.send("❌ Недостаточно денег в банке или неверная сумма!")
        return
    update_balance(ctx.author.id, amount, "cash")
    update_balance(ctx.author.id, -amount, "bank")
    await ctx.send(f"💵 Вы сняли **${amount}** наличными.")

@bot.command(name="выдать")
@commands.has_permissions(administrator=True)
async def txt_give(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Сумма должна быть больше нуля!")
        return
    update_balance(member.id, amount, "cash")
    await ctx.send(f"✅ Администратор выдал **${amount}** игроку {member.mention}.")


# Запускаем веб-сервер для Render
keep_alive()

# Вытаскиваем секретный ключ под именем "BOT_TOKEN". На компьютере или хостинге он должен быть настроен.
TOKEN = os.environ.get("BOT_TOKEN")

if TOKEN is None:
    print("❌ ОШИБКА: Секретный ключ 'BOT_TOKEN' не найден в переменных окружения!")
else:
    bot.run(TOKEN)
