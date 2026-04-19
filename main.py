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

API = "https://stats.jartexnetwork.com/api/profile/"

# ---------------- API ---------------- #

async def fetch_player(user):
    async with aiohttp.ClientSession() as session:
        async with session.get(API + user) as r:
            if r.status == 200:
                return await r.json()
            return None

# ---------------- PARSER SUPER FIX ---------------- #

def parse_stats(data, mode="ALL_MODES"):
    try:
        bw = data.get("stats", {}).get("BedWars", {})

        # modalità reali
        modes = {
            "SOLO": "solos",
            "DOUBLES": "doubles",
            "QUADS": "teams_of_four"
        }

        # -----------------------
        # PRENDI DATI
        # -----------------------

        # 1. prova alltime
        alltime = bw.get("alltime", {})

        # 2. fallback root (IMPORTANTISSIMO)
        root = bw

        def get_mode_stats(source, key):
            return source.get(key, {}) if source else {}

        # -----------------------
        # ALL MODES
        # -----------------------
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
                s = get_mode_stats(alltime, m)

                # fallback root se vuoto
                if not s:
                    s = get_mode_stats(root, m)

                for k in total:
                    total[k] += s.get(k, 0)

            stats = total

        else:
            key = modes.get(mode.upper(), "solos")

            stats = get_mode_stats(alltime, key)

            if not stats:
                stats = get_mode_stats(root, key)

        # ultimo fallback
        if not stats:
            stats = get_mode_stats(alltime, "overall") or get_mode_stats(root, "overall")

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
        print("PARSE ERROR:", e)
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

        draw.text((40, 30), user, fill=white, font=f_mid)
        draw.text((900, 20), str(level), fill=gold, font=f_big)

        def stat(x, y, name, value, color):
            draw.text((x, y), name, fill=color, font=f_small)
            draw.text((x, y+25), str(value), fill=white, font=f_mid)

        stat(80, 140, "WINS", stats["wins"], green)
        stat(260, 140, "LOSSES", stats["losses"], red)
        stat(440, 140, "WLR", stats["wlr"], gold)

        stat(80, 260, "KILLS", stats["kills"], green)
        stat(260, 260, "DEATHS", stats["deaths"], red)
        stat(440, 260, "FKDR", stats["fkdr"], gold)

        stat(80, 380, "BEDS", stats["beds"], green)
        stat(440, 380, "STREAK", stats["streak"], gold)

        draw.text((400, 520), mode.upper(), fill=gold, font=f_mid)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    except Exception as e:
        print("CARD ERROR:", e)
        return None

# ---------------- COMMAND ---------------- #

@bot.tree.command(name="bw")
async def bw(interaction: discord.Interaction, user: str, mode: str = "ALL_MODES"):

    await interaction.response.defer()

    data = await fetch_player(user)

    if not data:
        await interaction.followup.send("❌ Player non trovato")
        return

    stats = parse_stats(data, mode)

    if not stats:
        await interaction.followup.send("❌ Nessuna stats trovata")
        return

    loop = asyncio.get_running_loop()
    img = await loop.run_in_executor(None, draw_card, data, stats, mode)

    await interaction.followup.send(file=discord.File(img, f"{user}.png"))

# ---------------- READY ---------------- #

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("BOT ONLINE")

bot.run(TOKEN)
