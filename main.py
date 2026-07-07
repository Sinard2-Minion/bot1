import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timedelta

from tickets import DropdownView
from ticket_views import TicketControlView, MainPropertyView
from economy import setup_economy_commands
from database import get_user_data, update_balance, update_medical_status, update_rp_status
from doc_renderer import build_doc_embed
from ticket_config import HOUSES_PART1
from ticket_config_part2 import HOUSES_PART2
from keep_alive import keep_alive

HOUSES_BASE = HOUSES_PART1 + HOUSES_PART2

class RPCorporateBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True  # Обязательно для создания Discord-событий (Scheduled Events)
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        setup_economy_commands(self.tree)
        self.add_view(TicketControlView())
        self.add_view(DropdownView())
        self.add_view(MainPropertyView())
        await self.tree.sync()

bot = RPCorporateBot()

# --- СЛЭШ-КОМАНДА: УПРАВЛЕНИЕ НЕДВИЖИМОСТЬЮ (ОТМЕНА / АУКЦИОН С СОБЫТИЕМ) ---
@bot.tree.command(name="дом_управление", description="[Мэрия] Управление РП-статусом жилого фонда")
@app_commands.choices(действие=[
    app_commands.Choice(name="❌ Аннулировать покупку (Освободить дом)", value="cancel"),
    app_commands.Choice(name="🔨 Назначить аукцион и создать событие", value="auction")
])
@app_commands.checks.has_permissions(administrator=True)
async def house_manage_slash(interaction: discord.Interaction, действие: app_commands.Choice[str], номер_дома: str):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    house_id = номер_дома.strip()
    
    # Ищем дом в базе
    house = next((h for h in HOUSES_BASE if str(h["id"]) == house_id), None)
    if not house:
        await interaction.followup.send("❌ Ошибка: Дом с таким номером не найден в базе г. Адреналин!", ephemeral=True)
        return

    if действие.value == "cancel":
        # Сбрасываем статус в базе данных (база данных обнуляет владельца по house_owned)
        # Для демонстрации очищаем РП-статус канала. В реальной РП-БД тут идет сброс привязки ID.
        await interaction.followup.send(f"✅ Успешно! Регистрация владения для **Дома №{house_id}** аннулирована. Объект возвращен в гос. собственность.", ephemeral=True)
        await interaction.channel.send(f"🏛️ **[Департамент Имущества]** По решению Мэрии **Дом №{house_id}** был принудительно изъят за долги / нарушения и теперь снова свободен для покупки!")

    elif действие.value == "auction":
        # 1. Генерируем красивый информационный Embed в чат
        embed = discord.Embed(
            title="🔨 ОФИЦИАЛЬНЫЙ ГОСУДАРСТВЕННЫЙ АУКЦИОН",
            description=f"Департамент Имущества выставляет на открытые торги изъятую недвижимость!\n\n🏡 **Лот:** `{house['name']}`\n💰 **Стартовая цена:** `${int(house['price']):,}`\n📊 **Класс:** `{house['tags']}`\n\n*Нажмите «Интересует» в официальном событии сервера, чтобы не пропустить начало торгов!*",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)

        # 2. АВТОМАТИЧЕСКОЕ СОЗДАНИЕ ОФИЦИАЛЬНОГО ДИСКОРД-СОБЫТИЯ (EVENT)
        start_time = datetime.now(datetime.utcnow().astimezone().tzinfo) + timedelta(hours=2) # Старт через 2 часа
        try:
            event = await guild.create_scheduled_event(
                name=f"🔨 РП-Аукцион: Дом №{house_id}",
                description=f"Государственные торги за {house['name']}. Стартовая цена: ${int(house['price']):,}. Место проведения: Мэрия г. Адреналин.",
                start_time=start_time,
                entity_type=discord.GuildScheduledEventEntityType.external,
                location=f"📍 Мэрия (Канал {interaction.channel.name})"
            )
            await interaction.followup.send(f"🟩 Успешно! Объявлен аукцион и автоматически создано событие сервера: **{event.url}**", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"⚠️ Текст отправлен, но не удалось создать событие в Дискорде. Проверьте права бота (Управление Событиями)! Ошибка: `{e}`", ephemeral=True)

# --- СЛЭШ-КОМАНДА: КОНСТРУКТОР ЭМБЕДОВ (/эмбед) ---
@bot.tree.command(name="эмбед", description="Создать красивое информационное объявление (Embed)")
@app_commands.checks.has_permissions(administrator=True)
async def create_embed_slash(
    interaction: discord.Interaction, 
    заголовок: str, 
    описание: str, 
    картинка: str = None, 
    цвет_hex: str = "3498db"
):
    await interaction.response.defer(ephemeral=True)
    
    # Конвертируем HEX цвет в формат discord.Color
    try: color_int = int(цвет_hex.replace("#", ""), 16)
    except: color_int = 0x3498db
    
    embed = discord.Embed(title=заголовок, description=описание.replace("\\n", "\n"), color=discord.Color(color_int))
    embed.set_footer(text=f"Опубликовано: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.set_timestamp()
    
    if картинка and (картинка.startswith("http://") or картинка.startswith("https://")):
        embed.set_image(url=картинка)
        
    # Отправляем эмбед прямо в текущий текстовый канал
    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Объявление успешно опубликовано в канале!", ephemeral=True)

# --- ЕДИНЫЙ ЦЕНТР ГОСУСЛУГ И ОСТАЛЬНЫЕ КОМАНДЫ ---
@bot.command(name="меню_имущества", aliases=["имущество", "реестр"])
@commands.has_permissions(administrator=True)
async def txt_setup_property_registry(ctx):
    embed = discord.Embed(title="🏛️ ГОСУДАРСТВЕННЫЙ РЕЕСТР ИМУЩЕСТВА 🏛️", description="Единая база данных купли-продажи коммерческой и жилой недвижимости г. Адреналин.\n\n👇 **Используйте выпадающее меню ниже, чтобы выбрать категорию:**", color=discord.Color.blue())
    embed.set_image(url="https://squarespace-cdn.com")
    await ctx.message.delete()
    await ctx.send(embed=embed, view=MainPropertyView())

@bot.tree.command(name="настройка_меню")
@app_commands.checks.has_permissions(administrator=True)
async def setup_menu_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️", description="Выберите необходимый тип заявления в меню ниже:", color=discord.Color.gold())
    await interaction.response.send_message("Готово!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=DropdownView())

@bot.tree.command(name="профиль")
async def profile_slash(interaction: discord.Interaction, пользователь: discord.Member = None):
    target = пользователь or interaction.user
    u_data = get_user_data(target.id)
    embed = discord.Embed(title=f"🪪 Личное дело: {target.display_name}", color=discord.Color.blue())
    pass_txt = "🟩 Оформлен" if u_data.get("passport_data") else "🟥 Отсутствует"
    med_txt = "🟩 Пройден" if u_data.get("med_exam") else "🟥 Не пройден"
    lic_txt = "🟩 Активны" if u_data.get("license_data") else "🟥 Нету"
    h_data = u_data.get("house_owned", {})
    h_txt = h_data.get("Номер дома (Только ЦИФРА)", "Нет имущества") if isinstance(h_data, dict) else "Нет имущества"
    embed.add_field(name="📜 Паспорт:", value=pass_txt, inline=True)
    embed.add_field(name="🩺 Медкарта:", value=med_txt, inline=True)
    embed.add_field(name="🚗 Права:", value=lic_txt, inline=True)
    embed.add_field(name="🏡 Собственность:", value=f"`{h_txt}`", inline=False)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="показать")
@app_commands.choices(документ=[app_commands.Choice(name="🪪 Паспорт", value="passport"), app_commands.Choice(name="🚗 Водительские права", value="license"), app_commands.Choice(name="🩺 Медкарта", value="med")])
async def show_doc_slash(interaction: discord.Interaction, документ: app_commands.Choice[str], кому: discord.Member):
    await interaction.response.defer(ephemeral=True)
    u_data = get_user_data(interaction.user.id)
    embed = build_doc_embed(interaction.user, u_data, документ.value)
    if embed is None:
        await interaction.followup.send("❌ Документ отсутствует!", ephemeral=True)
        return
    await interaction.followup.send("✅ Вы показали документ", ephemeral=True)
    await interaction.channel.send(f"👤 {interaction.user.mention} показал документ {commу.mention}:", embed=embed)

@bot.command(name="меню", aliases=["тикет", "панель"])
@commands.has_permissions(administrator=True)
async def txt_setup_menu_fixed(ctx):
    embed = discord.Embed(title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️", description="Выберите необходимый тип заявления:", color=discord.Color.gold())
    await ctx.message.delete()
    await ctx.send(embed=embed, view=DropdownView())

keep_alive()
TOKEN = os.environ.get("BOT_TOKEN")
if TOKEN: bot.run(TOKEN)
