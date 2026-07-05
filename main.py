import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import asyncio

from tickets import DropdownView
from ticket_views import TicketControlView
from economy import setup_economy_commands
from database import get_user_data, update_balance, update_rp_status
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
        await self.tree.sync()

bot = RPCorporateBot()

# --- ФУНКЦИЯ ДЛЯ ГЕНЕРАЦИИ КАРТОЧКИ ДОКУМЕНТА ---
def build_doc_embed(target: discord.Member, u_data: dict, doc_type: str):
    if doc_type == "паспорт" and u_data["passport_data"]:
        d = u_data["passport_data"]
        embed = discord.Embed(title=f"🪪 ГОСУДАРСТВЕННЫЙ ПАСПОРТ РФ", color=discord.Color.red())
        embed.add_field(name="📋 Гражданин (ФИО, Возраст):", value=f"**{d['info']}**", inline=False)
        embed.add_field(name="🏛️ Выдано отделом:", value=f"`{d['authority']}`", inline=False)
        embed.add_field(name="📅 Дата выдачи:", value=f"`{d['date']}`", inline=True)
        embed.add_field(name="🔢 Серия и Номер:", value=f"`{d['number']}`", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        return embed
    
    elif doc_type == "лицензии" and u_data["license_data"]:
        d = u_data["license_data"]
        embed = discord.Embed(title=f"🚗 ВОДИТЕЛЬСКОЕ УДОСТОВЕРЕНИЕ", color=discord.Color.blue())
        embed.add_field(name="👤 Водитель:", value=target.mention, inline=False)
        embed.add_field(name="🪪 Категории / Разрешение:", value=f"**{d['info']}**", inline=False)
        embed.add_field(name="🏢 Кем выдано:", value=f"`{d['authority']}`", inline=False)
        embed.add_field(name="📅 Срок действия от:", value=f"`{d['date']}`", inline=True)
        embed.add_field(name="🔢 Номер бланка:", value=f"`{d['number']}`", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        return embed

    elif doc_type == "медкарта" and u_data["med_exam"]:
        d = u_data["med_exam"]
        embed = discord.Embed(title=f"🩺 МЕДИЦИНСКАЯ КАРТА ШТАТА", color=discord.Color.green())
        embed.add_field(name="👤 Пациент:", value=target.mention, inline=False)
        embed.add_field(name="📊 РП-Заключение врача:", value=f"**{d['info']}**", inline=False)
        embed.add_field(name="🏥 Медицинское учреждение:", value=f"`{d['authority']}`", inline=False)
        embed.add_field(name="📅 Осмотр от:", value=f"`{d['date']}`", inline=True)
        embed.add_field(name="🔢 Номер медкарт:", value=f"`{d['number']}`", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        return embed
    return None

# --- КОМАНДЫ РП ПРОФИЛЕЙ ---

@bot.tree.command(name="профиль", description="Посмотреть свою РП-карточку")
async def profile_slash(interaction: discord.Interaction, пользователь: discord.Member = None):
    target = пользователь or interaction.user
    u_data = get_user_data(target.id)
    embed = discord.Embed(title=f"🪪 Личное дело: {target.display_name}", color=discord.Color.blue())
    embed.set_thumbnail(url=target.display_avatar.url)
    
    pass_txt = f"🟩 Зарегистрирован" if u_data["passport_data"] else "🟥 Отсутствует"
    med_txt = f"🟩 Есть справка" if u_data["med_exam"] else "🟥 Не пройден"
    lic_txt = f"🟩 Активны" if u_data["license_data"] else "🟥 Нету"
    m_txt = u_data["married_data"] if u_data["married_data"] else "Нет"
    
    embed.add_field(name="📜 Паспорт:", value=pass_txt, inline=True)
    embed.add_field(name="🩺 Медкарта:", value=med_txt, inline=True)
    embed.add_field(name="🚗 Права:", value=lic_txt, inline=True)
    embed.add_field(name="💍 Брак:", value=f"`{m_txt}`", inline=False)
    embed.add_field(name="💵 Наличные:", value=f"${u_data['cash']:,}", inline=True)
    embed.add_field(name="🏦 Банк:", value=f"${u_data['bank']:,}", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="показать", description="Показать свой документ другому игроку")
async def show_doc_slash(interaction: discord.Interaction, документ: str, кому: discord.Member):
    dtype = документ.lower()
    if dtype not in ["паспорт", "лицензии", "медкарта"]:
        await interaction.response.send_message("❌ Выберите тип: `паспорт`, `лицензии` или `медкарта`", ephemeral=True)
        return
        
    u_data = get_user_data(interaction.user.id)
    embed = build_doc_embed(interaction.user, u_data, dtype)
    
    if embed is None:
        await interaction.response.send_message(f"❌ Ошибка! У вас ещё не оформлен этот документ (`{dtype}`). Зайдите в Центр Услуг.", ephemeral=True)
        return
        
    await interaction.response.send_message(f"✅ Вы показали документ игроку {кому.mention}", ephemeral=True)
    await interaction.channel.send(f"👤 {interaction.user.mention} протянул документ {кому.mention}:", embed=embed)

# --- ОБЫЧНЫЕ ТЕКСТОВЫЕ КОМАНДЫ ПРЕФИКСА (!) ---

@bot.command(name="профиль", aliases=["p"])
async def txt_profile(ctx, member: discord.Member = None):
    t = member or ctx.author
    u = get_user_data(t.id)
    emb = discord.Embed(title=f"🪪 Личное дело: {t.display_name}", color=discord.Color.blue())
    emb.add_field(name="📜 Паспорт:", value="🟩 Есть" if u["passport_data"] else "🟥 Нет", inline=True)
    emb.add_field(name="🩺 Медкарта:", value="🟩 Есть" if u["med_exam"] else "🟥 Нет", inline=True)
    emb.add_field(name="🚗 Права:", value="🟩 Есть" if u["license_data"] else "🟥 Нет", inline=True)
    await ctx.send(embed=emb)

@bot.command(name="показать")
async def txt_show(ctx, тип: str, member: discord.Member):
    u = get_user_data(ctx.author.id)
    emb = build_doc_embed(ctx.author, u, тип.lower())
    if not emb:
        await ctx.send("❌ Документ отсутствует или указан неверно (`паспорт`/`лицензии`/`медкарта`)!")
        return
    await ctx.send(f"👤 {ctx.author.mention} показал документ {member.mention}:", embed=emb)

@bot.command(name="настройка_меню")
@commands.has_permissions(administrator=True)
async def setup_menu_txt(ctx):
    embed = discord.Embed(title="🏛️ ГОСУДАРСТВЕННЫЙ ЦЕНТР УСЛУГ 🏛️", description="Выберите необходимый тип заявления в меню ниже:", color=discord.Color.gold())
    await ctx.message.delete()
    await ctx.send(embed=embed, view=DropdownView())

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

@bot.event
async def on_ready(): print(f"🤖 Система РП-паспортов с фото, авто-датами и ведомствами УМВД/ГАИ запущена!")

keep_alive()
TOKEN = os.environ.get("BOT_TOKEN")
if TOKEN: bot.run(TOKEN)
