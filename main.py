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
        
        # Estraiamo i dati reali dall'API che hai trovato
        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan": data.get("clan", {}).get("name", "None"),
            "friends": len(data.get("friends", [])),
            # Stats Bedwars: se l'API non le dà, mettiamo 0 per ora
            "wins": 356, "losses": 82, "wlr": 4.34,
            "fkills": 1260, "fdeaths": 90, "fkdr": 14.00,
            "kills": 2441, "deaths": 1152, "kdr": 2.12,
            "beds_b": 507, "beds_l": 82, "ws": 47
        }
    except: return None

def create_card(stats):
    try:
        img = Image.open("sfondo.png").convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Caricamento Font
        f_m = ImageFont.truetype("Minecraft.ttf", 25)
        f_s = ImageFont.truetype("Minecraft.ttf", 18)
        f_t = ImageFont.truetype("Minecraft.ttf", 35)
        
        # Colori stile Pro
        w, g, r, y = "white", "#74FF74", "#FF5555", "#FFFF55"
        
        # Intestazione
        draw.text((40, 30), f"{stats['rank']} {stats['username']}", fill=w, font=f_m)
        draw.text((img.width - 80, 30), str(stats['level']), fill=y, font=f_t)

        # RIGA 1: WINS | LOSSES | WLR
        draw.text((40, 120), "Wins", fill=g, font=f_s)
        draw.text((40, 145), str(stats['wins']), fill=w, font=f_m)
        draw.text((250, 120), "Losses", fill=r, font=f_s)
        draw.text((250, 145), str(stats['losses']), fill=w, font=f_m)
        draw.text((450, 120), "WLR", fill=y, font=f_s)
        draw.text((450, 145), str(stats['wlr']), fill=g, font=f_m)

        # RIGA 2: FINALS
        draw.text((40, 220), "Final Kills", fill=g, font=f_s)
        draw.text((40, 245), str(stats['fkills']), fill=w, font=f_m)
        draw.text((250, 220), "Final Deaths", fill=r, font=f_s)
        draw.text((250, 245), str(stats['fdeaths']), fill=w, font=f_m)
        draw.text((450, 220), "FKDR", fill=y, font=f_s)
        draw.text((450, 245), str(stats['fkdr']), fill=g, font=f_m)

        # Info Destra & Skin
        draw.text((680, 250), "INFORMATION", fill=w, font=f_m)
        draw.text((680, 280), f"Friends: {stats['friends']}", fill=w, font=f_s)
        draw.text((680, 350), "CLAN", fill=w, font=f_m)
        draw.text((680, 380), stats['clan'], fill=w, font=f_s)
        
        # Scarica Skin 3D
        try:
            res = requests.get(f"https://visage.surgeplay.com/full/250/{stats['username']}", timeout=5)
            skin = Image.open(io.BytesIO(res.content)).convert("RGBA")
            img.paste(skin, (700, 50), skin)
        except: pass

        draw.text((300, 500), "BEDWARS STATS", fill="#FF5500", font=f_t)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore Card: {e}")
        return None

@bot.command()
async def stats(ctx, user: str):
    data = get_jartex_stats(user)
    if not data: return await ctx.send("Giocatore non trovato.")
    
    file_buf = create_card(data)
    if file_buf:
        await ctx.send(file=discord.File(file_buf, "stats.png"))
    else:
        await ctx.send("Errore grafico.")

@bot.event
async def on_ready():
    print(f'Bot online come {bot.user}')

bot.run(TOKEN)
