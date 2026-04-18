import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests
import io

# ... (tieni la parte iniziale del bot e il TOKEN) ...

def get_stats(username):
    try:
        # Usiamo l'API per i dati base (Livello, Clan, Rank)
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        data = requests.get(api_url).json()
        
        # Simuliamo il recupero dei dati Bedwars (che dovresti grabbare dal sito o API specifica)
        # Se l'API non li dà, qui mettiamo dei valori di esempio basati sulla tua immagine
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
    except:
        return None

async def create_card(stats):
    # Carica lo sfondo e il font che hai già
    img = Image.open("sfondo.png").convert("RGBA")
    draw = ImageDraw.Draw(img)
    font_m = ImageFont.truetype("Minecraft.ttf", 25)
    font_s = ImageFont.truetype("Minecraft.ttf", 18)
    font_title = ImageFont.truetype("Minecraft.ttf", 35)

    # --- COORDINATE E COLORI (Riorganizzazione stile Pro) ---
    white, green, red, yellow = "white", "#74FF74", "#FF5555", "#FFFF55"
    
    # Intestazione
    draw.text((40, 30), f"{stats['rank']} {stats['username']}", fill=white, font=font_m)
    draw.text((700, 30), str(stats['level']), fill=yellow, font=font_title)

    # RIGA 1: WINS | LOSSES | WLR
    draw.text((40, 120), "Wins", fill=green, font=font_s)
    draw.text((40, 145), str(stats['wins']), fill=white, font=font_m)
    draw.text((250, 120), "Losses", fill=red, font=font_s)
    draw.text((250, 145), str(stats['losses']), fill=white, font=font_m)
    draw.text((450, 120), "WLR", fill=yellow, font=font_s)
    draw.text((450, 145), str(stats['wlr']), fill=green, font=font_m)

    # RIGA 2: FINAL KILLS | FINAL DEATHS | FKDR
    draw.text((40, 220), "Final Kills", fill=green, font=font_s)
    draw.text((40, 245), str(stats['fkills']), fill=white, font=font_m)
    draw.text((250, 220), "Final Deaths", fill=red, font=font_s)
    draw.text((250, 245), str(stats['fdeaths']), fill=white, font=font_m)
    draw.text((450, 220), "FKDR", fill=yellow, font=font_s)
    draw.text((450, 245), str(stats['fkdr']), fill=green, font=font_m)

    # RIGA 3: KILLS | DEATHS | KDR
    draw.text((40, 320), "Kills", fill=green, font=font_s)
    draw.text((40, 345), str(stats['kills']), fill=white, font=font_m)
    draw.text((250, 320), "Deaths", fill=red, font=font_s)
    draw.text((250, 345), str(stats['deaths']), fill=white, font=font_m)
    draw.text((450, 320), "KDR", fill=yellow, font=font_s)
    draw.text((450, 345), str(stats['kdr']), fill=green, font=font_m)

    # INFORMAZIONI LATERALI (Destra)
    draw.text((680, 250), "INFORMATION", fill=white, font=font_m)
    draw.text((680, 280), f"Friends: {stats['friends']}", fill=white, font=font_s)
    draw.text((680, 350), "CLAN", fill=white, font=font_m)
    draw.text((680, 380), stats['clan'], fill=white, font=font_s)

    # Titolo Basso
    draw.text((300, 500), "BEDWARS STATS", fill="#FF5500", font=font_title)

    # Aggiunta Skin 3D (Opzionale, scarica l'avatar)
    try:
        skin_url = f"https://visage.surgeplay.com/full/250/{stats['username']}"
        skin_img = Image.open(requests.get(skin_url, stream=True).raw).convert("RGBA")
        img.paste(skin_img, (750, 80), skin_img)
    except: pass

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
