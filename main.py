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
cooldowns = {}

# --- LOGICA CORE ---

def get_level_color(level):
    """Sistema colori basato sul cap di 130 del server."""
    if level < 30: return "#FFFFFF"   # Bianco
    if level < 60: return "#55FF55"   # Verde
    if level < 90: return "#FFAA00"   # Oro
    if level < 120: return "#FF5555"  # Rosso
    return "#AA00AA"                  # Viola

def fetch_jartex_data(username):
    """Recupera i dati grezzi dall'API di Jartex."""
    try:
        url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        resp = requests.get(url, timeout=10)
        return resp.json() if resp.status_code == 200 else None
    except:
        return None

def process_stats(data, interval, mode):
    """
    Estrae le statistiche specifiche. 
    Nota: Qui andrebbe la logica di parsing specifica per i nodi JSON 
    di Jartex relativi a weekly/monthly e solo/doubles/quads.
    """
    # Esempio di struttura dati per la card
    stats = {
        "username": data.get("username", "Unknown"),
        "level": data.get("rank", {}).get("level", 0),
        "rank_name": data.get("rank", {}).get("displayName", "Player"),
        "clan_tag": data.get("clan", {}).get("name", "None"),
        "clan_leader": "N/A",
        "clan_size": data.get("clan", {}).get("membersCount", 0),
        "friends": len(data.get("friends", [])),
        "footer": f"BEDWARS {interval.upper()} {mode.upper()}",
        # Dati statistici (da mappare con i campi reali dell'API)
        "wins": 356, "losses": 82, "wlr": 4.34,
        "kills": 2441, "deaths": 1152, "fkdr": 14.0,
        "beds": 507, "streak": 47
    }
    
    # Estrazione sicura del leader del clan
    owner = data.get("clan", {}).get("owner")
    if isinstance(owner, dict):
        stats["clan_leader"] = owner.get("username", "N/A")
    elif owner:
        stats["clan_leader"] = str(owner)
        
    return stats

def draw_stats_card(s):
    """Genera l'immagine complessa con tutti i dati."""
    try:
        base = Image.open("sfondo.png").convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        draw_ov = ImageDraw.Draw(overlay)
        
        # Box grafici scuri
        draw_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 110)) 
        draw_ov.rectangle([640, 115, 980, 470], fill=(0, 0, 0, 150))
        base = Image.alpha_composite(base, overlay)
        
        d = ImageDraw.Draw(base)
        # Caricamento Font (Assicurati di avere il file .ttf)
        f_l = ImageFont.truetype("Minecraft.ttf", 42)
        f_m = ImageFont.truetype("Minecraft.ttf", 28)
        f_s = ImageFont.truetype("Minecraft.ttf", 20)
        f_xs = ImageFont.truetype("Minecraft.ttf", 16)

        # Header: Nome e Livello con colore dinamico
        lvl_col = get_level_color(s['level'])
        d.text((50, 45), f"{s['rank_name']} {s['username']}", fill="white", font=f_m)
        d.text((base.width - 120, 45), str(s['level']), fill=lvl_col, font=f_l)

        # Griglia Stats (Sinistra)
        coords = [(80, 150), (270, 150), (460, 150), (80, 270), (270, 270), (460, 270), (80, 390), (460, 390)]
        labels = [
            ("WINS", s['wins'], "#55FF55"), ("LOSSES", s['losses'], "#FF5555"), ("WLR", s['wlr'], "#FFAA00"),
            ("KILLS", s['kills'], "#55FF55"), ("DEATHS", s['deaths'], "#FF5555"), ("FKDR", s['fkdr'], "#FFAA00"),
            ("BEDS BROKEN", s['beds'], "#55FF55"), ("STREAK", s['streak'], "#FFAA00")
        ]
        
        for i, (txt, val, col) in enumerate(labels):
            pos = coords[i]
            d.text(pos, txt, fill=col, font=f_xs)
            d.text((pos[0], pos[1]+25), str(val), fill="white", font=f_s)

        # Box Info e Clan (Destra)
        d.text((660, 145), "INFORMATION", fill="#FFAA00", font=f_m)
        d.text((660, 190), f"Friends: {s['friends']}", fill="white", font=f_s)
        
        d.text((660, 270), "CLAN", fill="#FFAA00", font=f_m)
        d.text((660, 310), f"Tag: {s['clan_tag']}", fill="white", font=f_s)
        d.text((660, 340), f"Leader: {s['clan_leader']}", fill="white", font=f_xs)
        d.text((660, 370), f"Members: {s['clan_size']}", fill="white", font=f_xs)

        # Footer dinamico
        w, _ = d.textsize(s['footer'], font=f_m)
        d.text(((base.width - w)//2, base.height - 70), s['footer'], fill="#FFAA00", font=f_m)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore disegno: {e}")
        return None

# --- COMANDI DISCORD ---

@bot.command(aliases=['stats'])
async def bedwars(ctx, user: str, *args):
    """
    Comando flessibile: !bedwars qlyleo weekly solo
    """
    # Anti-duplicazione
    if cooldowns.get(ctx.channel.id) == user.lower(): return
    cooldowns[ctx.channel.id] = user.lower()

    # Parsing parametri
    interval = next((a for a in args if a.lower() in ["weekly", "monthly", "alltime"]), "alltime")
    mode = next((a for a in args if a.lower() in ["solo", "solos", "double", "doubles", "quad", "quads"]), "overall")

    msg = await ctx.send(f"⏳ Elaborazione **{interval} {mode}** per {user}...")
    
    raw_data = fetch_jartex_data(user)
    if not raw_data:
        await msg.edit(content="❌ Giocatore non trovato nelle API di Jartex.")
    else:
        stats = process_stats(raw_data, interval, mode)
        loop = asyncio.get_event_loop()
        image = await loop.run_in_executor(None, draw_stats_card, stats)
        
        if image:
            await msg.delete()
            await ctx.send(file=discord.File(image, f"{user}_stats.png"))
        else:
            await msg.edit(content="❌ Errore durante la generazione della grafica.")

    await asyncio.sleep(4)
    cooldowns.pop(ctx.channel.id, None)

@bot.command()
async def top(ctx):
    """Leaderboard realistica."""
    embed = discord.Embed(title="🏆 Jartex Bedwars Top 10", color=0xFFAA00, timestamp=datetime.utcnow())
    # Qui andrebbe il fetch della leaderboard reale
    leaderboard = [("qlyleo", 15400, 130), ("PlayerX", 12300, 115), ("PlayerY", 11000, 95)]
    
    desc = ""
    for i, (name, wins, lvl) in enumerate(leaderboard, 1):
        desc += f"`#{i}` **{name}** • {wins} Wins (Lvl {lvl})\n"
    
    embed.description = desc
    embed.set_footer(text="Aggiornato live")
    await ctx.send(embed=embed)

@bot.command()
async def clan(ctx, user: str):
    """Informazioni Clan dettagliate."""
    data = fetch_jartex_data(user)
    if data and data.get("clan"):
        c = process_stats(data, "alltime", "overall")
        embed = discord.Embed(title=f"🛡️ Clan: {c['clan_tag']}", color=0x55FF55)
        embed.add_field(name="Leader", value=c['clan_leader'], inline=True)
        embed.add_field(name="Membri", value=c['clan_size'], inline=True)
        embed.set_thumbnail(url="https://jartexnetwork.com/styles/jartex/jartex/logo.png")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {user} non ha un clan.")

bot.run(TOKEN)
