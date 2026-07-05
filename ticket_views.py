import discord
import asyncio
from ticket_config import AUDIT_LOG_CHANNEL_ID, MAX_ALLOWED_ROLE_ID, CATEGORIES

# --- ФУНКЦИЯ ДЛЯ ОТПРАВКИ ЛОГОВ АУДИТА (ИСПРАВЛЕНА) ---
async def send_audit_log(guild, title, description, color):
    try:
        channel = guild.get_channel(int(AUDIT_LOG_CHANNEL_ID))
        if channel:
            embed = discord.Embed(title=title, description=description, color=color)
            embed.set_timestamp()
            await channel.send(embed=embed)
        else:
            print(f"⚠️ ПРЕДУПРЕЖДЕНИЕ: Канал аудита с ID {AUDIT_LOG_CHANNEL_ID} не найден на сервере!")
    except Exception as e:
        print(f"❌ Ошибка при отправке логов аудита: {e}")

class CustomRoleDropdown(discord.ui.Select):
    def __init__(self, guild: discord.Guild, ticket_type: str, creator: discord.Member):
        max_role = guild.get_role(int(MAX_ALLOWED_ROLE_ID))
        options = []
        sorted_roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)

        for role in sorted_roles:
            if role.name == "@everyone" or role.managed:
                continue
            if max_role and role.position < max_role.position:
                if len(options) >= 25: break
                options.append(discord.SelectOption(label=role.name, value=str(role.id), description=f"Позиция: {role.position}"))

        if not options:
            options.append(discord.SelectOption(label="Нет доступных ролей", value="0"))

        super().__init__(placeholder="Выберите фракционную роль для передачи...", min_values=1, max_values=1, options=options, custom_id="custom_role_forward")
        self.ticket_type = ticket_type
        self.creator = creator

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values)
        if role_id == 0: return

        guild = interaction.guild
        chosen_role = guild.get_role(role_id)
        if not chosen_role: return

        await interaction.channel.set_permissions(chosen_role, read_messages=True, send_messages=True)
        embed = discord.Embed(title="🔀 Статус: Дело перенаправлено", description=f"Рассмотрение заявления передано структуре: {chosen_role.mention}.", color=discord.Color.purple())
        
        await interaction.message.delete()
        await interaction.channel.send(f"{chosen_role.mention}, требуется ваша проверка!", embed=embed)
        await send_audit_log(guild, "🔀 Тикет перенаправлен", f"**Канал:** #{interaction.channel.name}\n**Кто:** {interaction.user.mention}\n**Кому:** {chosen_role.mention}", discord.Color.purple())

class CustomRoleSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild, ticket_type: str, creator: discord.Member):
        super().__init__(timeout=60)
        self.add_item(CustomRoleDropdown(guild, ticket_type, creator))

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type: str, creator: discord.Member):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.creator = creator

    def has_mod_permission(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator: return True
        cfg = CATEGORIES.get(self.ticket_type)
        return bool(cfg and member.get_role(int(cfg["role_id"])))

    @discord.ui.button(label="📥 Взять на рассмотрение", style=discord.ButtonStyle.primary, custom_id="take_ticket")
    async def take_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ Вы не являетесь уполномоченным проверяющим!", ephemeral=True)
            return

        top_role = "Администрация"
        for role in interaction.user.roles:
            if role.hoist and role.name != "@everyone":
                top_role = role.name
                break

        embed = discord.Embed(title="⏳ Статус: На рассмотрении", description=f"**Взято в работу!**\n\n👤 **Проверяющий:** {interaction.user.mention}\n💼 **Должность:** `{top_role}`", color=discord.Color.orange())
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)
        await send_audit_log(interaction.guild, "⏳ Тикет взят в работу", f"**Канал:** {interaction.channel.mention}\n**Кто:** {interaction.user.mention}", discord.Color.orange())

    @discord.ui.button(label="🔀 Передать", style=discord.ButtonStyle.secondary, custom_id="forward_ticket")
    async def forward_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): 
            await interaction.response.send_message("❌ У вас нет прав для управления этим заявлением!", ephemeral=True)
            return
        view = CustomRoleSelectView(interaction.guild, self.ticket_type, self.creator)
        await interaction.response.send_message("👇 Выберите роль из списка ниже для передачи дела:", view=view, ephemeral=True)

    @discord.ui.button(label="🟢 Одобрить", style=discord.ButtonStyle.success, custom_id="approve_ticket")
    async def approve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        
        # Защита от таймаута Дискорда
        await interaction.response.send_message("✅ **Заявление официально ОДОБРЕНО. Канал удалится через 5 секунд...**")
        await send_audit_log(interaction.guild, "✅ Одобрено", f"**Канал:** #{interaction.channel.name}\n**Проверяющий:** {interaction.user.mention}", discord.Color.green())
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔴 Отклонить", style=discord.ButtonStyle.secondary, custom_id="deny_ticket")
    async def deny_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        
        await interaction.response.send_message("❌ **Заявление ОТКЛОНЕНО. Канал удалится через 5 секунд...**")
        await send_audit_log(interaction.guild, "❌ Отклонено", f"**Канал:** #{interaction.channel.name}\n**Проверяющий:** {interaction.user.mention}", discord.Color.red())
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        
        await interaction.response.send_message("🔒 **Тикет закрывается. Удаление через 5 секунд...**")
        await send_audit_log(interaction.guild, "🔒 Тикет закрыт", f"**Канал:** #{interaction.channel.name}\n**Модератор:** {interaction.user.mention}", discord.Color.dark_gray())
        
        await asyncio.sleep(5)
        await interaction.channel.delete()
