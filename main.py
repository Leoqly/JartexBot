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

active_requests = {}

# Mappatura per le API di Jartex
MODE_MAP = {
    "overall": "overall", "solo": "solos", "solos": "solos",
    "double": "doubles", "doubles": "doubles",
    "quad": "teams_of_four", "quads": "teams_of_four", "threes": "teams_of_three"
}

def get_level_color(level):
    """Colori dinamici basati sul prestigio (Max 130)"""
    if level < 30: return "#FFFFFF"
    if level < 60: return "#55FF55"
    if level < 90: return "#FFAA00"
    if level < 120: return "#FF5555"
    return "#AA00AA"

# --- RECUPERO DATI REALI ---

def fetch_data(username, interval="alltime", mode="overall"):
    try:
        url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
        data = r.json()

        # Navigazione nel JSON per trovare le BedWars
        bw_root = data.get("stats", {}).get("BedWars", {})
        
        # Selezione dell'intervallo (weekly, monthly, alltime)
        time_node = bw_root.get(interval, {})
        # Selezione della modalità
        mode_key = MODE_MAP.get(mode.lower(), "overall")
        target = time_node.get(mode_key, {})

        # Se i dati sono vuoti (es. mai giocato weekly), usa 0 invece di crashare
        return {
            "user": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank_name": data.get("rank", {}).get("displayName", "Player"),
            "clan": data.get("clan", {}),
            "friends": len(data.get("friends", [])),
            "wins": target.get("wins", 0),
            "losses": target.get("losses", 0),
            "kills": target.get("kills", 0),
            "deaths": target.get("deaths", 0),
            "beds": target.get("beds_destroyed", 0),
            "streak": target.get("current_streak", 0),
            "wlr": round(target.get("wins", 0) / max(target.get("losses", 1), 1), 2),
            "fkdr": round(target.get("kills", 0) / max(target.get("deaths", 1), 1), 2)
        }
    except Exception as e:
        print(f"Errore API: {e}")
        return None

# --- GRAFICA AVANZATA ---

def create_card(s, interval, mode):
    try:
        base = Image.open("sfondo.png").convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        
        # Box grafici
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 130)) 
        d_ov.rectangle([635, 115, 985, 470], fill=(0, 0, 0, 160))
        base = Image.alpha_composite(base, overlay)
        
        draw = ImageDraw.Draw(base)
        f_title = ImageFont.truetype("Minecraft.ttf", 40)
        f_head = ImageFont.truetype("Minecraft.ttf", 26)
        f_data = ImageFont.truetype("Minecraft.ttf", 21)
        f_small = ImageFont.truetype("Minecraft.ttf", 16)

        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"

        # Intestazione
        draw.text((50, 40), f"{s['rank_name']} {s['user']}", fill=white, font=f_head)
        draw.text((base.width - 120, 35), str(s['level']), fill=get_level_color(s['level']), font=f_title)

        # Griglia Statistiche
        grid = [
            (80, 145, "WINS", s['wins'], green), (270, 145, "LOSSES", s['losses'], red), (460, 145, "WLR", s['wlr'], gold),
            (80, 265, "KILLS", s['kills'], green), (270, 265, "DEATHS", s['deaths'], red), (460, 265, "FKDR", s['fkdr'], gold),
            (80, 385, "BEDS BROKEN", s['beds'], green), (460, 385, "STREAK", s['streak'], gold)
        ]
        for x, y, lbl, val, col in grid:
            draw.text((x, y), lbl, fill=col, font=f_small)
            draw.text((x, y+22), str(val), fill=white, font=f_data)

        # Clan & Info
        clan = s['clan']
        owner = clan.get("owner", {})
        leader = owner.get("username", "N/A") if isinstance(owner, dict) else str(owner)
        
        draw.text((660, 140), "INFORMATION", fill=gold, font=f_head)
        draw.text((660, 185), f"Friends: {s['friends']}", fill=white, font=f_data)
        draw.text((660, 265), "CLAN", fill=gold, font=f_head)
        draw.text((660, 305), f"Tag: {clan.get('name', 'None')}", fill=white, font=f_small)
        draw.text((660, 335), f"Leader: {leader}", fill=white, font=f_small)
        draw.text((660, 365), f"Members: {clan.get('membersCount', 'N/A')}", fill=white, font=f_small)

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

# --- COMANDI DISCORD ---

@bot.command(aliases=['bw'])
async def bedwars(ctx, user: str, *args):
    # Parsing parametri (es: !bw qlyleo weekly solos)
    interval = next((a for a in args if a.lower() in ["weekly", "monthly", "alltime"]), "alltime")
    mode = next((a for a in args if a.lower() in ["solo", "solos", "double", "doubles", "quad", "quads"]), "overall")

    msg = await ctx.send(f"🛰️ Recupero dati reali per **{user}** ({interval} {mode})...")
    
    data = fetch_data(user, interval, mode)
    if data:
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, create_card, data, interval, mode)
        await msg.delete()
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))
    else:
        await msg.edit(content=f"❌ Errore: Giocatore **{user}** non trovato.")

@bot.command()
async def top(ctx):
    """Classifica reale aggiornata dalle API di Jartex"""
    try:
        url = "https://stats.jartexnetwork.com/api/leaderboards/BedWars/wins/alltime"
        lb = requests.get(url, timeout=5).json()[:10]
        
        embed = discord.Embed(title="🏆 Jartex Bedwars Global Leaderboard", color=0xFFAA00)
        desc = ""
        for i, p in enumerate(lb, 1):
            desc += f"**#{i} {p['username']}** • {p['value']} Wins\n"
        embed.description = desc
        embed.set_footer(text=f"Aggiornato: {datetime.now().strftime('%H:%M:%S')}")
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌ Impossibile caricare la Top 10 reale.")

@bot.command()
async def clan(ctx, user: str):
    data = fetch_data(user)
    if data and data['clan'].get('name'):
        c = data['clan']
        embed = discord.Embed(title=f"🛡️ Clan: {c.get('name')}", color=0x55FF55)
        embed.add_field(name="Leader", value=c.get("owner", {}).get("username", "N/A"))
        embed.add_field(name="Membri", value=c.get("membersCount", "N/A"))
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {user} non è in un clan.")

bot.run(TOKEN)
