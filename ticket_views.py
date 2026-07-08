import discord
import asyncio
import random
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from ticket_config import AUDIT_LOG_CHANNEL_ID, MAX_ALLOWED_ROLE_ID, CATEGORIES, VERDICTS, HOUSES_PART1, HOUSE_MAP_COORDINATES
from ticket_config_part2 import HOUSES_PART2, BUSINESSES_BASE, HOUSE_MAP_COORDINATES_PART2

ALL_HOUSES = HOUSES_PART1 + HOUSES_PART2
ALL_COORDINATES = {**HOUSE_MAP_COORDINATES, **HOUSE_MAP_COORDINATES_PART2}

MAP_TEMPLATE_URL = "https://ibb.co" 

async def send_audit_log(guild, title, description, color, file=None):
    try:
        channel = guild.get_channel(int(AUDIT_LOG_CHANNEL_ID))
        if channel:
            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_timestamp()
            if file:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed)
    except Exception as e: print(f"❌ Ошибка логов: {e}")

async def save_ticket_transcript(channel: discord.TextChannel, author_mention: str, ticket_type: str):
    filename = f"transcript-{channel.name}.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"==================================================\n")
            f.write(f"📜 ОФИЦИАЛЬНЫЙ ТРАНСКРИПТ ПЕРЕПИСКИ ТИКЕТА\n")
            f.write(f"🏛️ Сервер: {channel.guild.name}\n")
            f.write(f"Канал: #{channel.name}\n")
            f.write(f"Тип заявления: {ticket_type}\n")
            f.write(f"Дата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write(f"==================================================\n\n")

            messages = []
            async for msg in channel.history(limit=500, oldest_first=True):
                messages.append(msg)

            for msg in messages:
                time_str = msg.created_at.strftime("%d.%m.%Y %H:%M:%S")
                if msg.author.bot and (msg.embeds or msg.components):
                    continue
                clean_content = msg.clean_content.replace("\n", " [NEWLINE] ")
                f.write(f"[{time_str}] {msg.author.display_name} ({msg.author.id}): {clean_content}\n")
            f.write(f"\n==================== КОНЕЦ ПРОТОКОЛА ====================")
        
        if os.path.exists(filename):
            discord_file = discord.File(filename)
            await send_audit_log(
                guild=channel.guild,
                title="💾 Выгружен транскрипт закрытого тикета",
                description=f"**Канал:** #{channel.name}\n**Категория:** {ticket_type}\n**Автор тикета:** {author_mention}",
                color=discord.Color.blue(),
                file=discord_file
            )
            os.remove(filename)
    except Exception as e: print(f"❌ Ошибка транскрипта: {e}")

async def draw_sold_house_on_map(house_id: str) -> str:
    import requests
    from io import BytesIO
    output_filename = "updated_map.png"
    coord = ALL_COORDINATES.get(str(house_id))
    try:
        response = requests.get(MAP_TEMPLATE_URL)
        img = Image.open(BytesIO(response.content))
        draw = ImageDraw.Draw(img)
        if coord:
            x, y = coord["x"], coord["y"]
            draw.ellipse([x-20, y-20, x+20, y+20], fill=(255, 0, 0, 180), outline=(139, 0, 0), width=3)
            try: font = ImageFont.load_default()
            except: font = None
            draw.text((x-15, y-8), "SOLD", fill=(255, 255, 255), font=font)
        img.save(output_filename)
        return output_filename
    except Exception as e: print(f"❌ Ошибка PIL: {e}"); return None

class TargetBuyButton(discord.ui.Button):
    def __init__(self, obj_id: str, obj_name: str, obj_price: str, is_business: bool = False):
        super().__init__(label="🛒 Подать заявку на покупку", style=discord.ButtonStyle.success, custom_id=f"buy_obj_{obj_id}")
        self.obj_id, self.obj_name, self.obj_price, self.is_business = obj_id, obj_name, obj_price, is_business

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild, user = interaction.guild, interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        cfg_name = "Регистрация бизнеса" if self.is_business else "Покупка недвижимости"
        cfg = CATEGORIES.get(cfg_name, {"role_id": 1523079704007934123})
        role_obj = guild.get_role(int(cfg["role_id"]))
        if role_obj: overwrites[role_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        prefix = "бизнес" if self.is_business else "дом"
        ch_name = f"{prefix}-{self.obj_id}-{user.name}"
        ticket_channel = await guild.create_text_channel(name=ch_name, overwrites=overwrites)
        embed = discord.Embed(title="🤝 ОФОРМЛЕНИЕ СДЕЛКИ С ГОСУДАРСТВОМ", color=discord.Color.gold())
        embed.add_field(name="🏛️ Объект имущества:", value=f"**{self.obj_name}**", inline=False)
        embed.add_field(name="💰 Гос. стоимость:", value=f"`${int(self.obj_price.replace('$', '').replace(',', '')):,}`", inline=True)
        embed.add_field(name="👤 Покупатель:", value=user.mention, inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        await ticket_channel.send(embed=embed, view=TicketControlView(cfg_name, user.id))
        await interaction.followup.send(f"✅ Создан приватный тикет для оформления сделки: {ticket_channel.mention}", ephemeral=True)

class SpecificObjectSelect(discord.ui.Select):
    def __init__(self, mode: str):
        options = []
        self.mode = mode
        if mode == "houses":
            for h in ALL_HOUSES:
                options.append(discord.SelectOption(label=h["name"], value=h["id"], description=f"Цена: ${int(h['price']):,}", emoji="🏡"))
            placeholder_text = "Выберите номер дома для осмотра..."
        else:
            for b in BUSINESSES_BASE:
                options.append(discord.SelectOption(label=b["name"], value=b["id"], description=f"Цена: ${int(b['price']):,}", emoji="💼"))
            placeholder_text = "Выберите предприятие для осмотра..."
        super().__init__(placeholder=placeholder_text, min_values=1, max_values=1, options=options, custom_id=f"spec_select_{mode}")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        chosen_id = self.values
        if self.mode == "houses":
            item = next((h for h in ALL_HOUSES if str(h["id"]) == str(chosen_id)), None)
            is_biz = False
        else:
            item = next((b for b in BUSINESSES_BASE if str(b["id"]) == str(chosen_id)), None)
            is_biz = True
        if not item:
            await interaction.followup.send("❌ Ошибка: Объект не найден в реестре штата!", ephemeral=True)
            return
        embed_info = discord.Embed(title=f"📋 ИНФОРМАЦИОННАЯ КАРТОЧКА ОБЪЕКТА", color=discord.Color.blue())
        price_val = item["price"] if "$" in str(item["price"]) else f"${int(item['price']):,}"
        embed_info.add_field(name="🏷️ Название объекта:", value=f"**{item['name']}**", inline=False)
        embed_info.add_field(name="💰 Государственная цена:", value=f"`{price_val}`", inline=True)
        embed_info.add_field(name="📊 Категория / Класс:", value=f"`{item['tags']}`", inline=True)
        embed_info.add_field(name="📝 РП-Описание и Спецификация:", value=f"> *{item['desc']}*", inline=False)
        embed_info.set_footer(text="Нажмите кнопку ниже, чтобы открыть приватный тикет покупки.")
        view = discord.ui.View(timeout=120)
        view.add_item(TargetBuyButton(item["id"], item["name"], item["price"], is_biz))
        await interaction.followup.send(embed=embed_info, view=view, ephemeral=True)
