CHARACTERS = {
    "Spider-Man": {"id": "spider_man", "team": "Marvel", "hp": 90, "attack": 20, "defense": 14, "speed": 90, "special": "Web Trap", "emoji": "🕷️", "sp_mult": 1.8, "sp_type": "damage", "cd": 3},
    "Iron Man": {"id": "iron_man", "team": "Marvel", "hp": 100, "attack": 24, "defense": 20, "speed": 70, "special": "Repulsor Blast", "emoji": "🤖", "sp_mult": 1.8, "sp_type": "damage", "cd": 3},
    "Thor": {"id": "thor", "team": "Marvel", "hp": 115, "attack": 28, "defense": 23, "speed": 60, "special": "Thunder Strike", "emoji": "⚡", "sp_mult": 1.9, "sp_type": "damage", "cd": 4},
    "Hulk": {"id": "hulk", "team": "Marvel", "hp": 130, "attack": 25, "defense": 27, "speed": 45, "special": "Rage Smash", "emoji": "💪", "sp_mult": 2.0, "sp_type": "damage", "cd": 4},
    "Captain America": {"id": "cap", "team": "Marvel", "hp": 105, "attack": 19, "defense": 28, "speed": 65, "special": "Shield Counter", "emoji": "🛡️", "sp_mult": 1.7, "sp_type": "damage", "cd": 3},
    "Doctor Strange": {"id": "dr_strange", "team": "Marvel", "hp": 90, "attack": 23, "defense": 18, "speed": 75, "special": "Mystic Shield", "emoji": "🔮", "sp_mult": 0.0, "sp_type": "heal", "heal_amt": 30, "cd": 4},
    "Black Panther": {"id": "black_panther", "team": "Marvel", "hp": 95, "attack": 22, "defense": 20, "speed": 88, "special": "Kinetic Burst", "emoji": "🐾", "sp_mult": 1.8, "sp_type": "damage", "cd": 3},
    "Scarlet Witch": {"id": "scarlet_witch", "team": "Marvel", "hp": 90, "attack": 30, "defense": 14, "speed": 70, "special": "Chaos Magic", "emoji": "🔴", "sp_mult": 2.0, "sp_type": "damage", "cd": 4},
    "Ant-Man": {"id": "ant_man", "team": "Marvel", "hp": 85, "attack": 18, "defense": 16, "speed": 80, "special": "Giant Stomp", "emoji": "🐜", "sp_mult": 1.9, "sp_type": "damage", "cd": 3},
    "Wolverine": {"id": "wolverine", "team": "Marvel", "hp": 95, "attack": 26, "defense": 22, "speed": 75, "special": "Berserker Rage", "emoji": "🐺", "sp_mult": 2.0, "sp_type": "damage", "cd": 4},
    
    "Superman": {"id": "superman", "team": "DC", "hp": 120, "attack": 29, "defense": 27, "speed": 75, "special": "Heat Vision", "emoji": "🦸", "sp_mult": 1.9, "sp_type": "damage", "cd": 4},
    "Batman": {"id": "batman", "team": "DC", "hp": 95, "attack": 22, "defense": 24, "speed": 70, "special": "Tactical Counter", "emoji": "🦇", "sp_mult": 1.8, "sp_type": "damage", "cd": 3},
    "Flash": {"id": "flash", "team": "DC", "hp": 85, "attack": 19, "defense": 13, "speed": 100, "special": "Speed Blitz", "emoji": "💨", "sp_mult": 1.9, "sp_type": "damage", "cd": 3},
    "Wonder Woman": {"id": "wonder_woman", "team": "DC", "hp": 110, "attack": 26, "defense": 25, "speed": 78, "special": "Lasso Strike", "emoji": "🗡️", "sp_mult": 1.8, "sp_type": "damage", "cd": 3},
    "Aquaman": {"id": "aquaman", "team": "DC", "hp": 110, "attack": 24, "defense": 24, "speed": 60, "special": "Trident Strike", "emoji": "🔱", "sp_mult": 1.8, "sp_type": "damage", "cd": 3},
    "Green Lantern": {"id": "green_lantern", "team": "DC", "hp": 100, "attack": 25, "defense": 22, "speed": 70, "special": "Energy Construct", "emoji": "🟢", "sp_mult": 1.8, "sp_type": "damage", "cd": 3},
    "Cyborg": {"id": "cyborg", "team": "DC", "hp": 105, "attack": 23, "defense": 22, "speed": 55, "special": "Sonic Cannon", "emoji": "🦾", "sp_mult": 1.9, "sp_type": "damage", "cd": 3},
    "Shazam": {"id": "shazam", "team": "DC", "hp": 115, "attack": 27, "defense": 24, "speed": 72, "special": "Lightning Fury", "emoji": "⚡", "sp_mult": 1.9, "sp_type": "damage", "cd": 4},
    "Supergirl": {"id": "supergirl", "team": "DC", "hp": 110, "attack": 27, "defense": 23, "speed": 80, "special": "Solar Burst", "emoji": "🌟", "sp_mult": 1.9, "sp_type": "damage", "cd": 4},
    "Green Arrow": {"id": "green_arrow", "team": "DC", "hp": 90, "attack": 24, "defense": 15, "speed": 82, "special": "Trick Arrow", "emoji": "🏹", "sp_mult": 1.8, "sp_type": "damage", "cd": 3}
}

def get_marvel_chars():
    return [k for k, v in CHARACTERS.items() if v["team"] == "Marvel"]

def get_dc_chars():
    return [k for k, v in CHARACTERS.items() if v["team"] == "DC"]
