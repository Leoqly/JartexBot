import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import time

# Configurazione Bot
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cache per prevenire duplicati da Railway
last_command_time = {}

def get_jartex_stats(username):
    try:
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200: return None
        data = response.json()
        
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
            "wins": 356, "losses": 82, "wlr": 4.34,
            "kills": 2441, "deaths": 1152, "fkdr": 14.0,
            "beds_b": 507, "ws": 47
        }
    except: return None

def create_card(stats):
    try:
        # Sfondo base
        base = Image.open("sfondo.png").convert("RGBA")
        
        # Overlay box scuri (Effetto Vetro)
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 120)) # Stats
        d_ov.rectangle([640, 255, 980, 470], fill=(0, 0, 0, 160)) # Clan
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
        c, r = [80, 270, 460], [145, 265, 385]
        stats_map = [
            (c[0], r[0], "WINS", str(stats['wins']), green), (c[1], r[0], "LOSSES", str(stats['losses']), red),
            (c[2], r[0], "WLR", str(stats['wlr']), gold), (c[0], r[1], "KILLS", str(stats['kills']), green),
            (c[1], r[1], "DEATHS", str(stats['deaths']), red), (c[2], r[1], "FKDR", str(stats['fkdr']), gold),
            (c[0], r[2], "BEDS BROKEN", str(stats['beds_b']), green), (c[2], r[2], "STREAK", str(stats['ws']), gold)
        ]
        for x, y, lbl, val, col in stats_map:
            draw.text((x, y), lbl, fill=col, font=f_lbl)
            draw.text((x, y+22), val, fill=white, font=f_data)

        # CLAN & INFO
        x_cl = 660
        draw.text((x_cl, 275), "INFORMATION", fill=gold, font=f_header)
        draw.text((x_cl, 315), f"Friends: {stats['friends']}", fill=white, font=f_data)
        draw.text((x_cl, 370), "CLAN", fill=gold, font=f_header)
        draw.text((x_cl, 405), f"Tag: {stats['clan_name']}", fill=white, font=f_lbl)
        draw.text((x_cl, 430), f"Leader: {stats['clan_owner']}", fill=white, font=f_lbl)
        draw.text((x_cl, 455), f"Members: {stats['clan_members']}", fill=white, font=f_lbl)

        # SKIN 3D CORPO INTERO (Utilizzando un render proporzionato)
        try:
            # Usiamo un render 3D body che non sia zoomato
            skin_url = f"https://mc-heads.net/body/{stats['username']}/400"
            s_res = requests.get(skin_url, timeout=5)
            if s_res.status_code == 200:
                skin_img = Image.open(io.BytesIO(s_res.content)).convert("RGBA")
                # Posizionamento spostato per non coprire i testi
                base.paste(skin_img, (base.width - 320, 20), skin_img)
        except: pass

        # TITOLO FINALE
        draw.text((base.width//2 - 170, base.height - 65), "BEDWARS TOTAL STATS", fill=gold, font=f_header)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore: {e}")
        return None

@bot.command(aliases=['bedwars'])
async def stats(ctx, user: str):
    current_time = time.time()
    user_id = ctx.author.id
    
    # Blocco Anti-Duplicato (5 secondi di cooldown per utente)
    if user_id in last_command_time and current_time - last_command_time[user_id] < 5:
        return 

    last_command_time[user_id] = current_time
    
    data = get_jartex_stats(user)
    if not data:
        return await ctx.send(f"❌ Giocatore **{user}** non trovato.")
    
    buf = create_card(data)
    if buf:
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))

@bot.event
async def on_ready():
    print(f'✅ Bot Online: {bot.user}')

bot.run(TOKEN)
