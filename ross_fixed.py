import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime
import json
import os
import asyncio

# =========================================================
# AYARLAR
# =========================================================

TOKEN = "MTQyNzQ5MDcxMTU3MzYyNzAwMw.GRYzpb.CBI3khkxPtHLxbmILi_pXpGBMLK9Maja9KIzys"

GUILD_ID = 1427287350819422250
BASVURU_KANAL_ID = 1530821294575059020
BASVURU_DURUM_KANAL_ID = 1473385679659597954
BASVURU_LOG_KANAL_ID = 1530821341597663372
TICKET_KATEGORI_ID = 1530821224547221604
TICKET_LOG_KATEGORI_ID = 1530821645529387079

STAFF_ROLE_ID = 1530821833631469720
INTERVIEW_ROLE_ID = 1530822478879002624

DM_YETKILI_ROLE_ID = 1530821833631469720
KATILAN_LOG_CHANNEL_ID = 1473387310640005261

# Mazeret sistemi
MAZERET_PANEL_CHANNEL_ID = 1530823048033210438
MAZERET_BASVURU_CHANNEL_ID = 1530823495787745360
MAZERET_LOG_CHANNEL_ID = 1530823495787745360
MAZERET_YETKILI_ROLE_ID = 1530821833631469720

MAZERET_ROLE_1 = 1530822602602315887
MAZERET_ROLE_2 = 1530822614619258950
MAZERET_ROLE_3 = 1530822619547439164
MAZERET_ROLE_4 = 1530822623733219399
MAZERET_ROLE_5 = 1530822633128464416
MAZERET_ROLE_6 = 1530822635867340911
MAZERET_ROLE_7 = 1530822636953669734

# Dosyalar
PANEL_FILE = "panel.json"
BASVURU_DURUM_FILE = "basvuru_durum.json"
KATIL_LOG_FILE = "katil_log.json"
MAZERET_DB_FILE = "mazeret_db.json"
BASVURU_FILE = "basvuru.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================================================
# JSON YARDIMCI
# =========================================================

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

panel_data = load_json(PANEL_FILE, {})
basvuru_durum = load_json(BASVURU_DURUM_FILE, {"acik": True})
katil_log_data = load_json(KATIL_LOG_FILE, {"event_id": 0, "katilanlar": [], "mesaj_id": None})
basvurular = load_json(BASVURU_FILE,{})

mazeret_db = load_json(MAZERET_DB_FILE, {
    "applications": [],
    "active_permits": [],
    "panel_message_id": None
})

MAZERET_ROLE_MAP = {
    1: MAZERET_ROLE_1,
    2: MAZERET_ROLE_2,
    3: MAZERET_ROLE_3,
    4: MAZERET_ROLE_4,
    5: MAZERET_ROLE_5,
    6: MAZERET_ROLE_6,
    7: MAZERET_ROLE_7,
}

def save_mazeret_db():
    save_json(MAZERET_DB_FILE, mazeret_db)

def generate_mazeret_id(prefix="mz"):
    return f"{prefix}_{int(datetime.now().timestamp())}_{os.urandom(3).hex()}"

def format_dt(ts: int):
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M:%S")

def has_role(member: discord.Member, role_id: int) -> bool:
    return any(r.id == role_id for r in member.roles)

def get_pending_mazeret(user_id: int):
    for app in mazeret_db["applications"]:
        if app["user_id"] == user_id and app["status"] == "pending":
            return app
    return None

def get_active_mazeret(user_id: int):
    for permit in mazeret_db["active_permits"]:
        if permit["user_id"] == user_id:
            return permit
    return None

async def send_mazeret_log(guild: discord.Guild, embed: discord.Embed):
    kanal = guild.get_channel(MAZERET_LOG_CHANNEL_ID)
    if kanal:
        await kanal.send(embed=embed)

# =========================================================
# EMBEDLER
# =========================================================

def create_panel_embed():
    durum_text = "🟢 **Başvurular Açık**" if basvuru_durum["acik"] else "🔴 **Başvurular Kapalı**"
    embed = discord.Embed(
        title="📝 Ekip Başvurusu",
        description=f"{durum_text}\n\nBaşvuru yapmak için butona basın.",
        color=discord.Color.green() if basvuru_durum["acik"] else discord.Color.red()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1526155847909249054/1530838566253494272/1317.gif")
    return embed

def create_mazeret_panel_embed():
    embed = discord.Embed(
        title="📌 Mazeret Bildirim Sistemi",
        description=(
            "Mazeret bildirmek için aşağıdaki butona bas.\n\n"
        ),
        color=discord.Color.orange()
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1526155847909249054/1530838566253494272/1317.gif")
    return embed

# =========================================================
# KATIL VIEW
# =========================================================

class KatilView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Katıl", style=discord.ButtonStyle.success, custom_id="katil_button")
    async def katil(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        guild = bot.get_guild(GUILD_ID)
        if not guild:
            return await interaction.followup.send("Sunucu bulunamadı.", ephemeral=True)

        try:
            member = guild.get_member(interaction.user.id) or await guild.fetch_member(interaction.user.id)
        except Exception:
            return await interaction.followup.send("Sunucuda bulunamadın.", ephemeral=True)

        if member.id in katil_log_data["katilanlar"]:
            return await interaction.followup.send("Bu turda zaten katıldın 👍", ephemeral=True)

        log_channel = guild.get_channel(KATILAN_LOG_CHANNEL_ID)
        if not log_channel:
            return await interaction.followup.send("Katılım log kanalı bulunamadı.", ephemeral=True)

        mesaj_id = katil_log_data.get("mesaj_id")

        if mesaj_id:
            try:
                mesaj = await log_channel.fetch_message(mesaj_id)
                desc = mesaj.embeds[0].description if mesaj.embeds else ""
                new_embed = discord.Embed(
                    title=f"📋 Katılanlar Listesi • Tur {katil_log_data['event_id']}",
                    description=(desc or "") + f"{member.mention} (`{member.id}`)\n",
                    color=discord.Color.green()
                )
                await mesaj.edit(embed=new_embed)
            except Exception:
                mesaj_id = None

        if not mesaj_id:
            embed = discord.Embed(
                title=f"📋 Katılanlar Listesi • Tur {katil_log_data['event_id']}",
                description=f"{member.mention} (`{member.id}`)\n",
                color=discord.Color.green()
            )
            mesaj = await log_channel.send(embed=embed)
            katil_log_data["mesaj_id"] = mesaj.id

        katil_log_data["katilanlar"].append(member.id)
        save_json(KATIL_LOG_FILE, katil_log_data)

        await interaction.followup.send("Katılımın kaydedildi ✅", ephemeral=True)

# =========================================================
# ROLDM
# =========================================================

@bot.command()
async def roldm(ctx, role: discord.Role, *, mesaj):
    if not has_role(ctx.author, DM_YETKILI_ROLE_ID):
        return await ctx.send("Yetkin yok.")

    katil_log_data["event_id"] += 1
    katil_log_data["katilanlar"] = []
    katil_log_data["mesaj_id"] = None
    save_json(KATIL_LOG_FILE, katil_log_data)

    CONCURRENCY = 3
    PER_DM_SLEEP = 1.5
    RETRY_SLEEP = 3.0

    sem = asyncio.Semaphore(CONCURRENCY)

    ok = 0
    forbidden = 0
    failed = 0
    total = len(role.members)

    progress_msg = await ctx.send(f"📨 DM gönderimi başladı: 0/{total}")

    async def send_one(member: discord.Member):
        nonlocal ok, forbidden, failed
        async with sem:
            try:
                await member.send(mesaj, view=KatilView())
                ok += 1
                await asyncio.sleep(PER_DM_SLEEP)
            except discord.Forbidden:
                forbidden += 1
            except discord.HTTPException:
                failed += 1
                await asyncio.sleep(RETRY_SLEEP)

    tasks = [asyncio.create_task(send_one(m)) for m in role.members]
    await asyncio.gather(*tasks)

    await progress_msg.edit(
        content=(
            f"✅ DM gönderimi bitti.\n"
            f"Rol: **{role.name}**\n"
            f"Toplam: **{total}**\n"
            f"✅ Gönderildi: **{ok}**\n"
            f"🚫 DM kapalı/engel: **{forbidden}**\n"
            f"⚠️ Diğer hata: **{failed}**"
        )
    )

# =========================================================
# BAŞVURU RED MODAL
# =========================================================

class RedModal(Modal, title="Başvuru Red Sebebi"):
    sebep = TextInput(label="Red Sebebi", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, member, channel):
        super().__init__()
        self.member = member
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild

        await self.channel.send(
            embed=discord.Embed(
                title="❌ Başvuru Reddedildi",
                description=f"Sebep:\n{self.sebep.value}",
                color=discord.Color.red()
            )
        )

        durum = guild.get_channel(BASVURU_DURUM_KANAL_ID)
        if durum and self.member:
            await durum.send(f"{self.member.mention} Başvuru Reddedildi ❌")

        log = guild.get_channel(BASVURU_LOG_KANAL_ID)
        if log and self.member:
            embed = discord.Embed(
                title="❌ Başvuru Reddedildi",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Kullanıcı", value=self.member.mention, inline=False)
            embed.add_field(name="Reddeden", value=interaction.user.mention, inline=False)
            embed.add_field(name="Sebep", value=self.sebep.value, inline=False)
            await log.send(embed=embed)

        await interaction.response.send_message("Başvuru reddedildi.", ephemeral=True)

# =========================================================
# BAŞVURU KARAR VIEW
# =========================================================

class KararView(View):
    def __init__(self, applicant_id=None, channel_id=None):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.channel_id = channel_id

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, custom_id="approve_button")
    async def approve(self, interaction: discord.Interaction, button: Button):
        if not has_role(interaction.user, STAFF_ROLE_ID):
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)

        guild = interaction.guild
        channel = interaction.channel
        applicant_id = self.applicant_id

        if applicant_id is None:
            if channel.topic and channel.topic.isdigit():
                applicant_id = int(channel.topic)
            else:
                return await interaction.response.send_message("Başvuru verisi bulunamadı.", ephemeral=True)

        if interaction.user.id == applicant_id:
            return await interaction.response.send_message("Kendi başvurunu onaylayamazsın.", ephemeral=True)

        member = guild.get_member(applicant_id)
        if not member:
            return await interaction.response.send_message("Başvuru sahibi bulunamadı.", ephemeral=True)

        interview_role = guild.get_role(INTERVIEW_ROLE_ID)
        if interview_role:
            await member.add_roles(interview_role)

        log_category = guild.get_channel(TICKET_LOG_KATEGORI_ID)
        if log_category:
            await channel.edit(category=log_category)

        durum = guild.get_channel(BASVURU_DURUM_KANAL_ID)
        if durum:
            await durum.send(
                f"{member.mention} Başvurun Onaylandı ✅ "
                f"<#1473393756442071333> kanalına geçiş yap."
            )

        log = guild.get_channel(BASVURU_LOG_KANAL_ID)
        if log:
            embed = discord.Embed(
                title="✅ Başvuru Onaylandı",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Kullanıcı", value=member.mention, inline=False)
            embed.add_field(name="Onaylayan", value=interaction.user.mention, inline=False)
            await log.send(embed=embed)

        await interaction.response.send_message("Onaylandı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, custom_id="reject_button")
    async def reject(self, interaction: discord.Interaction, button: Button):
        if not has_role(interaction.user, STAFF_ROLE_ID):
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)

        guild = interaction.guild
        channel = interaction.channel
        applicant_id = self.applicant_id

        if applicant_id is None:
            if channel.topic and channel.topic.isdigit():
                applicant_id = int(channel.topic)
            else:
                return await interaction.response.send_message("Başvuru verisi bulunamadı.", ephemeral=True)

        if interaction.user.id == applicant_id:
            return await interaction.response.send_message("Kendi başvurunu reddedemezsin.", ephemeral=True)

        member = guild.get_member(applicant_id)
        if not member:
            return await interaction.response.send_message("Başvuru sahibi bulunamadı.", ephemeral=True)

        await interaction.response.send_modal(RedModal(member, channel))

    @discord.ui.button(label="Kanalı Sil", style=discord.ButtonStyle.secondary, custom_id="delete_channel_button")
    async def delete_channel(self, interaction: discord.Interaction, button: Button):
        if not has_role(interaction.user, STAFF_ROLE_ID):
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)

        guild = interaction.guild
        channel = interaction.channel

        applicant_id = self.applicant_id
        if applicant_id is None and channel.topic and channel.topic.isdigit():
            applicant_id = int(channel.topic)

        member = guild.get_member(applicant_id) if applicant_id else None

        log = guild.get_channel(BASVURU_LOG_KANAL_ID)
        if log:
            embed = discord.Embed(
                title="🗑 Başvuru Kanalı Silindi",
                color=discord.Color.dark_gray(),
                timestamp=datetime.now()
            )
            if member:
                embed.add_field(name="Başvuru Sahibi", value=f"{member.mention} (`{member.id}`)", inline=False)
            embed.add_field(name="Silen Yetkili", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            embed.add_field(name="Kanal", value=channel.name, inline=False)
            await log.send(embed=embed)

        await interaction.response.send_message("Kanal siliniyor...", ephemeral=True)
        await channel.delete(reason=f"Başvuru kapatıldı • {interaction.user}")

# =========================================================
# BAŞVURU VIEW
# =========================================================

class BasvuruView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Başvuru Yap", style=discord.ButtonStyle.primary, custom_id="basvuru_button")
    async def basvuru(self, interaction: discord.Interaction, button: Button):
        if not basvuru_durum["acik"]:
            return await interaction.response.send_message("❌ Başvurular şu anda kapalı.", ephemeral=True)

        user_id=str(interaction.user.id)
        if user_id in basvurular:
            return await interaction.response.send_message("❌ Zaten açık bir başvurunuz bulunmaktadır.",ephemeral=True)
        if get_pending_mazeret(interaction.user.id):
            return await interaction.response.send_message("❌ Bekleyen mazeret başvurunuz bulunmaktadır.",ephemeral=True)
        if get_active_mazeret(interaction.user.id):
            return await interaction.response.send_message("❌ Aktif mazeretiniz bulunduğu için başvuru yapamazsınız.",ephemeral=True)

        guild = interaction.guild
        kategori = guild.get_channel(TICKET_KATEGORI_ID)
        if not kategori:
            return await interaction.response.send_message("Ticket kategorisi bulunamadı.", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ekip-basvuru-{interaction.user.name}".lower().replace(" ", "-"),
            category=kategori,
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )

        basvurular[user_id]={"channel_id": channel.id}
        save_json(BASVURU_FILE, basvurular)

        embed = discord.Embed(
            title="📩 Ekip Başvuru Formu",
            description="Aşağıdaki soruları eksiksiz doldurunuz.",
            color=discord.Color.blue()
        )

        sorular = (
            "👤 **İsim :**\n"
            "🎂 **Yaş :**\n"
            "⏱ **Fivem Saat :**\n"
            "🔗 **Steam Profil Linki :**\n"
            "🗺 **Map Bilgisi :**\n"
            "👥 **Oynadığın Ekipler :**\n"
            "📊 **Ne Kadar Aktiflik Gosterebilirsin :**"
        )

        await channel.send(content=interaction.user.mention, embed=embed)
        await channel.send(sorular)
        await channel.send(
            "Yetkililer inceleyince aşağıdan işlem yapacaktır.",
            view=KararView(interaction.user.id, channel.id)
        )

        await interaction.response.send_message(f"Başvurun oluşturuldu: {channel.mention}", ephemeral=True)

# =========================================================
# BAŞVURU AÇ / KAPAT
# =========================================================

@bot.command()
async def basvurukapat(ctx):
    if not has_role(ctx.author, STAFF_ROLE_ID):
        return await ctx.send("Yetkin yok.")

    basvuru_durum["acik"] = False
    save_json(BASVURU_DURUM_FILE, basvuru_durum)

    kanal = bot.get_channel(BASVURU_KANAL_ID)
    mesaj_id = panel_data.get("panel_message_id")
    if kanal and mesaj_id:
        try:
            mesaj = await kanal.fetch_message(mesaj_id)
            await mesaj.edit(embed=create_panel_embed(), view=BasvuruView())
        except Exception:
            pass

    await ctx.send("🔒 Başvurular kapatıldı.")

@bot.command()
async def basvuruac(ctx):
    if not has_role(ctx.author, STAFF_ROLE_ID):
        return await ctx.send("Yetkin yok.")

    basvuru_durum["acik"] = True
    save_json(BASVURU_DURUM_FILE, basvuru_durum)

    kanal = bot.get_channel(BASVURU_KANAL_ID)
    mesaj_id = panel_data.get("panel_message_id")
    if kanal and mesaj_id:
        try:
            mesaj = await kanal.fetch_message(mesaj_id)
            await mesaj.edit(embed=create_panel_embed(), view=BasvuruView())
        except Exception:
            pass

    await ctx.send("🔓 Başvurular açıldı.")

# =========================================================
# TIK SİSTEMİ
# =========================================================

tik_events = {}

class TikView(View):
    def __init__(self, event_id, limit):
        super().__init__(timeout=None)
        self.event_id = event_id
        self.limit = limit

    async def update_embed(self, interaction: discord.Interaction):
        data = tik_events[self.event_id]
        mentions = "\n".join(f"<@{u}> (`{u}`)" for u in data["users"]) or "Henüz katılan yok"

        if self.limit is None:
            limit_text = f"{len(data['users'])}/Sınırsız"
        else:
            limit_text = f"{len(data['users'])}/{self.limit}"

        embed = discord.Embed(
            title=f"📋 {data['name']}",
            description=f"**Kontenjan:** {limit_text}\n\n{mentions}",
            color=discord.Color.green()
        )
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Katıl", style=discord.ButtonStyle.success, custom_id="tik_katil")
    async def join(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        data = tik_events[self.event_id]

        if interaction.user.id in data["users"]:
            return await interaction.followup.send("Zaten katıldın.", ephemeral=True)

        if self.limit is not None and len(data["users"]) >= self.limit:
            return await interaction.followup.send("Kontenjan dolu.", ephemeral=True)

        data["users"].append(interaction.user.id)
        await self.update_embed(interaction)
        await interaction.followup.send("Katıldın ✅", ephemeral=True)

    @discord.ui.button(label="Ayrıl", style=discord.ButtonStyle.danger, custom_id="tik_ayril")
    async def leave(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        data = tik_events[self.event_id]

        if interaction.user.id not in data["users"]:
            return await interaction.followup.send("Zaten katılı değilsin.", ephemeral=True)

        data["users"].remove(interaction.user.id)
        await self.update_embed(interaction)
        await interaction.followup.send("Ayrıldın ❌", ephemeral=True)

@bot.command()
async def tik(ctx, *, text):
    parts = text.split()

    limit = None
    if parts and parts[-1].isdigit():
        limit = int(parts[-1])
        name = " ".join(parts[:-1]).strip()
    else:
        name = text.strip()

    if not name:
        return await ctx.send("Etkinlik adı yazman gerekiyor.")

    event_id = int(datetime.now().timestamp())

    tik_events[event_id] = {
        "name": name,
        "users": []
    }

    limit_text = "0/Sınırsız" if limit is None else f"0/{limit}"

    embed = discord.Embed(
        title=f"📋 {name}",
        description=f"**Kontenjan:** {limit_text}\n\nHenüz katılan yok",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed, view=TikView(event_id, limit))

# =========================================================
# MAZERET SİSTEMİ
# =========================================================

mazeret_temp_data = {}

class MazeretModal(Modal, title="Mazeret Sebebi"):
    sebep = TextInput(
        label="Mazeret sebebin",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
        placeholder="Örn: sağlık, ailevi durum, şehir dışı..."
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        if get_pending_mazeret(user_id):
            return await interaction.response.send_message(
                "Zaten bekleyen bir mazeret başvurun var.",
                ephemeral=True
            )

        if get_active_mazeret(user_id):
            return await interaction.response.send_message(
                "Zaten aktif bir mazeretin var.",
                ephemeral=True
            )

        mazeret_temp_data[user_id] = {
            "reason": self.sebep.value
        }

        await interaction.response.send_message(
            "Sebebin alındı. Şimdi kaç gün mazeret istediğini seç.",
            ephemeral=True,
            view=MazeretGunSelectView(user_id)
        )

class MazeretGunSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        options = [discord.SelectOption(label=f"{i} Gün", value=str(i)) for i in range(1, 8)]
        super().__init__(
            placeholder="Kaç gün mazeret istiyorsun?",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"mazeret_day_select_{owner_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("Bu seçim sana ait değil.", ephemeral=True)

        temp = mazeret_temp_data.get(interaction.user.id)
        if not temp:
            return await interaction.response.send_message(
                "Geçici başvuru verisi bulunamadı. Tekrar dene.",
                ephemeral=True
            )

        days = int(self.values[0])
        reason = temp["reason"]
        role_id = MAZERET_ROLE_MAP.get(days)

        if not role_id:
            return await interaction.response.send_message(
                "Bu gün için mazeret rolü ayarlanmamış.",
                ephemeral=True
            )

        app_id = generate_mazeret_id("app")
        app = {
            "id": app_id,
            "user_id": interaction.user.id,
            "guild_id": interaction.guild.id,
            "reason": reason,
            "days": days,
            "role_id": role_id,
            "status": "pending",
            "created_at": int(datetime.now().timestamp()),
            "reviewed_by": None,
            "reviewed_at": None
        }

        mazeret_db["applications"].append(app)
        save_mazeret_db()
        mazeret_temp_data.pop(interaction.user.id, None)

        basvuru_kanal = interaction.guild.get_channel(MAZERET_BASVURU_CHANNEL_ID)
        if not basvuru_kanal:
            return await interaction.response.send_message("Mazeret başvuru kanalı bulunamadı.", ephemeral=True)

        embed = discord.Embed(
            title="🟡 Yeni Mazeret Başvurusu",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Başvuru ID", value=app["id"], inline=False)
        embed.add_field(name="Kullanıcı", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="Sebep", value=reason, inline=False)
        embed.add_field(name="Süre", value=f"{days} gün", inline=False)
        embed.add_field(name="Durum", value="Beklemede", inline=False)

        await basvuru_kanal.send(
            content=f"<@&{MAZERET_YETKILI_ROLE_ID}> yeni mazeret başvurusu geldi.",
            embed=embed,
            view=MazeretKararView(app["id"])
        )

        await interaction.response.edit_message(
            content="Başvurun başarıyla gönderildi. Yetkili onayı bekleniyor.",
            view=None
        )

class MazeretGunSelectView(View):
    def __init__(self, owner_id):
        super().__init__(timeout=300)
        self.add_item(MazeretGunSelect(owner_id))

class MazeretRedModal(Modal, title="Mazeret Red Sebebi"):
    sebep = TextInput(
        label="Red sebebi",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(self, app_id):
        super().__init__()
        self.app_id = app_id

    async def on_submit(self, interaction: discord.Interaction):
        app = next((a for a in mazeret_db["applications"] if a["id"] == self.app_id), None)
        if not app:
            return await interaction.response.send_message("Başvuru bulunamadı.", ephemeral=True)

        if app["status"] != "pending":
            return await interaction.response.send_message("Bu başvuru zaten işlenmiş.", ephemeral=True)

        app["status"] = "rejected"
        app["reviewed_by"] = interaction.user.id
        app["reviewed_at"] = int(datetime.now().timestamp())
        app["reject_reason"] = self.sebep.value
        save_mazeret_db()

        embed = discord.Embed(
            title="❌ Mazeret Başvurusu Reddedildi",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Kullanıcı", value=f"<@{app['user_id']}>", inline=False)
        embed.add_field(name="Reddeden", value=interaction.user.mention, inline=False)
        embed.add_field(name="Sebep", value=app["reason"], inline=False)
        embed.add_field(name="Süre", value=f"{app['days']} gün", inline=False)
        embed.add_field(name="Red Nedeni", value=self.sebep.value, inline=False)

        await send_mazeret_log(interaction.guild, embed)
        await interaction.response.send_message("Başvuru reddedildi.", ephemeral=True)

class MazeretKararView(View):
    def __init__(self, app_id=None):
        super().__init__(timeout=None)
        self.app_id = app_id

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, custom_id="mazeret_approve_button")
    async def approve(self, interaction: discord.Interaction, button: Button):
        if not has_role(interaction.user, MAZERET_YETKILI_ROLE_ID):
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)

        app_id = self.app_id
        if app_id is None and interaction.message.embeds:
            for field in interaction.message.embeds[0].fields:
                if field.name == "Başvuru ID":
                    app_id = field.value
                    break

        app = next((a for a in mazeret_db["applications"] if a["id"] == app_id), None)
        if not app:
            return await interaction.response.send_message("Başvuru bulunamadı.", ephemeral=True)

        if app["status"] != "pending":
            return await interaction.response.send_message("Bu başvuru zaten işlenmiş.", ephemeral=True)

        guild = interaction.guild
        member = guild.get_member(app["user_id"])
        if not member:
            return await interaction.response.send_message("Kullanıcı sunucuda bulunamadı.", ephemeral=True)

        current_role_ids = [r.id for r in member.roles]
        old_roles = [rid for rid in MAZERET_ROLE_MAP.values() if rid in current_role_ids]
        for rid in old_roles:
            role = guild.get_role(rid)
            if role:
                try:
                    await member.remove_roles(role)
                except Exception:
                    pass

        role = guild.get_role(app["role_id"])
        if not role:
            return await interaction.response.send_message("Verilecek mazeret rolü bulunamadı.", ephemeral=True)

        await member.add_roles(role)

        expire_at = int(datetime.now().timestamp()) + (app["days"] * 86400)

        app["status"] = "approved"
        app["reviewed_by"] = interaction.user.id
        app["reviewed_at"] = int(datetime.now().timestamp())
        app["expire_at"] = expire_at

        mazeret_db["active_permits"].append({
            "application_id": app["id"],
            "guild_id": guild.id,
            "user_id": member.id,
            "role_id": role.id,
            "reason": app["reason"],
            "days": app["days"],
            "approved_by": interaction.user.id,
            "approved_at": int(datetime.now().timestamp()),
            "expire_at": expire_at
        })

        save_mazeret_db()

        embed = discord.Embed(
            title="✅ Mazeret Başvurusu Onaylandı",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Kullanıcı", value=member.mention, inline=False)
        embed.add_field(name="Onaylayan", value=interaction.user.mention, inline=False)
        embed.add_field(name="Sebep", value=app["reason"], inline=False)
        embed.add_field(name="Süre", value=f"{app['days']} gün", inline=False)
        embed.add_field(name="Bitiş", value=format_dt(expire_at), inline=False)
        embed.add_field(name="Rol", value=role.mention, inline=False)

        await send_mazeret_log(guild, embed)
        await interaction.response.edit_message(content="Başvuru onaylandı.", embed=embed, view=None)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, custom_id="mazeret_reject_button")
    async def reject(self, interaction: discord.Interaction, button: Button):
        if not has_role(interaction.user, MAZERET_YETKILI_ROLE_ID):
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)

        app_id = self.app_id
        if app_id is None and interaction.message.embeds:
            for field in interaction.message.embeds[0].fields:
                if field.name == "Başvuru ID":
                    app_id = field.value
                    break

        await interaction.response.send_modal(MazeretRedModal(app_id))

class MazeretPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Mazeret Bildir", style=discord.ButtonStyle.primary, custom_id="mazeret_panel_button")
    async def mazeret_bildir(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(MazeretModal())

async def mazeret_sure_kontrol_loop():
    await bot.wait_until_ready()

    while not bot.is_closed():
        now_ts = int(datetime.now().timestamp())
        degisti = False

        for permit in mazeret_db["active_permits"][:]:
            if permit["expire_at"] <= now_ts:
                guild = bot.get_guild(permit["guild_id"])
                if guild:
                    member = guild.get_member(permit["user_id"])
                    role = guild.get_role(permit["role_id"])

                    if member and role and role in member.roles:
                        try:
                            await member.remove_roles(role)
                        except Exception:
                            pass

                    embed = discord.Embed(
                        title="⏰ Mazeret Süresi Sona Erdi",
                        color=discord.Color.dark_gray(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Kullanıcı", value=f"<@{permit['user_id']}>", inline=False)
                    embed.add_field(name="Rol", value=f"<@&{permit['role_id']}>", inline=False)
                    embed.add_field(name="Sebep", value=permit["reason"], inline=False)
                    embed.add_field(name="Süre", value=f"{permit['days']} gün", inline=False)

                    await send_mazeret_log(guild, embed)

                mazeret_db["active_permits"].remove(permit)
                degisti = True

        if degisti:
            save_mazeret_db()

        await asyncio.sleep(60)

@bot.command()
async def mazeretpanel(ctx):
    if not has_role(ctx.author, STAFF_ROLE_ID):
        return await ctx.send("Yetkin yok.")

    kanal = bot.get_channel(MAZERET_PANEL_CHANNEL_ID)
    if not kanal:
        return await ctx.send("Mazeret panel kanalı bulunamadı.")

    msg = await kanal.send(embed=create_mazeret_panel_embed(), view=MazeretPanelView())
    mazeret_db["panel_message_id"] = msg.id
    save_mazeret_db()

    await ctx.send("Mazeret paneli gönderildi.")

# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():
    print(f"Aktif: {bot.user}")

    bot.add_view(BasvuruView())
    bot.add_view(KatilView())
    bot.add_view(KararView())
    bot.add_view(MazeretPanelView())
    bot.add_view(MazeretKararView())

    if not hasattr(bot, "mazeret_loop_started"):
        bot.mazeret_loop_started = True
        bot.loop.create_task(mazeret_sure_kontrol_loop())

    # Başvuru paneli
    kanal = bot.get_channel(BASVURU_KANAL_ID)
    mesaj_id = panel_data.get("panel_message_id")

    if kanal:
        if mesaj_id:
            try:
                mesaj = await kanal.fetch_message(mesaj_id)
                await mesaj.edit(embed=create_panel_embed(), view=BasvuruView())
            except Exception:
                msg = await kanal.send(embed=create_panel_embed(), view=BasvuruView())
                panel_data["panel_message_id"] = msg.id
                save_json(PANEL_FILE, panel_data)
        else:
            msg = await kanal.send(embed=create_panel_embed(), view=BasvuruView())
            panel_data["panel_message_id"] = msg.id
            save_json(PANEL_FILE, panel_data)

    # Mazeret paneli
    mazeret_kanal = bot.get_channel(MAZERET_PANEL_CHANNEL_ID)
    mazeret_mesaj_id = mazeret_db.get("panel_message_id")

    if mazeret_kanal:
        if mazeret_mesaj_id:
            try:
                msg = await mazeret_kanal.fetch_message(mazeret_mesaj_id)
                await msg.edit(embed=create_mazeret_panel_embed(), view=MazeretPanelView())
            except Exception:
                yeni = await mazeret_kanal.send(embed=create_mazeret_panel_embed(), view=MazeretPanelView())
                mazeret_db["panel_message_id"] = yeni.id
                save_mazeret_db()
        else:
            yeni = await mazeret_kanal.send(embed=create_mazeret_panel_embed(), view=MazeretPanelView())
            mazeret_db["panel_message_id"] = yeni.id
            save_mazeret_db()

bot.run(TOKEN)