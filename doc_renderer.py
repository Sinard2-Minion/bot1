import discord

def build_doc_embed(target: discord.Member, u_data: dict, doc_type: str):
    if doc_type == "passport" and u_data.get("passport_data"):
        d = u_data["passport_data"]
        embed = discord.Embed(title="🪪 ГОСУДАРСТВЕННЫЙ ПАСПОРТ РФ", color=discord.Color.red())
        embed.add_field(name="👤 ФИО Гражданина:", value=f"**{d.get('РП ФИО Гражданина', 'Неизвестно')}**", inline=False)
        embed.add_field(name="📅 Дата рождения:", value=f"📅 `{d.get('Дата рождения (ДД.ММ.ГГГГ)', 'Неизвестно')}`", inline=True)
        embed.add_field(name="📍 Место жительства:", value=f"`{d.get('Место рождения / Жительства', 'Неизвестно')}`", inline=False)
        embed.add_field(name="🏛️ Кем выдан документ:", value=f"`{d.get('authority', 'УМВД')}`", inline=False)
        embed.add_field(name="📅 Дата выдачи паспорта:", value=f"`{d.get('date', '—')}`", inline=True)
        embed.add_field(name="🔢 Серия и Номер бланка:", value=f"`№{d.get('number', '—')}`", inline=True)
        embed.add_field(name="✒️ Электронная подпись инспектора:", value=f"`{d.get('signature', '—')}`", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        return embed
    
    elif doc_type == "license" and u_data.get("license_data"):
        d = u_data["license_data"]
        embed = discord.Embed(title="🚗 ВОДИТЕЛЬСКОЕ УДОСТОВЕРЕНИЕ РФ", color=discord.Color.blue())
        embed.add_field(name="👤 Водитель:", value=target.mention, inline=False)
        embed.add_field(name="🪪 Разрешенные категории:", value=f"⚙️ `{d.get('Категория транспорта', 'Неизвестно')}`", inline=True)
        embed.add_field(name="🩺 Мед. ограничения:", value=f"`{d.get('Медицинские ограничения', 'Неизвестно')}`", inline=False)
        embed.add_field(name="🏢 Кем выданы права:", value=f"`{d.get('authority', 'МРЭО ГАИ')}`", inline=False)
        embed.add_field(name="📅 Срок действия от:", value=f"`{d.get('date', '—')}`", inline=True)
        embed.add_field(name="🔢 Номер удостоверения:", value=f"`№{d.get('number', '—')}`", inline=True)
        embed.add_field(name="✒️ Подпись начальника МРЭО:", value=f"`{d.get('signature', '—')}`", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        return embed

    elif doc_type == "med" and u_data.get("med_exam"):
        d = u_data["med_exam"]
        embed = discord.Embed(title="🩺 МЕДИЦИНСКАЯ КАРТА ШТАТА", color=discord.Color.green())
        embed.add_field(name="👤 Пациент:", value=target.mention, inline=False)
        embed.add_field(name="📊 РП-Заключение врача:", value=f"**{d.get('info', 'Годен')}**", inline=False)
        embed.add_field(name="🏥 Медицинское учреждение:", value=f"`{d.get('authority', 'МЗ Штата')}`", inline=False)
        embed.add_field(name="📅 Осмотр от:", value=f"`{d.get('date', '—')}`", inline=True)
        embed.add_field(name="🔢 Номер медкарта:", value=f"`№{d.get('number', '—')}`", inline=True)
        embed.add_field(name="✒️ Личная подпись главврача:", value=f"`{d.get('signature', '—')}`", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        return embed
    return None
