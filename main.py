import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os
import asyncio

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- CONFIG ---------------- #

MODE_MAP = {
    "solo": "solos", "solos": "solos",
    "double": "doubles", "doubles": "doubles",
    "quad": "teams_of_four", "quads": "teams_of_four",
    "overall": "overall"
}

# ---------------- UTILS ---------------- #

def get_stats_safely(data, interval, mode):
    bw_root = data.get("stats", {}).get("BedWars", {})
    time_node = bw_root.get(interval, {})

    mode_key = MODE_MAP.get(mode.lower(), "overall")
    stats = time_node.get(mode_key, {})

    if not stats or stats.get("wins", 0) == 0:
        stats = bw_root.get("alltime", {}).get(mode_key, {})

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

        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        d_ov = ImageDraw.Draw(overlay)
        d_ov.rectangle([40, 115, 610, 470], fill=(0, 0, 0, 140))
        d_ov.rectangle([640, 115, 980, 470], fill=(0, 0, 0, 170))
        base = Image.alpha_composite(base, overlay)

        draw = ImageDraw.Draw(base)

        f_title = ImageFont.truetype("Minecraft.ttf", 40)
        f_head = ImageFont.truetype("Minecraft.ttf", 26)
        f_data = ImageFont.truetype("Minecraft.ttf", 22)
        f_small = ImageFont.truetype("Minecraft.ttf", 16)

        gold, green, red, white = "#FFAA00", "#55FF55", "#FF5555", "#FFFFFF"

        user = profile.get("username", "Unknown")
        lvl = profile.get("rank", {}).get("level", 0)

        draw.text((50, 40), f"{profile.get('rank', {}).get('displayName', 'Player')} {user}", fill=white, font=f_head)
        draw.text((base.width - 120, 35), str(lvl), fill=gold, font=f_title)

        grid = [
            (80, 145, "WINS", s['wins'], green),
            (270, 145, "LOSSES", s['losses'], red),
            (460, 145, "WLR", s['wlr'], gold),
            (80, 265, "KILLS", s['kills'], green),
            (270, 265, "DEATHS", s['deaths'], red),
            (460, 265, "FKDR", s['fkdr'], gold),
            (80, 385, "BEDS BROKEN", s['beds'], green),
            (460, 385, "STREAK", s['streak'], gold)
        ]

        for x, y, lbl, val, col in grid:
            draw.text((x, y), lbl, fill=col, font=f_small)
            draw.text((x, y+22), str(val), fill=white, font=f_data)

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

        footer = f"BEDWARS {interval.upper()} {mode.upper()}"
        draw.text((base.width//2 - 130, base.height - 70), footer, fill=gold, font=f_head)

        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return buf

    except Exception as e:
        print("Errore create_card:", e)
        return None

# ---------------- COMANDI ---------------- #

@bot.command(aliases=['bw'])
async def bedwars(ctx, user: str, *args):
    interval = next((a for a in args if a.lower() in ["weekly", "monthly", "alltime"]), "alltime")
    mode = next((a for a in args if a.lower() in ["solo", "solos", "double", "doubles", "quad", "quads"]), "overall")

    msg = await ctx.send(f"🛰️ Recupero stats **{interval} {mode}** per {user}...")

    url = f"https://stats.jartexnetwork.com/api/profile/{user}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:

                if r.status != 200:
                    await msg.edit(content="❌ Giocatore non trovato.")
                    return

                data = await r.json()

        loop = asyncio.get_running_loop()
        buf = await loop.run_in_executor(None, create_card, data, interval, mode)

        if buf is None:
            await msg.edit(content="❌ Errore generazione immagine.")
            return

        await msg.delete()
        await ctx.send(file=discord.File(buf, f"{user}.png"))

    except Exception as e:
        print("Errore comando bedwars:", e)
        await msg.edit(content="❌ Errore API.")

@bot.command()
async def clan(ctx, user: str):
    url = f"https://stats.jartexnetwork.com/api/profile/{user}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:

                if r.status != 200:
                    await ctx.send("❌ Errore API.")
                    return

                data = await r.json()

        c = data.get("clan", {})

        if not c.get("name"):
            await ctx.send("❌ Il giocatore non è in un clan.")
            return

        owner = c.get("owner", {})
        leader = owner.get("username", "N/A") if isinstance(owner, dict) else str(owner)

        embed = discord.Embed(title=f"🛡️ Clan: {c['name']}", color=0x55FF55)
        embed.add_field(name="Leader", value=leader, inline=True)
        embed.add_field(name="Membri", value=c.get("membersCount", "N/A"), inline=True)

        await ctx.send(embed=embed)

    except Exception as e:
        print("Errore clan:", e)
        await ctx.send("❌ Errore.")

@bot.command()
async def top(ctx):
    url = "https://stats.jartexnetwork.com/api/leaderboards/BedWars/wins/alltime"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:

                if r.status != 200:
                    await ctx.send("❌ Classifica non disponibile.")
                    return

                lb = await r.json()

        embed = discord.Embed(title="🏆 Jartex Global Top 10 Wins", color=0xFFAA00)

        desc = ""
        for i, p in enumerate(lb[:10], 1):
            desc += f"**#{i} {p['username']}** • {p['value']} Wins\n"

        embed.description = desc

        await ctx.send(embed=embed)

    except Exception as e:
        print("Errore top:", e)
        await ctx.send("❌ Errore classifica.")

# ---------------- START ---------------- #

bot.run(TOKEN)
