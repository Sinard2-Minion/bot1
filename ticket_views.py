import discord
import asyncio
import random
from datetime import datetime
from ticket_config import AUDIT_LOG_CHANNEL_ID, MAX_ALLOWED_ROLE_ID, CATEGORIES, VERDICTS

async def send_audit_log(guild, title, description, color):
    try:
        channel = guild.get_channel(int(AUDIT_LOG_CHANNEL_ID))
        if channel:
            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_timestamp()
            await channel.send(embed=embed)
    except Exception as e: print(f"❌ Ошибка логов: {e}")

# --- КНОПКА КУПИТЬ ПОД КАЖДЫМ ДОМОМ ---
class BuyHouseButton(discord.ui.Button):
    def __init__(self, house_id: str, house_name: str, house_price: str):
        super().__init__(label="🛒 Купить дом", style=discord.ButtonStyle.success, custom_id=f"buy_house_{house_id}")
        self.house_id = house_id
        self.house_name = house_name
        self.house_price = house_price

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild, user = interaction.guild, interaction.user
        
        # Настройка приватного тикета для покупки
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        cfg = CATEGORIES.get("Покупка недвижимости")
        if cfg and cfg.get("role_id"):
            role_obj = guild.get_role(int(cfg["role_id"]))
            if role_obj: overwrites[role_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Создаем канал сделки
        ch_name = f"дом-{self.house_id}-{user.name}"
        ticket_channel = await guild.create_text_channel(name=ch_name, overwrites=overwrites)

        embed_deal = discord.Embed(title="🤝 ОФОРМЛЕНИЕ СДЕЛКИ КУПЛИ-ПРОДАЖИ", color=discord.Color.gold())
        embed_deal.add_field(name="🏡 Выбранный объект:", value=f"**{self.house_name}**", inline=False)
        embed_deal.add_field(name="💰 Игровая стоимость:", value=f"`${int(self.house_price):,}`", inline=True)
        embed_deal.add_field(name="👤 Покупатель:", value=user.mention, inline=True)
        embed_deal.set_footer(text="Ожидайте проверяющее руководство Департамента Имущества.")
        embed_deal.set_thumbnail(url=user.display_avatar.url)

        # Подключаем пульт кнопок (Взять, Одобрить, Отклонить) к тикету дома
        await ticket_channel.send(embed=embed_deal, view=TicketControlView("Покупка недвижимости", user.id))
        await interaction.followup.send(f"✅ Тикет на покупку дома успешно открыт: {ticket_channel.mention}", ephemeral=True)

class HouseButtonView(discord.ui.View):
    def __init__(self, house_id: str, house_name: str, house_price: str):
        super().__init__(timeout=None)
        self.add_item(BuyHouseButton(house_id, house_name, house_price))

# --- ОКНО ВЕРДИКТА ЛИДЕРА ---
class VerdictModal(discord.ui.Modal):
    def __init__(self, ticket_type: str, creator_id: int):
        super().__init__(title="Заполнение реестра")
        self.ticket_type, self.creator_id = ticket_type, creator_id
        v_cfg = VERDICTS.get(ticket_type, {"fields": [{"label": "РП-Примечание", "placeholder": "Введите текст..."}], "db_field": None, "authority": "Гос. Органы"})
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
        embed = discord.Embed(title=f"📜 ОФИЦИАЛЬНЫЙ РЕЕСТР ВЕРДИКТОВ", color=discord.Color.green())
        embed.add_field(name="📅 Дата утверждения:", value=f"`{current_date}`", inline=True)
        embed.add_field(name="🔢 Номер записи:", value=f"`№{doc_num}`", inline=True)

        for inp in self.inputs:
            doc_data[inp.label] = inp.value
            embed.add_field(name=f"📝 {inp.label}:", value=f"**{inp.value}**", inline=False)

        embed.add_field(name="🖋️ Подпись лица:", value=f"`{signature}`", inline=False)
        if self.db_field and self.creator_id != 0: update_rp_status(self.creator_id, self.db_field, doc_data)

        await interaction.channel.send(embed=embed)
        await asyncio.sleep(10)
        await interaction.channel.delete()

# --- КНОПКИ ВНУТРИ ТИКЕТОВ ---
class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type: str = "Неизвестно", creator_id: int = 0):
        super().__init__(timeout=None)
        self.ticket_type, self.creator_id = ticket_type, creator_id

    def has_mod_permission(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator: return True
        cfg = CATEGORIES.get(self.ticket_type)
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
        await interaction.response.send_message("❌ **Сделка / Заявление ОТКЛОНЕНО. Канал удалится через 5 секунд...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        await interaction.channel.send("🔒 **Тикет закрывается. Очистка...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()
