import discord
import asyncio

# Настройки ID ролей проверяющих (ВСТАВЬТЕ СВОИ ID РОЛЕЙ ИЗ ДИСКОРДА)
ROLE_MAYOR = 112233445566778899        # Проверяющий смены данных / паспортов (например, Мэрия)
ROLE_GOVERNMENT = 223344556677889900   # Проверяющий реестра имущества (например, Правительство)
ROLE_LEADER = 334455667788990101       # Проверяющий отдела кадров (Лидеры/Замы фракций)
ROLE_JUDGE = 445566778899010202        # Проверяющий судебного департамента (Судьи/Прокуроры)

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type: str):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type  # Категория тикета для фильтра прав

    def has_mod_permission(self, member: discord.Member) -> bool:
        # Администраторы сервера могут модерировать любые тикеты без ограничений
        if member.guild_permissions.administrator:
            return True
            
        # Проверка прав по фракционным ролям
        if self.ticket_type == "Смена личных данных" and member.get_role(ROLE_MAYOR):
            return True
        elif self.ticket_type == "Реестр имущества" and member.get_role(ROLE_GOVERNMENT):
            return True
        elif self.ticket_type == "Отдел кадров" and member.get_role(ROLE_LEADER):
            return True
        elif self.ticket_type == "Судебный департамент" and member.get_role(ROLE_JUDGE):
            return True
            
        return False

    @discord.ui.button(label="📥 Взять на рассмотрение", style=discord.ButtonStyle.primary, custom_id="take_ticket")
    async def take_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ Вы не являетесь уполномоченным проверяющим для этой категории заявлений!", ephemeral=True)
            return

        # Находим высшую отображаемую роль проверяющего для вывода должности
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
        
        # Отключаем кнопку, чтобы тикет нельзя было взять повторно
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)

    @discord.ui.button(label="🟢 Одобрить", style=discord.ButtonStyle.success, custom_id="approve_ticket")
    async def approve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав для вынесения вердикта в этом тикете!", ephemeral=True)
            return
            
        await interaction.response.send_message("✅ **Заявление официально ОДОБРЕНО.** Канал удалится через 5 секунд...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔴 Отклонить", style=discord.ButtonStyle.secondary, custom_id="deny_ticket")
    async def deny_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав для вынесения вердикта в этом тикете!", ephemeral=True)
            return
            
        await interaction.response.send_message("❌ **Заявление ОТКЛОНЕНО.** Канал удалится через 5 секунд...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ У вас нет прав для закрытия этого тикета!", ephemeral=True)
            return
        await interaction.response.send_message("Тикет закрывается. Удаление через 5 секунд...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()
