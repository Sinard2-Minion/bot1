import discord
from database import get_user_data, update_balance, check_medical_status
from ticket_config import CATEGORIES
from ticket_views import TicketControlView, send_audit_log

class ApplicationModal(discord.ui.Modal):
    def __init__(self, ticket_type: str, med_checked: bool = False):
        super().__init__(title=ticket_type[:45])
        self.ticket_type = ticket_type
        self.med_checked = med_checked
        self.fields_inputs = {}

        self.rp_name = discord.ui.TextInput(label="Ваш РП ник (Имя_Фамилия)", placeholder="M1lton_James", required=True, max_length=50)
        self.add_item(self.rp_name)

        cfg = CATEGORIES.get(ticket_type)
        if cfg and "fields" in cfg:
            for idx, f_cfg in enumerate(cfg["fields"]):
                # Если это поле медосмотра и мы его уже проверили кодом, пропускаем создание этого поля ввода
                if "медицинский осмотр" in f_cfg["label"].lower():
                    continue
                style = discord.TextStyle.paragraph if f_cfg["style"] == "paragraph" else discord.TextStyle.short
                input_item = discord.ui.TextInput(label=f_cfg["label"][:45], placeholder=f_cfg["placeholder"][:100], style=style, required=f_cfg["required"])
                self.fields_inputs[f"field_{idx}"] = input_item
                self.add_item(input_item)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        cfg = CATEGORIES.get(self.ticket_type)

        if self.ticket_type == "Смена фамилии":
            u_data = get_user_data(user.id)
            if u_data["cash"] < 1000:
                await interaction.response.send_message("❌ Недостаточно денег для пошлины ($1,000)!", ephemeral=True)
                return
            update_balance(user.id, -1000, "cash")
            pay_status = "✅ Гос. пошлина ($1,000) успешно списана!"
        else:
            pay_status = "🆓 Бесплатная подача заявления."

        await interaction.response.send_message(f"⌛ Создаем ваше заявление в системе...", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ping_role_id = cfg["role_id"] if cfg else None
        if ping_role_id:
            role_obj = guild.get_role(ping_role_id)
            if role_obj: overwrites[role_obj] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(name=f"заявление-{user.name}", overwrites=overwrites)

        embed = discord.Embed(title=f"📋 НОВОЕ ЗАЯВЛЕНИЕ: {self.ticket_type.upper()}", color=discord.Color.blue())
        embed.add_field(name="👤 Автор заявления:", value=user.mention, inline=True)
        embed.add_field(name="🎭 РП Никнейм персонажа:", value=f"**{self.rp_name.value}**", inline=False)

        for _, input_item in self.fields_inputs.items():
            embed.add_field(name=f"📝 {input_item.label}:", value=input_item.value or "*Не заполнено*", inline=False)

        # Выводим автоматический статус верификации от врача
        if self.ticket_type == "Лицензия":
            med_status_text = "🟢 Пройден (Электронная справка заверена врачом в базе данных)" if self.med_checked else "⚠️ Проверен"
            embed.add_field(name="🩺 Медицинский осмотр:", value=med_status_text, inline=False)

        embed.add_field(name="💳 Оплата:", value=pay_status, inline=False)

        await ticket_channel.send(embed=embed, view=TicketControlView(self.ticket_type, user.id))
        if ping_role_id: await ticket_channel.send(f"<@&{ping_role_id}>, новое заявление!", delete_after=5)
        await send_audit_log(guild, "✉️ Открыт новый РП-тикет", f"**Пользователь:** {user.mention}\n**Категория:** {self.ticket_type}\n**Канал:** {ticket_channel.mention}", discord.Color.blue())

class ApplicationDropdown(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=n, description=c["description"][:100], emoji=c["emoji"]) for n, c in CATEGORIES.items()]
        super().__init__(placeholder="Выберите необходимый тип заявления...", min_values=1, max_values=1, options=options, custom_id="app_dropdown")

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values
        user = interaction.user

        # Если игрок выбирает Лицензию — бот жестко сверяет справку с базой данных медиков
        if chosen == "Лицензия":
            has_med_pass = check_medical_status(user.id)
            if not has_med_pass:
                await interaction.response.send_message(
                    "❌ **ОТКАЗ В ДОСТУПЕ:** Вы не можете подать на лицензию! Ваша медицинская карта пуста. "
                    "Пройдите медицинский осмотр у сотрудников больницы, чтобы врач внёс вас в электронный реестр.", 
                    ephemeral=True
                )
                return
            
            # Если медосмотр пройден, открываем анкету, передав статус True
            modal = ApplicationModal(chosen, med_checked=True)
        else:
            modal = ApplicationModal(chosen, med_checked=False)

        await interaction.response.send_modal(modal)

class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ApplicationDropdown())
