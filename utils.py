import random

def calc_damage(atk_stat, def_stat, is_defending=False, mult=1.0):
    base = max(1, (atk_stat - (def_stat * (0.3 if is_defending else 0.6))) * mult)
    variance = random.uniform(0.85, 1.15)
    crit = 1.5 if random.random() < 0.1 else 1.0
    damage = int(base * variance * crit)
    return max(1, damage)

def calc_dodge_chance(speed):
    return min(0.25 + (speed / 400), 0.50)

def get_player_name(context, user_id):
    try:
        chat_member = context.bot.get_chat_member(chat_id=user_id, user_id=user_id)
        name = chat_member.user.first_name or chat_member.user.username or str(user_id)
        return name
    except Exception:
        return str(user_id)

def format_number(n):
    return f"{n:,}"
