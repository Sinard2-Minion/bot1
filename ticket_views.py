import discord
import asyncio
from ticket_config import AUDIT_LOG_CHANNEL_ID, MAX_ALLOWED_ROLE_ID, CATEGORIES

# --- ФУНКЦИЯ ДЛЯ ОТПРАВКИ ЛОГОВ АУДИТА ---
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

# --- ИСПРАВЛЕННЫЙ ВЫБОР РОЛЕЙ (ПОКАЗЫВАЕТ ВСЕ РОЛИ НИЖЕ ЛИМИТА) ---
class CustomRoleDropdown(discord.ui.Select):
    def __init__(self, guild: discord.Guild, ticket_type: str, creator_id: int):
        max_role = guild.get_role(int(MAX_ALLOWED_ROLE_ID))
        options = []
        
        # Сортируем роли сервера по иерархии (от высших к низшим)
        sorted_roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)

        for role in sorted_roles:
            if role.name == "@everyone" or role.managed:
                continue
            
            # Строгий фильтр: добавляем только те роли, которые ниже лимита (position меньше)
            if max_role and role.position < max_role.position:
                if len(options) >= 25:  # Ограничение Дискорда на 25 позиций в меню
                    break
                options.append(discord.SelectOption(label=role.name, value=str(role.id), description=f"Позиция: {role.position}"))

        if not options:
            options.append(discord.SelectOption(label="Нет доступных ролей", value="0"))

        super().__init__(placeholder="Выберите фракционную роль для передачи...", min_values=1, max_values=1, options=options, custom_id="custom_role_forward")
        self.ticket_type = ticket_type
        self.creator_id = creator_id

    async def callback(self, interaction: discord.Interaction):
        val_str = self.values[0] if isinstance(self.values, list) else self.values
        if val_str == "0":
            await interaction.response.send_message("❌ Невозможно передать тикет на выбранную роль.", ephemeral=True)
            return

        role_id = int(val_str)
        guild = interaction.guild
        chosen_role = guild.get_role(role_id)
        
        if not chosen_role:
            await interaction.response.send_message("❌ Ошибка: данная роль не найдена на сервере.", ephemeral=True)
            return

        creator = guild.get_member(self.creator_id)
        creator_mention = creator.mention if creator else f"ID: {self.creator_id}"

        # Открываем права выбранной роли на чтение и отправку
        await interaction.channel.set_permissions(chosen_role, read_messages=True, send_messages=True)
        
        embed = discord.Embed(
            title="🔀 Статус: Дело перенаправлено", 
            description=f"Рассмотрение заявления официально передано структуре: {chosen_role.mention}.", 
            color=discord.Color.purple()
        )
        
        await interaction.response.defer()
        await interaction.message.delete()
        
        await interaction.channel.send(f"{chosen_role.mention}, требуется ваша проверка!", embed=embed)
        await send_audit_log(guild, "🔀 Тикет перенаправлен", f"**Канал:** #{interaction.channel.name}\n**Кто перенаправил:** {interaction.user.mention}\n**Кому передано:** {chosen_role.mention}\n**Автор тикета:** {creator_mention}", discord.Color.purple())

class CustomRoleSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild, ticket_type: str, creator_id: int):
        super().__init__(timeout=60)
        self.add_item(CustomRoleDropdown(guild, ticket_type, creator_id))

# --- ВЕЧНЫЙ ПУЛЬТ УПРАВЛЕНИЯ ТИКЕТОМ ---
class TicketControlView(discord.ui.View):
    def __init__(self, ticket_type: str = "Неизвестно", creator_id: int = 0):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.creator_id = creator_id

    def has_mod_permission(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator: 
            return True
        cfg = CATEGORIES.get(self.ticket_type)
        return bool(cfg and member.get_role(int(cfg["role_id"])))

    @discord.ui.button(label="📥 Взять на рассмотрение", style=discord.ButtonStyle.primary, custom_id="take_ticket_btn")
    async def take_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user):
            await interaction.response.send_message("❌ Вы не являетесь уполномоченным проверяющим для этой категории!", ephemeral=True)
            return

        creator_mention = f"<@{self.creator_id}>" if self.creator_id != 0 else "Автор заявления"

        top_role = "Администрация"
        for role in interaction.user.roles:
            if role.hoist and role.name != "@everyone":
                top_role = role.name
                break

        embed = discord.Embed(title="⏳ Статус: На рассмотрении", description=f"**Взято в работу!**\n\n👤 **Проверяющий:** {interaction.user.mention}\n💼 **Должность:** `{top_role}`", color=discord.Color.orange())
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)
        await send_audit_log(interaction.guild, "⏳ Тикет взят в работу", f"**Канал:** {interaction.channel.mention}\n**Кто:** {interaction.user.mention}\n**Автор заявки:** {creator_mention}", discord.Color.orange())

    @discord.ui.button(label="🔀 Передать", style=discord.ButtonStyle.secondary, custom_id="forward_ticket_btn")
    async def forward_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): 
            await interaction.response.send_message("❌ У вас нет прав для управления этим заявлением!", ephemeral=True)
            return
        
        view = CustomRoleSelectView(interaction.guild, self.ticket_type, self.creator_id)
        await interaction.response.send_message("👇 Выберите фракционную роль из списка ниже для передачи дела:", view=view, ephemeral=True)

    @discord.ui.button(label="🟢 Одобрить", style=discord.ButtonStyle.success, custom_id="approve_ticket_btn")
    async def approve_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        
        from database import update_rp_status
        creator_mention = f"<@{self.creator_id}>" if self.creator_id != 0 else "Автор заявления"
        
        # АВТО-ВЫДАЧА ДОКУМЕНТОВ В БАЗУ ДАННЫХ ПРОФИЛЯ ПРИ ОДОБРЕНИИ
        if self.creator_id != 0:
            if self.ticket_type == "Получение гражданства":
                update_rp_status(self.creator_id, "has_passport", True)
            elif self.ticket_type == "Лицензия":
                update_rp_status(self.creator_id, "drive_license", True)
            elif self.ticket_type == "Регистрация брака":
                update_rp_status(self.creator_id, "married_to", "Зарегистрирован брачный союз")
        
        await interaction.response.send_message("✅ **Заявление ОДОБРЕНО. Документы занесены в профиль! Канал удалится через 5 секунд...**")
        await send_audit_log(interaction.guild, "✅ Одобрено", f"**Канал:** #{interaction.channel.name}\n**Проверяющий:** {interaction.user.mention}\n**Автор:** {creator_mention}\n**Категория:** {self.ticket_type}", discord.Color.green())
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔴 Отклонить", style=discord.ButtonStyle.secondary, custom_id="deny_ticket_btn")
    async def deny_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        creator_mention = f"<@{self.creator_id}>" if self.creator_id != 0 else "Автор заявления"
        
        await interaction.response.send_message("❌ **Заявление ОТКЛОНЕНО. Канал удалится через 5 секунд...**")
        await send_audit_log(interaction.guild, "❌ Отклонено", f"**Канал:** #{interaction.channel.name}\n**Проверяющий:** {interaction.user.mention}\n**Автор:** {creator_mention}\n**Категория:** {self.ticket_type}", discord.Color.red())
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.has_mod_permission(interaction.user): return
        creator_mention = f"<@{self.creator_id}>" if self.creator_id != 0 else "Автор заявления"
        
        await interaction.response.send_message("🔒 **Тикет закрывается. Удаление через 5 секунд...**")
        await send_audit_log(interaction.guild, "🔒 Тикет закрыт", f"**Канал:** #{interaction.channel.name}\n**Модератор:** {interaction.user.mention}\n**Автор:** {creator_mention}", discord.Color.dark_gray())
        
        await asyncio.sleep(5)
        await interaction.channel.delete()
