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
        
        # Estrazione dati reali (con fallback se mancano)
        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan": data.get("clan", {}).get("name", "None"),
            "friends": len(data.get("friends", [])),
            # Nota: Questi sono dati di esempio. L'API Jartex richiede 
            # chiamate specifiche per le Bedwars che sono spesso protette.
            "wins": 356, "losses": 82, "wlr": 4.34,
            "fkills": 1260, "fdeaths": 90, "fkdr": 14.00,
            "kills": 2441, "deaths": 1152, "kdr": 2.12,
            "beds_b": 507, "beds_l": 82, "ws": 47
        }
    except: return None

def create_card(stats):
    try:
        # Carica sfondo.png (la tua immagine con la montagna)
        img = Image.open("sfondo.png").convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Caricamento Font Minecraft
        f_large = ImageFont.truetype("Minecraft.ttf", 35)
        f_med = ImageFont.truetype("Minecraft.ttf", 25)
        f_small = ImageFont.truetype("Minecraft.ttf", 18)
        
        # Colori Jartex
        white, green, red, yellow = "white", "#74FF74", "#FF5555", "#FFFF55"
        
        # 1. INTESTAZIONE (Rank, Nome e Livello in alto)
        draw.text((40, 35), f"{stats['rank']} {stats['username']}", fill=white, font=f_med)
        draw.text((img.width - 100, 35), str(stats['level']), fill=yellow, font=f_large)

        # 2. COLONNE STATISTICHE (Posizionate nella zona scura a sinistra)
        y_start = 140
        
        # Colonna 1: Wins / Kills / Beds Broken
        draw.text((60, y_start), "Wins", fill=green, font=f_small)
        draw.text((60, y_start+25), str(stats['wins']), fill=white, font=f_med)
        
        draw.text((60, y_start+110), "Kills", fill=green, font=f_small)
        draw.text((60, y_start+135), str(stats['kills']), fill=white, font=f_med)
        
        draw.text((60, y_start+220), "Beds Broken", fill=green, font=f_small)
        draw.text((60, y_start+245), str(stats['beds_b']), fill=white, font=f_med)

        # Colonna 2: Losses / Deaths / Beds Lost (Sbarrati)
        x_col2 = 260
        draw.text((x_col2, y_start), "Losses", fill=red, font=f_small)
        draw.line((x_col2, y_start+10, x_col2+65, y_start+10), fill=red, width=2)
        draw.text((x_col2, y_start+25), str(stats['losses']), fill=white, font=f_med)
        
        draw.text((x_col2, y_start+110), "Deaths", fill=red, font=f_small)
        draw.line((x_col2, y_start+120, x_col2+65, y_start+120), fill=red, width=2)
        draw.text((x_col2, y_start+135), str(stats['deaths']), fill=white, font=f_med)

        # Colonna 3: Rapporti (WLR, FKDR, WS)
        x_col3 = 460
        draw.text((x_col3, y_start), "WLR", fill=yellow, font=f_small)
        draw.text((x_col3, y_start+25), str(stats['wlr']), fill=green, font=f_med)
        
        draw.text((x_col3, y_start+110), "FKDR", fill=yellow, font=f_small)
        draw.text((x_col3, y_start+135), str(stats['fkdr']), fill=green, font=f_med)
        
        draw.text((x_col3, y_start+220), "WS", fill=yellow, font=f_small)
        draw.text((x_col3, y_start+245), str(stats['ws']), fill=green, font=f_med)

        # 3. INFORMATION & CLAN (Zona destra)
        x_info = 680
        draw.text((x_info, 300), "INFORMATION", fill=white, font=f_med)
        draw.text((x_info, 330), f"Friends: {stats['friends']}", fill=white, font=f_small)
        
        draw.text((x_info, 400), "CLAN", fill=white, font=f_med)
        draw.text((x_info, 430), stats['clan'], fill=white, font=f_small)

        # 4. SKIN 3D (Posizionata sopra l'Information a destra)
        try:
            skin_url = f"https://visage.surgeplay.com/full/300/{stats['username']}"
            skin_res = requests.get(skin_url, stream=True).raw
            skin_img = Image.open(skin_res).convert("RGBA")
            # Incolla la skin a destra
            img.paste(skin_img, (img.width - 280, 50), skin_img)
        except Exception as e:
            print(f"Errore skin: {e}")

        # 5. TITOLO IN BASSO
        draw.text((img.width // 2 - 140, img.height - 70), "BEDWARS STATS", fill="#FF5500", font=f_large)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore generazione: {e}")
        return None

# Accetta sia !stats che !bedwars
@bot.command(aliases=['bedwars'])
async def stats(ctx, user: str):
    data = get_jartex_stats(user)
    if not data: return await ctx.send(f"❌ Utente **{user}** non trovato su Jartex.")
    
    file_buf = create_card(data)
    if file_buf:
        await ctx.send(file=discord.File(file_buf, f"{user}_stats.png"))
    else:
        await ctx.send("❌ Errore grafico nella creazione della card.")

@bot.event
async def on_ready():
    print(f'✅ Bot Jartex Pro Online come {bot.user}')

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Errore: Variabile 'TOKEN' non trovata su Railway!")
