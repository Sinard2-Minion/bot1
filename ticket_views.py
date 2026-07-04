import discord
import asyncio

# --- НАСТРОЙКИ СЕРВЕРА ---
AUDIT_LOG_CHANNEL_ID = 111222333444  # ВСТАВЬТЕ СЮДА ID КАНАЛА ДЛЯ ЛОГОВ АУДИТА

# --- ДИНАМИЧЕСКИЙ СПИСОК КАТЕГОРИЙ (ПОД ВАШ ФОРУМ) ---
CATEGORIES = {
    "Заявление на гражданина": {
        "description": "Жалобы, иски и заявления на правонарушителей",
        "emoji": "⚖️",
        "role_id": 112233445566778899  
    },
    "Получение лидерской должности": {
        "description": "Подача анкет на лидерство в гос. структурах / бандах",
        "emoji": "👑",
        "role_id": 223344556677889900  
    },
    "Регистрация брак": {
        "description": "Подача заявления в ЗАГС на заключение брака",
        "emoji": "💍",
        "role_id": 334455667788990101  
    },
    "Получение гражданства": {
        "description": "Анкеты для миграционной службы / новичков",
        "emoji": "🌍",
        "role_id": 445566778899010202  
    },
    "Смена фамилии": {
        "description": "Изменение личных паспортных данных (Пошлина: 1000$)",
        "emoji": "👤",
        "role_id": 556677889900112233  
    },
    "Регистрация бизнеса": {
        "description": "Внесение коммерческого enterprise в гос. реестр",
        "emoji": "💼",
        "role_id": 667788990011223344  
    },
    "Лицензия": {
        "description": "Заявления на получение лицензий (оружие, вождение, бизнес)",
        "emoji": "🪪",
        "role_id": 778899001122334455  
    }
}

async def send_audit_log(guild, title, description, color):
    channel = guild.get_channel(AUDIT_LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_timestamp()
        await channel.send(embed=embed)

# --- КНОПКИ УПРАВЛЕНИЯ ВНУТРИ ТТИКЕТА ---
class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type: str, creator: discord.Member):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.creator = creator

    def has_mod_permission(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
        cfg = CATEGORIES.get(self.ticket_type)
        if cfg and member.get_role(cfg["role_id"]):
            return True
        return False

    @discord.ui.button(label="📥 Взять на рассмотрение", style=discord.ButtonStyle.primary, custom_id="take_ticket")
    async def take_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ Вы не являетесь уполномоченным проверяющим для этой категории заявлений!", ephemeral=True)
            return

        top_role = "Администрация"
        for role in interaction.user.roles:
            if role.hoist and role.name != "@everyone":
                top_role = role.name
                break

        embed = discord.Embed(
            title="⏳ Статус: На рассмотрении",
            description=(
                f"**Ваше заявление было взято в работу!**\n\n"
                f"👤 **Проверяющий:** {interaction.user.mention} ({interaction.user.display_name})\n"
                f"💼 **Должность/Роль:** `{top_role}`\n\n"
                f"Пожалуйста, ожидайте окончательного вердикта."
            ),
            color=discord.Color.orange()
        )
        
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)

        await send_audit_log(
            interaction.guild, 
            "⏳ Заявление взято на рассмотрение", 
            f"**Тикет:** {interaction.channel.mention}\n**Проверяющий:** {interaction.user.mention}\n**Категория:** {self.ticket_type}\n**Автор:** {self.creator.mention}",
            discord.Color.orange()
        )

    # --- НОВАЯ КНОПКА ПЕРЕДАЧИ СТАРШЕМУ СОСТАВУ ---
    @discord.ui.button(label="🔀 Передать", style=discord.ButtonStyle.secondary, custom_id="forward_ticket")
    async def forward_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав для управления этим заявлением!", ephemeral=True)
            return

        cfg = CATEGORIES.get(self.ticket_type)
        if not cfg:
            await interaction.response.send_message("❌ Ошибка: категория не найдена в базе данных.", ephemeral=True)
            return

        guild = interaction.guild
        base_role = guild.get_role(cfg["role_id"])
        
        if not base_role:
            await interaction.response.send_message("❌ Ошибка: не удается найти базовую роль проверяющего на сервере.", ephemeral=True)
            return

        # Ищем роль, которая находится выше базовой по списку ролей Дискорда
        higher_role = None
        sorted_roles = sorted(guild.roles, key=lambda r: r.position)
        
        for role in sorted_roles:
            if role.position > base_role.position and not role.managed and role.name != "@everyone":
                higher_role = role
                break

        if higher_role:
            # Выдаем права новой высшей роли на чтение этого тикета
            await interaction.channel.set_permissions(higher_role, read_messages=True, send_messages=True)
            
            embed = discord.Embed(
                title="🔀 Статус: Передано руководству",
                description=f"Рассмотрение дела передано старшему составу: {higher_role.mention}.\nОжидайте ответа от руководства фракции.",
                color=discord.Color.purple()
            )
            await interaction.channel.send(f"{higher_role.mention}, требуется ваше вмешательство!", embed=embed)
            
            # Пишем лог в аудит
            await send_audit_log(
                guild,
                "🔀 Тикет перенаправлен роли выше",
                f"**Канал:** {interaction.channel.mention}\n**Кто передал:** {interaction.user.mention}\n**Кому передано:** {higher_role.mention}\n**Автор тикета:** {self.creator.mention}",
                discord.Color.purple()
            )
            await interaction.response.send_message("✅ Тикет успешно передан роли рангом выше!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Выше этой роли в списке сервера нет других фракционных ролей (высшая инстанция).", ephemeral=True)

    @discord.ui.button(label="🟢 Одобрить", style=discord.ButtonStyle.success, custom_id="approve_ticket")
    async def approve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав для вынесения вердикта в этом тикете!", ephemeral=True)
            return
            
        await interaction.response.send_message("✅ **Заявление официально ОДОБРЕНО.** Канал удалится через 5 секунд...", ephemeral=False)
        
        await send_audit_log(
            interaction.guild, 
            "✅ Заявление Одобрено", 
            f"**Канал:** #{interaction.channel.name}\n**Проверяющий:** {interaction.user.mention}\n**Автор:** {self.creator.mention}",
            discord.Color.green()
        )
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔴 Отклонить", style=discord.ButtonStyle.secondary, custom_id="deny_ticket")
    async def deny_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав для вынесения вердикта в этом тикете!", ephemeral=True)
            return
            
        await interaction.response.send_message("❌ **Заявление ОТКЛОНЕНО.** Канал удалится через 5 секунд...", ephemeral=False)
        
        await send_audit_log(
            interaction.guild, 
            "❌ Заявление Отклонено", 
            f"**Канал:** #{interaction.channel.name}\n**Проверяющий:** {interaction.user.mention}\n**Автор:** {self.creator.mention}",
            discord.Color.red()
        )
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав для закрытия этого тикета!", ephemeral=True)
            return
        await interaction.response.send_message("Тикет закрывается. Удаление через 5 секунд...", ephemeral=False)
        
        await send_audit_log(
            interaction.guild, 
            "🔒 Тикет закрыт", 
            f"**Канал:** #{interaction.channel.name}\n**Модератор:** {interaction.user.mention}\n**Автор:** {self.creator.mention}",
            discord.Color.dark_gray()
        )
        await asyncio.sleep(5)
        await interaction.channel.delete()
