import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os

# Configurazione Bot - Assicurati che 'TOKEN' sia nelle Variables di Railway
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_jartex_stats(username):
    try:
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        # Aumentiamo il timeout per l'API se è lenta
        response = requests.get(api_url, timeout=12)
        if response.status_code != 200: return None
        data = response.json()
        
        # Pulizia dati clan
        clan = data.get("clan", {})
        owner_data = clan.get("owner", "N/A")
        owner_name = owner_data.get("username", "N/A") if isinstance(owner_data, dict) else owner_data

        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan_name": clan.get("name", "None"),
            "clan_owner": owner_name,
            "clan_members": clan.get("membersCount", 0),
            "friends": len(data.get("friends", [])),
            # Statistiche simulate
            "wins": 356, "losses": 82, "wlr": 4.34,
            "kills": 2441, "deaths": 1152, "fkdr": 14.0,
            "beds_b": 507, "ws": 47
        }
    except Exception as e:
        print(f"Errore API: {e}")
        return None

def create_card(stats):
    try:
        # Carica base
        base = Image.open("sfondo.png").convert("RGBA")
        
        # Box scuri trasparenti
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 110)) 
        d_ov.rectangle([640, 255, 980, 470], fill=(0, 0, 0, 150)) 
        base = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(base)
        f_title = ImageFont.truetype("Minecraft.ttf", 42)
        f_header = ImageFont.truetype("Minecraft.ttf", 28)
        f_data = ImageFont.truetype("Minecraft.ttf", 22)
        f_lbl = ImageFont.truetype("Minecraft.ttf", 15)
        
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"

        # INTESTAZIONE
        draw.text((50, 40), f"{stats['rank']} {stats['username']}", fill=white, font=f_header)
        draw.text((base.width - 110, 40), str(stats['level']), fill=gold, font=f_title)

        # GRID STATS
        c = [80, 270, 460]
        r = [145, 265, 385]

        stats_map = [
            (c[0], r[0], "WINS", str(stats['wins']), green),
            (c[1], r[0], "LOSSES", str(stats['losses']), red),
            (c[2], r[0], "WLR", str(stats['wlr']), gold),
            (c[0], r[1], "KILLS", str(stats['kills']), green),
            (c[1], r[1], "DEATHS", str(stats['deaths']), red),
            (c[2], r[1], "FKDR", str(stats['fkdr']), gold),
            (c[0], r[2], "BEDS BROKEN", str(stats['beds_b']), green),
            (c[2], r[2], "STREAK", str(stats['ws']), gold)
        ]

        for x, y, lbl, val, col in stats_map:
            draw.text((x, y), lbl, fill=col, font=f_lbl)
            draw.text((x, y+22), val, fill=white, font=f_data)

        # INFO & CLAN
        x_cl = 660
        draw.text((x_cl, 275), "INFORMATION", fill=gold, font=f_header)
        draw.text((x_cl, 315), f"Friends: {stats['friends']}", fill=white, font=f_data)
        
        draw.text((x_cl, 370), "CLAN", fill=gold, font=f_header)
        draw.text((x_cl, 405), f"Tag: {stats['clan_name']}", fill=white, font=f_lbl)
        draw.text((x_cl, 430), f"Leader: {stats['clan_owner']}", fill=white, font=f_lbl)
        draw.text((x_cl, 455), f"Members: {stats['clan_members']}", fill=white, font=f_lbl)

        # 4. CARICAMENTO SKIN 3D (Migliorato e più veloce)
        try:
            skin_url = f"https://visage.surgeplay.com/full/400/{stats['username']}"
            # Timeout molto basso così il bot non si blocca
            s_res = requests.get(skin_url, stream=True, timeout=5)
            if s_res.status_code == 200:
                skin_img = Image.open(s_res.raw).convert("RGBA")
                base.paste(skin_img, (base.width - 320, 10), skin_img)
            else:
                print(f"Skin non trovata per {stats['username']}, uso Steve.")
                # Opzionale: carica un'immagine "steve.png" di default che hai su GitHub
                # default_skin = Image.open("steve.png").convert("RGBA")
                # base.paste(default_skin, (base.width - 320, 10), default_skin)
        except Exception as e:
            print(f"Errore caricamento skin: {e}")

        # FOOTER
        draw.text((base.width//2 - 170, base.height - 65), "BEDWARS TOTAL STATS", fill=gold, font=f_header)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore generazione card: {e}")
        return None

# Accetta sia !stats che !bedwars
@bot.command(aliases=['bedwars'])
async def stats(ctx, user: str):
    # Invia un messaggio di attesa per evitare cheDiscord duplichi il comando
    waiting_msg = await ctx.send(f"🔍 Recupero statistiche per **{user}**...")
    
    data = get_jartex_stats(user)
    if not data: 
        await waiting_msg.delete()
        return await ctx.send(f"❌ Utente **{user}** non trovato.")
    
    buf = create_card(data)
    if buf: 
        await waiting_msg.delete()
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))
    else:
        await waiting_msg.delete()
        await ctx.send("❌ Errore nella generazione della card grafica.")

@bot.event
async def on_ready():
    print(f'✅ Bot Online: {bot.user} (Pronto per !stats)')

bot.run(TOKEN)
