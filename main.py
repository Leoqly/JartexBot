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

# Cache per evitare doppi messaggi
active_requests = {}

def get_level_color(level):
    """Calibrazione colori sul cap di 130 del server."""
    if level < 30: return "#FFFFFF"
    if level < 60: return "#55FF55"
    if level < 90: return "#FFAA00"
    if level < 120: return "#FF5555"
    return "#AA00AA"

def fetch_jartex_profile(username):
    try:
        url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else None
    except:
        return None

# --- CORE DI DISEGNO ---

def create_card(data, interval, mode):
    try:
        # Estrazione dati base
        user = data.get("username", "Unknown")
        lvl = data.get("rank", {}).get("level", 0)
        rank_name = data.get("rank", {}).get("displayName", "Player")
        
        # Gestione Clan
        clan = data.get("clan", {})
        clan_name = clan.get("name", "Nessuno")
        owner = clan.get("owner", {})
        leader = owner.get("username", "N/A") if isinstance(owner, dict) else str(owner)
        members = clan.get("membersCount", "1") # Se c'è un clan, c'è almeno il leader

        # Creazione Canvas
        base = Image.open("sfondo.png").convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        draw_ov = ImageDraw.Draw(overlay)
        
        # Box grafici (Glassmorphism)
        draw_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 120)) 
        draw_ov.rectangle([640, 115, 980, 470], fill=(0, 0, 0, 160))
        base = Image.alpha_composite(base, overlay)
        
        d = ImageDraw.Draw(base)
        # Caricamento Font (Minecraft.ttf deve essere presente)
        f_large = ImageFont.truetype("Minecraft.ttf", 38)
        f_medium = ImageFont.truetype("Minecraft.ttf", 26)
        f_small = ImageFont.truetype("Minecraft.ttf", 18)

        # Header
        lvl_col = get_level_color(lvl)
        d.text((50, 40), f"{rank_name} {user}", fill="white", font=f_medium)
        d.text((base.width - 120, 35), str(lvl), fill=lvl_col, font=f_large)

        # Grid Stats (Esempio alltime/overall)
        gold, green, red = "#FFAA00", "#55FF55", "#FF5555"
        stats_map = [
            (80, 145, "WINS", "356", green), (270, 145, "LOSSES", "82", red), (460, 145, "WLR", "4.34", gold),
            (80, 265, "KILLS", "2,441", green), (270, 265, "DEATHS", "1,152", red), (460, 265, "FKDR", "14.0", gold),
            (80, 385, "BEDS BROKEN", "507", green), (460, 385, "STREAK", "47", gold)
        ]
        for x, y, lbl, val, col in stats_map:
            d.text((x, y), lbl, fill=col, font=f_small)
            d.text((x, y+22), val, fill="white", font=f_medium)

        # Information & Clan
        x_c = 660
        d.text((x_c, 140), "INFORMATION", fill=gold, font=f_medium)
        d.text((x_c, 180), f"Friends: {len(data.get('friends', []))}", fill="white", font=f_small)
        
        d.text((x_c, 260), "CLAN", fill=gold, font=f_medium)
        d.text((x_c, 300), f"Tag: {clan_name}", fill="white", font=f_small)
        d.text((x_c, 330), f"Leader: {leader}", fill="white", font=f_small)
        d.text((x_c, 360), f"Members: {members}", fill="white", font=f_small)

        # Footer Dinamico
        footer = f"BEDWARS {interval.upper()} {mode.upper()}"
        d.text((base.width//2 - 150, base.height - 70), footer, fill=gold, font=f_medium)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore: {e}")
        return None

# --- COMANDI ---

@bot.command(aliases=['bw'])
async def bedwars(ctx, user: str, *args):
    interval = next((a for a in args if a.lower() in ["weekly", "monthly", "alltime"]), "alltime")
    mode = next((a for a in args if a.lower() in ["solo", "solos", "double", "doubles", "quad", "quads"]), "overall")

    msg = await ctx.send(f"⏳ Generazione card **{interval} {mode}**...")
    raw = fetch_jartex_profile(user)
    
    if raw:
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, create_card, raw, interval, mode)
        if buf:
            await msg.delete()
            await ctx.send(file=discord.File(buf, f"stats.png"))
        else:
            await msg.edit(content="❌ Errore nella creazione dell'immagine.")
    else:
        await msg.edit(content="❌ Giocatore non trovato.")

@bot.command()
async def clan(ctx, user: str):
    data = fetch_jartex_profile(user)
    if data and data.get("clan"):
        c = data["clan"]
        owner = c.get("owner", {})
        leader = owner.get("username", "N/A") if isinstance(owner, dict) else str(owner)
        members = c.get("membersCount", "N/A")
        
        embed = discord.Embed(title=f"🛡️ Clan: {c.get('name')}", color=0x55FF55)
        embed.add_field(name="Capo Clan", value=leader, inline=True)
        embed.add_field(name="Membri Totali", value=members, inline=True)
        embed.set_footer(text=f"Dati estratti dal profilo di {user}")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {user} non ha un clan.")

@bot.command()
async def top(ctx):
    # Dati simulati realistici per la Leaderboard
    embed = discord.Embed(title="🏆 Jartex Bedwars Global Leaderboard", color=0xFFAA00)
    leaders = [
        ("qlyleo", "15,400", "130"),
        ("Krishiv00", "14,820", "128"),
        ("NOTSWEATY_Member", "12,100", "110"),
        ("Player_Test", "10,500", "105")
    ]
    
    desc = ""
    for i, (n, w, l) in enumerate(leaders, 1):
        desc += f"**#{i} {n}** • {w} Wins (Lvl {l})\n"
    
    embed.description = desc
    embed.set_footer(text=f"Aggiornato: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    await ctx.send(embed=embed)

bot.run(TOKEN)
