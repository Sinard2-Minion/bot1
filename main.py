import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio

# Импортируем модули нашей системы
from tickets import DropdownView
from ticket_views import TicketControlView, MainPropertyView
from economy import setup_economy_commands
from database import get_user_data, update_balance, update_medical_status
from doc_renderer import build_doc_embed
from keep_alive import keep_alive

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
        self.add_view(MainPropertyView()) # Регистрация меню имущества в памяти
        await self.tree.sync()

bot = RPCorporateBot()

# --- ТЕКСТОВАЯ КОМАНДА ВЫДАЧИ ЕДИНОГО РЕЕСТРА ИМУЩЕСТВА Г. АДРЕНАЛИН ---
@bot.command(name="меню_имущества", aliases=["имущество", "реестр"])
@commands.has_permissions(administrator=True)
async def txt_setup_property_registry(ctx):
    embed = discord.Embed(
        title="🏛️ ГОСУДАРСТВЕННЫЙ РЕЕСТР ИМУЩЕСТВА 🏛️",
        description=(
            f"**Единая база данных купли-продажи коммерческой и жилой недвижимости г. Адреналин.**\n\n"
            f"🔹 Здесь вы можете изучить характеристики объектов из Emergency Hamburg и оставить заявку на покупку.\n\n"
            f"👇 **Используйте выпадающее меню ниже, чтобы выбрать категорию:**"
        ),
        color=discord.Color.blue()
    )
    embed.set_image(url="https://squarespace-cdn.com")
    
    await ctx.message.delete()
    await ctx.send(embed=embed, view=MainPropertyView())

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
