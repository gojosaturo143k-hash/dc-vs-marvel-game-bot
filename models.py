import database as db
from datetime import datetime

def get_or_create_user(user_id, username=None, first_name=None):
    user = db.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not user:
        db.execute_query(
            "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name), commit=True
        )
        user = db.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    elif username or first_name:
        db.execute_query(
            "UPDATE users SET username = COALESCE(?, username), first_name = COALESCE(?, first_name) WHERE user_id = ?",
            (username, first_name, user_id), commit=True
        )
    return dict(user)

def update_user_stats(user_id, xp_gain, coins_gain, win, kills):
    user = db.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if not user: return
    
    new_xp = user['xp'] + xp_gain
    new_coins = user['coins'] + coins_gain
    new_battles = user['battles'] + 1
    new_wins = user['wins'] + (1 if win else 0)
    new_losses = user['losses'] + (0 if win else 1)
    new_kills = user['total_kills'] + kills
    
    db.execute_query(
        """UPDATE users SET xp=?, coins=?, battles=?, wins=?, losses=?, total_kills=? WHERE user_id=?""",
        (new_xp, new_coins, new_battles, new_wins, new_losses, new_kills, user_id), commit=True
    )

def set_favorite_char(user_id, char_id):
    db.execute_query("UPDATE users SET favorite_char = ? WHERE user_id = ?", (char_id, user_id), commit=True)

def get_leaderboard():
    return db.execute_query("SELECT * FROM users ORDER BY xp DESC LIMIT 20", fetchall=True)

def can_claim_daily(user_id):
    res = db.execute_query("SELECT last_claim FROM daily_rewards WHERE user_id = ?", (user_id,), fetchone=True)
    if not res: return True
    last = datetime.fromisoformat(res['last_claim'])
    return (datetime.now() - last).days >= 1

def claim_daily(user_id, xp, coins):
    db.execute_query(
        "INSERT OR REPLACE INTO daily_rewards (user_id, last_claim) VALUES (?, CURRENT_TIMESTAMP)",
        (user_id,), commit=True
    )
    db.execute_query(
        "UPDATE users SET xp = xp + ?, coins = coins + ? WHERE user_id = ?",
        (xp, coins, user_id), commit=True
    )

def add_battle_log(game_id, chat_id, winner, log_text=""):
    db.execute_query(
        "INSERT INTO battle_logs (game_id, chat_id, winner, log_text) VALUES (?, ?, ?, ?)",
        (game_id, chat_id, winner, log_text), commit=True
    )

def get_battle_history(chat_id):
    return db.execute_query(
        "SELECT * FROM battle_logs WHERE chat_id = ? ORDER BY created_at DESC LIMIT 10",
        (chat_id,), fetchall=True
    )

def create_game(chat_id):
    return db.execute_query(
        "INSERT INTO games (chat_id) VALUES (?)", (chat_id,), commit=True
    )

def get_active_game(chat_id):
    return db.execute_query(
        "SELECT * FROM games WHERE chat_id = ? AND status IN ('lobby', 'character_select', 'battle')",
        (chat_id,), fetchone=True
    )

def get_game_by_id(game_id):
    return db.execute_query("SELECT * FROM games WHERE game_id = ?", (game_id,), fetchone=True)

def update_game_status(game_id, status):
    db.execute_query("UPDATE games SET status = ? WHERE game_id = ?", (status, game_id), commit=True)

def update_turn_index(game_id, idx):
    db.execute_query("UPDATE games SET current_turn_idx = ? WHERE game_id = ?", (idx, game_id), commit=True)

def add_player_to_game(game_id, user_id, team):
    db.execute_query(
        "INSERT INTO game_players (game_id, user_id, team) VALUES (?, ?, ?)",
        (game_id, user_id, team), commit=True
    )

def get_game_players(game_id):
    return db.execute_query("SELECT * FROM game_players WHERE game_id = ?", (game_id,), fetchall=True)

def get_player_in_game(game_id, user_id):
    return db.execute_query(
        "SELECT * FROM game_players WHERE game_id = ? AND user_id = ?", (game_id, user_id), fetchone=True
    )

def update_player_character(game_id, user_id, char_id, hp):
    db.execute_query(
        "UPDATE game_players SET character_id = ?, current_hp = ? WHERE game_id = ? AND user_id = ?",
        (char_id, hp, game_id, user_id), commit=True
    )

def update_battle_state(game_id, user_id, hp=None, is_defending=None, is_dodging=None, special_cooldown=None, is_alive=None, kills=None):
    p = get_player_in_game(game_id, user_id)
    if not p: return
    
    hp = hp if hp is not None else p['current_hp']
    is_defending = 1 if is_defending else (0 if is_defending is False else p['is_defending'])
    is_dodging = 1 if is_dodging else (0 if is_dodging is False else p['is_dodging'])
    special_cooldown = special_cooldown if special_cooldown is not None else p['special_cooldown']
    is_alive = 1 if is_alive else (0 if is_alive is False else p['is_alive'])
    kills = kills if kills is not None else p['kills']
    
    db.execute_query(
        """UPDATE game_players SET current_hp=?, is_defending=?, is_dodging=?, special_cooldown=?, is_alive=?, kills=? 
           WHERE game_id=? AND user_id=?""",
        (hp, is_defending, is_dodging, special_cooldown, is_alive, kills, game_id, user_id), commit=True
    )
