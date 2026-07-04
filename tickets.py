import discord
from database import get_user_data, update_balance
from ticket_views import TicketControlView, ROLE_MAYOR, ROLE_GOVERNMENT, ROLE_LEADER, ROLE_JUDGE

class ApplicationDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Смена личных данных", description="Изменение РП Имени/Фамилии (Пошлина: 1000$)", emoji="👤"),
            discord.SelectOption(label="Реестр имущества", description="Регистрация купленных домов/бизнесов", emoji="🏡"),
            discord.SelectOption(label="Отдел кадров", description="Контракты на трудоустройство во фракции", emoji="💼"),
            discord.SelectOption(label="Судебный департамент", description="Подача исков, жалоб и апелляций", emoji="🏛️"),
        ]
        super().__init__(placeholder="Выберите необходимый тип заявления...", min_values=1, max_values=1, options=options, custom_id="app_dropdown")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        chosen = self.values

        # Логика списания пошлины для смены личных данных
        if chosen == "Смена личных данных":
            u_data = get_user_data(user.id)
            if u_data["cash"] < 1000:
                await interaction.response.send_message("❌ У вас недостаточно наличных денег для оплаты гос. пошлины ($1,000)!", ephemeral=True)
                return
            update_balance(user.id, -1000, "cash")
            payment_status = "✅ Гос. пошлина ($1,000) успешно списана с вашего баланса!"
        else:
            payment_status = "🆓 Подача в эту категорию бесплатна."

        # Базовые права доступа к новому тикету (Игрок и Бот)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Распределяем доступ к тикету для конкретной роли проверяющей фракции
        ping_role_id = None
        if chosen == "Смена личных данных":
            ping_role_id = ROLE_MAYOR
        elif chosen == "Реестр имущества":
            ping_role_id = ROLE_GOVERNMENT
        elif chosen == "Отдел кадров":
            ping_role_id = ROLE_LEADER
        elif chosen == "Судебный департамент":
            ping_role_id = ROLE_JUDGE

        # Выдаем права фракционной роли, если она настроена
        if ping_role_id:
            role_obj = guild.get_role(ping_role_id)
            if role_obj:
                overwrites[role_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Создаем скрытый текстовый канал на сервере
        channel_name = f"заявление-{user.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        # Подбираем официальный РП-бланк
        blank_text = ""
        if chosen == "Смена личных данных":
            blank_text = f"```ini\n[ ⚖️ ОФИЦИАЛЬНЫЙ БЛАНК: ИЗМЕНЕНИЕ ЛИЧНЫХ ДАННЫХ ]\n\n1. Ваш текущий Дискорд-аккаунт: @{user.name}\n2. Ваш текущий РП-ник (Имя_Фамилия): \n3. Новый желаемый РП-ник (Имя_Фамилия): \n4. Причина смены данных (РП-ситуация): \n5. Статус оплаты: {payment_status}\n\n==================================================\n[ Скопируйте, заполните и отправьте в этот чат ]\n```"
        elif chosen == "Реестр имущества":
            blank_text = "```ini\n[ 🏦 ОФИЦИАЛЬНЫЙ БЛАНК: РЕГИСТРАЦИЯ ПРАВ СОБСТВЕННОСТИ ]\n\n1. Имя и Фамилия законного владельца: \n2. Тип имущества (Дом / Бизнес): \n3. Номер или адрес имущества (Например: Дом №042): \n4. Будут ли в доме проживать сожители?:\n5. Скриншот покупки/владения домом:\n\n==================================================\n[ Скопируйте, заполните и отправьте в этот чат ]\n```"
        elif chosen == "Отдел кадров":
            blank_text = "```ini\n[ 📁 ОФИЦИАЛЬНЫЙ БЛАНК: ЗАЯВЛЕНИЕ НА ТРУДОУСТРОЙСТВО ]\n\n1. Ваши РП Имя и Фамилия: \n2. В какую фракцию подаёте заявление: \n3. На какую должность/ранг претендуете: \n4. Краткая РП-биография персонажа (2-3 предложения):\n\n==================================================\n[ Скопируйте, заполните и отправьте в этот чат ]\n```"
        elif chosen == "Судебный департамент":
            blank_text = "```ini\n[ 🏛️ ОФИЦИАЛЬНЫЙ БЛАНК: ИСКОГОВОЕ ЗАЯВЛЕНИЕ В СУД ]\n\n1. Имя Фамилия Истца (Вы): \n2. Имя Фамилия Ответчика (Нарушитель): \n3. Суть и подробное описание совершенного правонарушения: \n4. Требования к Суду: \n5. Ссылки на доказательства (видео/скриншоты):\n\n==================================================\n[ Скопируйте, заполните и отправьте в этот чат ]\n```"

        embed = discord.Embed(
            title=f"✉️ Тикет открыт: {chosen}",
            description=f"Приветствуем, {user.mention}!\n{payment_status}\n\nНиже предоставлен официальный бланк. Заполните его прямо здесь.\n\n**Для проверяющих:** нажмите кнопку «📥 Взять на рассмотрение» перед проверкой.",
            color=discord.Color.blue()
        )
        
        # Отправляем эмбед и подключаем пульт кнопок, передавая туда тип заявления
        await ticket_channel.send(embed=embed, view=TicketControlView(chosen))
        await ticket_channel.send(blank_text)
        
        # Автоматически пингуем нужную фракцию (пингующее сообщение удалится через 5 секунд для чистоты чата)
        if ping_role_id:
            await ticket_channel.send(f"<@&{ping_role_id}>, поступило новое заявление!", delete_after=5)
            
        await interaction.response.send_message(f"✅ Ваш тикет успешно создан: {ticket_channel.mention}", ephemeral=True)

class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationDropdown())
