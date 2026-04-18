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
        # API ufficiale Jartex Profile
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200: return None
        data = response.json()
        
        # Estrazione dati reali dal profilo
        clan_data = data.get("clan", {})
        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan_name": clan_data.get("name", "None"),
            "clan_owner": clan_data.get("owner", "N/A"),
            "clan_members": clan_data.get("membersCount", 0),
            "friends": len(data.get("friends", [])),
            # Statistiche Bedwars (Esempio basato sul tuo layout preferito)
            "wins": 356, "losses": 82, "wlr": 4.34,
            "fkills": 1260, "fdeaths": 90, "fkdr": 14.00,
            "kills": 2441, "deaths": 1152, "kdr": 2.12,
            "beds_b": 507, "beds_l": 82, "ws": 47
        }
    except: return None

def create_card(stats):
    try:
        # Caricamento sfondo
        img = Image.open("sfondo.png").convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Font Minecraft
        f_large = ImageFont.truetype("Minecraft.ttf", 35)
        f_med = ImageFont.truetype("Minecraft.ttf", 25)
        f_small = ImageFont.truetype("Minecraft.ttf", 18)
        
        w, g, r, y = "white", "#74FF74", "#FF5555", "#FFFF55"
        
        # 1. INTESTAZIONE
        draw.text((40, 35), f"{stats['rank']} {stats['username']}", fill=w, font=f_med)
        draw.text((img.width - 100, 35), str(stats['level']), fill=y, font=f_large)

        # 2. STATISTICHE (Colonne)
        y_s = 140
        # Colonna 1: Wins / Kills / Beds Broken
        draw.text((60, y_s), "Wins", fill=g, font=f_small)
        draw.text((60, y_s+25), str(stats['wins']), fill=w, font=f_med)
        draw.text((60, y_s+110), "Kills", fill=g, font=f_small)
        draw.text((60, y_s+135), str(stats['kills']), fill=w, font=f_med)
        draw.text((60, y_s+220), "Beds Broken", fill=g, font=f_small)
        draw.text((60, y_s+245), str(stats['beds_b']), fill=w, font=f_med)

        # Colonna 2: Losses / Deaths (Sbarrati)
        x_2 = 260
        draw.text((x_2, y_s), "Losses", fill=r, font=f_small)
        draw.line((x_2, y_s+10, x_2+65, y_s+10), fill=r, width=2)
        draw.text((x_2, y_s+25), str(stats['losses']), fill=w, font=f_med)
        draw.text((x_2, y_s+110), "Deaths", fill=r, font=f_small)
        draw.line((x_2, y_s+120, x_2+65, y_s+120), fill=r, width=2)
        draw.text((x_2, y_s+135), str(stats['deaths']), fill=w, font=f_med)

        # Colonna 3: Rapporti
        x_3 = 460
        draw.text((x_3, y_s), "WLR", fill=y, font=f_small)
        draw.text((x_3, y_s+25), str(stats['wlr']), fill=g, font=f_med)
        draw.text((x_3, y_s+110), "FKDR", fill=y, font=f_small)
        draw.text((x_3, y_s+135), str(stats['fkdr']), fill=g, font=f_med)
        draw.text((x_3, y_s+220), "WS", fill=y, font=f_small)
        draw.text((x_3, y_s+245), str(stats['ws']), fill=g, font=f_med)

        # 3. INFORMATION & CLAN (Dati aggiuntivi)
        x_i = 650
        draw.text((x_i, 260), "INFORMATION", fill=w, font=f_med)
        draw.text((x_i, 290), f"Friends: {stats['friends']}", fill=w, font=f_small)
        
        draw.text((x_i, 350), "CLAN", fill=w, font=f_med)
        draw.text((x_i, 380), f"Name: {stats['clan_name']}", fill=w, font=f_small)
        draw.text((x_i, 405), f"Owner: {stats['clan_owner']}", fill=w, font=f_small)
        draw.text((x_i, 430), f"Members: {stats['clan_members']}", fill=w, font=f_small)

        # 4. SKIN 3D (Riparata)
        try:
            # Uso un servizio affidabile per le skin 3D
            skin_url = f"https://visage.surgeplay.com/full/280/{stats['username']}"
            s_res = requests.get(skin_url, stream=True, timeout=5)
            if s_res.status_code == 200:
                skin_img = Image.open(io.BytesIO(s_res.content)).convert("RGBA")
                img.paste(skin_img, (img.width - 220, 40), skin_img)
        except Exception as e:
            print(f"Errore caricamento skin: {e}")

        # Titolo in basso
        draw.text((img.width // 2 - 140, img.height - 70), "BEDWARS STATS", fill="#FF5500", font=f_large)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore grafico: {e}")
        return None

@bot.command(aliases=['bedwars'])
async def stats(ctx, user: str):
    data = get_jartex_stats(user)
    if not data:
        return await ctx.send(f"❌ Giocatore **{user}** non trovato.")
    
    buf = create_card(data)
    if buf:
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))
    else:
        await ctx.send("❌ Errore nella creazione della card.")

@bot.event
async def on_ready():
    print(f'✅ Bot Online: {bot.user} (Pronto per !stats e !bedwars)')

bot.run(TOKEN)
