import discord
import asyncio
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
        v_cfg = VERDICTS.get(ticket_type, {"label": "РП-примечание", "placeholder": "Введите данные...", "db_field": None})
        super().__init__(title="Реестр гос. документов")
        self.ticket_type = ticket_type
        self.creator_id = creator_id
        self.db_field = v_cfg["db_field"]

        self.verdict_input = discord.ui.TextInput(label=v_cfg["label"][:45], placeholder=v_cfg["placeholder"][:100], required=True, max_length=100)
        self.add_item(self.verdict_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        from database import update_rp_status
        guild, user, val = interaction.guild, interaction.user, self.verdict_input.value
        creator = guild.get_member(self.creator_id)
        c_mention = creator.mention if creator else f"ID: {self.creator_id}"

        if self.db_field and self.creator_id != 0:
            formatted_val = f"🟩 {val}" if self.ticket_type != "Регистрация брака" else val
            update_rp_status(self.creator_id, self.db_field, formatted_val)

        embed = discord.Embed(
            title="📜 ГОСУДАРСТВЕННЫЙ УКАЗ / ВЕРДИКТ",
            description=f"**Заявление гражданина было официально ОДОБРЕНО.**\n\n👤 **Заявитель:** {c_mention}\n🤵 **Проверяющий:** {user.mention}\n📦 **Категория:** `{self.ticket_type}`\n📝 **Внесено в базу:**\n> *{val}*\n\nДанные сохранены в `/профиль`. Канал удалится через 10 секунд...",
            color=discord.Color.green()
        )
        await interaction.channel.send(embed=embed)
        await send_audit_log(guild, "✅ Одобрено (Вручную)", f"**Канал:** #{interaction.channel.name}\n**Кто:** {user.mention}\n**Автор:** {c_mention}\n**Что внесено:** {val}", discord.Color.green())
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
        if not options: options.append(discord.SelectOption(label="Нет доступных ролей", value="0"))
        super().__init__(placeholder="Выберите роль для передачи...", min_values=1, max_values=1, options=options, custom_id="custom_role_forward")
        self.ticket_type, self.creator_id = ticket_type, creator_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.values == "0": return
        guild = interaction.guild
        chosen_role = guild.get_role(int(self.values))
        if not chosen_role: return
        creator = guild.get_member(self.creator_id)
        c_mention = creator.mention if creator else f"ID: {self.creator_id}"

        await interaction.channel.set_permissions(chosen_role, read_messages=True, send_messages=True)
        embed = discord.Embed(title="🔀 Статус: Дело перенаправлено", description=f"Рассмотрение заявления передано структуре: {chosen_role.mention}.", color=discord.Color.purple())
        await interaction.message.delete()
        await interaction.channel.send(f"{chosen_role.mention}, требуется ваша проверка!", embed=embed)
        await send_audit_log(guild, "🔀 Тикет перенаправлен", f"**Канал:** #{interaction.channel.name}\n**Кто:** {interaction.user.mention}\n**Кому:** {chosen_role.mention}\n**Автор:** {c_mention}", discord.Color.purple())

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
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав проверяющего!", ephemeral=True)
            return
        c_mention = f"<@{self.creator_id}>" if self.creator_id != 0 else "Автор заявки"
        top_role = next((role.name for role in interaction.user.roles if role.hoist and role.name != "@everyone"), "Администрация")
        
        embed = discord.Embed(title="⏳ Статус: На рассмотрении", description=f"**Взято в работу!**\n\n👤 **Проверяющий:** {interaction.user.mention}\n💼 **Должность:** `{top_role}`", color=discord.Color.orange())
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)
        await send_audit_log(interaction.guild, "⏳ Тикет взят в работу", f"**Канал:** {interaction.channel.mention}\n**Кто:** {interaction.user.mention}\n**Автор:** {c_mention}", discord.Color.orange())

    @discord.ui.button(label="🔀 Передать", style=discord.ButtonStyle.secondary, custom_id="forward_ticket_btn")
    async def forward_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав управления!", ephemeral=True)
            return
        view = CustomRoleSelectView(interaction.guild, self.ticket_type, self.creator_id)
        await interaction.response.send_message("👇 Выберите роль из списка ниже для передачи дела:", view=view, ephemeral=True)

    @discord.ui.button(label="🟢 Одобрить", style=discord.ButtonStyle.success, custom_id="approve_ticket_btn")
    async def approve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав одобрения!", ephemeral=True)
            return
        await interaction.response.send_modal(VerdictModal(self.ticket_type, self.creator_id))

    @discord.ui.button(label="🔴 Отклонить", style=discord.ButtonStyle.secondary, custom_id="deny_ticket_btn")
    async def deny_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        c_mention = f"<@{self.creator_id}>" if self.creator_id != 0 else "Автор заявления"
        await interaction.response.send_message("❌ **Заявление ОТКЛОНЕНО. Канал удалится через 5 секунд...**")
        await send_audit_log(interaction.guild, "❌ Отклонено", f"**Канал:** #{interaction.channel.name}\n**Проверяющий:** {interaction.user.mention}\n**Автор:** {c_mention}", discord.Color.red())
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        c_mention = f"<@{self.creator_id}>" if self.creator_id != 0 else "Автор заявления"
        await interaction.response.send_message("🔒 **Тикет закрывается. Удаление через 5 секунд...**")
        await send_audit_log(interaction.guild, "🔒 Тикет закрыт", f"**Канал:** #{interaction.channel.name}\n**Модератор:** {interaction.user.mention}\n**Автор:** {c_mention}", discord.Color.dark_gray())
        await asyncio.sleep(5)
        await interaction.channel.delete()
