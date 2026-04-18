import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import asyncio
from datetime import datetime

# --- CONFIGURAZIONE ---
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cache per evitare che Railway risponda due volte
active_requests = {}

# --- MAPPA MODALITÀ API ---
# Jartex usa nomi interni diversi per le modalità
MODE_MAP = {
    "overall": "overall",
    "solo": "solos",
    "solos": "solos",
    "double": "doubles",
    "doubles": "doubles",
    "quad": "teams_of_four",
    "quads": "teams_of_four"
}

# --- FUNZIONI DI SUPPORTO ---

def get_level_color(level):
    if level < 30: return "#FFFFFF"
    if level < 60: return "#55FF55"
    if level < 90: return "#FFAA00"
    if level < 120: return "#FF5555"
    return "#AA00AA"

def fetch_jartex_data(username):
    """Scarica il profilo completo."""
    try:
        url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def extract_bedwars_stats(data, interval, mode):
    """
    Tenta di estrarre le statistiche Bedwars reali.
    Nota: Se Jartex non fornisce il nodo specifico nel profilo, 
    usa i dati globali per non lasciare i campi vuoti.
    """
    # Navigazione nel JSON complesso di Jartex
    game_stats = data.get("stats", {}).get("BedWars", {})
    
    # Cerchiamo il nodo corretto (es. stats['BedWars']['weekly']['solos'])
    target = game_stats.get(interval, {}).get(MODE_MAP.get(mode, "overall"), {})
    
    # Se il nodo è vuoto (es. non hai giocato questa settimana), restituisce 0
    return {
        "wins": target.get("wins", 0),
        "losses": target.get("losses", 0),
        "kills": target.get("kills", 0),
        "deaths": target.get("deaths", 0),
        "beds": target.get("beds_destroyed", 0),
        "ws": target.get("current_streak", 0),
        "wlr": round(target.get("wins", 0) / max(target.get("losses", 1), 1), 2),
        "fkdr": round(target.get("kills", 0) / max(target.get("deaths", 1), 1), 2)
    }

# --- DISEGNO CARD ---

def create_card(profile, interval, mode):
    try:
        # Estrazione stats reali
        bw = extract_bedwars_stats(profile, interval, mode)
        
        base = Image.open("sfondo.png").convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        
        # Box grafici complessi
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 140)) 
        d_ov.rectangle([640, 115, 980, 470], fill=(0, 0, 0, 170))
        base = Image.alpha_composite(base, overlay)
        
        draw = ImageDraw.Draw(base)
        f_title = ImageFont.truetype("Minecraft.ttf", 40)
        f_head = ImageFont.truetype("Minecraft.ttf", 26)
        f_val = ImageFont.truetype("Minecraft.ttf", 22)
        f_small = ImageFont.truetype("Minecraft.ttf", 16)
        
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"
        lvl = profile.get("rank", {}).get("level", 0)

        # Header
        draw.text((50, 40), f"{profile.get('username')}", fill=white, font=f_head)
        draw.text((base.width - 120, 35), str(lvl), fill=get_level_color(lvl), font=f_title)

        # Griglia Stats Reali
        grid = [
            (80, 145, "WINS", bw['wins'], green), (270, 145, "LOSSES", bw['losses'], red), (460, 145, "WLR", bw['wlr'], gold),
            (80, 265, "KILLS", bw['kills'], green), (270, 265, "DEATHS", bw['deaths'], red), (460, 265, "FKDR", bw['fkdr'], gold),
            (80, 385, "BEDS BROKEN", bw['beds'], green), (460, 385, "STREAK", bw['ws'], gold)
        ]
        
        for x, y, lbl, val, col in grid:
            draw.text((x, y), lbl, fill=col, font=f_small)
            draw.text((x, y+22), str(val), fill=white, font=f_val)

        # Clan & Info
        clan = profile.get("clan", {})
        leader = clan.get("owner", {}).get("username", "N/A") if isinstance(clan.get("owner"), dict) else "N/A"
        
        draw.text((660, 140), "INFORMATION", fill=gold, font=f_head)
        draw.text((660, 180), f"Friends: {len(profile.get('friends', []))}", fill=white, font=f_val)
        draw.text((660, 260), "CLAN", fill=gold, font=f_head)
        draw.text((660, 300), f"Tag: {clan.get('name', 'None')}", fill=white, font=f_small)
        draw.text((660, 330), f"Leader: {leader}", fill=white, font=f_small)
        draw.text((660, 360), f"Members: {clan.get('membersCount', 1)}", fill=white, font=f_small)

        # Footer Dinamico
        footer = f"BEDWARS {interval.upper()} {mode.upper()}"
        draw.text((base.width//2 - 130, base.height - 70), footer, fill=gold, font=f_head)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore Card: {e}")
        return None

# --- COMANDI ---

@bot.command(aliases=['bw'])
async def bedwars(ctx, user: str, *args):
    # Logica per estrarre interval e mode dagli argomenti
    interval = next((a for a in args if a.lower() in ["weekly", "monthly", "alltime"]), "alltime")
    mode = next((a for a in args if a.lower() in ["solo", "solos", "double", "doubles", "quad", "quads"]), "overall")

    msg = await ctx.send(f"🛰️ Caricamento dati **{interval} {mode}** per {user}...")
    
    data = fetch_jartex_data(user)
    if data:
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, create_card, data, interval, mode)
        if buf:
            await msg.delete()
            await ctx.send(file=discord.File(buf, f"{user}.png"))
        else:
            await msg.edit(content="❌ Errore nella generazione grafica.")
    else:
        await msg.edit(content="❌ Giocatore non trovato.")

@bot.command()
async def top(ctx):
    """Tenta di recuperare la Top 10 reale dal server."""
    msg = await ctx.send("⏳ Recupero classifica globale Bedwars...")
    
    # Jartex ha un endpoint per le leaderboards
    try:
        url = "https://stats.jartexnetwork.com/api/leaderboards/BedWars/wins/alltime"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            lb_data = r.json()[:10] # Prendi i primi 10
            embed = discord.Embed(title="🏆 Jartex Bedwars Global Leaderboard", color=0xFFAA00)
            desc = ""
            for i, p in enumerate(lb_data, 1):
                desc += f"**#{i} {p['username']}** • {p['value']} Wins\n"
            embed.description = desc
            await msg.edit(content=None, embed=embed)
        else:
            await msg.edit(content="❌ Impossibile caricare la Top 10 reale al momento.")
    except:
        await msg.edit(content="❌ Errore di connessione alle API.")

bot.run(TOKEN)
