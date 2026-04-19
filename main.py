import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import asyncio
import io
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ CONFIG ------------------ #

MODE_MAP = {
    "solo": "solo",
    "solos": "solo",
    "double": "double",
    "doubles": "double",
    "quad": "quad",
    "quads": "quad",
    "overall": "overall"
}

INTERVAL_MAP = {
    "weekly": "weekly",
    "monthly": "monthly",
    "alltime": "alltime"
}

# ------------------ API PARSER FIXATO ------------------ #

def extract_stats(data, interval, mode):
    try:
        bw = data["stats"]["BedWars"]

        interval = INTERVAL_MAP.get(interval, "alltime")
        mode = MODE_MAP.get(mode, "overall")

        # ⚠️ STRUTTURA REALE API JARTEX
        stats = bw.get(interval, {}).get(mode, {})

        # fallback intelligenti
        if not stats:
            stats = bw.get("alltime", {}).get(mode, {})

        if not stats:
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
            "wlr": round(wins / losses, 2) if losses > 0 else wins,
            "fkdr": round(kills / deaths, 2) if deaths > 0 else kills
        }

    except Exception as e:
        print("ERRORE PARSING:", e)
        return {
            "wins": 0, "losses": 0, "kills": 0,
            "deaths": 0, "beds": 0, "streak": 0,
            "wlr": 0, "fkdr": 0
        }

# ------------------ CARD ------------------ #

def create_card(data, interval, mode):
    try:
        stats = extract_stats(data, interval, mode)

        img = Image.open("sfondo.png").convert("RGBA")
        draw = ImageDraw.Draw(img)

        # font
        font_big = ImageFont.truetype("Minecraft.ttf", 40)
        font_mid = ImageFont.truetype("Minecraft.ttf", 22)
        font_small = ImageFont.truetype("Minecraft.ttf", 16)

        white = "#FFFFFF"
        gold = "#FFAA00"
        green = "#55FF55"
        red = "#FF5555"

        user = data.get("username", "Unknown")
        level = data.get("rank", {}).get("level", 0)

        # titolo
        draw.text((50, 40), user, font=font_mid, fill=white)
        draw.text((900, 40), str(level), font=font_big, fill=gold)

        # stats
        y = 150

        def stat(x, y, label, value, color):
            draw.text((x, y), label, font=font_small, fill=color)
            draw.text((x, y+25), str(value), font=font_mid, fill=white)

        stat(80, y, "WINS", stats["wins"], green)
        stat(250, y, "LOSSES", stats["losses"], red)
        stat(420, y, "WLR", stats["wlr"], gold)

        stat(80, y+120, "KILLS", stats["kills"], green)
        stat(250, y+120, "DEATHS", stats["deaths"], red)
        stat(420, y+120, "FKDR", stats["fkdr"], gold)

        stat(80, y+240, "BEDS", stats["beds"], green)
        stat(420, y+240, "STREAK", stats["streak"], gold)

        footer = f"{interval.upper()} {mode.upper()}"
        draw.text((400, 500), footer, font=font_mid, fill=gold)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return buf

    except Exception as e:
        print("ERRORE CARD:", e)
        return None

# ------------------ COMMAND ------------------ #

@bot.command(aliases=["bw"])
async def bedwars(ctx, user: str, interval="alltime", mode="overall"):

    msg = await ctx.send("🔄 Caricamento...")

    url = f"https://stats.jartexnetwork.com/api/profile/{user}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:

                if r.status != 200:
                    await msg.edit(content="❌ Player non trovato")
                    return

                data = await r.json()

        loop = asyncio.get_running_loop()
        img = await loop.run_in_executor(None, create_card, data, interval, mode)

        if not img:
            await msg.edit(content="❌ Errore generazione")
            return

        await msg.delete()
        await ctx.send(file=discord.File(img, f"{user}.png"))

    except Exception as e:
        print("ERRORE:", e)
        await msg.edit(content="❌ Errore API")

# ------------------ READY ------------------ #

@bot.event
async def on_ready():
    print(f"✅ Bot online: {bot.user}")

# ------------------ START ------------------ #

bot.run(TOKEN)
