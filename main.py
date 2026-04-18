import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
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
        # Pulizia del nome Owner (prende solo lo username se è un dizionario)
        owner = clan.get("owner", "N/A")
        if isinstance(owner, dict):
            owner = owner.get("username", "N/A")

        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan_name": clan.get("name", "None"),
            "clan_owner": owner,
            "clan_members": clan.get("membersCount", 0),
            "friends": len(data.get("friends", [])),
            # Statistiche simulate (Sostituisci con logica API se disponibile)
            "wins": 356, "losses": 82, "wlr": 4.34,
            "fkills": 1260, "fdeaths": 90, "fkdr": 14.00,
            "kills": 2441, "deaths": 1152, "kdr": 2.12,
            "beds_b": 507, "beds_l": 82, "ws": 47
        }
    except Exception as e:
        print(f"Errore API: {e}")
        return None

def create_card(stats):
    try:
        # Carica sfondo (Assicurati che sia sfondo.png su GitHub)
        img = Image.open("sfondo.png").convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Caricamento Font
        f_large = ImageFont.truetype("Minecraft.ttf", 40)
        f_med = ImageFont.truetype("Minecraft.ttf", 26)
        f_small = ImageFont.truetype("Minecraft.ttf", 18)
        
        w, g, r, y = "white", "#74FF74", "#FF5555", "#FFFF55"
        
        # 1. TESTI IN ALTO
        draw.text((45, 35), f"{stats['rank']} {stats['username']}", fill=w, font=f_med)
        draw.text((img.width - 110, 35), str(stats['level']), fill=y, font=f_large)

        # 2. COLONNE STATS (Area scura sinistra)
        y_pos = [140, 250, 360] # Altezze per le 3 righe
        
        # Riga 1: Wins | Losses | WLR
        draw.text((60, y_pos[0]), "Wins", fill=g, font=f_small)
        draw.text((60, y_pos[0]+25), str(stats['wins']), fill=w, font=f_med)
        
        draw.text((260, y_pos[0]), "Losses", fill=r, font=f_small)
        draw.line((260, y_pos[0]+10, 330, y_pos[0]+10), fill=r, width=2)
        draw.text((260, y_pos[0]+25), str(stats['losses']), fill=w, font=f_med)
        
        draw.text((460, y_pos[0]), "WLR", fill=y, font=f_small)
        draw.text((460, y_pos[0]+25), str(stats['wlr']), fill=g, font=f_med)

        # Riga 2: Kills | Deaths | FKDR
        draw.text((60, y_pos[1]), "Kills", fill=g, font=f_small)
        draw.text((60, y_pos[1]+25), str(stats['kills']), fill=w, font=f_med)
        
        draw.text((260, y_pos[1]), "Deaths", fill=r, font=f_small)
        draw.line((260, y_pos[1]+10, 330, y_pos[1]+10), fill=r, width=2)
        draw.text((260, y_pos[1]+25), str(stats['deaths']), fill=w, font=f_med)
        
        draw.text((460, y_pos[1]), "FKDR", fill=y, font=f_small)
        draw.text((460, y_pos[1]+25), str(stats['fkdr']), fill=g, font=f_med)

        # Riga 3: Beds Broken | WS
        draw.text((60, y_pos[2]), "Beds Broken", fill=g, font=f_small)
        draw.text((60, y_pos[2]+25), str(stats['beds_b']), fill=w, font=f_med)
        
        draw.text((460, y_pos[2]), "WS", fill=y, font=f_small)
        draw.text((460, y_pos[2]+25), str(stats['ws']), fill=g, font=f_med)

        # 3. AREA INFORMAZIONI (Destra basso)
        x_info = 660
        draw.text((x_info, 280), "INFORMATION", fill=w, font=f_med)
        draw.text((x_info, 310), f"Friends: {stats['friends']}", fill=w, font=f_small)
        
        draw.text((x_info, 360), "CLAN", fill=w, font=f_med)
        draw.text((x_info, 390), f"Name: {stats['clan_name']}", fill=w, font=f_small)
        draw.text((x_info, 415), f"Owner: {stats['clan_owner']}", fill=w, font=f_small)
        draw.text((x_info, 440), f"Members: {stats['clan_members']}", fill=w, font=f_small)

        # 4. SKIN 3D (Posizionata a destra della luna)
        try:
            skin_url = f"https://visage.surgeplay.com/full/350/{stats['username']}"
            s_res = requests.get(skin_url, stream=True, timeout=5)
            if s_res.status_code == 200:
                skin_img = Image.open(io.BytesIO(s_res.content)).convert("RGBA")
                img.paste(skin_img, (img.width - 300, 20), skin_img)
        except: pass

        # TITOLO FINALE
        draw.text((img.width // 2 - 150, img.height - 70), "BEDWARS STATS", fill="#FF5500", font=f_large)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore Card: {e}")
        return None

@bot.command(aliases=['bedwars'])
async def stats(ctx, user: str):
    data = get_jartex_stats(user)
    if not data:
        return await ctx.send(f"❌ Utente **{user}** non trovato.")
    
    buf = create_card(data)
    if buf:
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))

@bot.event
async def on_ready():
    print(f'✅ Bot Jartex Pronto!')

bot.run(TOKEN)
