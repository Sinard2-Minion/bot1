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

class VerdictModal(discord.ui.Modal):
    def __init__(self, ticket_type: str, creator_id: int):
        super().__init__(title="Заполнение гос. реестра")
        self.ticket_type, self.creator_id = ticket_type, creator_id
        v_cfg = VERDICTS.get(ticket_type, {"fields": [{"label": "РП-Вердикт / Примечание", "placeholder": "Введите текст вердикта..."}], "db_field": None, "authority": "Государственные Структуры"})
        self.db_field = v_cfg.get("db_field")
        self.authority = v_cfg.get("authority", "Государственные Структуры")
        self.inputs = []

        fields_list = v_cfg.get("fields", [{"label": "РП-Вердикт / Примечание", "placeholder": "Введите текст вердикта..."}])
        for idx, f_info in enumerate(fields_list):
            txt_input = discord.ui.TextInput(label=f_info["label"][:45], placeholder=f_info["placeholder"][:100], required=True, max_length=100, custom_id=f"v_f_{idx}")
            self.inputs.append(txt_input)
            self.add_item(txt_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        from database import update_rp_status
        guild, user = interaction.guild, interaction.user
        creator = guild.get_member(self.creator_id)
        c_mention = creator.mention if creator else f"ID: {self.creator_id}"
        current_date, doc_num = datetime.now().strftime("%d.%m.%Y"), f"{random.randint(10, 99)} {random.randint(1000, 9999)}"
        clean_name = user.display_name.replace(" ", "_")
        signature = f"{clean_name[:1].upper()}.{clean_name.split('_')[-1][:10] if '_' in clean_name else clean_name[:10]} ✍️"

        # Сохранение структуры документа
        doc_data = {"date": current_date, "number": doc_num, "authority": self.authority, "signature": signature}
        embed = discord.Embed(title=f"📜 ОФИЦИАЛЬНЫЙ РЕЕСТР: {self.ticket_type.upper()}", color=discord.Color.green())
        embed.add_field(name="🏛️ Выдано ведомством:", value=f"`{self.authority}`", inline=False)
        embed.add_field(name="📅 Дата утверждения:", value=f"`{current_date}`", inline=True)
        embed.add_field(name="🔢 Серийный номер:", value=f"`№{doc_num}`", inline=True)

        for inp in self.inputs:
            doc_data[inp.label] = inp.value
            embed.add_field(name=f"📝 {inp.label}:", value=f"**{inp.value}**", inline=False)

        embed.add_field(name="专 Личная подпись должностного лица:", value=f"`{signature}`", inline=False)
        if creator: embed.set_thumbnail(url=creator.display_avatar.url)
        if self.db_field and self.creator_id != 0: update_rp_status(self.creator_id, self.db_field, doc_data)

        await interaction.channel.send(embed=embed)
        await send_audit_log(guild, "✅ Одобрено", f"**Тикет:** #{interaction.channel.name}\n**Кто:** {user.mention}\n**Автор:** {c_mention}\n**Подпись:** {signature}", discord.Color.green())
        await asyncio.sleep(10)
        await interaction.channel.delete()

class CustomRoleDropdown(discord.ui.Select):
    def __init__(self, guild: discord.Guild, ticket_type: str, creator_id: int):
        max_role = guild.get_role(int(MAX_ALLOWED_ROLE_ID))
        options = []
        for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
            if role.name == "@everyone" or role.managed: continue
            if max_role and role.position < max_role.position:
                if len(options) >= 25: break
                options.append(discord.SelectOption(label=role.name, value=str(role.id), description=f"Позиция: {role.position}"))
        if not options: options.append(discord.SelectOption(label="Нет ролей", value="0"))
        super().__init__(placeholder="Выберите роль для передачи...", min_values=1, max_values=1, options=options, custom_id="c_role_forward")
        self.ticket_type, self.creator_id = ticket_type, creator_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.values == "0" or not interaction.guild.get_role(int(self.values)): return
        chosen_role = interaction.guild.get_role(int(self.values))
        await interaction.channel.set_permissions(chosen_role, read_messages=True, send_messages=True)
        embed = discord.Embed(title="🔀 Статус: Перенаправлено", description=f"Рассмотрение заявления передано структуре: {chosen_role.mention}.", color=discord.Color.purple())
        await interaction.message.delete()
        await interaction.channel.send(f"{chosen_role.mention}, требуется ваша проверка!", embed=embed)

class CustomRoleSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild, ticket_type: str, creator_id: int):
        super().__init__(timeout=60)
        self.add_item(CustomRoleDropdown(guild, ticket_type, creator_id))

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type: str = "Неизвестно", creator_id: int = 0):
        super().__init__(timeout=None)
        self.ticket_type, self.creator_id = ticket_type, creator_id

    def has_mod_permission(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator: return True
        cfg = CATEGORIES.get(self.ticket_type)
        return bool(cfg and member.get_role(int(cfg["role_id"])))

    @discord.ui.button(label="📥 Взять на рассмотрение", style=discord.ButtonStyle.primary, custom_id="take_ticket_btn")
    async def take_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"⏳ Тикет взят на рассмотрение сотрудником {interaction.user.mention}.")

    @discord.ui.button(label="🔀 Передать", style=discord.ButtonStyle.secondary, custom_id="forward_ticket_btn")
    async def forward_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        view = CustomRoleSelectView(interaction.guild, self.ticket_type, self.creator_id)
        await interaction.response.send_message("👇 Выберите роль для передачи:", view=view, ephemeral=True)

    @discord.ui.button(label="🟢 Одобрить", style=discord.ButtonStyle.success, custom_id="approve_ticket_btn")
    async def approve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        await interaction.response.send_modal(VerdictModal(self.ticket_type, self.creator_id))

    @discord.ui.button(label="🔴 Отклонить", style=discord.ButtonStyle.secondary, custom_id="deny_ticket_btn")
    async def deny_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        await interaction.response.send_message("❌ **Заявление ОТКЛОНЕНО. Канал удалится через 5 секунд...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        await interaction.response.send_message("🔒 **Тикет закрывается. Удаление через 5 секунд...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()
