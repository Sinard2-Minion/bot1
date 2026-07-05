import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import asyncio

# Импортируем модули нашей системы
from tickets import DropdownView
from economy import setup_economy_commands
from database import get_user_data, update_balance
from keep_alive import keep_alive

class RPCorporateBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        # Регистрируем префикс "!" для текстовых команд
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Подключаем слэш-команды экономики
        setup_economy_commands(self.tree)
        # Синхронизируем слэш-команды глобально
        await self.tree.sync()

bot = RPCorporateBot()

# --- СИСТЕМНЫЕ СЛЭШ-КОМАНДЫ АДМИНИСТРАЦИИ ---
@bot.tree.command(name="настройка_меню", description="Отправить главное меню подачи заявлений")
@app_commands.checks.has_permissions(administrator=True)
async def setup_menu_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️",
        description="Приветствуем вас в едином центре обработки заявлений граждан!\n\n👇 **Выберите необходимый тип заявления в меню ниже:**",
        color=discord.Color.gold()
    )
    await interaction.response.send_message("Menus создано!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=DropdownView())

# --- ОБРАБОТКА ОШИБОК ДЛЯ СЛЭШ-КОМАНД (ИСПРАВЛЕНО) ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        time_left = f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
        await interaction.response.send_message(f"⏱️ Команда на перезарядке! Подождите еще **{time_left}**.", ephemeral=True)
    else:
        raise error

# --- ОБРАБОТКА ОШИБОК ДЛЯ ТЕКСТОВЫХ КОМАНД (!) ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        time_left = f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
        await ctx.send(f"⏱️ Команда на перезарядке! Подождите еще **{time_left}**.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав администратора для использования этой команды!")
    else:
        raise error

# ====================================================================
#     ОФИЦИАЛЬНЫЙ СПИСОК ТЕКСТОВЫХ КОМАНД С ПРЕФИКСОМ "!"
# ====================================================================

# --- КОМАНДЫ ЭКОНОМИКИ И БАНКА ---

@bot.command(name="баланс", aliases=["bal", "money"])
async def txt_balance(ctx, member: discord.Member = None):
    target = member or ctx.author
    u_data = get_user_data(target.id)
    embed = discord.Embed(title=f"💰 Баланс {target.display_name}", color=discord.Color.green())
    embed.add_field(name="💵 Наличные:", value=f"${u_data['cash']}", inline=False)
    embed.add_field(name="🏦 В банке:", value=f"${u_data['bank']}", inline=False)
    embed.add_field(name="💳 Всего:", value=f"${u_data['cash'] + u_data['bank']}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="депозит", aliases=["dep"])
async def txt_deposit(ctx, amount: int):
    u_data = get_user_data(ctx.author.id)
    if amount <= 0:
        await ctx.send("❌ Сумма должна быть больше нуля!")
        return
    if u_data["cash"] < amount:
        await ctx.send("❌ У вас нет столько наличных денег!")
        return
    update_balance(ctx.author.id, -amount, "cash")
    update_balance(ctx.author.id, amount, "bank")
    await ctx.send(f"🏦 Вы успешно положили **${amount}** на банковский счет.")

@bot.command(name="снять", aliases=["with"])
async def txt_withdraw(ctx, amount: int):
    u_data = get_user_data(ctx.author.id)
    if amount <= 0:
        await ctx.send("❌ Сумма должна быть больше нуля!")
        return
    if u_data["bank"] < amount:
        await ctx.send("❌ На вашем банковском счете нет столько денег!")
        return
    update_balance(ctx.author.id, amount, "cash")
    update_balance(ctx.author.id, -amount, "bank")
    await ctx.send(f"💵 Вы успешно сняли **${amount}** наличными.")

# --- КОМАНДЫ ЗАРАБОТКА И КРИМИНАЛА ---

@bot.command(name="работа", aliases=["work"])
@commands.cooldown(1, 1800, commands.BucketType.user)  # Кулдаун 30 минут
async def txt_work(ctx):
    reward = random.randint(150, 400)
    jobs = ["курьером", "офисным клерком", "водителем автобуса", "программистом", "автомехаником", "поваром"]
    update_balance(ctx.author.id, reward, "cash")
    await ctx.send(f"👔 Вы отработали смену **{random.choice(jobs)}** и заработали **${reward}**.")

@bot.command(name="криминал", aliases=["crime"])
@commands.cooldown(1, 10800, commands.BucketType.user)  # Кулдаун 3 часа
async def txt_crime(ctx):
    if random.randint(1, 100) <= 55:
        fine = random.randint(500, 1000)
        update_balance(ctx.author.id, -fine, "cash")
        await ctx.send(f"🚨 Ограбление пошло не по плану! Спецназ зажал вас в углу. Суд выписал штраф **${fine}**.")
    else:
        reward = random.randint(800, 2000)
        update_balance(ctx.author.id, reward, "cash")
        await ctx.send(f"💰 Вы успешно взломали банкомат на окраине города и унесли куш в размере **${reward}**!")

@bot.command(name="ограбить", aliases=["rob"])
@commands.cooldown(1, 21600, commands.BucketType.user)  # Кулдаун 6 часов
async def txt_rob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("❌ Вы не можете ограбить самого себя!")
        return
        
    victim_data = get_user_data(member.id)
    if victim_data["cash"] < 200:
        await ctx.send(f"❌ У {member.display_name} слишком мало наличных денег в кармане. Грабить нечего!")
        return

    if random.randint(1, 100) <= 50:
        fine = 500
        update_balance(ctx.author.id, -fine, "cash")
        update_balance(member.id, fine, "cash")
        await ctx.send(f"👮‍♂️ {member.mention} поймал вас за руку во время кражи! Вы выплатили ему компенсацию **$500**.")
    else:
        percent = random.randint(20, 50)
        stolen_amount = int(victim_data["cash"] * (percent / 100))
        
        update_balance(member.id, -stolen_amount, "cash")
        update_balance(ctx.author.id, stolen_amount, "cash")
        await ctx.send(f"🥷 Вы незаметно вытащили кошелек у {member.mention} и украли **${stolen_amount}** ({percent}% от его наличных)!")

# --- КОМАНДЫ АДМИНИСТРАЦИИ И ТИКЕТОВ ---

@bot.command(name="выдать")
@commands.has_permissions(administrator=True)
async def txt_give(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Сумма должна быть больше нуля!")
        return
    update_balance(member.id, amount, "cash")
    await ctx.send(f"✅ Администратор выдал **${amount}** игроку {member.mention}.")

@bot.command(name="меню", aliases=["тикет", "панель"])
@commands.has_permissions(administrator=True)
async def txt_setup_menu(ctx):
    embed = discord.Embed(
        title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️",
        description="Приветствуем вас в едином центре обработки заявлений граждан!\n\n👇 **Выберите необходимый тип заявления в меню ниже:**",
        color=discord.Color.gold()
    )
    await ctx.message.delete()
    await ctx.send(embed=embed, view=DropdownView())

@bot.command(name="закрыть", aliases=["close"])
async def txt_close_ticket(ctx):
    if "заявление-" in ctx.channel.name:
        await ctx.send("Тикет будет удален через 5 секунд...", delete_after=5)
        await asyncio.sleep(5)
        await ctx.channel.delete()
    else:
        await ctx.send("❌ Эту команду можно использовать только внутри каналов-заявлений!", delete_after=5)

# --- КОМАНДА ДЛЯ МЕДИЦИНСКОЙ СЛУЖБЫ (ВСТАВЛЯТЬ В КОНЕЦ MAIN.PY) ---

from database import update_medical_status

ROLE_MEDIC_ID = 1523265245030649866  # ВСТАВЬТЕ СЮДА ID РОЛИ ВАШИХ ВРАЧЕЙ / МЕДИКОВ

@bot.command(name="медосмотр", aliases=["med", "справка"])
async def txt_med_exam(ctx, member: discord.Member, статус: str = "одобрить"):
    # Проверяем, является ли автор сообщения врачом (роль медика) или админом
    is_medic = ctx.author.get_role(ROLE_MEDIC_ID) is not None
    is_admin = ctx.author.guild_permissions.administrator

    if not (is_medic or is_admin):
        await ctx.send("❌ Эту команду могут использовать только квалифицированные сотрудники Медицинской Службы!")
        return

    if статус.lower() in ["одобрить", "+", "yes", "пройден"]:
        update_medical_status(member.id, True)
        
        embed = discord.Embed(
            title="🩺 Электронная медицинская карта обновлена",
            description=f"👤 **Гражданин:** {member.mention}\n🚑 **Врач:** {ctx.author.mention}\n📊 **Статус медосмотра:** `ПРОЙДЕН (Годен к получению лицензий)`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        # Позволяет врачам аннулировать справку (например, если она просрочена)
        update_medical_status(member.id, False)
        await ctx.send(f"⚠️ Медицинский осмотр для игрока {member.mention} был аннулирован сотрудником {ctx.author.mention}.")


@bot.event
async def on_ready():
    print(f"🤖 Бот {bot.user.name} успешно запущен. Все префиксы и слэш-команды активны!")

# Запускаем веб-сервер Flask для Render
keep_alive()

# Загружаем скрытый токен из переменных окружения
TOKEN = os.environ.get("BOT_TOKEN")

if TOKEN is None:
    print("❌ ОШИБКА: Секретный ключ 'BOT_TOKEN' не найден в переменных окружения!")
else:
    bot.run(TOKEN)
