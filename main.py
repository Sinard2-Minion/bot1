import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio

from tickets import DropdownView
from ticket_views import TicketControlView, HouseButtonView
from economy import setup_economy_commands
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
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        setup_economy_commands(self.tree)
        self.add_view(TicketControlView())
        self.add_view(DropdownView())
        await self.tree.sync()

bot = RPCorporateBot()

# --- ТЕКСТОВАЯ КОМАНДА !настройка_домов (СОЗДАНИЕ КАНАЛА С КНОПКАМИ КУПИТЬ) ---
@bot.command(name="настройка_домов", aliases=["домы", "домики"])
@commands.has_permissions(administrator=True)
async def txt_setup_houses_final(ctx):
    guild = ctx.guild
    category_id = 1510757796591829114
    category = guild.get_channel(category_id)
    
    if not category or not isinstance(category, discord.CategoryChannel):
        await ctx.send("❌ Ошибка: Указанная категория домов не найдена на сервере!")
        return

    status_msg = await ctx.send("⌛ **Запускаю выгрузку каталога недвижимости г. Адреналин, пожалуйста подождите...**")

    try:
        # Создаем обычный текстовый канал (работает со 100% стабильностью)
        house_channel = await guild.create_text_channel(
            name="🏡｜база-домов",
            category=category,
            topic="Официальный перечень жилой недвижимости г. Адреналин. Нажмите на зелёную кнопку под домом для покупки."
        )
        
        await status_msg.edit(content=f"🟩 **Текстовый канал {house_channel.mention} успешно создан! Выгружаю 21 дом с кнопками купли-продажи...**")

        for house in HOUSES_BASE:
            embed = discord.Embed(
                title=f"🏡 ОБЪЕКТ НЕДВИЖИМОСТИ: {house['name'].upper()}",
                description=f"**Характеристики объекта:**\n\n💰 **Стоимость в игре:** `${int(house['price']):,}`\n🏷️ **Класс:** `{house['tags']}`\n\n📝 **Описание:**\n> *{house['desc']}*",
                color=discord.Color.gold()
            )
            
            # Подключаем к карточке дома персональную кнопку покупки
            view = HouseButtonView(house["id"], house["name"], house["price"])
            await house_channel.send(embed=embed, view=view)
            await asyncio.sleep(1.2)

        await ctx.send(f"✅ **Все 21 дом из Emergency Hamburg успешно выгружены с кнопками покупки в канал {house_channel.mention}!**")

    except Exception as e:
        await ctx.send(f"❌ Произошла ошибка при генерации: `{e}`")

# --- КОМАНДЫ ПРОФИЛЕЙ И ДОКУМЕНТОВ ---
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
    h_txt = h_data.get("Номер дома", "Нет имущества") if isinstance(h_data, dict) else "Нет имущества"
    
    embed.add_field(name="📜 Паспорт:", value=pass_txt, inline=True)
    embed.add_field(name="🩺 Медкарта:", value=med_txt, inline=True)
    embed.add_field(name="🚗 Права:", value=lic_txt, inline=True)
    embed.add_field(name="🏡 Собственность:", value=f"`{h_txt}`", inline=False)
    embed.set_thumbnail(url=target.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="показать")
@app_commands.choices(документ=[
    app_commands.Choice(name="🪪 Паспорт", value="passport"),
    app_commands.Choice(name="🚗 Водительские права", value="license"),
    app_commands.Choice(name="🩺 Медкарта", value="med")
])
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
@commands.has_permissions(administrator=True)
async def txt_setup_menu_fixed(ctx):
    embed = discord.Embed(title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️", description="Выберите необходимый тип заявления:", color=discord.Color.gold())
    await ctx.message.delete()
    await ctx.send(embed=embed, view=DropdownView())

keep_alive()
TOKEN = os.environ.get("BOT_TOKEN")
if TOKEN: bot.run(TOKEN)
