import discord
from discord import app_commands
import random
from database import get_user_data, update_balance

def setup_economy_commands(tree: app_commands.CommandTree):

    @tree.command(name="баланс", description="Проверить свой текущий баланс денег")
    async def balance(interaction: discord.Interaction, пользователь: discord.Member = None):
        target = пользователь or interaction.user
        u_data = get_user_data(target.id)
        
        embed = discord.Embed(title=f"💰 Баланс {target.display_name}", color=discord.Color.green())
        embed.add_field(name="💵 Наличные:", value=f"${u_data['cash']}", inline=False)
        embed.add_field(name="🏦 В банке:", value=f"${u_data['bank']}", inline=False)
        embed.add_field(name="💳 Всего:", value=f"${u_data['cash'] + u_data['bank']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @tree.command(name="депозит", description="Положить наличные деньги в банк")
    async def deposit(interaction: discord.Interaction, сумма: int):
        u_data = get_user_data(interaction.user.id)
        if сумма <= 0:
            await interaction.response.send_message("❌ Сумма должна быть больше нуля!", ephemeral=True)
            return
        if u_data["cash"] < сумма:
            await interaction.response.send_message("❌ У вас нет столько наличных денег!", ephemeral=True)
            return
        
        update_balance(interaction.user.id, -сумма, "cash")
        update_balance(interaction.user.id, сумма, "bank")
        await interaction.response.send_message(f"🏦 Вы успешно положили **${сумма}** на банковский счет.")

    @tree.command(name="снять", description="Снять деньги с банковского счета")
    async def withdraw(interaction: discord.Interaction, сумма: int):
        u_data = get_user_data(interaction.user.id)
        if сумма <= 0:
            await interaction.response.send_message("❌ Сумма должна быть больше нуля!", ephemeral=True)
            return
        if u_data["bank"] < сумма:
            await interaction.response.send_message("❌ На вашем банковском счете нет столько денег!", ephemeral=True)
            return
        
        update_balance(interaction.user.id, сумма, "cash")
        update_balance(interaction.user.id, -сумма, "bank")
        await interaction.response.send_message(f"💵 Вы успешно сняли **${сумма}** наличными.")

    @tree.command(name="работа", description="Пойти на безопасную работу")
    @app_commands.checks.cooldown(1, 1800, key=lambda i: (i.user.id))
    async def work(interaction: discord.Interaction):
        reward = random.randint(150, 400)
        jobs = ["курьером", "офисным клерком", "водителем автобуса", "программистом", "автомехаником", "поваром"]
        update_balance(interaction.user.id, reward, "cash")
        await interaction.response.send_message(f"👔 Вы отработали смену **{random.choice(jobs)}** и заработали **${reward}**.")

    @tree.command(name="криминал", description="Совершить серьезное преступление (Высокий риск)")
    @app_commands.checks.cooldown(1, 10800, key=lambda i: (i.user.id))
    async def crime(interaction: discord.Interaction):
        if random.randint(1, 100) <= 55:
            fine = random.randint(500, 1000)
            update_balance(interaction.user.id, -fine, "cash")
            await interaction.response.send_message(f"🚨 Ограбление пошло не по плану! Спецназ зажал вас в углу. Суд выписал штраф **${fine}**.")
        else:
            reward = random.randint(800, 2000)
            update_balance(interaction.user.id, reward, "cash")
            await interaction.response.send_message(f"💰 Вы успешно взломали банкомат на окраине города и унесли куш в размере **${reward}**!")

    @tree.command(name="ограбить", description="Ограбить другого игрока (Украсть наличные)")
    @app_commands.checks.cooldown(1, 21600, key=lambda i: (i.user.id))
    async def rob(interaction: discord.Interaction, жертва: discord.Member):
        if  жертва.id == interaction.user.id:
            await interaction.response.send_message("❌ Вы не можете ограбить самого себя!", ephemeral=True)
            return
            
        victim_data = get_user_data(жертва.id)
        if victim_data["cash"] < 200:
            await interaction.response.send_message(f"❌ У {жертва.display_name} слишком мало наличных денег в кармане. Грабить нечего!", ephemeral=True)
            return

        if random.randint(1, 100) <= 50:
            fine = 500
            update_balance(interaction.user.id, -fine, "cash")
            update_balance(жертва.id, fine, "cash")
            await interaction.response.send_message(f"👮‍♂️ {жертва.mention} поймал вас за руку во время кражи! Вы выплатили ему компенсацию **$500**.")
        else:
            percent = random.randint(20, 50)
            stolen_amount = int(victim_data["cash"] * (percent / 100))
            
            update_balance(жертва.id, -stolen_amount, "cash")
            update_balance(interaction.user.id, stolen_amount, "cash")
            await interaction.response.send_message(f"🥷 Вы незаметно вытащили кошелек у {жертва.mention} и украли **${stolen_amount}** ({percent}% от его наличных)!")
