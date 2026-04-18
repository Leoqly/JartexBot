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

# Cache per evitare duplicati
active_requests = {}

# Mappatura corretta per le API di Jartex
MODE_MAP = {
    "overall": "overall", "solo": "solos", "solos": "solos",
    "double": "doubles", "doubles": "doubles",
    "quad": "teams_of_four", "quads": "teams_of_four", "threes": "teams_of_three"
}

# --- LOGICA RECUPERO DATI ---

def get_jartex_data(username):
    try:
        # Endpoint profilo principale
        url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def extract_stats(data, interval, mode):
    """Estrae i dati BedWars dal JSON complesso."""
    # Jartex mette tutto sotto 'stats' -> 'BedWars'
    all_games = data.get("stats", {})
    bw_data = all_games.get("BedWars", {})
    
    # Se cerchiamo 'weekly' o 'monthly', Jartex li separa
    time_node = bw_data.get(interval, {})
    mode_key = MODE_MAP.get(mode, "overall")
    stats = time_node.get(mode_key, {})

    if not stats and interval == "alltime":
        # Se non trova la modalità specifica, prova a prendere i dati generali
        stats = bw_data.get("overall", {})

    return {
        "wins": stats.get("wins", 0),
        "losses": stats.get("losses", 0),
        "kills": stats.get("kills", 0),
        "deaths": stats.get("deaths", 0),
        "beds": stats.get("beds_destroyed", 0),
        "ws": stats.get("current_streak", 0),
        "wlr": round(stats.get("wins", 0) / max(stats.get("losses", 1), 1), 2),
        "fkdr": round(stats.get("kills", 0) / max(stats.get("deaths", 1), 1), 2)
    }

# --- DISEGNO CARD ---

def create_card(profile, interval, mode):
    try:
        bw = extract_stats(profile, interval, mode)
        base = Image.open("sfondo.png").convert("RGBA")
        
        # Overlay Box
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 130)) 
        d_ov.rectangle([635, 115, 985, 470], fill=(0, 0, 0, 160))
        base = Image.alpha_composite(base, overlay)
        
        draw = ImageDraw.Draw(base)
        f_title = ImageFont.truetype("Minecraft.ttf", 40)
        f_head = ImageFont.truetype("Minecraft.ttf", 26)
        f_val = ImageFont.truetype("Minecraft.ttf", 21)
        f_small = ImageFont.truetype("Minecraft.ttf", 16)
        
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"
        lvl = profile.get("rank", {}).get("level", 0)

        # Header
        draw.text((50, 40), profile.get("username", "Unknown"), fill=white, font=f_head)
        draw.text((base.width - 120, 35), str(lvl), fill=gold, font=f_title)

        # Grid
        grid = [
            (80, 145, "WINS", bw['wins'], green), (270, 145, "LOSSES", bw['losses'], red), (460, 145, "WLR", bw['wlr'], gold),
            (80, 265, "KILLS", bw['kills'], green), (270, 265, "DEATHS", bw['deaths'], red), (460, 265, "FKDR", bw['fkdr'], gold),
            (80, 385, "BEDS BROKEN", bw['beds'], green), (460, 385, "STREAK", bw['ws'], gold)
        ]
        for x, y, lbl, val, col in grid:
            draw.text((x, y), lbl, fill=col, font=f_small)
            draw.text((x, y+22), str(val), fill=white, font=f_val)

        # Clan (Logica corretta)
        clan = profile.get("clan", {})
        leader = "N/A"
        if clan.get("owner"):
            leader = clan["owner"].get("username", "N/A") if isinstance(clan["owner"], dict) else clan["owner"]
        
        draw.text((660, 140), "INFORMATION", fill=gold, font=f_head)
        draw.text((660, 180), f"Friends: {len(profile.get('friends', []))}", fill=white, font=f_val)
        draw.text((660, 260), "CLAN", fill=gold, font=f_head)
        draw.text((660, 300), f"Tag: {clan.get('name', 'None')}", fill=white, font=f_small)
        draw.text((660, 330), f"Leader: {leader}", fill=white, font=f_small)
        draw.text((660, 360), f"Members: {clan.get('membersCount', 'N/A')}", fill=white, font=f_small)

        # Footer
        footer = f"BW {interval.upper()} {mode.upper()}"
        draw.text((base.width//2 - 120, base.height - 70), footer, fill=gold, font=f_head)

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
    interval = next((a for a in args if a.lower() in ["weekly", "monthly", "alltime"]), "alltime")
    mode = next((a for a in args if a.lower() in ["solo", "solos", "double", "doubles", "quad", "quads"]), "overall")

    msg = await ctx.send(f"🛰️ Analisi dati {user}...")
    data = get_jartex_data(user)
    
    if data:
        buf = create_card(data, interval, mode)
        if buf:
            await msg.delete()
            await ctx.send(file=discord.File(buf, f"{user}.png"))
        else:
            await msg.edit(content="❌ Errore nella grafica.")
    else:
        await msg.edit(content="❌ Player non trovato.")

@bot.command()
async def clan(ctx, user: str):
    data = get_jartex_data(user)
    if data and data.get("clan"):
        c = data["clan"]
        leader = c["owner"].get("username", "N/A") if isinstance(c.get("owner"), dict) else "N/A"
        embed = discord.Embed(title=f"🛡️ Clan: {c.get('name')}", color=0x55FF55)
        embed.add_field(name="Leader", value=leader, inline=True)
        embed.add_field(name="Membri", value=c.get("membersCount", "N/A"), inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {user} non ha un clan.")

@bot.command()
async def top(ctx):
    """Questa volta proviamo l'endpoint alternativo per la Top 10."""
    try:
        # Jartex leaderboard Bedwars (Wins Alltime)
        url = "https://stats.jartexnetwork.com/api/leaderboards/BedWars/wins/alltime"
        r = requests.get(url, timeout=10)
        lb = r.json()[:10]
        
        embed = discord.Embed(title="🏆 Jartex Bedwars Top 10 (Wins)", color=0xFFAA00)
        desc = ""
        for i, p in enumerate(lb, 1):
            desc += f"**#{i} {p['username']}** • {p['value']} Wins\n"
        embed.description = desc
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌ API Leaderboard temporaneamente offline.")

bot.run(TOKEN)
