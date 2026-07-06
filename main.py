import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import asyncio

# Импортируем модули нашей системы
from tickets import DropdownView
from ticket_views import TicketControlView
from economy import setup_economy_commands
from database import get_user_data, update_balance, update_medical_status, update_rp_status
from doc_renderer import build_doc_embed
from ticket_config import HOUSES_PART1
from ticket_config_part2 import HOUSES_PART2
from keep_alive import keep_alive

# Склеиваем две части базы недвижимости в один общий массив для форума
HOUSES_BASE = HOUSES_PART1 + HOUSES_PART2

class RPCorporateBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Подключаем слэш-команды экономики
        setup_economy_commands(self.tree)
        # Регистрируем постоянный вид кнопок, чтобы они не ломались после перезапуска
        self.add_view(TicketControlView())
        self.add_view(DropdownView())
        # Синхронизируем слэш-команды глобально
        await self.tree.sync()

bot = RPCorporateBot()

# --- КОМАНДЫ РП ПРОФИЛЕЙ (СЛЭШИ) ---

@bot.tree.command(name="настройка_меню", description="Отправить главное меню подачи заявлений")
@app_commands.checks.has_permissions(administrator=True)
async def setup_menu_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️",
        description="Приветствуем вас в едином центре обработки заявлений граждан!\n\n👇 **Выберите необходимый тип заявления в меню ниже:**",
        color=discord.Color.gold()
    )
    await interaction.response.send_message("Меню создано!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=DropdownView())

@bot.tree.command(name="профиль", description="Посмотреть свою РП-карточку")
async def profile_slash(interaction: discord.Interaction, пользователь: discord.Member = None):
    target = пользователь or interaction.user
    u_data = get_user_data(target.id)
    embed = discord.Embed(title=f"🪪 Личное дело: {target.display_name}", color=discord.Color.blue())
    embed.set_thumbnail(url=target.display_avatar.url)
    
    pass_txt = "🟩 Зарегистрирован" if u_data.get("passport_data") else "🟥 Отсутствует"
    med_txt = "🟩 Есть справка" if u_data.get("med_exam") else "🟥 Не пройден"
    lic_txt = "🟩 Активны" if u_data.get("license_data") else "🟥 Нету"
    
    m_data = u_data.get("married_data", {})
    m_txt = m_data.get("Запись гражданского состояния", "Нет") if isinstance(m_data, dict) else "Нет"
    
    embed.add_field(name="📜 Паспорт:", value=pass_txt, inline=True)
    embed.add_field(name="🩺 Медкарта:", value=med_txt, inline=True)
    embed.add_field(name="🚗 Права:", value=lic_txt, inline=True)
    embed.add_field(name="💍 Брак:", value=f"`{m_txt}`", inline=False)
    embed.add_field(name="💵 Наличные:", value=f"${u_data['cash']:,}", inline=True)
    embed.add_field(name="🏦 Банк:", value=f"${u_data['bank']:,}", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="показать", description="Показать свой документ другому игроку")
@app_commands.choices(документ=[
    app_commands.Choice(name="🪪 Паспорт гражданина", value="passport"),
    app_commands.Choice(name="🚗 Водительские права", value="license"),
    app_commands.Choice(name="🩺 Медицинская карта", value="med")
])
async def show_doc_slash(interaction: discord.Interaction, документ: app_commands.Choice[str], кому: discord.Member):
    await interaction.response.defer(ephemeral=True)
    dtype = документ.value
    u_data = get_user_data(interaction.user.id)
    embed = build_doc_embed(interaction.user, u_data, dtype)
    
    if embed is None:
        await interaction.followup.send(f"❌ Ошибка! У вас ещё не оформлен этот документ.", ephemeral=True)
        return
        
    await interaction.followup.send(f"✅ Вы успешно показали документ игроку {кому.mention}", ephemeral=True)
    await interaction.channel.send(f"👤 {interaction.user.mention} протянул документ {кому.mention}:", embed=embed)

# --- АВТОМАТИЧЕСКАЯ НАСТРОЙКА ФОРУМА ДОМОВ (EMERGENCY HAMBURG) ---

@bot.command(name="настройка_домов", aliases=["домы", "домики"])
@commands.has_permissions(administrator=True)
async def txt_setup_houses_final(ctx):
    guild = ctx.guild
    
    # Использование указанной вами РП-категории для недвижимости
    category_id = 1510757796591829114
    category = guild.get_channel(category_id)
    
    if not category or not isinstance(category, discord.CategoryChannel):
        await ctx.send("❌ Ошибка: Указанная категория домов не найдена на сервере!")
        return

    status_msg = await ctx.send("⌛ **Запускаю генерацию РП-форума недвижимости г. Адреналин, пожалуйста подождите...**")

    try:
        # Создаем канал-форум напрямую через контекст текстовой команды без багов
        forum_channel = await guild.create_forum_channel(
            name="🏡｜база-домов",
            category=category,
            topic="Официальный каталог жилой недвижимости г. Адреналин (Emergency Hamburg Roblox)."
        )
        
        await status_msg.edit(content=f"🟩 **Канал-форум {forum_channel.mention} успешно создан! Начинаю выгрузку 21 вкладки...**")

        for house in HOUSES_BASE:
            embed = discord.Embed(
                title=f"🏡 КАТАЛОГ ЖИЛЬЯ: {house['name'].upper()}",
                description=f"**Официальная карточка жилого объекта недвижимости.**\n\n💰 **Рыночная стоимость в игре:** `{house['price']}`\n🏷️ **Класс недвижимости:** `{house['tags']}`\n\n📝 **Описание объекта:**\n> *{house['desc']}*\n\n==================================================\n⚠️ Чтобы зарегистрировать этот дом на себя, подайте заявление в разделе `Реестр имущества` центра госуслуг!",
                color=discord.Color.gold()
            )

            # Публикуем вкладки-треды в форуме, добавляя текстовое наполнение
            await forum_channel.create_thread(
                name=f"{house['name']} | {house['price']}",
                content=f"📈 Спецификация недвижимости для объекта: **{house['name']}**",
                embed=embed
            )
            # Стабильный интервал, чтобы Discord не выдал ошибку Rate Limit
            await asyncio.sleep(1.5)

        await ctx.send(f"✅ **Все дома из Emergency Hamburg успешно загружены в новый форум недвижимости {forum_channel.mention}!**")

    except Exception as e:
        await ctx.send(f"❌ Произошла ошибка при генерации форума: `{e}`")

# --- ОБЫЧНЫЕ ТЕКСТОВЫЕ КОМАНДЫ ПРЕФИКСА (!) ---

@bot.command(name="меню", aliases=["тикет", "панель"])
@commands.has_permissions(administrator=True)
async def txt_setup_menu_fixed(ctx):
    embed = discord.Embed(title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️", description="Выберите необходимый тип заявления в меню ниже:", color=discord.Color.gold())
    await ctx.message.delete()
    await ctx.send(embed=embed, view=DropdownView())

@bot.command(name="профиль", aliases=["p", "паспорт"])
async def txt_profile(ctx, member: discord.Member = None):
    t = member or ctx.author
    u = get_user_data(t.id)
    emb = discord.Embed(title=f"🪪 Личное дело: {t.display_name}", color=discord.Color.blue())
    emb.add_field(name="📜 Паспорт:", value="🟩 Есть" if u.get("passport_data") else "🟥 Нет", inline=True)
    emb.add_field(name="🩺 Медкарта:", value="🟩 Есть" if u.get("med_exam") else "🟥 Нет", inline=True)
    emb.add_field(name="🚗 Права:", value="🟩 Есть" if u.get("license_data") else "🟥 Нет", inline=True)
    await ctx.send(embed=emb)

@bot.command(name="показать")
async def txt_show(ctx, тип: str, member: discord.Member):
    u = get_user_data(ctx.author.id)
    dtype_map = {"паспорт": "passport", "права": "license", "лицензии": "license", "медкарта": "med"}
    resolved_type = dtype_map.get(тип.lower(), "unknown")
    emb = build_doc_embed(ctx.author, u, resolved_type)
    if not emb:
        await ctx.send("❌ Документ отсутствует или указан неверно (`паспорт`/`права`/`медкарта`)!")
        return
    await ctx.send(f"👤 {ctx.author.mention} показал документ {member.mention}:", embed=emb)

@bot.command(name="закрыть", aliases=["close"])
async def txt_close_ticket(ctx):
    if "заявление-" in ctx.channel.name:
        await ctx.send("Тикет будет удален через 5 секунд...")
        await asyncio.sleep(5)
        await ctx.channel.delete()

# --- КОМАНДА МЕДИКОВ ---
ROLE_MEDIC_ID = 555666777888  
@bot.command(name="медосмотр", aliases=["med"])
async def txt_med_exam(ctx, member: discord.Member, статус: str = "одобрить"):
    if not (ctx.author.get_role(ROLE_MEDIC_ID) or ctx.author.guild_permissions.administrator): return
    if статус.lower() in ["одобрить", "+", "пройден"]:
        update_medical_status(member.id, True)
        await ctx.send(f"✅ Врач {ctx.author.mention} зафиксировал прохождение медосмотра для {member.mention}.")
    else:
        update_medical_status(member.id, False)
        await ctx.send(f"⚠️ Медосмотр для {member.mention} аннулирован.")

# --- ОБРАБОТКА ОШИБОК ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message("⏱️ Команда на перезарядке!", ephemeral=True)

@bot.event
async def on_ready(): 
    print(f"🤖 Бот {bot.user.name} успешно запущен. Движок генерации РП-форумов онлайн!")

keep_alive()
TOKEN = os.environ.get("BOT_TOKEN")
if TOKEN: bot.run(TOKEN)
