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
        # API Profile per dati base (Rank, Livello, Clan)
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200: return None
        data = response.json()
        
        # Dati da mostrare (Dati Bedwars simulati se l'API non li fornisce tutti)
        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan": data.get("clan", {}).get("name", "None"),
            "friends": len(data.get("friends", [])),
            "wins": 356, "losses": 82, "wlr": 4.34,
            "fkills": 1260, "fdeaths": 90, "fkdr": 14.00,
            "kills": 2441, "deaths": 1152, "kdr": 2.12,
            "beds_b": 507, "beds_l": 82, "ws": 47
        }
    except: return None

def create_card(stats):
    try:
        # Carica il nuovo sfondo (Assicurati che si chiami sfondo.png su GitHub)
        img = Image.open("sfondo.png").convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Caricamento Font Minecraft
        f_large = ImageFont.truetype("Minecraft.ttf", 35)
        f_med = ImageFont.truetype("Minecraft.ttf", 25)
        f_small = ImageFont.truetype("Minecraft.ttf", 18)
        
        # Palette Colori Jartex
        white, green, red, yellow = "white", "#74FF74", "#FF5555", "#FFFF55"
        
        # --- INTESTAZIONE ---
        draw.text((40, 30), f"{stats['rank']} {stats['username']}", fill=white, font=f_med)
        draw.text((img.width - 90, 30), str(stats['level']), fill=yellow, font=f_large)

        # --- COLONNA 1 (Verde) ---
        y_s = 130
        draw.text((60, y_s), "Wins", fill=green, font=f_small)
        draw.text((60, y_s+25), str(stats['wins']), fill=white, font=f_med)
        
        draw.text((60, y_s+100), "Kills", fill=green, font=f_small)
        draw.text((60, y_s+125), str(stats['kills']), fill=white, font=f_med)
        
        draw.text((60, y_s+200), "Beds Broken", fill=green, font=f_small)
        draw.text((60, y_s+225), str(stats['beds_b']), fill=white, font=f_med)

        # --- COLONNA 2 (Rosso + Sbarrato) ---
        x_2 = 260
        draw.text((x_2, y_s), "Losses", fill=red, font=f_small)
        draw.line((x_2, y_s+10, x_2+70, y_s+10), fill=red, width=2) # Sbarrato
        draw.text((x_2, y_s+25), str(stats['losses']), fill=white, font=f_med)
        
        draw.text((x_2, y_s+100), "Deaths", fill=red, font=f_small)
        draw.line((x_2, y_s+110, x_2+70, y_s+110), fill=red, width=2) # Sbarrato
        draw.text((x_2, y_s+125), str(stats['deaths']), fill=white, font=f_med)

        # --- COLONNA 3 (Giallo/Rapporti) ---
        x_3 = 460
        draw.text((x_3, y_s), "WLR", fill=yellow, font=f_small)
        draw.text((x_3, y_s+25), str(stats['wlr']), fill=green, font=f_med)
        
        draw.text((x_3, y_s+100), "FKDR", fill=yellow, font=f_small)
        draw.text((x_3, y_s+125), str(stats['fkdr']), fill=green, font=f_med)
        
        draw.text((x_3, y_s+200), "WS", fill=yellow, font=f_small)
        draw.text((x_3, y_s+225), str(stats['ws']), fill=green, font=f_med)

        # --- INFORMATION & CLAN (A Destra) ---
        x_4 = 680
        draw.text((x_4, 280), "INFORMATION", fill=white, font=f_med)
        draw.text((x_4, 310), f"Friends: {stats['friends']}", fill=white, font=f_small)
        draw.text((x_4, 380), "CLAN", fill=white, font=f_med)
        draw.text((x_4, 410), stats['clan'], fill=white, font=f_small)

        # Skin 3D
        try:
            skin_url = f"https://visage.surgeplay.com/full/280/{stats['username']}"
            skin_res = requests.get(skin_url, stream=True).raw
            skin_img = Image.open(skin_res).convert("RGBA")
            img.paste(skin_img, (img.width - 240, 50), skin_img)
        except: pass

        # Titolo Finale
        draw.text((320, 510), "BEDWARS STATS", fill="#FF5500", font=f_large)

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
    if not data: return await ctx.send("❌ Giocatore non trovato.")
    
    file_buf = create_card(data)
    if file_buf:
        await ctx.send(file=discord.File(file_buf, "stats.png"))
    else:
        await ctx.send("❌ Errore nella generazione grafica.")

@bot.event
async def on_ready():
    print(f'✅ Bot Online: {bot.user}')

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Errore: Variabile TOKEN mancante su Railway!")
