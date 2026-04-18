import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import requests
import io
import os

# Configurazione Bot
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_jartex_stats(username):
    try:
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200: return None
        data = response.json()
        
        clan = data.get("clan", {})
        owner_data = clan.get("owner", "N/A")
        # Pulizia Owner: se è un dizionario, estraiamo solo lo username
        owner_name = owner_data.get("username", "N/A") if isinstance(owner_data, dict) else owner_data

        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan_name": clan.get("name", "None"),
            "clan_owner": owner_name,
            "clan_members": clan.get("membersCount", 0),
            "friends": len(data.get("friends", [])),
            # Stats (Qui puoi collegare altre API se ne hai)
            "wins": 356, "losses": 82, "wlr": 4.34,
            "kills": 2441, "deaths": 1152, "fkdr": 14.0,
            "beds_b": 507, "ws": 47
        }
    except: return None

def create_card(stats):
    try:
        # 1. Base e Overlay
        base = Image.open("sfondo.png").convert("RGBA")
        txt_layer = Image.new("RGBA", base.size, (0,0,0,0))
        draw = ImageDraw.Draw(txt_layer)
        
        # Font (Minecraftia)
        f_title = ImageFont.truetype("Minecraft.ttf", 45)
        f_header = ImageFont.truetype("Minecraft.ttf", 30)
        f_data = ImageFont.truetype("Minecraft.ttf", 24)
        f_lbl = ImageFont.truetype("Minecraft.ttf", 16)
        
        # Colori
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"

        # 2. BOX SEMI-TRASPARENTE (Effetto Vetro per le Stats)
        # Disegniamo un rettangolo scuro sfumato a sinistra
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        d_ov.rectangle([30, 110, 600, 480], fill=(0, 0, 0, 80)) # Box stats
        d_ov.rectangle([640, 250, 980, 480], fill=(0, 0, 0, 120)) # Box clan
        base = Image.alpha_composite(base, overlay)

        # 3. TESTI - INTESTAZIONE
        draw.text((40, 30), f"{stats['rank']} {stats['username']}", fill=white, font=f_header)
        draw.text((base.width - 100, 30), str(stats['level']), fill=gold, font=f_title)

        # 4. GRIGLIA STATS (Pulita)
        cols = [70, 260, 450]
        rows = [150, 270, 390]

        # Riga 1
        draw.text((cols[0], rows[0]), "WINS", fill=green, font=f_lbl)
        draw.text((cols[0], rows[0]+25), str(stats['wins']), fill=white, font=f_data)
        draw.text((cols[1], rows[0]), "LOSSES", fill=red, font=f_lbl)
        draw.text((cols[1], rows[0]+25), str(stats['losses']), fill=white, font=f_data)
        draw.text((cols[2], rows[0]), "WLR", fill=gold, font=f_lbl)
        draw.text((cols[2], rows[0]+25), f"{stats['wlr']}", fill=white, font=f_data)

        # Riga 2
        draw.text((cols[0], rows[1]), "KILLS", fill=green, font=f_lbl)
        draw.text((cols[0], rows[1]+25), str(stats['kills']), fill=white, font=f_data)
        draw.text((cols[1], rows[1]), "DEATHS", fill=red, font=f_lbl)
        draw.text((cols[1], rows[1]+25), str(stats['deaths']), fill=white, font=f_data)
        draw.text((cols[2], rows[1]), "FKDR", fill=gold, font=f_lbl)
        draw.text((cols[2], rows[1]+25), f"{stats['fkdr']}", fill=white, font=f_data)

        # Riga 3
        draw.text((cols[0], rows[2]), "BEDS BROKEN", fill=green, font=f_lbl)
        draw.text((cols[0], rows[2]+25), str(stats['beds_b']), fill=white, font=f_data)
        draw.text((cols[2], rows[2]), "STREAK", fill=gold, font=f_lbl)
        draw.text((cols[2], rows[2]+25), str(stats['ws']), fill=white, font=f_data)

        # 5. BOX INFORMATION & CLAN (Destra)
        x_cl = 660
        draw.text((x_cl, 270), "INFORMATION", fill=gold, font=f_header)
        draw.text((x_cl, 310), f"Friends: {stats['friends']}", fill=white, font=f_data)
        
        draw.text((x_cl, 365), "CLAN", fill=gold, font=f_header)
        draw.text((x_cl, 400), f"Tag: {stats['clan_name']}", fill=white, font=f_lbl)
        draw.text((x_cl, 425), f"Leader: {stats['clan_owner']}", fill=white, font=f_lbl)
        draw.text((x_cl, 450), f"Members: {stats['clan_members']}", fill=white, font=f_lbl)

        # 6. SKIN 3D (Posizionata perfettamente a destra della montagna)
        try:
            skin_url = f"https://visage.surgeplay.com/full/400/{stats['username']}"
            res = requests.get(skin_url, timeout=5)
            skin = Image.open(io.BytesIO(res.content)).convert("RGBA")
            base.paste(skin, (base.width - 320, 0), skin)
        except: pass

        # 7. FOOTER
        draw.text((base.width//2 - 160, base.height - 60), "BEDWARS TOTAL STATS", fill=gold, font=f_header)

        # Unione finale
        out = Image.alpha_composite(base, txt_layer)
        buf = io.BytesIO()
        out.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore: {e}")
        return None

@bot.command(aliases=['bedwars'])
async def stats(ctx, user: str):
    data = get_jartex_stats(user)
    if not data: return await ctx.send("❌ Player non trovato.")
    
    buf = create_card(data)
    if buf:
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))

bot.run(TOKEN)
