import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timedelta

from tickets import DropdownView
from ticket_views import TicketControlView, MainPropertyView
from economy import setup_economy_commands, ADMIN_ROLE_ID
from database import get_user_data, update_balance, update_medical_status
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
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        setup_economy_commands(self.tree)
        self.add_view(TicketControlView())
        self.add_view(DropdownView())
        self.add_view(MainPropertyView())
        await self.tree.sync()

bot = RPCorporateBot()

def has_admin_role_txt(ctx) -> bool:
    if ctx.author.guild_permissions.administrator: return True
    role = ctx.guild.get_role(ADMIN_ROLE_ID)
    return bool(role and role in ctx.author.roles)

@bot.tree.command(name="дом_управление", description="[Мэрия] Управление РП-статусом жилого фонда")
@app_commands.choices(действие=[
    app_commands.Choice(name="❌ Аннулировать покупку (Освободить дом)", value="cancel"),
    app_commands.Choice(name="🔨 Назначить аукцион и создать событие", value="auction")
])
async def house_manage_slash(interaction: discord.Interaction, действие: app_commands.Choice[str], номер_дома: str):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if not (interaction.user.guild_permissions.administrator or (role and role in interaction.user.roles)):
        await interaction.response.send_message("❌ Недостаточно прав!", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    house_id = номер_дома.strip()
    house = next((h for h in HOUSES_BASE if str(h["id"]) == house_id), None)
    
    if not house:
        await interaction.followup.send("❌ Дом не найден!", ephemeral=True)
        return

    if действие.value == "cancel":
        await interaction.followup.send(f"✅ Владение домом №{house_id} аннулировано.", ephemeral=True)
        await interaction.channel.send(f"🏛️ **[Департамент Имущества]** Дом №{house_id} возвращен в гос. собственность!")
    elif действие.value == "auction":
        embed = discord.Embed(title="🔨 ОФИЦИАЛЬНЫЙ ГОСУДАРСТВЕННЫЙ АУКЦИОН", description=f"Лот: `{house['name']}`\n💰 Стартовая цена: `${int(house['price']):,}`", color=discord.Color.red())
        await interaction.channel.send(embed=embed)
        start_time = datetime.now(datetime.utcnow().astimezone().tzinfo) + timedelta(hours=2)
        try:
            event = await guild.create_scheduled_event(name=f"🔨 Аукцион: Дом №{house_id}", description=f"Старт: ${int(house['price']):,}", start_time=start_time, entity_type=discord.GuildScheduledEventEntityType.external, location=f"📍 Мэрия ({interaction.channel.name})")
            await interaction.followup.send(f"🟩 Создано событие: {event.url}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"⚠️ Событие не создано. Ошибка: `{e}`", ephemeral=True)

@bot.tree.command(name="эмбед", description="Создать красивое информационное объявление (Embed)")
async def create_embed_slash(interaction: discord.Interaction, заголовок: str, описание: str, картинка: str = None, цвет_hex: str = "3498db"):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if not (interaction.user.guild_permissions.administrator or (role and role in interaction.user.roles)):
        await interaction.response.send_message("❌ Недостаточно прав!", ephemeral=True)
        return
        
    await interaction.response.defer(ephemeral=True)
    try: color_int = int(цвет_hex.replace("#", ""), 16)
    except: color_int = 0x3498db
    
    embed = discord.Embed(title= заголовок, description=описание.replace("\\n", "\n"), color=discord.Color(color_int))
    embed.set_footer(text=f"Автор: {interaction.user.display_name}")
    embed.set_timestamp()
    if картинка and (картинка.startswith("http://") or картинка.startswith("https://")):
        embed.set_image(url=картинка)
    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Опубликовано!", ephemeral=True)

@bot.command(name="меню_имущества", aliases=["имущество", "реестр"])
async def txt_setup_property_registry(ctx):
    if not has_admin_role_txt(ctx): return
    embed = discord.Embed(title="🏛️ ГОСУДАРСТВЕННЫЙ РЕЕСТР ИМУЩЕСТВА 🏛️", description="Единая база данных купли-продажи коммерческой и жилой недвижимости г. Адреналин.\n\n👇 **Используйте меню ниже для выбора категории:**", color=discord.Color.blue())
    embed.set_image(url="https://squarespace-cdn.com")
    await ctx.message.delete()
    await ctx.send(embed=embed, view=MainPropertyView())

@bot.tree.command(name="настройка_меню")
async def setup_menu_slash(interaction: discord.Interaction):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if not (interaction.user.guild_permissions.administrator or (role and role in interaction.user.roles)):
        await interaction.response.send_message("❌ Недостаточно прав!", ephemeral=True)
        return
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
    await interaction.channel.send(f"👤 {interaction.user.mention} показал документ {кому.mention}:", embed=embed)

@bot.command(name="меню", aliases=["тикет", "панель"])
async def txt_setup_menu_fixed(ctx):
    if not has_admin_role_txt(ctx): return
    embed = discord.Embed(title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️", description="Выберите необходимый тип заявления:", color=discord.Color.gold())
    await ctx.message.delete()
    await ctx.send(embed=embed, view=DropdownView())

keep_alive()
TOKEN = os.environ.get("BOT_TOKEN")
if TOKEN: bot.run(TOKEN)
