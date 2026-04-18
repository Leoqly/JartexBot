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

active_requests = {}

def get_level_color(level):
    # Ricalibrato su un massimo di 130
    if level < 30: return "#FFFFFF"   # 0-29: Bianco
    if level < 60: return "#55FF55"   # 30-59: Verde
    if level < 90: return "#FFAA00"   # 60-89: Oro
    if level < 120: return "#FF5555"  # 90-119: Rosso
    return "#AA00AA"                  # 120-130: Viola (Elite)

def get_jartex_stats(username, mode="overall", interval="alltime"):
    try:
        api_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200: return None
        data = response.json()
        
        clan = data.get("clan", {})
        owner_data = clan.get("owner", "N/A")
        owner_name = owner_data.get("username", "N/A") if isinstance(owner_data, dict) else owner_data

        return {
            "username": data.get("username", username),
            "level": data.get("rank", {}).get("level", 0),
            "rank": data.get("rank", {}).get("displayName", "Player"),
            "clan_name": clan.get("name", "None"),
            "clan_owner": owner_name,
            "clan_members": clan.get("membersCount", 0),
            "friends": len(data.get("friends", [])),
            "mode_label": f"{mode.upper()} - {interval.upper()}",
            # Placeholder per stats reali bedwars (da collegare appena possibile)
            "wins": 356, "losses": 82, "wlr": 4.34,
            "kills": 2441, "deaths": 1152, "fkdr": 14.0,
            "beds_b": 507, "ws": 47
        }
    except: return None

def create_card(stats):
    try:
        base = Image.open("sfondo.png").convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        # Box principale e Box Clan
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 110)) 
        d_ov.rectangle([640, 115, 980, 470], fill=(0, 0, 0, 150)) 
        base = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(base)
        f_title = ImageFont.truetype("Minecraft.ttf", 42)
        f_header = ImageFont.truetype("Minecraft.ttf", 28)
        f_data = ImageFont.truetype("Minecraft.ttf", 22)
        f_lbl = ImageFont.truetype("Minecraft.ttf", 15)
        
        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"
        lvl_color = get_level_color(stats['level'])

        # Intestazione
        draw.text((50, 40), f"{stats['rank']} {stats['username']}", fill=white, font=f_header)
        draw.text((base.width - 110, 40), str(stats['level']), fill=lvl_color, font=f_title)

        # Griglia Stats
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

        # Clan & Info
        x_cl = 660
        draw.text((x_cl, 145), "INFORMATION", fill=gold, font=f_header)
        draw.text((x_cl, 185), f"Friends: {stats['friends']}", fill=white, font=f_data)
        draw.text((x_cl, 260), "CLAN", fill=gold, font=f_header)
        draw.text((x_cl, 300), f"Tag: {stats['clan_name']}", fill=white, font=f_lbl)
        draw.text((x_cl, 330), f"Leader: {stats['clan_owner']}", fill=white, font=f_lbl)
        draw.text((x_cl, 360), f"Members: {stats['clan_members']}", fill=white, font=f_lbl)

        # Footer Dinamico
        draw.text((base.width//2 - 170, base.height - 65), f"BEDWARS {stats['mode_label']}", fill=gold, font=f_header)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"Errore card: {e}")
        return None

# --- COMANDI ---

@bot.command()
async def stats(ctx, user: str, interval: str = "alltime", mode: str = "overall"):
    if active_requests.get(ctx.channel.id) == user.lower(): return
    active_requests[ctx.channel.id] = user.lower()
    
    msg = await ctx.send(f"⏳ Caricamento dati {mode} ({interval}) per **{user}**...")
    data = get_jartex_stats(user, mode, interval)
    
    if data:
        loop = asyncio.get_event_loop()
        buf = await loop.run_in_executor(None, create_card, data)
        await msg.delete()
        await ctx.send(file=discord.File(buf, f"{user}_stats.png"))
    else:
        await msg.edit(content="❌ Giocatore non trovato.")
    
    await asyncio.sleep(3)
    active_requests.pop(ctx.channel.id, None)

@bot.command()
async def top(ctx):
    # Esempio di Embed elegante per la Top 10
    embed = discord.Embed(title="🏆 Bedwars Leaderboard - Top Wins", color=discord.Color.gold())
    # Qui andrebbe il loop sui dati reali dell'API leaderboard di Jartex
    embed.add_field(name="1. qlyleo", value="15,400 Wins - Lvl 130", inline=False)
    embed.add_field(name="2. PlayerX", value="14,200 Wins - Lvl 125", inline=False)
    embed.set_footer(text="Aggiornato in tempo reale")
    await ctx.send(embed=embed)

@bot.command()
async def clan(ctx, user: str):
    data = get_jartex_stats(user)
    if data and data['clan_name'] != "None":
        embed = discord.Embed(title=f"🛡️ Clan: {data['clan_name']}", color=discord.Color.blue())
        embed.add_field(name="Leader", value=data['clan_owner'])
        embed.add_field(name="Membri", value=data['clan_members'])
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {user} non appartiene a nessun clan.")

@bot.event
async def on_ready():
    print(f'✅ Bot Jartex Pronto: {bot.user}')

bot.run(TOKEN)
