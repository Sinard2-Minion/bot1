import discord
from database import get_user_data, update_balance
from ticket_views import TicketControlView, CATEGORIES, send_audit_log

# --- КЛАСС ВСПЛЫВАЮЩЕГО ОКНА (МОДАЛКИ) ---
class ApplicationModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        # Заголовок всплывающего окна
        super().__init__(title=f"Бланк: {ticket_type}")
        self.ticket_type = ticket_type

        # Добавляем текстовые поля для ввода (максимум 5 полей в одной модалке)
        self.rp_name = discord.ui.TextInput(
            label="Ваш РП ник (Имя_Фамилия)",
            placeholder="Например: M1lton_James",
            required=True,
            max_length=50
        )
        self.add_item(self.rp_name)

        self.details = discord.ui.TextInput(
            label="Суть вашего заявления / обращения",
            placeholder="Подробно опишите вашу ситуацию или цель подачи...",
            style=discord.TextStyle.paragraph, # Длинное поле
            required=True,
            max_length=1000
        )
        self.add_item(self.details)

        self.proofs = discord.ui.TextInput(
            label="Доказательства (если требуются)",
            placeholder="Ссылки на скриншоты, видеозаписи или прочерк '—'",
            required=False,
            max_length=200
        )
        self.add_item(self.proofs)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        cfg = CATEGORIES.get(self.ticket_type)

        # Обработка пошлины для смены личных данных
        if self.ticket_type == "Смена фамилии":
            u_data = get_user_data(user.id)
            if u_data["cash"] < 1000:
                await interaction.response.send_message("❌ У вас недостаточно наличных денег для оплаты гос. пошлины ($1,000)!", ephemeral=True)
                return
            update_balance(user.id, -1000, "cash")
            payment_status = "✅ Гос. пошлина ($1,000) успешно списана с вашего баланса!"
        else:
            payment_status = "🆓 Подача в эту категорию бесплатна."

        # Отвечаем игроку сразу, чтобы Discord не выдал ошибку
        await interaction.response.send_message(f"⌛ Создаем ваше заявление в системе... Пожалуйста, подождите.", ephemeral=True)

        # Настраиваем права доступа к будущему тикету
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ping_role_id = cfg["role_id"] if cfg else None
        if ping_role_id:
            role_obj = guild.get_role(ping_role_id)
            if role_obj:
                overwrites[role_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Создаем текстовый канал на основе имени пользователя
        channel_name = f"заявление-{user.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        # Формируем красивую карточку (Embed) с заполненными ответами игрока
        embed_report = discord.Embed(
            title=f"📋 НОВОЕ ЗАЯВЛЕНИЕ: {self.ticket_type.upper()}",
            color=discord.Color.blue()
        )
        embed_report.add_field(name="👤 Автор заявления:", value=user.mention, inline=True)
        embed_report.add_field(name="🆔 Discord Никнейм:", value=f"`{user.name}`", inline=True)
        embed_report.add_field(name="🎭 РП Имя персонажа:", value=f"**{self.rp_name.value}**", inline=False)
        embed_report.add_field(name="📝 Содержание / Описание:", value=self.details.value, inline=False)
        embed_report.add_field(name="🔗 Доказательства:", value=self.proofs.value or "*Не предоставлены*", inline=False)
        embed_report.add_field(name="💳 Финансовый статус:", value=payment_status, inline=False)
        embed_report.set_footer(text="Управляйте статусом дела с помощью пульта кнопок ниже.")

        # Отправляем оформленный бланк и подключаем пульт кнопок
        await ticket_channel.send(embed=embed_report, view=TicketControlView(self.ticket_type, user))
        
        if ping_role_id:
            await ticket_channel.send(f"<@&{ping_role_id}>, поступило новое заявление на проверку!", delete_after=5)

        # Пишем лог в аудит администрации
        await send_audit_log(
            guild, 
            "✉️ Открыто новое РП-заявление", 
            f"**Пользователь:** {user.mention}\n**Категория:** {self.ticket_type}\n**Канал:** {ticket_channel.mention}",
            discord.Color.blue()
        )

# --- ВЫПАДАЮЩЕЕ МЕНЮ ВЫБОРА КАТЕГОРИИ ---
class ApplicationDropdown(discord.ui.Select):
    def __init__(self):
        options = []
        for name, cfg in CATEGORIES.items():
            options.append(discord.SelectOption(label=name, description=cfg["description"], emoji=cfg["emoji"]))
            
        super().__init__(placeholder="Выберите необходимый тип заявления...", min_values=1, max_values=1, options=options, custom_id="app_dropdown")

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        
        # Вместо создания канала бот моментально выдает всплывающее окно на экран
        modal = ApplicationModal(chosen)
        await interaction.response.send_modal(modal)

class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationDropdown())
