import logging
import threading
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from characters import CHARACTERS, get_marvel_chars, get_dc_chars
import models as db
from game import GameEngine
from utils import format_number, get_player_name
from config import MIN_PLAYERS, MAX_PLAYERS, LOBBY_TIMEOUT_SECONDS
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

LOBBY_MESSAGES = {}

# --- Lobby Timeout without JobQueue ---
def run_lobby_timer(chat_id, game_id, context):
    time.sleep(LOBBY_TIMEOUT_SECONDS)
    game = db.get_game_by_id(game_id)
    if game and game['status'] == 'lobby':
        db.update_game_status(game_id, 'expired')
        msg_id = LOBBY_MESSAGES.get(chat_id)
        if msg_id:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(context.bot.edit_message_text(
                        "⌛ This battle lobby has expired.\nStart a new game with /startgame",
                        chat_id=chat_id, message_id=msg_id
                    ))
                else:
                    loop.run_until_complete(context.bot.edit_message_text(
                        "⌛ This battle lobby has expired.\nStart a new game with /startgame",
                        chat_id=chat_id, message_id=msg_id
                    ))
            except Exception as e:
                logger.warning(f"Could not edit expired lobby message: {e}")

async def startgame_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == 'private':
        await update.message.reply_text("❌ This game can only be played in groups!")
        return
    
    active = db.get_active_game(chat_id)
    if active:
        await update.message.reply_text("❌ A game is already active in this group!\nUse /cancelgame to end it.")
        return
    
    game_id = db.create_game(chat_id)
    text = (
        "⚔️ MARVEL VS DC ⚔️\n\n"
        "A new battle is forming!\n\n"
        "👥 Players: 0/10\n"
        "🟥 Marvel: 0\n"
        "🟦 DC: 0\n\n"
        "Minimum players: 2\n"
        "Maximum players: 10\n\n"
        "Choose your side:"
    )
    keyboard = [
        [InlineKeyboardButton("🟥 Join Marvel", callback_data=f"join_{game_id}_Marvel"),
         InlineKeyboardButton("🟦 Join DC", callback_data=f"join_{game_id}_DC")],
        [InlineKeyboardButton("🎭 Choose Character", callback_data="noop"),
         InlineKeyboardButton("👥 Players", callback_data=f"list_{game_id}")],
        [InlineKeyboardButton("🚀 Start Battle", callback_data=f"start_{game_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{game_id}")]
    ]
    msg = await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    LOBBY_MESSAGES[chat_id] = msg.message_id
    
    # Start timeout in background thread
    timer_thread = threading.Thread(target=run_lobby_timer, args=(chat_id, game_id, context), daemon=True)
    timer_thread.start()

def get_lobby_text(game_id):
    players = db.get_game_players(game_id)
    marvel = [p for p in players if p['team'] == 'Marvel']
    dc = [p for p in players if p['team'] == 'DC']
    
    text = "⚔️ MARVEL VS DC ⚔️\n\n"
    text += f"👥 Players: {len(players)}/{MAX_PLAYERS}\n\n"
    
    text += "🟥 MARVEL\n"
    if marvel:
        for i, p in enumerate(marvel, 1):
            char = CHARACTERS.get(p['character_id'])
            c_str = f" ({char['emoji']} {p['character_id']})" if char else ""
            text += f"{i}. {p['first_name'] or p['username'] or str(p['user_id'])}{c_str}\n"
    else:
        text += "Empty\n"
        
    text += "\n🟦 DC\n"
    if dc:
        for i, p in enumerate(dc, 1):
            char = CHARACTERS.get(p['character_id'])
            c_str = f" ({char['emoji']} {p['character_id']})" if char else ""
            text += f"{i}. {p['first_name'] or p['username'] or str(p['user_id'])}{c_str}\n"
    else:
        text += "Empty\n"
        
    if len(marvel) != len(dc) or len(players) < MIN_PLAYERS:
        text += "\nWaiting for players..."
    else:
        all_selected = all(p['character_id'] is not None for p in players)
        if not all_selected:
            text += "\n⏳ All players must select a character!"
        else:
            text += "\n✅ Ready to start!"
            
    return text

def get_lobby_keyboard(game_id, user_id=None):
    players = db.get_game_players(game_id)
    marvel = [p for p in players if p['team'] == 'Marvel']
    dc = [p for p in players if p['team'] == 'DC']
    
    player = None
    if user_id:
        player = db.get_player_in_game(game_id, user_id)
    
    row1 = []
    if not player:
        row1 = [InlineKeyboardButton("🟥 Join Marvel", callback_data=f"join_{game_id}_Marvel"),
                InlineKeyboardButton("🟦 Join DC", callback_data=f"join_{game_id}_DC")]
    else:
        row1 = [InlineKeyboardButton(f"🟥 Team Marvel ({len(marvel)})", callback_data="noop"),
                InlineKeyboardButton(f"🟦 Team DC ({len(dc)})", callback_data="noop")]
        
    row2 = []
    if player and not player['character_id']:
        team = player['team']
        row2 = [InlineKeyboardButton("🎭 Choose Character", callback_data=f"chars_{game_id}_{user_id}_{team}_0")]
    else:
        row2 = [InlineKeyboardButton("🎭 Choose Character", callback_data="noop")]
        
    row2.append(InlineKeyboardButton("👥 Players", callback_data=f"list_{game_id}"))
    
    row3 = [InlineKeyboardButton("🚀 Start Battle", callback_data=f"start_{game_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{game_id}")]
            
    return InlineKeyboardMarkup([row1, row2, row3])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    chat_id = query.message.chat_id
    # FIX: Correct way to get message_id
    msg_id = query.message.message_id
    
    db.get_or_create_user(user.id, user.username, user.first_name)
    
    if data == "noop":
        return
        
    try:
        parts = data.split('_')
        action = parts[0]
        
        if action == "join":
            game_id = int(parts[1])
            team = parts[2]
            await handle_join(query, context, game_id, team, user, chat_id, msg_id)
            
        elif action == "chars":
            game_id = int(parts[1])
            req_user_id = int(parts[2])
            team = parts[3]
            page = int(parts[4])
            await handle_char_menu(query, context, game_id, req_user_id, team, page, user.id, chat_id, msg_id)
            
        elif action == "selchar":
            game_id = int(parts[1])
            char_name = '_'.join(parts[2:])
            await handle_select_char(query, context, game_id, char_name, user.id, chat_id, msg_id)
            
        elif action == "start":
            game_id = int(parts[1])
            await handle_start_battle(query, context, game_id, chat_id, msg_id)
            
        elif action == "cancel":
            game_id = int(parts[1])
            await handle_cancel(query, context, game_id, chat_id, msg_id)
            
        elif action == "list":
            game_id = int(parts[1])
            text = get_lobby_text(game_id)
            kb = get_lobby_keyboard(game_id, user.id)
            try:
                await query.edit_message_text(text, reply_markup=kb)
            except Exception:
                pass
                
        elif action == "turn":
            game_id = int(parts[1])
            uid = int(parts[2])
            await handle_turn_action(query, context, game_id, uid, chat_id, msg_id)
            
        elif action == "target":
            game_id = int(parts[1])
            attacker_id = int(parts[2])
            target_id = int(parts[3])
            await handle_target(query, context, game_id, attacker_id, target_id, chat_id, msg_id)
            
        elif action == "sp_target":
            game_id = int(parts[1])
            attacker_id = int(parts[2])
            target_id = int(parts[3])
            await handle_special_target(query, context, game_id, attacker_id, target_id, chat_id, msg_id)
            
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ This action is no longer valid.")
        except Exception:
            pass

async def handle_join(query, context, game_id, team, user, chat_id, msg_id):
    game = db.get_game_by_id(game_id)
    if not game or game['status'] != 'lobby':
        await query.edit_message_text("❌ This action is no longer valid.")
        return
        
    if game['chat_id'] != chat_id:
        return
        
    existing = db.get_player_in_game(game_id, user.id)
    if existing:
        if existing['team'] == team:
            await query.answer(f"❌ You are already in Team {team}.", show_alert=True)
        else:
            await query.answer(f"❌ You are already in Team {existing['team']}.", show_alert=True)
        return
        
    players = db.get_game_players(game_id)
    curr_team_count = len([p for p in players if p['team'] == team])
    other_team = 'DC' if team == 'Marvel' else 'Marvel'
    other_count = len([p for p in players if p['team'] == other_team])
    
    if curr_team_count >= 5:
        await query.answer("❌ This team is full (max 5).", show_alert=True)
        return
    if curr_team_count > other_count:
        await query.answer("❌ Teams must be balanced. Join the other team.", show_alert=True)
        return
        
    db.add_player_to_game(game_id, user.id, team)
    
    text = get_lobby_text(game_id)
    kb = get_lobby_keyboard(game_id, user.id)
    
    try:
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=LOBBY_MESSAGES.get(chat_id, msg_id), reply_markup=kb)
    except Exception:
        pass
        
    await query.answer(f"🟥 You joined Team {team}!" if team == "Marvel" else f"🟦 You joined Team {team}!")

async def handle_char_menu(query, context, game_id, req_user_id, team, page, actual_user_id, chat_id, msg_id):
    if actual_user_id != req_user_id:
        await query.answer("❌ You cannot use another player's character selection!", show_alert=True)
        return
        
    game = db.get_game_by_id(game_id)
    if not game or game['status'] not in ('lobby', 'character_select'):
        await query.edit_message_text("❌ This action is no longer valid.")
        return
        
    player = db.get_player_in_game(game_id, req_user_id)
    if not player or player['character_id']:
        await query.edit_message_text("❌ This action is no longer valid.")
        return
        
    chars = get_marvel_chars() if team == "Marvel" else get_dc_chars()
    taken_chars = [p['character_id'] for p in db.get_game_players(game_id) if p['character_id']]
    
    per_page = 5
    total_pages = (len(chars) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_chars = chars[start:end]
    
    text = f"🎭 Select {team} Character (Page {page+1}/{total_pages})\n\n"
    buttons = []
    
    for c_name in page_chars:
        c = CHARACTERS[c_name]
        is_taken = c_name in taken_chars
        state = " ❌ Taken" if is_taken else ""
        text += f"{c['emoji']} {c_name}{state}\n"
        text += f"   HP:{c['hp']} ATK:{c['attack']} DEF:{c['defense']} SPD:{c['speed']}\n"
        text += f"   🔥 {c['special']}\n\n"
        
        cb = f"selchar_{game_id}_{c_name}" if not is_taken else "noop"
        buttons.append(InlineKeyboardButton(f"{c['emoji']} {c_name}", callback_data=cb))
        
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Back", callback_data=f"chars_{game_id}_{req_user_id}_{team}_{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"chars_{game_id}_{req_user_id}_{team}_{page+1}"))
        
    if nav:
        buttons.append(nav)
        
    kb = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(text, reply_markup=kb)
    except Exception:
        pass

async def handle_select_char(query, context, game_id, char_name, user_id, chat_id, msg_id):
    game = db.get_game_by_id(game_id)
    if not game or game['status'] not in ('lobby', 'character_select'):
        await query.edit_message_text("❌ This action is no longer valid.")
        return
        
    player = db.get_player_in_game(game_id, user_id)
    if not player or player['character_id']:
        await query.edit_message_text("❌ This action is no longer valid.")
        return
        
    char = CHARACTERS.get(char_name)
    if not char: return
    
    if char['team'] != player['team']:
        await query.answer("❌ You must choose a character from your team!", show_alert=True)
        return
        
    taken = [p['character_id'] for p in db.get_game_players(game_id) if p['character_id']]
    if char_name in taken:
        await query.answer(f"❌ {char_name} is already selected by another player.\nPlease choose another character.", show_alert=True)
        return
        
    db.update_player_character(game_id, user_id, char_name, char['hp'])
    db.set_favorite_char(user_id, char_name)
    
    text = f"✅ You selected {char['emoji']} {char_name}!\n\n"
    text += get_lobby_text(game_id)
    kb = get_lobby_keyboard(game_id, user_id)
    
    try:
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=LOBBY_MESSAGES.get(chat_id, msg_id), reply_markup=kb)
    except Exception:
        pass

async def handle_start_battle(query, context, game_id, chat_id, msg_id):
    game = db.get_game_by_id(game_id)
    if not game or game['status'] == 'battle':
        await query.answer("❌ Game already in progress or invalid.", show_alert=True)
        return
        
    players = db.get_game_players(game_id)
    marvel = [p for p in players if p['team'] == 'Marvel']
    dc = [p for p in players if p['team'] == 'DC']
    
    if len(players) < MIN_PLAYERS:
        await query.answer(f"❌ Need at least {MIN_PLAYERS} players.", show_alert=True)
        return
    if len(marvel) != len(dc):
        await query.answer(f"❌ Teams must have equal players.\nMarvel: {len(marvel)}\nDC: {len(dc)}", show_alert=True)
        return
    if not all(p['character_id'] for p in players):
        await query.answer("❌ All players must select a character first!", show_alert=True)
        return
        
    db.update_game_status(game_id, 'battle')
        
    engine = GameEngine(game_id)
    current_uid = engine.get_current_turn()
    
    if not current_uid:
        await query.edit_message_text("❌ Error starting battle.")
        return
        
    cur_p = engine.players[current_uid]
    cur_c = CHARACTERS[cur_p['character_id']]
    
    text = "⚔️ BATTLE START! ⚔️\n\n"
    text += get_battle_status(engine)
    text += f"\n🟢 {cur_p['first_name'] or cur_p['username']}'s Turn ({cur_c['emoji']} {cur_p['character_id']})"
    
    kb = get_battle_keyboard(game_id, current_uid, engine)
    
    try:
        await context.bot.edit_message_text(text, chat_id=chat_id, message_id=LOBBY_MESSAGES.get(chat_id, msg_id), reply_markup=kb)
    except Exception as e:
        logger.error(f"Start battle edit error: {e}")

def get_battle_status(engine):
    text = ""
    m_players = [(uid, p) for uid, p in engine.players.items() if CHARACTERS.get(p['character_id'], {}).get('team') == 'Marvel']
    d_players = [(uid, p) for uid, p in engine.players.items() if CHARACTERS.get(p['character_id'], {}).get('team') == 'DC']
    
    text += "🟥 MARVEL\n"
    for uid, p in m_players:
        c = CHARACTERS[p['character_id']]
        status = "" if p['is_alive'] else " 💀"
        text += f"{c['emoji']} {p['first_name'] or p['username']} ({p['character_id']}): {p['current_hp']}/{c['hp']} HP{status}\n"
        
    text += "\n🟦 DC\n"
    for uid, p in d_players:
        c = CHARACTERS[p['character_id']]
        status = "" if p['is_alive'] else " 💀"
        text += f"{c['emoji']} {p['first_name'] or p['username']} ({p['character_id']}): {p['current_hp']}/{c['hp']} HP{status}\n"
    return text

def get_battle_keyboard(game_id, current_uid, engine):
    p = engine.players.get(current_uid)
    if not p or not p['is_alive']: return InlineKeyboardMarkup([[InlineKeyboardButton("Error", callback_data="noop")]])
    
    c = CHARACTERS[p['character_id']]
    cd_text = f" ({p['special_cooldown']} CD)" if p['special_cooldown'] > 0 else ""
    
    kb = [
        [InlineKeyboardButton("⚔️ Attack", callback_data=f"turn_{game_id}_{current_uid}_attack"),
         InlineKeyboardButton("🛡️ Defend", callback_data=f"turn_{game_id}_{current_uid}_defend"),
         InlineKeyboardButton(f"💨 Dodge", callback_data=f"turn_{game_id}_{current_uid}_dodge")],
        [InlineKeyboardButton(f"🔥 Special{cd_text}", callback_data=f"turn_{game_id}_{current_uid}_special")]
    ]
    return InlineKeyboardMarkup(kb)

async def handle_turn_action(query, context, game_id, uid, chat_id, msg_id):
    user_id = query.from_user.id
    if user_id != uid:
        await query.answer("⏳ It's not your turn!", show_alert=True)
        return
        
    engine = GameEngine(game_id)
    current_uid = engine.get_current_turn()
    
    if current_uid != uid:
        await query.answer("⏳ It's not your turn!", show_alert=True)
        return
        
    p = engine.players[uid]
    c = CHARACTERS[p['character_id']]
    action = query.data.split('_')[-1]
    
    if action == "defend":
        engine.process_defend(uid)
        log = f"🛡️ {c['emoji']} {p['first_name'] or p['username']} is defending!\nIncoming damage will be reduced."
        await finish_turn(query, context, engine, game_id, chat_id, msg_id, log)
        
    elif action == "dodge":
        success = engine.process_dodge(uid)
        log = f"💨 {c['emoji']} {p['first_name'] or p['username']} attempts to dodge!\n{'✨ Dodge stance ready!' if success else '❌ Failed to enter dodge stance!'}"
        await finish_turn(query, context, engine, game_id, chat_id, msg_id, log)
        
    elif action == "attack":
        enemies = [uid_e for uid_e, p_e in engine.players.items() if p_e['is_alive'] and CHARACTERS.get(p_e['character_id'], {}).get('team') != c['team']]
        if not enemies: return
        text = "🎯 Choose your target:\n\n"
        buttons = []
        for e_id in enemies:
            e_p = engine.players[e_id]
            e_c = CHARACTERS[e_p['character_id']]
            text += f"{e_c['emoji']} {e_p['first_name'] or e_p['username']} ({e_p['character_id']}) ❤️ {e_p['current_hp']}\n"
            buttons.append(InlineKeyboardButton(f"{e_c['emoji']} {e_p['character_id']}", callback_data=f"target_{game_id}_{uid}_{e_id}"))
        kb = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
        try:
            await query.edit_message_text(text, reply_markup=kb)
        except Exception: pass
        
    elif action == "special":
        if p['special_cooldown'] > 0:
            await query.answer(f"⏳ Special is on cooldown.\n{p['special_cooldown']} turns remaining.", show_alert=True)
            return
            
        if c['sp_type'] == 'heal':
            winner, log = engine.process_special(uid)
            await finish_turn(query, context, engine, game_id, chat_id, msg_id, log, winner)
        else:
            enemies = [uid_e for uid_e, p_e in engine.players.items() if p_e['is_alive'] and CHARACTERS.get(p_e['character_id'], {}).get('team') != c['team']]
            if not enemies: return
            text = f"🔥 {c['special']} - Choose target:\n\n"
            buttons = []
            for e_id in enemies:
                e_p = engine.players[e_id]
                e_c = CHARACTERS[e_p['character_id']]
                text += f"{e_c['emoji']} {e_p['first_name'] or e_p['username']} ({e_p['character_id']}) ❤️ {e_p['current_hp']}\n"
                buttons.append(InlineKeyboardButton(f"{e_c['emoji']} {e_p['character_id']}", callback_data=f"sp_target_{game_id}_{uid}_{e_id}"))
            kb = InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
            try:
                await query.edit_message_text(text, reply_markup=kb)
            except Exception: pass

async def handle_target(query, context, game_id, attacker_id, target_id, chat_id, msg_id):
    if query.from_user.id != attacker_id:
        await query.answer("⏳ It's not your turn!", show_alert=True)
        return
    engine = GameEngine(game_id)
    if engine.get_current_turn() != attacker_id:
        await query.answer("⏳ It's not your turn!", show_alert=True)
        return
        
    winner, log = engine.process_attack(attacker_id, target_id)
    await finish_turn(query, context, engine, game_id, chat_id, msg_id, log, winner)

async def handle_special_target(query, context, game_id, attacker_id, target_id, chat_id, msg_id):
    if query.from_user.id != attacker_id:
        await query.answer("⏳ It's not your turn!", show_alert=True)
        return
    engine = GameEngine(game_id)
    if engine.get_current_turn() != attacker_id:
        await query.answer("⏳ It's not your turn!", show_alert=True)
        return
        
    winner, log = engine.process_special(attacker_id, target_id)
    await finish_turn(query, context, engine, game_id, chat_id, msg_id, log, winner)

async def finish_turn(query, context, engine, game_id, chat_id, msg_id, log, winner=None):
    engine.reduce_cooldowns()
    
    if winner:
        await handle_win(query, context, engine, game_id, chat_id, msg_id, winner)
        return
        
    next_uid = engine.next_turn()
    if not next_uid:
        await handle_win(query, context, engine, game_id, chat_id, msg_id, "Draw")
        return
        
    next_p = engine.players[next_uid]
    next_c = CHARACTERS[next_p['character_id']]
    
    text = f"{log}\n\n{'-'*20}\n\n"
    text += get_battle_status(engine)
    text += f"\n🟢 {next_p['first_name'] or next_p['username']}'s Turn ({next_c['emoji']} {next_p['character_id']})"
    
    kb = get_battle_keyboard(game_id, next_uid, engine)
    try:
        await query.edit_message_text(text, reply_markup=kb)
    except Exception as e:
        logger.error(f"Finish turn edit error: {e}")

async def handle_win(query, context, engine, game_id, chat_id, msg_id, winner):
    db.update_game_status(game_id, 'finished')
    players = engine.players
    
    survivors = []
    kill_dict = {}
    mvp_uid = None
    mvp_kills = -1
    
    for uid, p in players.items():
        c = CHARACTERS.get(p['character_id'])
        if p['is_alive']:
            survivors.append(f"{c['emoji']} {p['character_id']} — {p['current_hp']} HP")
        if p['kills'] > 0:
            kill_dict[p['character_id']] = p['kills']
        if p['kills'] > mvp_kills:
            mvp_kills = p['kills']
            mvp_uid = uid
            
    mvp_p = players.get(mvp_uid)
    mvp_c = CHARACTERS.get(mvp_p['character_id']) if mvp_p else None
    
    text = "🏆 BATTLE OVER! 🏆\n\n"
    text += f"🟥 MARVEL WINS!\n" if winner == "Marvel" else f"🟦 DC WINS!\n"
    text += "\nSurvivors:\n" + "\n".join(survivors) if survivors else "\nNo survivors!"
    
    if mvp_c and mvp_p:
        text += f"\n\nMVP:\n{mvp_c['emoji']} {mvp_p['first_name'] or mvp_p['username']} ({mvp_c['id']})"
        
    if kill_dict:
        text += "\n\nKills:\n" + "\n".join([f"{c} — {k}" for c, k in kill_dict.items()])
        
    text += "\n\n🎁 Rewards:\n"
    for uid, p in players.items():
        c = CHARACTERS.get(p['character_id'])
        is_winner = c['team'] == winner if winner != "Draw" else False
        xp = 500 if is_winner else 150
        coins = 250 if is_winner else 50
        db.update_user_stats(uid, xp, coins, is_winner, p['kills'])
        name = p['first_name'] or p['username'] or str(uid)
        text += f"{name}: +{xp} XP, +{coins} Coins\n"
        
    db.add_battle_log(game_id, chat_id, winner)
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([]))
    except Exception as e:
        logger.error(f"Handle win edit error: {e}")
        try:
            await context.bot.send_message(chat_id, text)
        except Exception: pass

async def handle_cancel(query, context, game_id, chat_id, msg_id):
    game = db.get_game_by_id(game_id)
    if not game or game['status'] == 'finished':
        await query.edit_message_text("❌ This action is no longer valid.")
        return
    db.update_game_status(game_id, 'cancelled')
    try:
        await query.edit_message_text("❌ Game cancelled.", reply_markup=InlineKeyboardMarkup([]))
    except Exception: pass

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = db.get_or_create_user(user.id, user.username, user.first_name)
    
    wr = (u['wins'] / u['battles'] * 100) if u['battles'] > 0 else 0.0
    fav = u['favorite_char'] or "None"
    
    text = (
        f"👤 PLAYER PROFILE\n\n"
        f"Name: {u['first_name'] or u['username'] or user.id}\n"
        f"Level: {max(1, u['xp'] // 500)}\n"
        f"XP: {format_number(u['xp'])}\n\n"
        f"⚔️ Battles: {u['battles']}\n"
        f"🏆 Wins: {u['wins']}\n"
        f"💀 Losses: {u['losses']}\n"
        f"📈 Win Rate: {wr:.1f}%\n\n"
        f"💰 Coins: {format_number(u['coins'])}\n\n"
        f"⭐ Favorite Character:\n{fav}\n\n"
        f"🔥 Total Kills: {u['total_kills']}"
    )
    await update.message.reply_text(text)

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaders = db.get_leaderboard()
    if not leaders:
        await update.message.reply_text("🏆 No players yet!")
        return
    text = "🏆 MARVEL VS DC LEADERBOARD\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = u['first_name'] or u['username'] or str(u['user_id'])
        text += f"{medal} {name} — {format_number(u['xp'])} XP\n"
    await update.message.reply_text(text)

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logs = db.get_battle_history(chat_id)
    if not logs:
        await update.message.reply_text("📜 No battle history in this group yet.")
        return
    text = "📜 BATTLE HISTORY\n\n"
    for i, log in enumerate(logs, 1):
        date_str = log['created_at'].split(' ')[0] if log['created_at'] else "Unknown"
        text += f"{i}. {log['winner']} defeated {'DC' if log['winner'] == 'Marvel' else 'Marvel'}\n   {date_str}\n\n"
    await update.message.reply_text(text)

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.first_name)
    if db.can_claim_daily(user.id):
        db.claim_daily(user.id, 50, 100)
        await update.message.reply_text("🎁 DAILY REWARD\n\nYou received:\n💰 +100 Coins\n⭐ +50 XP")
    else:
        await update.message.reply_text("⏳ You have already claimed your daily reward today!\nCome back tomorrow.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚔️ MARVEL VS DC BOT HELP ⚔️\n\n"
        "/startgame - Start a new match\n"
        "/cancelgame - Cancel active lobby\n"
        "/endgame - Force end game (Admins only)\n"
        "/profile - View your stats\n"
        "/leaderboard - Global rankings\n"
        "/history - Group battle history\n"
        "/daily - Claim daily reward\n"
        "/help - Show this message\n\n"
        "🎯 HOW TO PLAY:\n"
        "1. Use /startgame to create a lobby\n"
        "2. Pick Marvel or DC\n"
        "3. Choose a unique character\n"
        "4. Press Start Battle\n"
        "5. Take turns using Attacks, Defends, Dodges, and Specials!\n"
        "6. Defeat the enemy team to win XP and Coins!"
    )
    await update.message.reply_text(text)

async def cancelgame_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    game = db.get_active_game(chat_id)
    if not game:
        await update.message.reply_text("❌ No active game to cancel.")
        return
    db.update_game_status(game['game_id'], 'cancelled')
    msg_id = LOBBY_MESSAGES.get(chat_id)
    if msg_id:
        try:
            await context.bot.edit_message_text("❌ Game cancelled by command.", chat_id=chat_id, message_id=msg_id)
        except Exception: pass
    await update.message.reply_text("❌ Game cancelled successfully.")

async def endgame_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user.id)
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Only group admins can use this command.")
            return
    except Exception:
        await update.message.reply_text("❌ Could not verify admin status.")
        return
        
    game = db.get_active_game(chat_id)
    if not game:
        await update.message.reply_text("❌ No active game to end.")
        return
    db.update_game_status(game['game_id'], 'cancelled')
    msg_id = LOBBY_MESSAGES.get(chat_id)
    if msg_id:
        try:
            await context.bot.edit_message_text("🛑 Game forcefully ended by admin.", chat_id=chat_id, message_id=msg_id)
        except Exception: pass
    await update.message.reply_text("🛑 Game forcefully ended.")

async def dm_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        return
    text = "👋 Hey! I am the Marvel vs DC Battle Bot!\n\nI only work inside Telegram Groups. Add me to a group to start a battle!\n\nType /help in the group to see all commands."
    await update.message.reply_text(text)
