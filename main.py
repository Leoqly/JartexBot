import keep_alive
import discord
from discord.ext import commands
import requests
from PIL import Image, ImageDraw, ImageFont
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

def get_jartex_data(username):
    profile_url = f"https://stats.jartexnetwork.com/api/profile/{username}"
    stats_url = f"https://stats.jartexnetwork.com/api/profile/{username}/leaderboard?type=bedwars&interval=total&mode=ALL_MODES"
    data = {"profile": None, "stats": None}
    try:
        p_res = requests.get(profile_url, timeout=5)
        if p_res.status_code == 200: data["profile"] = p_res.json()
        s_res = requests.get(stats_url, timeout=5)
        if s_res.status_code == 200: data["stats"] = s_res.json()
    except: pass
    return data

def create_card(username, all_data):
    profile = all_data.get("profile") or {}
    lb = all_data.get("stats") or {}
    # Cerchiamo il blocco statistiche in più posti possibili
    bw_raw = profile.get("stats", {}).get("BedWars", {}) or profile.get("stats", {}).get("bedwars", {}) or {}
    
    width, height = 1100, 700
    try:
        base = Image.open("sfondo.png").convert("RGBA").resize((width, height))
    except:
        base = Image.new("RGBA", (width, height), (20, 20, 25, 255))
    
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d_overlay = ImageDraw.Draw(overlay)
    d_overlay.rectangle([40, 150, 620, 660], fill=(15, 15, 20, 190), outline="#FFAA00", width=3)
    d_overlay.rectangle([650, 420, 1060, 660], fill=(15, 15, 20, 190), outline="#FFAA00", width=3)
    
    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)
    
    try:
        f_path = "Minecraft.ttf"
        f_name, f_val, f_sub = ImageFont.truetype(f_path, 50), ImageFont.truetype(f_path, 32), ImageFont.truetype(f_path, 18)
    except:
        f_name = f_val = f_sub = ImageFont.load_default()

    draw.text((40, 40), f"PLAYER: {username.upper()}", fill="#FFAA00", font=f_name)
    draw.text((40, 95), f"LEVEL: {profile.get('rank', {}).get('level', '0')}", fill="#FFFFFF", font=f_sub)

    # --- FUNZIONE MAGICA: Cerca il valore in ogni modo possibile ---
    def grab(keys):
        for k in keys:
            # Cerca nel profilo raw
            if k in bw_raw: return int(bw_raw[k])
            # Cerca nella leaderboard (se presente)
            main_key = k.replace("_", " ").capitalize() 
            if lb and main_key in lb and lb[main_key].get("entries"):
                return int(lb[main_key]["entries"][0].get("value", 0))
        return 0

    # Recupero dati con nomi flessibili
    wins = grab(["wins", "Wins", "WINS"])
    losses = grab(["losses", "Losses", "LOSSES"])
    kills = grab(["kills", "Kills", "KILLS"])
    deaths = grab(["deaths", "Deaths", "DEATHS"])
    fkills = grab(["final_kills", "Final kills", "finalkills"])
    fdeaths = grab(["final_deaths", "Final deaths", "finaldeaths"])
    beds = grab(["beds_destroyed", "Beds destroyed", "bedsbroken", "Beds Broken"])
    games = grab(["games_played", "Games played", "gamesplayed"])

    # Calcolo Rapporti
    wlr = round(wins / losses, 2) if losses > 0 else float(wins)
    kdr = round(kills / deaths, 2) if deaths > 0 else float(kills)
    fkdr = round(fkills / fdeaths, 2) if fdeaths > 0 else float(fkills)

    def get_rank(key):
        if lb and key in lb and lb[key].get("entries"):
            return lb[key]["entries"][0].get("place", "N/A")
        return "N/A"

    def d_row(label, val, rank, x, y, color):
        draw.text((x, y), label, fill=color, font=f_sub)
        draw.text((x, y + 22), str(val), fill="white", font=f_val)
        if rank and rank != "N/A":
            draw.text((x, y + 55), f"Rank: #{rank}", fill="#AAAAAA", font=f_sub)

    # Colonna 1
    d_row("WINS", wins, get_rank("Wins"), 70, 170, "#55FF55")
    d_row("KILLS", kills, get_rank("Kills"), 70, 310, "#FF5555")
    d_row("FINAL KILLS", fkills, get_rank("Final kills"), 70, 450, "#FFFF55")
    d_row("BEDS BROKEN", beds, get_rank("Beds destroyed"), 70, 590, "#55FFFF")

    # Colonna 2
    d_row("WLR", wlr, "N/A", 330, 170, "#55FF55")
    d_row("KDR", kdr, "N/A", 330, 310, "#FF5555")
    d_row("FKDR", fkdr, "N/A", 330, 450, "#FFAA00")
    d_row("GAMES PLAYED", games, get_rank("Games played"), 330, 590, "#FFFFFF")

    # --- CLAN INFO PULITO ---
    clan = profile.get("clan")
    c_x, c_y = 670, 440
    draw.text((c_x, c_y), "CLAN INFO", fill="#FFAA00", font=f_val)
    if clan:
        owner = clan.get('owner', {})
        owner_name = owner.get('username', 'N/A') if isinstance(owner, dict) else str(owner)
        m_list = clan.get('members', [])
        m_count = len(m_list) if isinstance(m_list, list) else clan.get('memberCount', '0')

        draw.text((c_x, c_y + 50), f"NAME: {clan.get('name', 'N/A')}", fill="white", font=f_sub)
        draw.text((c_x, c_y + 90), f"TAG: {clan.get('tag', 'N/A')}", fill="white", font=f_sub)
        draw.text((c_x, c_y + 130), f"OWNER: {owner_name}", fill="white", font=f_sub)
        draw.text((c_x, c_y + 170), f"MEMBERS: {m_count}", fill="white", font=f_sub)
    else:
        draw.text((c_x, c_y + 50), "NAME: NONE", fill="white", font=f_sub)

    # LOGO
    try:
        logo = Image.open("logo.png").convert("RGBA")
        logo.thumbnail((420, 420), Image.Resampling.LANCZOS)
        base.paste(logo, (670, 30), logo)
    except: pass

    output_path = f"card_{username}.png"
    base.save(output_path)
    return output_path

@bot.command()
async def bedwars(ctx, username: str):
    data = get_jartex_data(username)
    if not data["profile"]: return await ctx.send(f"❌ Player **{username}** non trovato.")
    path = create_card(username, data)
    await ctx.send(file=discord.File(path))
    if os.path.exists(path): os.remove(path)

bot.run(TOKEN)