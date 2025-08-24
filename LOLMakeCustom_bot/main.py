import discord
from discord.ext import commands
import json
import os
import re
import random
from dotenv import load_dotenv
from itertools import combinations, permutations
from keep_alive import keep_alive
from time import time

# ===== Intents / Bot: 一意に1回だけ生成 =====
intents = discord.Intents.all()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 定数・ファイル =====
lanes = ['top', 'jg', 'mid', 'adc', 'sup']
ability_file = 'abilities.json'
team_file = 'last_teams.json'
history_file = 'history.json'
participants = {}  # {guild_id(int): {user_id(int): [lane1, lane2]}} または ['fill']
ability_cap = 300 #勝利時の上限値 #元ソースの想定上限値は120
EARLY_MATCHES = 5 # 最初の5戦まで
DELTA_EARLY = 10  # 1～5戦目の増減
DELTA_LATE = 5    # 6戦目以降の増減

# ===== 環境変数 =====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN が .env に定義されていません。")

keep_alive()  # Flask サーバーを起動

# ===== 汎用I/O =====
def load_data(file):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return {}

def save_data(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

def get_server_data(guild_id):
    data = load_data(ability_file)
    return data.setdefault(str(guild_id), {})

def update_server_data(guild_id, server_data):
    data = load_data(ability_file)
    data[str(guild_id)] = server_data
    save_data(ability_file, data)

def get_last_teams(guild_id):
    lt = load_data(team_file)
    return lt.get(str(guild_id))

def set_last_teams(guild_id, value):
    lt = load_data(team_file)
    lt[str(guild_id)] = value
    save_data(team_file, lt)

# ===== Guild参加時のガイダンス =====
@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send("""
📘 **LOLMakeCustom コマンド詳細説明**

---

### 🧠 能力値関連
- `!ability @user 10 10 10 10 10`  
  → @user に **top, jg, mid, adc, sup** の順で能力値を登録（0以上）

- `!delete_ability @user`  
  → 指定ユーザーの能力値を削除

- `!show_ability`  
  → 登録済みの全ユーザーの能力値と **合計値順** で表示

---

### 🎮 参加関連
- `!join @user top jg`  
  → 希望レーンを2つまで登録（例：top と jg）

- `!join @user fill fill`  
  → レーンがどこでも良い場合は **fill** を利用

- `!leave @user`  
  → 参加リストから @user を削除

- `!participants_list`  
  → 現在の参加メンバー一覧と希望レーンを表示

- `!reset`  
  → 参加者を全てリセット

---

### ⚔️ チーム編成関連
- `!make_teams [lane_diff] [team_diff]`  
  （例：`!make_teams 30 150`）  
  → 希望レーンを考慮して10人を自動で5v5に分ける  
  　- 引数指定なしの場合、**レーン差30以内／合計差150以内**を目安  
  　- 条件を満たせない場合も、最もバランスの良い組み合わせを提示（警告あり）

- `!make_teams_aspe [lane_diff] [team_diff] [top_n]`  
  （例：`!make_teams_aspe 40 200 5`）  
  → **上位N案からランダムに選ぶ FUNモード**  
  　- デフォルト: レーン差40／合計差200／N=5  
  　- 条件に一致しない場合も、ペナルティ加点済み候補から選択

- `!swap @user1 @user2`  
  → レーン・チームを入れ替え（直前の `!make_teams` 系コマンド必須）

---

### 🏆 勝敗報告と成績
- `!win A` または `!win B`  
  → 勝利チームのレーン能力値を **+**、敗者を **−** で調整  
  　- 5戦目までは ±10  
  　- 6戦目以降は ±5

---

### 📊 各種統計
- `!ranking`  
  → 各レーンの能力値上位ランキングを表示

- `!show_custom @user`  
  → 指定ユーザーの **勝率・試合数・レーン別戦績** を表示

---

### ℹ️ その他
- `!help_mc` → コマンド一覧（簡易）  
- `!help_mc_detail` → この詳細説明を再表示
""")
            break


# ===== ちょい動作確認 =====
@bot.command()
async def hello(ctx):
    await ctx.send("こんにちは！Botは稼働中です。")

@bot.command()
async def bye(ctx):
    await ctx.send("さようなら！※Botは停止しません。")

# ===== 能力登録系 =====
@bot.command()
async def ability(ctx, member: discord.Member, top: int, jg: int, mid: int, adc: int, sup: int):
    guild_id = str(ctx.guild.id)
    data = load_data(ability_file)
    if guild_id not in data:
        data[guild_id] = {}
    user_id = str(member.id)
    data[guild_id][user_id] = {
        'name': member.name,
        'top': top,
        'jg': jg,
        'mid': mid,
        'adc': adc,
        'sup': sup
    }
    save_data(ability_file, data)
    await ctx.send(f"{member.mention} の能力値を登録しました。")

@bot.command()
async def delete_ability(ctx, member: discord.Member):
    server_data = get_server_data(ctx.guild.id)
    if str(member.id) in server_data:
        del server_data[str(member.id)]
        update_server_data(ctx.guild.id, server_data)
        await ctx.send(f"{member.display_name} の能力値を削除しました。")
    else:
        await ctx.send("そのユーザーのデータは存在しません。")

@bot.command()
async def show_ability(ctx):
    data = load_data(ability_file)
    guild_id = str(ctx.guild.id)
    if guild_id not in data or not data[guild_id]:
        await ctx.send("まだ能力が登録されていません。")
        return
    sorted_data = sorted(
        data[guild_id].items(),
        key=lambda x: sum(x[1][lane] for lane in lanes),
        reverse=True
    )
    msg = "**能力一覧（合計順）**\n"
    for user_id, info in sorted_data:
        total = sum(info[lane] for lane in lanes)
        msg += f"<@{user_id}> top{info['top']} jg{info['jg']} mid{info['mid']} adc{info['adc']} sup{info['sup']} | 合計{total}\n"
    await ctx.send(msg)

# ===== 参加系 =====
@bot.command()
async def join(ctx, *args):
    global participants
    mentions = ctx.message.mentions
    if mentions:
        member = mentions[0]
        args = args[1:]
    else:
        member = ctx.author
    if len(args) != 2:
        await ctx.send("希望レーンを2つ指定してください。例：!join @user top mid または !join top mid")
        return
    lane1 = args[0].lower()
    lane2 = args[1].lower()
    valid_lanes = lanes + ['fill']
    if lane1 not in valid_lanes or lane2 not in valid_lanes:
        await ctx.send(f"指定されたレーンが無効です。有効なレーン: {', '.join(valid_lanes)}")
        return
    guild_id = ctx.guild.id
    if guild_id not in participants:
        participants[guild_id] = {}
    participants[guild_id][member.id] = [lane1, lane2]
    lanes_str = f"{lane1.upper()} / {lane2.upper()}" if lane1 != lane2 else lane1.upper()
    await ctx.send(f"{member.display_name} が [{lanes_str}] で参加登録しました。")

@bot.command()
async def leave(ctx, member: discord.Member = None):
    global participants
    guild_id = ctx.guild.id
    if member is None:
        member = ctx.author
    if guild_id not in participants or member.id not in participants[guild_id]:
        await ctx.send(f"{member.display_name} は参加していません。")
        return
    del participants[guild_id][member.id]
    await ctx.send(f"{member.display_name} の参加を解除しました。")

@bot.command()
async def participants_list(ctx):
    guild_id = ctx.guild.id
    if guild_id not in participants or not participants[guild_id]:
        await ctx.send("現在、参加者は登録されていません。")
        return
    msg = "**現在の参加者一覧：**\n"
    for uid, two in participants[guild_id].items():
        member = ctx.guild.get_member(uid)
        if not member:
            continue
        lane1, lane2 = two
        msg += f"{member.display_name}：{lane1.upper()} / {lane2.upper()}\n"
    await ctx.send(msg)

@bot.command()
async def reset(ctx):
    gid = ctx.guild.id
    if gid in participants:
        participants[gid].clear()
        await ctx.send("✅ 参加リストをリセットしました。")
    else:
        await ctx.send("参加リストはすでに空です。")

# ===== チーム分け =====
@bot.command()
async def make_teams(ctx, lane_diff: int = 30, team_diff: int = 150):
    guild_id = ctx.guild.id
    if guild_id not in participants or len(participants[guild_id]) < 10:
        await ctx.send("参加者が10人未満です。")
        return
    member_ids = list(participants[guild_id].keys())
    server_data = get_server_data(guild_id)
    if not all(str(mid) in server_data for mid in member_ids):
        unregistered_ids = [mid for mid in member_ids if str(mid) not in server_data]
        mention_list = ', '.join(f'<@{uid}>' for uid in unregistered_ids)
        await ctx.send(f"一部の参加者が能力値を登録していません：{mention_list}")
        return

    best_score = float('inf')
    best_result = None
    warnings = []

    for team1_ids in combinations(member_ids, 5):
        team2_ids = [uid for uid in member_ids if uid not in team1_ids]
        for team1_roles in permutations(lanes):
            role_map = {}
            valid_team1 = True
            for uid, lane in zip(team1_ids, team1_roles):
                prefs = participants[guild_id].get(uid, [])
                if prefs and lane not in prefs and 'fill' not in prefs:
                    valid_team1 = False
                    break
                role_map[uid] = lane
            if not valid_team1:
                continue

            try:
                valid = False
                for team2_roles in permutations(lanes):
                    try_role_map = role_map.copy()
                    success = True
                    for uid, lane in zip(team2_ids, team2_roles):
                        prefs = participants[guild_id].get(uid, [])
                        if prefs and lane not in prefs and 'fill' not in prefs:
                            success = False
                            break
                        try_role_map[uid] = lane
                    if success:
                        role_map = try_role_map
                        valid = True
                        break
                if not valid or len(role_map) != 10:
                    continue

                team1_score = 0
                team2_score = 0
                total_lane_diff = 0
                exceeded = False

                for lane in lanes:
                    uid1 = [u for u in team1_ids if role_map[u] == lane][0]
                    uid2 = [u for u in team2_ids if role_map[u] == lane][0]
                    val1 = server_data[str(uid1)][lane]
                    val2 = server_data[str(uid2)][lane]
                    team1_score += val1
                    team2_score += val2
                    diff = abs(val1 - val2)
                    total_lane_diff += diff
                    if diff > lane_diff:
                        exceeded = True

                team_diff_value = abs(team1_score - team2_score)
                if team_diff_value > team_diff:
                    exceeded = True

                score = total_lane_diff + team_diff_value
                if exceeded:
                    score += 1000

                if score < best_score:
                    best_score = score
                    best_result = (team1_ids, team2_ids, role_map)
                    warnings = []
                    if exceeded:
                        for lane in lanes:
                            uid1 = [u for u in team1_ids if role_map[u] == lane][0]
                            uid2 = [u for u in team2_ids if role_map[u] == lane][0]
                            val1 = server_data[str(uid1)][lane]
                            val2 = server_data[str(uid2)][lane]
                            diff = abs(val1 - val2)
                            if diff > lane_diff:
                                warnings.append(f"{lane} の能力差が {diff} あります。")
                        if team_diff_value > team_diff:
                            warnings.append(f"チーム合計の能力差が {team_diff_value} あります。")
            except Exception as e:
                print(f"make_teams exception: {e}")
                continue

    if not best_result:
        await ctx.send("チーム分けに失敗しました。条件を緩和するか、参加者の希望レーンや能力値を見直してください。")
        return

    team1_ids, team2_ids, role_map = best_result

    # 直近チーム保存（match_id, recorded）
    match_id = str(int(time()))
    last_teams_data = load_data(team_file)
    if not last_teams_data:
        last_teams_data = {}
    last_teams_data[str(ctx.guild.id)] = {
        "team_a": {str(uid): role_map[uid] for uid in team1_ids},
        "team_b": {str(uid): role_map[uid] for uid in team2_ids},
        "guild_id": str(ctx.guild.id),
        "match_id": match_id,
        "recorded": False
    }
    save_data(team_file, last_teams_data)

    team1_sorted = sorted([(ctx.guild.get_member(uid), role_map[uid]) for uid in team1_ids],
                          key=lambda x: lanes.index(x[1]))
    team2_sorted = sorted([(ctx.guild.get_member(uid), role_map[uid]) for uid in team2_ids],
                          key=lambda x: lanes.index(x[1]))

    server_data = get_server_data(ctx.guild.id)
    team1_total = sum(server_data[str(uid)][role_map[uid]] for uid in team1_ids)
    team2_total = sum(server_data[str(uid)][role_map[uid]] for uid in team2_ids)

    msg = f"**チームが決まりました！（match_id: {match_id}）**\n"
    msg += f"**Team A**（合計: {team1_total}）\n"
    for member, lane in team1_sorted:
        if not member:
            continue
        val = server_data[str(member.id)][lane]
        msg += f"{member.display_name}（{lane.upper()} - {val}）\n"

    msg += f"\n**Team B**（合計: {team2_total}) \n"
    for member, lane in team2_sorted:
        if not member:
            continue
        val = server_data[str(member.id)][lane]
        msg += f"{member.display_name}（{lane.upper()} - {val}）\n"

    if best_score >= 1000:
        msg += "\n⚠️ 条件を完全には満たすチームは見つかりませんでしたが、最善の組み合わせを選びました。\n"
        msg += "\n".join(f"⚠️ {w}" for w in warnings)

    await ctx.send(msg)

# ===== チーム分け（アスペモード） =====
@bot.command(name="make_teams_aspe")
async def make_teams_aspe(ctx, lane_diff: int = 40, team_diff: int = 200, top_n: int = 5):
    """
    ネタ用：総当たりから上位N案を抽出してランダムに決定するチーム分け
    使い方:
      !make_teams_aspe              -> lane差40以内、合計差200以内で上位5案からランダム
      !make_teams_aspe 30 150       -> lane差30以内、合計差150以内で上位5案からランダム
      !make_teams_aspe 30 150 7     -> 上位7案からランダム
    """
    guild_id = ctx.guild.id
    if guild_id not in participants or len(participants[guild_id]) < 10:
        await ctx.send("参加者が10人未満です。")
        return

    member_ids = list(participants[guild_id].keys())
    server_data = get_server_data(guild_id)
    if not all(str(mid) in server_data for mid in member_ids):
        unregistered_ids = [mid for mid in member_ids if str(mid) not in server_data]
        mention_list = ', '.join(f'<@{uid}>' for uid in unregistered_ids)
        await ctx.send(f"一部の参加者が能力値を登録していません：{mention_list}")
        return

    candidates = []  # (score, (team1_ids, team2_ids, role_map), warnings)

    # ===== チーム案を総当たりで探索（make_teamsとほぼ同じ処理） =====
    for team1_ids in combinations(member_ids, 5):
        team2_ids = [uid for uid in member_ids if uid not in team1_ids]
        for team1_roles in permutations(lanes):
            role_map = {}
            valid_team1 = True
            for uid, lane in zip(team1_ids, team1_roles):
                prefs = participants[guild_id].get(uid, [])
                if prefs and lane not in prefs and 'fill' not in prefs:
                    valid_team1 = False
                    break
                role_map[uid] = lane
            if not valid_team1:
                continue

            try:
                valid = False
                for team2_roles in permutations(lanes):
                    try_role_map = role_map.copy()
                    success = True
                    for uid, lane in zip(team2_ids, team2_roles):
                        prefs = participants[guild_id].get(uid, [])
                        if prefs and lane not in prefs and 'fill' not in prefs:
                            success = False
                            break
                        try_role_map[uid] = lane
                    if success:
                        role_map = try_role_map
                        valid = True
                        break
                if not valid or len(role_map) != 10:
                    continue

                team1_score = 0
                team2_score = 0
                total_lane_diff = 0
                exceeded = False
                local_warnings = []

                for lane in lanes:
                    uid1 = [u for u in team1_ids if role_map[u] == lane][0]
                    uid2 = [u for u in team2_ids if role_map[u] == lane][0]
                    val1 = server_data[str(uid1)][lane]
                    val2 = server_data[str(uid2)][lane]
                    team1_score += val1
                    team2_score += val2
                    diff = abs(val1 - val2)
                    total_lane_diff += diff
                    if diff > lane_diff:
                        exceeded = True
                        local_warnings.append(f"{lane} の能力差が {diff} あります。")

                team_diff_value = abs(team1_score - team2_score)
                if team_diff_value > team_diff:
                    exceeded = True
                    local_warnings.append(f"チーム合計の能力差が {team_diff_value} あります。")

                score = total_lane_diff + team_diff_value
                if exceeded:
                    score += 1000  # 制限超過ペナルティ

                candidates.append((score, (team1_ids, team2_ids, role_map), local_warnings))

            except Exception as e:
                print(f"make_teams_aspe exception: {e}")
                continue

    if not candidates:
        await ctx.send("チーム分けに失敗しました。条件を緩和するか、参加者の希望レーンや能力値を見直してください。")
        return

    # ===== 上位 top_n 案からランダム選択 =====
    candidates.sort(key=lambda x: x[0])
    top_n = max(1, min(top_n, len(candidates)))
    top_slice = candidates[:top_n]
    picked = random.choice(top_slice)
    picked_score, picked_result, picked_warnings = picked
    picked_index = top_slice.index(picked)  # 0始まり → 後で +1 して表示用順位に

    team1_ids, team2_ids, role_map = picked_result

    # ===== 結果を保存 =====
    match_id = str(int(time()))
    last_teams_data = load_data(team_file) or {}
    last_teams_data[str(ctx.guild.id)] = {
        "team_a": {str(uid): role_map[uid] for uid in team1_ids},
        "team_b": {str(uid): role_map[uid] for uid in team2_ids},
        "guild_id": str(ctx.guild.id),
        "match_id": match_id,
        "recorded": False
    }
    save_data(team_file, last_teams_data)

    # ===== 表示用 =====
    team1_sorted = sorted([(ctx.guild.get_member(uid), role_map[uid]) for uid in team1_ids],
                          key=lambda x: lanes.index(x[1]))
    team2_sorted = sorted([(ctx.guild.get_member(uid), role_map[uid]) for uid in team2_ids],
                          key=lambda x: lanes.index(x[1]))

    server_data = get_server_data(ctx.guild.id)
    team1_total = sum(server_data[str(uid)][role_map[uid]] for uid in team1_ids)
    team2_total = sum(server_data[str(uid)][role_map[uid]] for uid in team2_ids)

    msg = f"**[ASPE] チームが決まりました！（match_id: {match_id}）**\n"
    msg += f"**Team A**（合計: {team1_total}）\n"
    for member, lane in team1_sorted:
        if not member:
            continue
        val = server_data[str(member.id)][lane]
        msg += f"{member.display_name}（{lane.upper()} - {val}）\n"

    msg += f"\n**Team B**（合計: {team2_total}) \n"
    for member, lane in team2_sorted:
        if not member:
            continue
        val = server_data[str(member.id)][lane]
        msg += f"{member.display_name}（{lane.upper()} - {val}）\n"

    if picked_score >= 1000:
        msg += "\n⚠️ 条件を完全には満たすチームは見つかりませんでしたが、ASPEモードで候補から選びました。\n"
        for w in picked_warnings:
            msg += f"⚠️ {w}\n"

    msg += f"\n今回の組合せは上位 {top_n} 候補のうち {picked_index+1} 位 を採用しました。"
    msg += f"\n（ASPEモード: バランス上位 {top_n} 案からランダム選択／lane_diff={lane_diff}, team_diff={team_diff}）"
    await ctx.send(msg)



@bot.command()
async def show_teams(ctx):
    guild_id = str(ctx.guild.id)
    last_teams = load_data(team_file)
    if not last_teams or guild_id not in last_teams or "team_a" not in last_teams[guild_id]:
        await ctx.send("保存されたチームが見つかりません。")
        return

    server_data = get_server_data(guild_id)
    lane_order = lanes

    def format_team(team, name):
        msg = f"**{name}**\n"
        sorted_items = sorted(team.items(), key=lambda item: lane_order.index(item[1]) if item[1] in lane_order else 999)
        total = 0
        for uid, lane in sorted_items:
            member = ctx.guild.get_member(int(uid))
            if not member:
                continue
            val = server_data.get(uid, {}).get(lane, 0)
            total += val
            msg += f"{member.display_name}（{lane.upper()} - {val}）\n"
        msg += f"**合計: {total}**\n"
        return msg

    lt = last_teams[guild_id]
    header = f"match_id: {lt.get('match_id')} / recorded: {lt.get('recorded')}\n"
    msg = header + format_team(lt["team_a"], "Team A") + "\n" + format_team(lt["team_b"], "Team B")
    await ctx.send(msg)

# ===== スワップ =====
@bot.command()
async def swap(ctx, member1: discord.Member, member2: discord.Member):
    guild_id = str(ctx.guild.id)
    last_teams = load_data(team_file)
    if not last_teams or guild_id not in last_teams:
        await ctx.send("直近のチームデータが存在しません。")
        return

    teams = last_teams[guild_id]
    team_a = teams.get("team_a", {})
    team_b = teams.get("team_b", {})

    uid1, uid2 = str(member1.id), str(member2.id)

    def find_team_and_lane(uid):
        if uid in team_a:
            return "A", team_a[uid]
        elif uid in team_b:
            return "B", team_b[uid]
        return None, None

    team1, lane1 = find_team_and_lane(uid1)
    team2, lane2 = find_team_and_lane(uid2)

    if team1 is None or team2 is None:
        await ctx.send("どちらかのユーザーが現在のチームに含まれていません。")
        return

    if team1 == team2:
        if team1 == "A":
            team_a[uid1], team_a[uid2] = lane2, lane1
        else:
            team_b[uid1], team_b[uid2] = lane2, lane1
        await ctx.send("同じチーム内のレーンを交換しました。")
    else:
        if team1 == "A":
            team_a.pop(uid1)
            team_b.pop(uid2)
            team_a[uid2] = lane1
            team_b[uid1] = lane2
        else:
            team_b.pop(uid1)
            team_a.pop(uid2)
            team_b[uid2] = lane1
            team_a[uid1] = lane2
        await ctx.send("異なるチーム間のメンバーをレーンを維持したまま交換しました。")

    save_data(team_file, last_teams)
    await ctx.invoke(bot.get_command("show_teams"))

# ===== 勝敗処理 =====
@bot.command()
async def win(ctx, winner: str):
    winner = winner.upper()
    if winner not in ["A", "B"]:
        await ctx.send("勝者は A または B で指定してください。")
        return

    guild_id = str(ctx.guild.id)
    last_teams_data = load_data(team_file)
    if guild_id not in last_teams_data or "team_a" not in last_teams_data[guild_id] or "team_b" not in last_teams_data[guild_id]:
        await ctx.send("直近のチームデータが見つかりません。")
        return

    # 二重報告防止
    if last_teams_data[guild_id].get("recorded"):
        await ctx.send("この試合は既に結果記録済みです。新しく !make_teams してから報告してください。")
        return

    # 誤爆防止: 実行者が直近チームに含まれているか
    author_uid = str(ctx.author.id)
    if (author_uid not in last_teams_data[guild_id]["team_a"]) and (author_uid not in last_teams_data[guild_id]["team_b"]):
        await ctx.send("警告: 実行者が直近の編成に含まれていません。!show_teams で確認してから報告してください。")
        return

    # abilities.json
    ability_data = load_data(ability_file)
    if guild_id not in ability_data:
        await ctx.send("能力値データが見つかりません。")
        return
    guild_abilities = ability_data[guild_id]

    # history.json
    history_data = load_data(history_file)

    # 勝者・敗者
    winner_key = "team_a" if winner == 'A' else "team_b"
    loser_key = "team_b" if winner == 'A' else "team_a"
    team_win = last_teams_data[guild_id][winner_key]
    team_lose = last_teams_data[guild_id][loser_key]

    def update_ability(uid, lane, is_winner, match_count):
        # しきい値に応じた増減値
        delta = DELTA_EARLY if match_count < EARLY_MATCHES else DELTA_LATE
        current_ability = guild_abilities[uid].get(lane, 60)
        if is_winner:
            guild_abilities[uid][lane] = min(ability_cap, current_ability + delta)
        else:
            guild_abilities[uid][lane] = max(0, current_ability - delta)

    def update_history(uid, lane, is_winner):
        if uid not in history_data:
            history_data[uid] = {"total_win": 0, "total_lose": 0, "lanes": {}}
        if lane not in history_data[uid]["lanes"]:
            history_data[uid]["lanes"][lane] = {"win": 0, "lose": 0}
        if is_winner:
            history_data[uid]["total_win"] += 1
            history_data[uid]["lanes"][lane]["win"] += 1
        else:
            history_data[uid]["total_lose"] += 1
            history_data[uid]["lanes"][lane]["lose"] += 1

    for team, is_winner in [(team_win, True), (team_lose, False)]:
        for uid, lane in team.items():
            if uid not in guild_abilities or lane not in guild_abilities[uid]:
                continue
            match_count = history_data.get(uid, {}).get("total_win", 0) + history_data.get(uid, {}).get("total_lose", 0)
            update_ability(uid, lane, is_winner, match_count)
            update_history(uid, lane, is_winner)

    # 保存
    save_data(ability_file, ability_data)
    save_data(history_file, history_data)
    # 記録済みフラグ
    last_teams_data[guild_id]["recorded"] = True
    save_data(team_file, last_teams_data)

    await ctx.send(f"チーム{winner} の勝利を記録しました。能力値と戦績を更新しました。")

# ===== 戦績・ランキング =====
@bot.command()
async def show_custom(ctx, member: discord.Member = None):
    history_data = load_data(history_file)
    member = member or ctx.author
    uid = str(member.id)
    if uid not in history_data:
        await ctx.send(f"{member.display_name} のカスタム戦績は記録されていません。")
        return
    user_history = history_data[uid]
    total_win = user_history.get("total_win", 0)
    total_lose = user_history.get("total_lose", 0)
    total_games = total_win + total_lose
    rate = f"{round((total_win / total_games) * 100, 1)}%" if total_games else "0%"

    msg = f"**📘 {member.display_name} のカスタム戦績**\n"
    msg += f"🔹 合計: {total_games}戦 {total_win}勝 {total_lose}敗　勝率 {rate}\n"
    for lane in lanes:
        lane_data = user_history.get("lanes", {}).get(lane, {"win": 0, "lose": 0})
        win = lane_data["win"]
        lose = lane_data["lose"]
        lt = win + lose
        rate_l = f"{round((win / lt) * 100, 1)}%" if lt else "0%"
        msg += f"　- {lane}: {lt}戦 {win}勝 {lose}敗　勝率 {rate_l}\n"
    await ctx.send(msg)

@bot.command()
async def ranking(ctx):
    server_data = get_server_data(ctx.guild.id)
    if not server_data:
        await ctx.send("データが存在しません。")
        return
    rankings = {lane: [] for lane in lanes}
    for uid, stats in server_data.items():
        member = ctx.guild.get_member(int(uid))
        if not member:
            continue
        for lane in lanes:
            rankings[lane].append((member.display_name, stats.get(lane, 0)))
    msg = "**🔝 レーン別ランキング**\n"
    for lane in lanes:
        msg += f"\n**{lane.upper()}**\n"
        for i, (name, score) in enumerate(sorted(rankings[lane], key=lambda x: x[1], reverse=True), 1):
            msg += f"{i}. {name} - {score}\n"
    await ctx.send(msg)

# ===== ヘルプ =====
@bot.command(name="help_mc")
async def help_mc_command(ctx):
    await ctx.send("""
📘 **LOLMakeCustom コマンド一覧（簡易版）**

!ability @user 10 10 10 10 10 - 能力値登録  
!delete_ability @user - 能力値削除  
!show_ability - 能力値一覧表示  

!join top mid - 参加登録（レーン指定：top/jg/mid/adc/sup または fill）  
!leave @user - 参加解除  
!participants_list - 参加者一覧表示  
!reset - 全参加者リセット  

!make_teams [lane_diff] [team_diff] - 公平寄りチーム分け（例: 30 150）  
!make_teams_aspe [lane_diff] [team_diff] [top_n] - ASPE寄りチーム分け（ランダム要素あり／top_n=上位候補数）  
!swap @user1 @user2 - レーン・チーム入替（直前の !make_teams 系コマンド必須）  

!win A / B - 勝敗報告（5戦目まで ±10 ／ 6戦目以降 ±5）  

!ranking - レーン別ランキング  
!show_custom @user - 個人戦績表示  
!show_teams - 直近チーム表示  

!help_mc_detail - 詳細説明
""")


@bot.command(name="help_mc_detail")
async def help_mc_detail_command(ctx):
    await ctx.send("""
📘 **LOLMakeCustom コマンド詳細説明**

---

### 🧠 能力値関連
- `!ability @user 10 10 10 10 10`  
  → @user に **top, jg, mid, adc, sup** の順で能力値を登録（0以上）

- `!delete_ability @user`  
  → 指定ユーザーの能力値を削除

- `!show_ability`  
  → 登録済みの全ユーザーの能力値と **合計値順** で表示

---

### 🎮 参加関連
- `!join @user top jg`  
  → 希望レーンを2つまで登録（例：top と jg）

- `!join @user fill fill`  
  → レーンがどこでも良い場合は **fill** を利用

- `!leave @user`  
  → 参加リストから @user を削除

- `!participants_list`  
  → 現在の参加メンバー一覧と希望レーンを表示

- `!reset`  
  → 参加者を全てリセット

---

### ⚔️ チーム編成関連
- `!make_teams [lane_diff] [team_diff]`  
  （例：`!make_teams 30 150`）  
  → 希望レーンを考慮して10人を自動で5v5に分ける  
  　- デフォルト: **対面差30以内／合計差150以内**  
  　- 条件を満たせない場合も最良案を提示（警告あり）

- `!make_teams_aspe [lane_diff] [team_diff] [top_n]`  
  （例：`!make_teams_aspe 40 200 5`）  
  → **FUNモード**：上位N案からランダムに選ぶ  
  　- デフォルト: レーン差40／合計差200／N=5  
  　- 条件未満しか無い場合もペナルティ加点候補から選択

- `!swap @user1 @user2`  
  → レーン・チームを入れ替え（直前の編成が必要）

---

### 🏆 勝敗報告と成績
- `!win A` または `!win B`  
  → 勝利チームのレーン能力値を **+**、敗者を **−** で調整  
  　- 5戦目までは ±10  
  　- 6戦目以降は ±5  
  　- 二重報告はブロック  
  　- 実行者が直近チームに含まれていない場合は警告  

---

### 📊 各種統計
- `!ranking`  
  → 各レーンの能力値上位ランキングを表示

- `!show_custom @user`  
  → 指定ユーザーの **勝率・試合数・レーン別戦績** を表示

- `!show_teams`  
  → 直近チーム編成と合計能力値を表示
""")


# ===== 起動 =====
bot.run(BOT_TOKEN)
