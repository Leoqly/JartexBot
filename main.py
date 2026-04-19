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

# Mappa per tradurre i termini dell'utente in chiavi API Jartex
MODE_MAP = {
    "overall": "overall", "solo": "solos", "solos": "solos",
    "double": "doubles", "doubles": "doubles",
    "quad": "teams_of_four", "quads": "teams_of_four", "threes": "teams_of_three"
}

def get_level_color(level):
    if level < 30: return "#FFFFFF"
    if level < 60: return "#55FF55"
    if level < 90: return "#FFAA00"
    if level < 120: return "#FF5555"
    return "#AA00AA"

def extract_bw_stats(data, interval, mode):
    """Estrae i dati con sistema di fallback per evitare gli '0'."""
    bw_root = data.get("stats", {}).get("BedWars", {})
    
    # Prova a prendere l'intervallo richiesto (weekly/monthly/alltime)
    time_node = bw_root.get(interval, {})
    if not time_node and interval != "alltime":
        time_node = bw_root.get("alltime", {}) # Fallback se l'intervallo è vuoto

    mode_key = MODE_MAP.get(mode.lower(), "overall")
    stats = time_node.get(mode_key, {})

    # Se dopo il filtro è ancora tutto vuoto, prendiamo i dati globali del profilo
    if not stats or stats.get("wins") is None:
        stats = bw_root.get("overall", {})

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
        bw = extract_bw_stats(profile, interval, mode)
        base = Image.open("sfondo.png").convert("RGBA")
        
        # Overlay Box
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 135)) 
        d_ov.rectangle([635, 115, 985, 470], fill=(0, 0, 0, 165))
        base = Image.alpha_composite(base, overlay)
        
        draw = ImageDraw.Draw(base)
        f_title = ImageFont.truetype("Minecraft.ttf", 40)
        f_head = ImageFont.truetype("Minecraft.ttf", 26)
        f_val = ImageFont.truetype("Minecraft.ttf", 22)
        f_small = ImageFont.truetype("Minecraft.ttf", 16)
        
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"

        # Header
        lvl = profile.get("rank", {}).get("level", 0)
        draw.text((50, 40), f"{profile.get('username')}", fill=white, font=f_head)
        draw.text((base.width - 120, 35), str(lvl), fill=get_level_color(lvl), font=f_title)

        # Griglia Stats
        grid = [
            (80, 145, "WINS", bw['wins'], green), (270, 145, "LOSSES", bw['losses'], red), (460, 145, "WLR", bw['wlr'], gold),
            (80, 265, "KILLS", bw['kills'], green), (270, 265, "DEATHS", bw['deaths'], red), (460, 265, "FKDR", bw['fkdr'], gold),
            (80, 385, "BEDS BROKEN", bw['beds'], green), (460, 385, "STREAK", bw['ws'] if 'ws' in bw else bw['streak'], gold)
        ]
        for x, y, lbl, val, col in grid:
            draw.text((x, y), lbl, fill=col, font=f_small)
            draw.text((x, y+22), str(val), fill=white, font=f_val)

        # Sezione Clan reale
        clan = profile.get("clan", {})
        leader = "N/A"
        if clan.get("owner"):
            leader = clan["owner"].get("username", "N/A") if isinstance(clan["owner"], dict) else clan["owner"]
        
        draw.text((660, 140), "INFORMATION", fill=gold, font=f_head)
        draw.text((660, 185), f"Friends: {len(profile.get('friends', []))}", fill=white, font=f_val)
        draw.text((660, 265), "CLAN", fill=gold, font=f_head)
        draw.text((660, 305), f"Tag: {clan.get('name', 'None')}", fill=white, font=f_small)
        draw.text((660, 335), f"Leader: {leader}", fill=white, font=f_small)
        draw.text((660, 365), f"Members: {clan.get('membersCount', 'N/A')}", fill=white, font=f_small)

        # Footer
        footer = f"BW {interval.upper()} {mode.upper()}"
        draw.text((base.width//2 - 130, base.height - 70), footer, fill=gold, font=f_head)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore: {e}")
        return None

@bot.command(aliases=['bw'])
async def bedwars(ctx, user: str, *args):
    interval = next((a for a in args if a.lower() in ["weekly", "monthly", "alltime"]), "alltime")
    mode = next((a for a in args if a.lower() in ["solo", "solos", "double", "doubles", "quad", "quads"]), "overall")

    msg = await ctx.send(f"⏳ Analisi Jartex per **{user}**...")
    
    r = requests.get(f"https://stats.jartexnetwork.com/api/profile/{user}")
    if r.status_code == 200:
        data = r.json()
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, create_card, data, interval, mode)
        await msg.delete()
        await ctx.send(file=discord.File(buf, f"{user}.png"))
    else:
        await msg.edit(content="❌ Utente non trovato.")

@bot.command()
async def top(ctx):
    try:
        # Recupero classifica REALE
        lb = requests.get("https://stats.jartexnetwork.com/api/leaderboards/BedWars/wins/alltime").json()[:10]
        embed = discord.Embed(title="🏆 Jartex Bedwars Top 10", color=0xFFAA00)
        desc = ""
        for i, p in enumerate(lb, 1):
            desc += f"**#{i} {p['username']}** • {p['value']} Wins\n"
        embed.description = desc
        embed.set_footer(text=f"Aggiornato: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌ API Classifica non raggiungibile.")

bot.run(TOKEN)
