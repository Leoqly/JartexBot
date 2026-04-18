import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import asyncio

# Configurazione Bot
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cache per prevenire risposte doppie
active_requests = {}

def get_jartex_stats(username):
    try:
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200: return None
        data = response.json()
        
        clan = data.get("clan", {})
        owner_data = clan.get("owner", "N/A")
        # Estrae il nome del leader se i dati sono in un dizionario
        owner_name = owner_data.get("username", "N/A") if isinstance(owner_data, dict) else owner_data

        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan_name": clan.get("name", "None"),
            "clan_owner": owner_name,
            "clan_members": clan.get("membersCount", 0),
            "friends": len(data.get("friends", [])),
            # Statistiche (al momento simulate, le collegheremo dopo)
            "wins": 356, "losses": 82, "wlr": 4.34,
            "kills": 2441, "deaths": 1152, "fkdr": 14.0,
            "beds_b": 507, "ws": 47
        }
    except: return None

def create_card(stats):
    try:
        # Carica lo sfondo (sfondo.png deve essere nella cartella principale su GitHub)
        base = Image.open("sfondo.png").convert("RGBA")
        
        # Creazione dei box scuri trasparenti
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        # Box per le statistiche principali
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 110)) 
        # Box per Informazioni e Clan (ora più largo e leggibile)
        d_ov.rectangle([640, 115, 980, 470], fill=(0, 0, 0, 150)) 
        base = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(base)
        # Assicurati che il file Minecraft.ttf sia su GitHub
        f_title = ImageFont.truetype("Minecraft.ttf", 42)
        f_header = ImageFont.truetype("Minecraft.ttf", 28)
        f_data = ImageFont.truetype("Minecraft.ttf", 22)
        f_lbl = ImageFont.truetype("Minecraft.ttf", 15)
        
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"

        # Testi in alto: Nome e Livello
        draw.text((50, 40), f"{stats['rank']} {stats['username']}", fill=white, font=f_header)
        draw.text((base.width - 110, 40), str(stats['level']), fill=gold, font=f_title)

        # Griglia statistiche (Sinistra)
        c, r = [80, 270, 460], [145, 265, 385]
        stats_map = [
            (c[0], r[0], "WINS", str(stats['wins']), green), (c[1], r[0], "LOSSES", str(stats['losses']), red),
            (c[2], r[0], "WLR", str(stats['wlr']), gold), (c[0], r[1], "KILLS", str(stats['kills']), green),
            (c[1], r[1], "DEATHS", str(stats['deaths']), red), (c[2], r[1], "FKDR", str(stats['fkdr']), gold),
            (c[0], r[2], "BEDS BROKEN", str(stats['beds_b']), green), (c[2], r[2], "STREAK", str(stats['ws']), gold)
        ]
        for x, y, lbl, val, col in stats_map:
            draw.text((x, y), lbl, fill=col, font=f_lbl)
            draw.text((x, y+22), val, fill=white, font=f_data)

        # Sezione Informazioni e Clan (Destra)
        x_cl = 660
        draw.text((x_cl, 145), "INFORMATION", fill=gold, font=f_header)
        draw.text((x_cl, 185), f"Friends: {stats['friends']}", fill=white, font=f_data)
        
        draw.text((x_cl, 260), "CLAN", fill=gold, font=f_header)
        draw.text((x_cl, 300), f"Tag: {stats['clan_name']}", fill=white, font=f_lbl)
        draw.text((x_cl, 330), f"Leader: {stats['clan_owner']}", fill=white, font=f_lbl)
        draw.text((x_cl, 360), f"Members: {stats['clan_members']}", fill=white, font=f_lbl)

        # Footer
        draw.text((base.width//2 - 170, base.height - 65), "BEDWARS TOTAL STATS", fill=gold, font=f_header)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore generazione card: {e}")
        return None

@bot.command(aliases=['bedwars'])
async def stats(ctx, user: str):
    # Controllo per evitare che il bot risponda due volte
    if active_requests.get(ctx.channel.id) == user.lower(): return
    active_requests[ctx.channel.id] = user.lower()
    
    waiting = await ctx.send(f"⏳ Generando la card per **{user}**...")
    
    data = get_jartex_stats(user)
    if data:
        # Esegue la creazione della card in un thread separato per non bloccare il bot
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, create_card, data)
        await waiting.delete()
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))
    else:
        await waiting.edit(content="❌ Errore: Giocatore non trovato o API non raggiungibile.")
    
    # Aspetta un po' prima di permettere un altro comando nello stesso canale
    await asyncio.sleep(5)
    active_requests.pop(ctx.channel.id, None)

@bot.event
async def on_ready():
    print(f'✅ JartexBot è online come {bot.user}')

bot.run(TOKEN)
