import logging
from characters import CHARACTERS
from utils import calc_damage, calc_dodge_chance
import models as db

logger = logging.getLogger(__name__)

class GameEngine:
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = {}
        self.turn_queue = []
        self.current_turn_idx = 0
        self.load_state()

    def load_state(self):
        db_players = db.get_game_players(self.game_id)
        for p in db_players:
            self.players[p['user_id']] = dict(p)
        game = db.get_game_by_id(self.game_id)
        if game:
            self.current_turn_idx = game['current_turn_idx']
        self.build_turn_queue()

    def build_turn_queue(self):
        alive = [uid for uid, p in self.players.items() if p['is_alive']]
        self.turn_queue = sorted(alive, key=lambda uid: self.players[uid].get('speed', 0), reverse=True)

    def get_current_turn(self):
        if not self.turn_queue: return None
        idx = self.current_turn_idx % len(self.turn_queue)
        return self.turn_queue[idx]

    def next_turn(self):
        if not self.turn_queue: return None
        self.build_turn_queue()
        if not self.turn_queue: return None
        
        self.current_turn_idx = (self.current_turn_idx + 1) % len(self.turn_queue)
        db.update_turn_index(self.game_id, self.current_turn_idx)
        return self.get_current_turn()

    def process_attack(self, attacker_id, target_id):
        atk_p = self.players.get(attacker_id)
        def_p = self.players.get(target_id)
        if not atk_p or not def_p: return None, "Invalid players."

        atk_c = CHARACTERS.get(atk_p['character_id'])
        def_c = CHARACTERS.get(def_p['character_id'])
        if not atk_c or not def_c: return None, "Missing character data."

        is_defending = bool(def_p['is_defending'])
        damage = calc_damage(atk_c['attack'], def_c['defense'], is_defending)
        
        log = f"{atk_c['emoji']} {atk_p['character_id']} attacks {def_c['emoji']} {def_p['character_id']}!\n💥 Damage: {damage}"
        
        if is_defending:
            log += "\n🛡️ Damage was reduced by defense!"

        new_hp = max(0, def_p['current_hp'] - damage)
        db.update_battle_state(self.game_id, target_id, hp=new_hp, is_defending=False, is_dodging=False)
        self.players[target_id]['current_hp'] = new_hp
        self.players[target_id]['is_defending'] = 0
        self.players[target_id]['is_dodging'] = 0

        log += f"\n\n{def_c['emoji']} {def_p['character_id']}\n❤️ {new_hp}/{def_c['hp']} HP"

        if new_hp == 0:
            db.update_battle_state(self.game_id, target_id, is_alive=False)
            self.players[target_id]['is_alive'] = 0
            db.update_battle_state(self.game_id, attacker_id, kills=atk_p['kills'] + 1)
            self.players[attacker_id]['kills'] += 1
            log += f"\n\n💀 {def_p['character_id']} HAS BEEN DEFEATED!"
            
            self.build_turn_queue()
            if self.current_turn_idx >= len(self.turn_queue) and self.turn_queue:
                self.current_turn_idx = 0
                db.update_turn_index(self.game_id, 0)

        return self.check_win(), log

    def process_dodge(self, user_id):
        p = self.players.get(user_id)
        if not p: return None
        c = CHARACTERS.get(p['character_id'])
        chance = calc_dodge_chance(c['speed'])
        success = random.random() < chance
        db.update_battle_state(self.game_id, user_id, is_dodging=success)
        self.players[user_id]['is_dodging'] = 1 if success else 0
        return success

    def process_defend(self, user_id):
        db.update_battle_state(self.game_id, user_id, is_defending=True)
        self.players[user_id]['is_defending'] = 1

    def process_special(self, attacker_id, target_id=None):
        atk_p = self.players.get(attacker_id)
        if not atk_p or atk_p['special_cooldown'] > 0: return None, "On cooldown"
        
        atk_c = CHARACTERS.get(atk_p['character_id'])
        if not atk_c: return None, "No char"

        log = f"🔥 {atk_p['character_id']} used {atk_c['special']}!"

        if atk_c['sp_type'] == 'heal':
            heal = atk_c.get('heal_amt', 30)
            new_hp = min(atk_c['hp'], atk_p['current_hp'] + heal)
            db.update_battle_state(self.game_id, attacker_id, hp=new_hp, special_cooldown=atk_c['cd'])
            self.players[attacker_id]['current_hp'] = new_hp
            self.players[attacker_id]['special_cooldown'] = atk_c['cd']
            log += f"\n❤️ Healed for {heal} HP!\n❤️ {new_hp}/{atk_c['hp']} HP"
            log += f"\n⏳ Special cooldown: {atk_c['cd']} turns"
            return self.check_win(), log

        if not target_id: return None, "No target"
        def_p = self.players.get(target_id)
        def_c = CHARACTERS.get(def_p['character_id']) if def_p else None
        if not def_p or not def_c: return None, "Invalid target"

        damage = calc_damage(atk_c['attack'], def_c['defense'], mult=atk_c['sp_mult'])
        new_hp = max(0, def_p['current_hp'] - damage)
        
        db.update_battle_state(self.game_id, target_id, hp=new_hp, is_defending=False, is_dodging=False)
        db.update_battle_state(self.game_id, attacker_id, special_cooldown=atk_c['cd'])
        
        self.players[target_id]['current_hp'] = new_hp
        self.players[target_id]['is_defending'] = 0
        self.players[target_id]['is_dodging'] = 0
        self.players[attacker_id]['special_cooldown'] = atk_c['cd']

        log += f"\n💥 {damage} damage dealt!"
        log += f"\n\n{def_c['emoji']} {def_p['character_id']}\n❤️ {new_hp}/{def_c['hp']} HP"
        log += f"\n⏳ Special cooldown: {atk_c['cd']} turns"

        if new_hp == 0:
            db.update_battle_state(self.game_id, target_id, is_alive=False)
            db.update_battle_state(self.game_id, attacker_id, kills=atk_p['kills'] + 1)
            self.players[target_id]['is_alive'] = 0
            self.players[attacker_id]['kills'] += 1
            log += f"\n\n💀 {def_p['character_id']} HAS BEEN DEFEATED!"
            self.build_turn_queue()
            if self.current_turn_idx >= len(self.turn_queue) and self.turn_queue:
                self.current_turn_idx = 0
                db.update_turn_index(self.game_id, 0)

        return self.check_win(), log

    def check_win(self):
        marvel_alive = any(1 == self.players[uid]['is_alive'] and CHARACTERS.get(self.players[uid]['character_id'], {}).get('team') == 'Marvel' for uid in self.players)
        dc_alive = any(1 == self.players[uid]['is_alive'] and CHARACTERS.get(self.players[uid]['character_id'], {}).get('team') == 'DC' for uid in self.players)
        
        if not marvel_alive: return "DC"
        if not dc_alive: return "Marvel"
        return None

    def reduce_cooldowns(self):
        for uid, p in self.players.items():
            if p['is_alive'] and p['special_cooldown'] > 0 and uid != self.get_current_turn():
                db.update_battle_state(self.game_id, uid, special_cooldown=p['special_cooldown'] - 1)
                self.players[uid]['special_cooldown'] -= 1

import random
