import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import time

# Configurazione Bot - Assicurati che 'TOKEN' sia nelle Variables di Railway
TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cache per prevenire duplicati
active_requests = {}

def get_jartex_stats(username):
    try:
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200: return None
        data = response.json()
        
        # Pulizia dati clan
        clan = data.get("clan", {})
        owner_data = clan.get("owner", "N/A")
        # Pulizia leader se è un oggetto
        owner_name = owner_data.get("username", "N/A") if isinstance(owner_data, dict) else owner_data

        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan_name": clan.get("name", "None"),
            "clan_owner": owner_name,
            "clan_members": clan.get("membersCount", 0),
            "friends": len(data.get("friends", [])),
            # Statistiche simulate (Sostituisci se hai API Bedwars)
            "wins": 356, "losses": 82, "wlr": 4.34,
            "kills": 2441, "deaths": 1152, "fkdr": 14.0,
            "beds_b": 507, "ws": 47
        }
    except Exception as e:
        print(f"Errore API: {e}")
        return None

def create_card(stats):
    try:
        # Carica sfondo base (sfondo.png deve essere su GitHub)
        base = Image.open("sfondo.png").convert("RGBA")
        
        # Overlay box scuri (Glassmorphism)
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 110)) # Box stats
        d_ov.rectangle([620, 255, 980, 470], fill=(0, 0, 0, 150)) # Box clan
        base = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(base)
        f_title = ImageFont.truetype("Minecraft.ttf", 42)
        f_header = ImageFont.truetype("Minecraft.ttf", 28)
        f_data = ImageFont.truetype("Minecraft.ttf", 22)
        f_lbl = ImageFont.truetype("Minecraft.ttf", 15)
        
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"

        # 1. INTESTAZIONE (Player qlyleo e Livello in alto)
        draw.text((50, 40), f"{stats['rank']} {stats['username']}", fill=white, font=f_header)
        draw.text((base.width - 110, 40), str(stats['level']), fill=gold, font=f_title)

        # 2. GRID STATS (Nelle zone scure a sinistra)
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

        # 3. INFO & CLAN (Zona scura a destra, spostata a sinistra per non essere coperta)
        # Ho ridotto x_cl da 660 a 640
        x_cl = 640
        draw.text((x_cl, 275), "INFORMATION", fill=gold, font=f_header)
        draw.text((x_cl, 315), f"Friends: {stats['friends']}", fill=white, font=f_data)
        draw.text((x_cl, 370), "CLAN", fill=gold, font=f_header)
        draw.text((x_cl, 405), f"Tag: {stats['clan_name']}", fill=white, font=f_lbl)
        draw.text((x_cl, 430), f"Leader: {stats['clan_owner']}", fill=white, font=f_lbl)
        draw.text((x_cl, 455), f"Members: {stats['clan_members']}", fill=white, font=f_lbl)

        # 4. SKIN 3D BODY (Nuovo servizio ultra rapido e posizionamento corretto)
        try:
            # Body render a corpo intero, proporzionato
            # Ho ridotto la size a 350 per non coprire nulla
            skin_url = f"https://mc-heads.net/body/{stats['username']}/350"
            s_res = requests.get(skin_url, stream=True, timeout=5)
            if s_res.status_code == 200:
                skin_img = Image.open(s_res.raw).convert("RGBA")
                # Posizioniamo la skin sulla destra, lontana dai testi del clan
                # base.paste(skin_img, (base.width - 280, 20), skin_img)
                base.paste(skin_img, (base.width - 280, 20), skin_img)
        except Exception as e:
            print(f"Errore skin: {e}")

        # TITOLO FINALE
        draw.text((base.width//2 - 170, base.height - 65), "BEDWARS TOTAL STATS", fill=gold, font=f_header)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore Card: {e}")
        return None

# Accetta sia !stats che !bedwars
@bot.command(aliases=['bedwars'])
async def stats(ctx, user: str):
    # Cooldown anti-duplicato (se Railway ne lancia due, il secondo aspetta)
    if active_requests.get(ctx.channel.id) == user: return 
    active_requests[ctx.channel.id] = user
    
    # Messaggio di attesa
    waiting = await ctx.send(f"⏳ Caricamento card per **{user}**...")
    
    data = get_jartex_stats(user)
    if not data:
        await waiting.delete()
        active_requests.pop(ctx.channel.id)
        return await ctx.send("❌ Giocatore non trovato.")
    
    buf = create_card(data)
    if buf:
        await waiting.delete()
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))
    
    active_requests.pop(ctx.channel.id, None)

@bot.event
async def on_ready():
    print(f'✅ Bot Jartex Pronto: {bot.user}')

# Avvio del bot
bot.run(TOKEN)
