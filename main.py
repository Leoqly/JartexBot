import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
from PIL import Image, ImageDraw, ImageFont
import io
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

API_BASE = "https://stats.jartexnetwork.com/api"

# ---------------- API ---------------- #

async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                return await r.json()
            return None

# ---------------- PARSER FIX DEFINITIVO ---------------- #

def parse_bedwars(data, mode="ALL_MODES", interval="total"):
    try:
        bw = data.get("stats", {}).get("BedWars", {})

        interval_map = {
            "weekly": "weekly",
            "monthly": "monthly",
            "total": "alltime"
        }

        i = interval_map.get(interval.lower(), "alltime")
        time_data = bw.get(i, {})

        modes_real = {
            "SOLO": "solos",
            "DOUBLES": "doubles",
            "QUADS": "teams_of_four"
        }

        # 🔥 ALL MODES = somma reale
        if mode.upper() == "ALL_MODES":
            total = {
                "wins": 0,
                "losses": 0,
                "kills": 0,
                "deaths": 0,
                "beds_destroyed": 0,
                "current_streak": 0
            }

            for m in ["solos", "doubles", "teams_of_four"]:
                s = time_data.get(m, {})
                for k in total:
                    total[k] += s.get(k, 0)

            stats = total
        else:
            key = modes_real.get(mode.upper(), "solos")
            stats = time_data.get(key, {})

        # fallback
        if not stats or stats.get("wins", 0) == 0:
            stats = bw.get("alltime", {}).get("overall", {})

        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)

        return {
            "wins": wins,
            "losses": losses,
            "kills": kills,
            "deaths": deaths,
            "beds": stats.get("beds_destroyed", 0),
            "streak": stats.get("current_streak", 0),
            "wlr": round(wins / losses, 2) if losses else wins,
            "fkdr": round(kills / deaths, 2) if deaths else kills
        }

    except Exception as e:
        print("Parse error:", e)
        return None

# ---------------- CARD ---------------- #

def draw_card(profile, stats, mode):
    try:
        img = Image.open("sfondo.png").convert("RGBA")
        draw = ImageDraw.Draw(img)

        f_big = ImageFont.truetype("Minecraft.ttf", 42)
        f_mid = ImageFont.truetype("Minecraft.ttf", 22)
        f_small = ImageFont.truetype("Minecraft.ttf", 16)

        white = "#FFFFFF"
        gold = "#FFAA00"
        green = "#55FF55"
        red = "#FF5555"

        user = profile.get("username", "Unknown")
        level = profile.get("rank", {}).get("level", 0)

        # HEADER
        draw.text((40, 30), user, fill=white, font=f_mid)
        draw.text((900, 20), str(level), fill=gold, font=f_big)

        def stat(x, y, name, value, color):
            draw.text((x, y), name, fill=color, font=f_small)
            draw.text((x, y+25), str(value), fill=white, font=f_mid)

        # GRID
        stat(80, 140, "WINS", stats["wins"], green)
        stat(260, 140, "LOSSES", stats["losses"], red)
        stat(440, 140, "WLR", stats["wlr"], gold)

        stat(80, 260, "KILLS", stats["kills"], green)
        stat(260, 260, "DEATHS", stats["deaths"], red)
        stat(440, 260, "FKDR", stats["fkdr"], gold)

        stat(80, 380, "BEDS", stats["beds"], green)
        stat(440, 380, "STREAK", stats["streak"], gold)

        # FOOTER
        draw.text((400, 520), f"{mode.upper()}", fill=gold, font=f_mid)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    except Exception as e:
        print("Render error:", e)
        return None

# ---------------- COMMAND ---------------- #

@bot.tree.command(name="bw", description="Mostra stats Bedwars")
@app_commands.describe(
    user="Nome player",
    mode="SOLO / DOUBLES / QUADS / ALL_MODES",
    interval="weekly / monthly / total"
)
async def bw(interaction: discord.Interaction, user: str, mode: str = "ALL_MODES", interval: str = "total"):

    await interaction.response.defer()

    profile = await fetch_json(f"{API_BASE}/profile/{user}")

    if not profile:
        await interaction.followup.send("❌ Player non trovato")
        return

    stats = parse_bedwars(profile, mode, interval)

    if not stats:
        await interaction.followup.send("❌ Nessuna stats trovata")
        return

    loop = asyncio.get_running_loop()
    img = await loop.run_in_executor(None, draw_card, profile, stats, mode)

    if not img:
        await interaction.followup.send("❌ Errore immagine")
        return

    await interaction.followup.send(file=discord.File(img, f"{user}.png"))

# ---------------- READY ---------------- #

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot online: {bot.user}")

# ---------------- START ---------------- #

bot.run(TOKEN)
