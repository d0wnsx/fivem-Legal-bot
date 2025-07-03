import discord
from discord.ext import commands
from discord import ui
import os
import json
from datetime import datetime, timedelta
from discord import Permissions
from discord import ui
import ssl
import certifi

ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

config = {}
with open('agrsf.cfg', 'r', encoding='utf-8') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            config[key] = value

TOKEN = config['BOT_TOKEN']
PREFIX = config.get('PREFIX', '!')
BOT_STATUS = config.get('BOT_STATUS', 'agresivo-legal bot')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

ROLE_ID = 1385376426202501175 

KAYIT_DOSYASI = 'mesai_kayitlari.json'

TICKET_KATEGORI_ID = 1385376426936500228
TICKET_YETKILI_ROL_ID = 1390306276801515592
TICKET_LOG_KATEGORI_ID = 1387167578677444850
TICKET_LOG_KANAL_ID = 1390325518318047232

def load_mesai_data():
    if not os.path.exists(KAYIT_DOSYASI):
        return {}
    with open(KAYIT_DOSYASI, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_mesai_data(data):
    with open(KAYIT_DOSYASI, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_now_str():
    return datetime.utcnow().strftime('%d.%m.%Y %H:%M')

def get_now_iso():
    return datetime.utcnow().isoformat()

def format_sure(seconds):
    td = timedelta(seconds=seconds)
    saatler, kalan = divmod(td.seconds, 3600)
    dakikalar, _ = divmod(kalan, 60)
    return f"{td.days*24 + saatler} saat {dakikalar} dakika"

@bot.event
async def on_ready():
    print(f'Bot giriş yaptı: {bot.user}')
    await bot.change_presence(activity=discord.Game(name=BOT_STATUS))

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        user = interaction.user
        user_id = str(user.id)
        mesai_data = load_mesai_data()
        now = datetime.utcnow()
        now_str = now.strftime('%d.%m.%Y %H:%M')
        if interaction.data.get('custom_id') == 'mesai_giris':
            mesai_data.setdefault(user_id, {"toplam_saniye": 0, "giris": None})
            mesai_data[user_id]["giris"] = now.isoformat()
            save_mesai_data(mesai_data)
            try:
                await user.send(f"Mesaiye girdin!\nGiriş saatin: {now_str}")
            except Exception:
                pass
            log_channel_id = 1390311960137957417
            log_channel = bot.get_channel(log_channel_id)
            toplam = mesai_data[user_id]["toplam_saniye"]
            if log_channel:
                await log_channel.send(
                    f"{user.mention} mesaiye girdi!\n"
                    f"Giriş saati: {now_str}\n"
                    f"Toplam mesai: {format_sure(toplam)}"
                )
            await interaction.response.send_message("Mesaiye giriş işlemin kaydedildi!", ephemeral=True)
        elif interaction.data.get('custom_id') == 'mesai_cikis':
            kayit = mesai_data.get(user_id)
            if kayit and kayit.get("giris"):
                giris_zaman = datetime.fromisoformat(kayit["giris"])
                oturum_sure = int((now - giris_zaman).total_seconds())
                kayit["toplam_saniye"] += oturum_sure
                kayit["giris"] = None
                save_mesai_data(mesai_data)
                toplam = kayit["toplam_saniye"]
                try:
                    await user.send(
                        f"Mesaiden çıktın!\nÇıkış saatin: {now_str}\n"
                        f"Bu oturumda: {format_sure(oturum_sure)} mesaide kaldın.\n"
                        f"Toplam mesai süren: {format_sure(toplam)}"
                    )
                except Exception:
                    pass
                log_channel_id = 1390316129871728701
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(
                        f"{user.mention} mesaiden çıktı!\n"
                        f"Çıkış saati: {now_str}\n"
                        f"Bu oturum: {format_sure(oturum_sure)}\n"
                        f"Toplam mesai: {format_sure(toplam)}"
                    )
                await interaction.response.send_message("Mesaiden çıkış işlemin kaydedildi!", ephemeral=True)
            else:
                await interaction.response.send_message("Önce mesaiye giriş yapmalısın!", ephemeral=True)
        elif interaction.data.get('custom_id') == 'bilgilerim':
            kayit = mesai_data.get(user_id)
            toplam = kayit["toplam_saniye"] if kayit else 0
            if kayit and kayit.get("giris"):
                giris_zaman = datetime.fromisoformat(kayit["giris"])
                toplam += int((now - giris_zaman).total_seconds())
            try:
                await user.send(f"Toplam mesai süren: {format_sure(toplam)}")
            except Exception:
                pass
            await interaction.response.send_message("Toplam mesai süren DM olarak gönderildi!", ephemeral=True)
        elif interaction.data.get('custom_id') == 'ticket_destek':
            existing = discord.utils.get(interaction.guild.text_channels, name=f"ticket-{interaction.user.name.lower()}")
            if existing:
                await interaction.response.send_message(f"Zaten bir ticket kanalınız var: {existing.mention}", ephemeral=True)
            else:
                channel = await create_ticket_channel(interaction.guild, interaction.user, is_basvuru=False)
                await interaction.response.send_message(f"Destek bileti kanalınız oluşturuldu: {channel.mention}", ephemeral=True)
        elif interaction.data.get('custom_id') == 'ticket_basvuru':
            existing = discord.utils.get(interaction.guild.text_channels, name=f"ticket-{interaction.user.name.lower()}")
            if existing:
                await interaction.response.send_message(f"Zaten bir ticket kanalınız var: {existing.mention}", ephemeral=True)
            else:
                channel = await create_ticket_channel(interaction.guild, interaction.user, is_basvuru=True)
                await interaction.response.send_message(f"Başvuru kanalınız oluşturuldu: {channel.mention}", ephemeral=True)
        elif interaction.data.get('custom_id') == 'ticket_kapat':
            await interaction.response.send_message("Bilet sonlandırma özelliği yakında aktif olacak!", ephemeral=True)
        elif interaction.data.get('custom_id') == 'rapor_gonder':
            await interaction.response.send_modal(RaporModal())

def guild_only():
    async def predicate(ctx):
        if ctx.guild is None:
            await ctx.send("Bu komut sadece sunucuda kullanılabilir.", delete_after=5)
            return False
        return True
    return commands.check(predicate)

@bot.command()
@guild_only()
async def mesai(ctx):
    member = ctx.author
    if not ctx.guild:
        await ctx.send("Bu komut sadece sunucuda kullanılabilir.", delete_after=5)
        return
    if not any(role.id == ROLE_ID for role in getattr(member, 'roles', [])):
        await ctx.send('Bu komutu sadece yetkili rol kullanabilir.', delete_after=5)
        return
    try:
        embed = discord.Embed(
            title="San Andres Park Rangeris",
            description=(
                "Merhabalar, Buradan Mesaiye **Giriş/Çıkış** İşlemlerini Yapabilirsiniz.\n\n"
                ":green_circle: **MESAI GIR** Mesaiye **Girmenizi** Sağlar.\n"
                ":white_circle: **MESAI CIK** Mesaiden **Çıkmanızı** Sağlar.\n\n"
                ":exclamation: Oyunda Değilseniz Ve Mesainizi Açık Olarak Bıraktıysanız Verileriniz Silinir\n"
                "Bu Durumun Tekrar Halinde İhraç Edilirsiniz."
            ),
            color=discord.Color.blue()
        )
        embed.set_author(name="Fivem Department Helper")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Mesaiye Giriş", style=discord.ButtonStyle.success, custom_id="mesai_giris"))
        view.add_item(discord.ui.Button(label="Mesaiden Çıkış", style=discord.ButtonStyle.danger, custom_id="mesai_cikis"))
        view.add_item(discord.ui.Button(label="Bilgilerim", style=discord.ButtonStyle.secondary, custom_id="bilgilerim"))
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"Bir hata oluştu: {e}", delete_after=5)

@bot.command()
@guild_only()
async def toplammesai(ctx):
    mesai_data = load_mesai_data()
    now = datetime.utcnow()
    sirali = []
    for user_id, kayit in mesai_data.items():
        toplam = kayit["toplam_saniye"]
        if kayit.get("giris"):
            giris_zaman = datetime.fromisoformat(kayit["giris"])
            toplam += int((now - giris_zaman).total_seconds())
        sirali.append((user_id, toplam))
    sirali.sort(key=lambda x: x[1], reverse=True)
    if not sirali:
        await ctx.send("Hiç mesai kaydı yok.")
        return
    mesaj = "**Toplam Mesai Sıralaması:**\n"
    for i, (user_id, saniye) in enumerate(sirali, 1):
        member = ctx.guild.get_member(int(user_id))
        isim = member.display_name if member else f"<@{user_id}>"
        mesaj += f"{i}. {isim} — {format_sure(saniye)}\n"
    await ctx.send(mesaj)

@bot.command()
@guild_only()
async def mesaidekimvar(ctx):
    mesai_data = load_mesai_data()
    aktifler = []
    for user_id, kayit in mesai_data.items():
        if kayit.get("giris"):
            giris_zaman = datetime.fromisoformat(kayit["giris"])
            aktifler.append((user_id, giris_zaman))
    if not aktifler:
        await ctx.send("Şu anda aktif mesai yapan kimse yok.")
        return
    mesaj = "**Aktif Mesai Yapanlar:**\n"
    for user_id, giris_zaman in aktifler:
        member = ctx.guild.get_member(int(user_id))
        isim = member.display_name if member else f"<@{user_id}>"
        saat = giris_zaman.strftime('%d.%m.%Y %H:%M')
        mesaj += f"- {isim} (Giriş: {saat})\n"
    await ctx.send(mesaj)

@bot.command()
@guild_only()
async def ticket(ctx):
    try:
        embed = discord.Embed(
            title="Destek Sistemi",
            description="Aşağıdaki butonlardan birini kullanarak destek bileti veya başvuru oluşturabilirsiniz.",
            color=discord.Color.green()
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Destek Bileti", style=discord.ButtonStyle.primary, custom_id="ticket_destek"))
        view.add_item(discord.ui.Button(label="Başvuru", style=discord.ButtonStyle.success, custom_id="ticket_basvuru"))
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"Bir hata oluştu: {e}", delete_after=5)

@bot.command()
@guild_only()
async def rapor(ctx):
    try:
        embed = discord.Embed(
            title="Rapor Sistemi",
            description="Aşağıdaki butona basarak rapor gönderebilirsiniz.",
            color=discord.Color.red()
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Rapor Gönder", style=discord.ButtonStyle.primary, custom_id="rapor_gonder"))
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"Bir hata oluştu: {e}", delete_after=5)

class RaporModal(ui.Modal, title="Rapor Formu"):
    rozet_ve_ad = ui.TextInput(label="Rozet numaran ve adın", placeholder="Örn: 1234 - Ahmet Yılmaz", required=True)
    rapor_nedir = ui.TextInput(label="Rapor nedir?", style=discord.TextStyle.paragraph, placeholder="Raporunuzu buraya yazın...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        rapor_kanal_id = interaction.channel.id
        kanal = interaction.guild.get_channel(rapor_kanal_id)
        if kanal:
            try:
                await kanal.send(
                    f"**Yeni Rapor!**\n"
                    f"**Rozet ve Ad:** ```{self.rozet_ve_ad.value}```\n"
                    f"**Rapor:** ```{self.rapor_nedir.value}```\n"
                    f"Gönderen: {interaction.user.mention}"
                )
            except Exception:
                pass
        await interaction.response.send_message("Raporun başarıyla gönderildi!", ephemeral=True)

@bot.command()
@guild_only()
async def komutlar(ctx):
    mesaj = (
        "**Kullanabileceğiniz Komutlar:**\n"
        "\n"
        "**!mesai** — Mesai panelini açar, sadece yetkili rol kullanabilir.\n"
        "**!mesaidekimvar** — Şu anda aktif mesai yapanları ve giriş saatlerini listeler.\n"
        "**!toplammesai** — Tüm kullanıcıların toplam mesai sürelerini sıralar.\n"
        "**!ticket** — Destek veya başvuru bileti açma panelini gönderir.\n"
        "**!rapor** — Rapor gönderme formunu açar.\n"
        "**!komutlar** — Tüm komutları ve açıklamalarını listeler.\n"
    )
    await ctx.send(mesaj)

async def create_ticket_channel(guild, user, is_basvuru=False):
    kategori = guild.get_channel(TICKET_KATEGORI_ID)
    if kategori is None:
        return None
    overwrites = {
        guild.default_role: Permissions(view_channel=False),
        guild.get_role(TICKET_YETKILI_ROL_ID): Permissions(view_channel=True, send_messages=True, read_message_history=True),
        user: Permissions(view_channel=True, send_messages=True, read_message_history=True)
    }
    channel_name = f"ticket-{user.name.lower()}"
    try:
        channel = await guild.create_text_channel(channel_name, category=kategori, overwrites=overwrites)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Bileti Sonlandır", style=discord.ButtonStyle.danger, custom_id="ticket_kapat"))
        if is_basvuru:
            await channel.send(f"Merhaba {user.mention}, başvurunuz alınmıştır. Yetkililer en kısa sürede sizinle ilgilenecek.", view=view)
        else:
            await channel.send(f"Merhaba {user.mention}, destek talebiniz oluşturuldu. Yetkililer yakında sizinle ilgilenecek.", view=view)
        return channel
    except Exception:
        return None

if __name__ == "__main__":
    bot.run(TOKEN) 