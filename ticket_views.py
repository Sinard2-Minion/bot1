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

# Ссылка на ваше базовое изображение карты (чистый шаблон)
MAP_TEMPLATE_URL = "https://i.postimg.cc/L8yh47fz/54e6f2be-e010-4d2a-9e8f-028a746e965c.png" 

async def send_audit_log(guild, title, description, color):
    try:
        channel = guild.get_channel(int(AUDIT_LOG_CHANNEL_ID))
        if channel:
            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_timestamp()
            await channel.send(embed=embed)
    except Exception as e: print(f"❌ Ошибка логов: {e}")

# Функция динамической отрисовки статуса "Куплено" на РП-карте штата
async def draw_sold_house_on_map(house_id: str) -> str:
    import requests
    from io import BytesIO
    
    output_filename = "updated_map.png"
    coord = ALL_COORDINATES.get(str(house_id))
    
    try:
        # Скачиваем чистый шаблон карты по прямой ссылке
        response = requests.get(MAP_TEMPLATE_URL)
        img = Image.open(BytesIO(response.content))
        draw = ImageDraw.Draw(img)
        
        # Если координаты дома найдены — рисуем индикатор
        if coord:
            x, y = coord["x"], coord["y"]
            # Рисуем красный полупрозрачный круг-маркер вокруг номера дома
            draw.ellipse([x-20, y-20, x+20, y+20], fill=(255, 0, 0, 180), outline=(139, 0, 0), width=3)
            
            # Попытка загрузить красивый шрифт, иначе используем стандартный
            try: font = ImageFont.load_default()
            except: font = None
                
            draw.text((x-15, y-8), "SOLD", fill=(255, 255, 255), font=font)
            
        img.save(output_filename)
        return output_filename
    except Exception as e:
        print(f"❌ Ошибка PIL отрисовки: {e}")
        return None

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
        embed_info.set_footer(text="Нажмите кнопку ниже, чтобы открыть приватный тикет покупки с Департаментом Имущества.")

        view = discord.ui.View(timeout=120)
        view.add_item(TargetBuyButton(item["id"], item["name"], item["price"], is_biz))
        await interaction.followup.send(embed=embed_info, view=view, ephemeral=True)
class PropertyCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Жилая недвижимость (Дома)", value="cat_houses", description="Каталог из 21 дома в г. Адреналин", emoji="🏡"),
            discord.SelectOption(label="Коммерческие предприятия (Бизнесы)", value="cat_biz", description="Покупка заправок, автосалонов, магазинов", emoji="💼")
        ]
        super().__init__(placeholder="Выберите тип интересующего имущества...", min_values=1, max_values=1, options=options, custom_id="prop_cat_select")

    async def callback(self, interaction: discord.Interaction):
        chosen_cat = self.values
        view = discord.ui.View(timeout=None)
        if chosen_cat == "cat_houses":
            view.add_item(SpecificObjectSelect("houses"))
            msg = "⬇️ **Реестр жилого фонда обновлен. Выберите необходимый ДОМ в меню ниже:**"
        else:
            view.add_item(SpecificObjectSelect("businesses"))
            msg = "⬇️ **Реестр коммерции обновлен. Выберите необходимый БИЗНЕС в меню ниже:**"
        await interaction.response.send_message(msg, view=view, ephemeral=True)

class MainPropertyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PropertyCategorySelect())

class VerdictModal(discord.ui.Modal):
    def __init__(self, ticket_type: str, creator_id: int):
        super().__init__(title="Заполнение реестра")
        self.ticket_type, self.creator_id = ticket_type, creator_id
        v_cfg = VERDICTS.get(ticket_type, {"fields": [{"label": "РП-Примечание", "placeholder": "Текст..."}], "db_field": None})
        self.db_field = v_cfg.get("db_field")
        self.inputs = []
        for idx, f_info in enumerate(v_cfg.get("fields", [])):
            txt_input = discord.ui.TextInput(label=f_info["label"][:45], placeholder=f_info["placeholder"][:100], required=True, max_length=100, custom_id=f"v_f_{idx}")
            self.inputs.append(txt_input)
            self.add_item(txt_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        from database import update_rp_status
        guild, user = interaction.guild, interaction.user
        current_date, doc_num = datetime.now().strftime("%d.%m.%Y"), f"{random.randint(10, 99)} {random.randint(1000, 9999)}"
        clean_name = user.display_name.replace(" ", "_")
        signature = f"{clean_name[:1].upper()}.{clean_name.split('_')[-1][:10] if '_' in clean_name else clean_name[:10]} ✍️"
        doc_data = {"date": current_date, "number": doc_num, "signature": signature}
        
        embed = discord.Embed(title="📜 ОФИЦИАЛЬНЫЙ РЕЕСТР ВЕРДИКТОВ", color=discord.Color.green())
        embed.add_field(name="📅 Дата выдачи:", value=f"`{current_date}`", inline=True)
        embed.add_field(name="🔢 Номер записи:", value=f"`№{doc_num}`", inline=True)
        
        house_num = None
        for inp in self.inputs:
            doc_data[inp.label] = inp.value
            embed.add_field(name=f"📝 {inp.label}:", value=f"**{inp.value}**", inline=False)
            if "номер дома" in inp.label.lower():
                house_num = str(inp.value).strip()

        embed.add_field(name="🖋️ Подпись должностного лица:", value=f"`{signature}`", inline=False)
        if self.db_field and self.creator_id != 0: 
            update_rp_status(self.creator_id, self.db_field, doc_data)
            
        await interaction.channel.send(embed=embed)

        # АВТОМАТИЧЕСКАЯ ОТРИСОВКА И ОБНОВЛЕНИЕ КАРТЫ НА СЕРВЕРЕ
        if self.ticket_type == "Покупка недвижимости" and house_num:
            await interaction.channel.send("🎨 *Генерирую обновленную карту жилого фонда города...*")
            map_file_path = await draw_sold_house_on_map(house_num)
            if map_file_path and os.path.exists(map_file_path):
                map_embed = discord.Embed(
                    title="🗺️ РЕЕСТР ИМУЩЕСТВА: ОБНОВЛЕННАЯ КАРТА ГОРОДА",
                    description=f"Дом **№{house_num}** официально перешёл в частную собственность гражданина. Изменения зафиксированы на спутниковой схеме жилых кварталов.",
                    color=discord.Color.red()
                )
                discord_file = discord.File(map_file_path, filename="map.png")
                map_embed.set_image(url="attachment://map.png")
                
                # Отправляем карту как в текущий тикет, так и дублируем в логи аудита
                await interaction.channel.send(embed=map_embed, file=discord_file)
                
                audit_channel = guild.get_channel(int(AUDIT_LOG_CHANNEL_ID))
                if audit_channel:
                    discord_file_audit = discord.File(map_file_path, filename="map_audit.png")
                    audit_embed = discord.Embed(title="🗺️ Обновление карты недвижимости", description=f"Дом №{house_num} отмечен как проданный.", color=discord.Color.red())
                    audit_embed.set_image(url="attachment://map_audit.png")
                    await audit_channel.send(embed=audit_embed, file=discord_file_audit)
                    
                try: os.remove(map_file_path)
                except: pass

        await asyncio.sleep(15)
        await interaction.channel.delete()

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type: str = "Неизвестно", creator_id: int = 0):
        super().__init__(timeout=None)
        self.ticket_type, self.creator_id = ticket_type, creator_id

    def has_mod_permission(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator: return True
        cfg = CATEGORIES.get(self.ticket_type, {"role_id": 1523079704007934123})
        return bool(cfg and member.get_role(int(cfg["role_id"])))

    @discord.ui.button(label="📥 Взять в работу", style=discord.ButtonStyle.primary, custom_id="take_ticket_btn")
    async def take_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"⏳ Сотрудник {interaction.user.mention} взял дело на рассмотрение.")

    @discord.ui.button(label="🟢 Одобрить", style=discord.ButtonStyle.success, custom_id="approve_ticket_btn")
    async def approve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        await interaction.response.send_modal(VerdictModal(self.ticket_type, self.creator_id))

    @discord.ui.button(label="🔴 Отклонить", style=discord.ButtonStyle.secondary, custom_id="deny_ticket_btn")
    async def deny_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        await interaction.response.send_message("❌ **Заявление / Имущественная сделка ОТКЛОНЕНА. Канал удалится через 5 секунд...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        await interaction.channel.send("🔒 **Тикет закрывается. Очистка...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()
