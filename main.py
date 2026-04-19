import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import asyncio
from datetime import datetime

TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Mappatura modalità Jartex
MODE_MAP = {
    "solo": "solos", "solos": "solos",
    "double": "doubles", "doubles": "doubles",
    "quad": "teams_of_four", "quads": "teams_of_four",
    "overall": "overall"
}

def get_stats_safely(data, interval, mode):
    """Scava nel JSON di Jartex per trovare i dati reali."""
    bw_root = data.get("stats", {}).get("BedWars", {})
    
    # Navigazione gerarchica: [interval][mode]
    # Se chiedi weekly quads, cerca in bw_root['weekly']['teams_of_four']
    time_node = bw_root.get(interval, {})
    mode_key = MODE_MAP.get(mode.lower(), "overall")
    stats = time_node.get(mode_key, {})

    # Se i dati sono 0 o mancanti, prova il fallback su 'alltime' dello stesso tipo
    if not stats or stats.get("wins", 0) == 0:
        stats = bw_root.get("alltime", {}).get(mode_key, {})
    
    # Se è ancora tutto 0, prendi i dati generali 'overall'
    if not stats or stats.get("wins", 0) == 0:
        stats = bw_root.get("alltime", {}).get("overall", {})

    return {
        "wins": stats.get("wins", 0),
        "losses": stats.get("losses", 0),
        "kills": stats.get("kills", 0),
        "deaths": stats.get("deaths", 0),
        "beds": stats.get("beds_destroyed", 0),
        "streak": stats.get("current_streak", 0),
        "wlr": round(stats.get("wins", 0) / max(stats.get("losses", 1), 1), 2),
        "fkdr": round(stats.get("kills", 0) / max(stats.get("deaths", 1), 1), 2)
    }

def create_card(profile, interval, mode):
    try:
        s = get_stats_safely(profile, interval, mode)
        base = Image.open("sfondo.png").convert("RGBA")
        
        # Disegno Box
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 140)) # Box Stats
        d_ov.rectangle([640, 115, 980, 470], fill=(0, 0, 0, 170)) # Box Info
        base = Image.alpha_composite(base, overlay)
        
        draw = ImageDraw.Draw(base)
        f_title = ImageFont.truetype("Minecraft.ttf", 40)
        f_head = ImageFont.truetype("Minecraft.ttf", 26)
        f_data = ImageFont.truetype("Minecraft.ttf", 22)
        f_small = ImageFont.truetype("Minecraft.ttf", 16)
        
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"

        # Intestazione Nome e Livello
        user = profile.get("username", "Unknown")
        lvl = profile.get("rank", {}).get("level", 0)
        draw.text((50, 40), f"{profile.get('rank', {}).get('displayName', 'Player')} {user}", fill=white, font=f_head)
        draw.text((base.width - 120, 35), str(lvl), fill=gold, font=f_title)

        # Griglia Stats Reali
        grid = [
            (80, 145, "WINS", s['wins'], green), (270, 145, "LOSSES", s['losses'], red), (460, 145, "WLR", s['wlr'], gold),
            (80, 265, "KILLS", s['kills'], green), (270, 265, "DEATHS", s['deaths'], red), (460, 265, "FKDR", s['fkdr'], gold),
            (80, 385, "BEDS BROKEN", s['beds'], green), (460, 385, "STREAK", s['streak'], gold)
        ]
        for x, y, lbl, val, col in grid:
            draw.text((x, y), lbl, fill=col, font=f_small)
            draw.text((x, y+22), str(val), fill=white, font=f_data)

        # Clan & Information
        clan = profile.get("clan", {})
        leader = "N/A"
        if isinstance(clan.get("owner"), dict):
            leader = clan["owner"].get("username", "N/A")
        elif clan.get("owner"):
            leader = str(clan["owner"])

        draw.text((660, 140), "INFORMATION", fill=gold, font=f_head)
        draw.text((660, 185), f"Friends: {len(profile.get('friends', []))}", fill=white, font=f_data)
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
        print(f"Errore generazione: {e}")
        return None

# --- COMANDI ---

@bot.command(aliases=['bw'])
async def bedwars(ctx, user: str, *args):
    interval = next((a for a in args if a.lower() in ["weekly", "monthly", "alltime"]), "alltime")
    mode = next((a for a in args if a.lower() in ["solo", "solos", "double", "doubles", "quad", "quads"]), "overall")

    msg = await ctx.send(f"🛰️ Recupero stats **{interval} {mode}** per {user}...")
    
    r = requests.get(f"https://stats.jartexnetwork.com/api/profile/{user}")
    if r.status_code == 200:
        data = r.json()
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, create_card, data, interval, mode)
        await msg.delete()
        await ctx.send(file=discord.File(buf, f"{user}.png"))
    else:
        await msg.edit(content="❌ Giocatore non trovato.")

@bot.command()
async def clan(ctx, user: str):
    r = requests.get(f"https://stats.jartexnetwork.com/api/profile/{user}")
    if r.status_code == 200:
        c = r.json().get("clan", {})
        if c.get("name"):
            owner = c.get("owner", {})
            leader = owner.get("username", "N/A") if isinstance(owner, dict) else str(owner)
            embed = discord.Embed(title=f"🛡️ Clan: {c['name']}", color=0x55FF55)
            embed.add_field(name="Leader", value=leader, inline=True)
            embed.add_field(name="Membri", value=c.get("membersCount", "N/A"), inline=True)
            await ctx.send(embed=embed)
        else: await ctx.send("❌ Il giocatore non è in un clan.")
    else: await ctx.send("❌ Errore API.")

@bot.command()
async def top(ctx):
    try:
        # Recupero classifica REALE Bedwars Wins
        r = requests.get("https://stats.jartexnetwork.com/api/leaderboards/BedWars/wins/alltime")
        lb = r.json()[:10]
        embed = discord.Embed(title="🏆 Jartex Global Top 10 Wins", color=0xFFAA00)
        desc = ""
        for i, p in enumerate(lb, 1):
            desc += f"**#{i} {p['username']}** • {p['value']} Wins\n"
        embed.description = desc
        await ctx.send(embed=embed)
    except: await ctx.send("❌ Classifica non disponibile.")

bot.run(TOKEN)
