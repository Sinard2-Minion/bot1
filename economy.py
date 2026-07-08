import discord
from discord import app_commands
from database import get_user_data, update_balance

ADMIN_ROLE_ID = 1524372208791851191

def is_admin_check(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    return bool(role and role in interaction.user.roles)

async def give_money_to_role_logic(guild: discord.Guild, role: discord.Role, amount: int, mode: str = "cash") -> int:
    counter = 0
    for member in role.members:
        if member.bot: continue
        u_data = get_user_data(member.id)
        if mode == "cash":
            new_cash = u_data["cash"] + amount
            update_balance(member.id, new_cash, u_data["bank"])
        else:
            new_bank = u_data["bank"] + amount
            update_balance(member.id, u_data["cash"], new_bank)
        counter += 1
    return counter

def setup_economy_commands(tree: app_commands.CommandTree):
    
    @tree.command(name="выдать_роли", description="[Админ] Выдать деньги всем участникам с определенной ролью")
    @app_commands.choices(тип_счета=[
        app_commands.Choice(name="💵 Наличные", value="cash"),
        app_commands.Choice(name="🏦 Банковский счет", value="bank")
    ])
    async def give_money_to_role_slash(interaction: discord.Interaction, роль: discord.Role, сумма: int, тип_счета: app_commands.Choice[str]):
        if not is_admin_check(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        if сумма <= 0:
            await interaction.followup.send("❌ Сумма должна быть больше нуля!", ephemeral=True)
            return
        guild = interaction.guild
        mode = тип_счета.value
        total_payed = await give_money_to_role_logic(guild, роль, сумма, mode)
        account_name = "наличные" if mode == "cash" else "банковский счет"
        
        if total_payed == 0:
            await interaction.followup.send(f"⚠️ У роли {роль.mention} нет участников, деньги никому не начислены.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🏛️ ГОСУДАРСТВЕННОЕ ФИНАНСИРОВАНИЕ",
            description=(
                f"Правительство г. Адреналин произвело массовую выплату средств!\n\n"
                f"👥 **Ведомство/Роль:** {роль.mention}\n"
                f"💵 **Сумма на человека:** `${сумма:,}`\n"
                f"🏦 **Куда зачислено:** `{account_name}`\n"
                f"📊 **Всего сотрудников получило:** `{total_payed}`"
            ),
            color=discord.Color.green()
        )
        embed.set_timestamp()
        await interaction.channel.send(embed=embed)
        await interaction.followup.send(f"✅ Успешно начислено по ${сумма:,} для {total_payed} участников роли {роль.name}!", ephemeral=True)

    @tree.command(name="выдать_деньги", description="[Админ] Выдать РП-деньги конкретному пользователю")
    @app_commands.choices(тип_счета=[
        app_commands.Choice(name="💵 Наличные", value="cash"),
        app_commands.Choice(name="🏦 Банковский счет", value="bank")
    ])
    async def give_money_slash(interaction: discord.Interaction, пользователь: discord.Member, сумма: int, тип_счета: app_commands.Choice[str]):
        if not is_admin_check(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        if сумма <= 0:
            await interaction.followup.send("❌ Сумма должна быть больше нуля!", ephemeral=True)
            return
            
        u_data = get_user_data(пользователь.id)
        mode = тип_счета.value
        
        if mode == "cash":
            new_cash = u_data["cash"] + сумма
            update_balance(пользователь.id, new_cash, u_data["bank"])
            msg = f"🟩 Администратор выдал **${сумма:,}** наличными игроку {пользователь.mention}!"
        else:
            new_bank = u_data["bank"] + сумма
            update_balance(пользователь.id, u_data["cash"], new_bank)
            msg = f"🟩 Администратор начислил **${сумма:,}** на банковский счет игрока {пользователь.mention}!"
            
        await interaction.channel.send(msg)
        await interaction.followup.send("✅ Баланс игрока успешно обновлен!", ephemeral=True)
