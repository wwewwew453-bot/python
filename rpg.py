import asyncio
import random
import logging
import sqlite3
import json
from typing import Dict, List, Optional, Tuple, Any
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАЛАШТУВАННЯ СИСТЕМИ ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_TOKEN = '8427031492:AAFFuyxxzMrIP5ACuToEYJ5Ep_48dDFC9nU'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "rpg_epic_universe.db"

# --- СТАНЫ ГРИ (FSM) ---
class GameStates(StatesGroup):
    MAIN_MENU = State()
    CHOOSE_CLASS = State()
    DUNG_CHOOSE = State()
    FIGHT = State()
    SHOP = State()
    BLACKSMITH = State()
    INVENTORY = State()
    QUEST_BOARD = State()
    STARS_SHOP = State()

# ==============================================================================
# 1. БАЗА ДАНИХ (ПОВНОЦІННА АРХІТЕКТУРА)
# ==============================================================================
class Database:
    @staticmethod
    def init():
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Таблиця користувачів
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    hero_class TEXT,
                    level INTEGER DEFAULT 1,
                    exp INTEGER DEFAULT 0,
                    gold INTEGER DEFAULT 200,
                    stars INTEGER DEFAULT 0,
                    hp INTEGER,
                    max_hp INTEGER,
                    mp INTEGER,
                    max_mp INTEGER,
                    base_atk INTEGER,
                    base_def INTEGER,
                    kills INTEGER DEFAULT 0,
                    boss_kills INTEGER DEFAULT 0,
                    active_quest_id INTEGER DEFAULT 0,
                    quest_progress INTEGER DEFAULT 0,
                    location_id INTEGER DEFAULT 1
                )
            ''')
            # Таблиця предметів (Інвентар)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    item_id TEXT,
                    item_name TEXT,
                    item_type TEXT, -- 'weapon', 'armor', 'material', 'potion'
                    stat_bonus INTEGER DEFAULT 0,
                    rarity TEXT DEFAULT 'common', -- 'common', 'rare', 'epic', 'legendary'
                    is_equipped INTEGER DEFAULT 0,
                    quantity INTEGER DEFAULT 1,
                    FOREIGN KEY(user_id) REFERENCES players(user_id)
                )
            ''')
            conn.commit()

    @staticmethod
    def get_player(user_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            p = dict(row)
            
            cursor.execute("SELECT * FROM inventory WHERE user_id = ?", (user_id,))
            p['inventory'] = [dict(r) for r in cursor.fetchall()]
            return p

    @staticmethod
    def register_player(user_id: int, name: str, hero_class: str) -> Dict[str, Any]:
        # Статичні пресети початкових класів
        presets = {
            "Воїн":    {"hp": 200, "mp": 40,  "atk": 22, "def": 15},
            "Маг":     {"hp": 110, "mp": 150, "atk": 35, "def": 6},
            "Слідопит": {"hp": 140, "mp": 70,  "atk": 28, "def": 10}
        }
        data = presets.get(hero_class, presets["Воїн"])
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO players 
                (user_id, name, hero_class, level, exp, gold, stars, hp, max_hp, mp, max_mp, base_atk, base_def, active_quest_id, quest_progress, location_id)
                VALUES (?, ?, ?, 1, 0, 200, 0, ?, ?, ?, ?, ?, ?, 0, 0, 1)
            ''', (user_id, name, hero_class, data["hp"], data["hp"], data["mp"], data["mp"], data["atk"], data["def"]))
            
            # Початковий лут
            cursor.execute('''
                INSERT INTO inventory (user_id, item_id, item_name, item_type, stat_bonus, rarity, is_equipped, quantity)
                VALUES (?, 'starter_weapon', 'Новачок-Клинок', 'weapon', 5, 'common', 1, 1)
            ''', (user_id,))
            cursor.execute('''
                INSERT INTO inventory (user_id, item_id, item_name, item_type, stat_bonus, rarity, is_equipped, quantity)
                VALUES (?, 'starter_armor', 'Тканинна накидка', 'armor', 3, 'common', 1, 1)
            ''', (user_id,))
            cursor.execute('''
                INSERT INTO inventory (user_id, item_id, item_name, item_type, stat_bonus, rarity, is_equipped, quantity)
                VALUES (?, 'potion_hp_small', 'Мале зілля здоров''я', 'potion', 60, 'common', 0, 3)
            ''', (user_id,))
            conn.commit()
        return Database.get_player(user_id)

    @staticmethod
    def save_player(p: Dict[str, Any]):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE players SET 
                level=?, exp=?, gold=?, stars=?, hp=?, max_hp=?, mp=?, max_mp=?, 
                base_atk=?, base_def=?, kills=?, boss_kills=?, active_quest_id=?, quest_progress=?, location_id=?
                WHERE user_id=?
            ''', (p['level'], p['exp'], p['gold'], p['stars'], p['hp'], p['max_hp'], p['mp'], p['max_mp'],
                  p['base_atk'], p['base_def'], p['kills'], p['boss_kills'], p['active_quest_id'], p['quest_progress'], p['location_id'], p['user_id']))
            conn.commit()

    @staticmethod
    def add_item(user_id: int, item_id: str, name: str, itype: str, bonus: int, rarity: str = 'common', qty: int = 1):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            if itype in ['potion', 'material']:
                cursor.execute("SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id))
                exist = cursor.fetchone()
                if exist:
                    cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE id = ?", (qty, exist[0]))
                    conn.commit()
                    return
            cursor.execute('''
                INSERT INTO inventory (user_id, item_id, item_name, item_type, stat_bonus, rarity, is_equipped, quantity)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            ''', (user_id, item_id, name, itype, bonus, rarity, qty))
            conn.commit()

    @staticmethod
    def remove_item_by_id(inv_db_id: int):
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT quantity, id FROM inventory WHERE id = ?", (inv_db_id,))
            res = cursor.fetchone()
            if res:
                if res[0] > 1:
                    cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (inv_db_id,))
                else:
                    cursor.execute("DELETE FROM inventory WHERE id = ?", (inv_db_id,))
            conn.commit()

# ==============================================================================
# 2. ДАТА-СТРУКТУРИ ТА СИСТЕМНІ ПРЕСЕТИ (ЛОКАЦІЇ, МОНСТРИ, СКІЛИ, КВЕСТИ)
# ==============================================================================
class Skill:
    def __init__(self, name: str, dmg_mod: float, mp_cost: int, effect: Optional[str] = None):
        self.name = name
        self.dmg_mod = dmg_mod
        self.mp_cost = mp_cost
        self.effect = effect

class Location:
    def __init__(self, loc_id: int, name: str, min_lvl: int, desc: str):
        self.id = loc_id
        self.name = name
        self.min_lvl = min_lvl
        self.desc = desc

class MonsterTemplate:
    def __init__(self, name: str, hp: int, atk: int, gold: int, exp: int, is_boss: bool = False):
        self.name = name
        self.hp = hp
        self.atk = atk
        self.gold = gold
        self.exp = exp
        self.is_boss = is_boss

class Quest:
    def __init__(self, qid: int, title: str, desc: str, req_kills: int, gold_rew: int, exp_rew: int, item_reward_id: Optional[str] = None):
        self.id = qid
        self.title = title
        self.desc = desc
        self.req_kills = req_kills
        self.gold_reward = gold_rew
        self.exp_reward = exp_rew
        self.item_reward_id = item_reward_id

# --- СИСТЕМНІ СЛОВНИКИ-БАЗИ ДАНИХ ДЛЯ РУШІЯ ---
GAME_LOCATIONS = {
    1: Location(1, "🌲 Зелена Дівоча Пуща", 1, "Спокійне місце для новачків, але у кущах шарудять гобліни."),
    2: Location(2, "💀 Катакомби Забутих Королів", 3, "Темні сирі лабіринти, де повстають скелети та мерці."),
    3: Location(3, "⛰️ Розколоті Піки Грому", 6, "Високогір'я, засіяне гніздами гарпій та кам'яними големами."),
    4: Location(4, "🌋 Пекельне Жерло Абаддону", 10, "Ріки магми. Тут мешкають демони вищого рангу та дракони.")
}

SKILLS_DATABASE = {
    "Воїн": [
        Skill("⚔️ Нищівний Удар", 1.4, 6),
        Skill("🛡️ Стіна Захисту", 0.3, 10, "buff_def"),
        Skill("🩸 Кривавий Смерч", 2.0, 22, "bleed")
    ],
    "Маг": [
        Skill("🔥 Іскри Вогню", 1.7, 12),
        Skill("⚡ Грозовий Розряд", 2.4, 25),
        Skill("❄️ Абсолютний Нуль", 3.2, 45, "freeze")
    ],
    "Слідопит": [
        Skill("🎯 Постріл у Серце", 1.5, 8),
        Skill("🏹 Тіньовий Віяло", 1.9, 15),
        Skill("🐍 Отруйна Стріла", 1.3, 14, "poison")
    ]
}

MONSTERS_POOL = {
    1: [ # Монстри для Локації 1
        MonsterTemplate("👺 Гоблін-Крадій", 45, 9, 20, 25),
        MonsterTemplate("🐀 Чумний Пацюк", 35, 7, 12, 18),
        MonsterTemplate("👑 Ватажок Гоблінів", 180, 24, 110, 150, True) # БОС
    ],
    2: [ # Монстри для Локації 2
        MonsterTemplate("💀 Повсталий Скелет", 85, 17, 35, 45),
        MonsterTemplate("🧟 Гнилий Зомбі", 110, 14, 42, 55),
        MonsterTemplate("👑 Проклятий Лицар", 390, 38, 260, 380, True) # БОС
    ],
    3: [ # Монстри для Локації 3
        MonsterTemplate("🦅 Гірська Гарпія", 160, 28, 65, 90),
        MonsterTemplate("💎 Кам'яний Голем", 230, 22, 80, 110),
        MonsterTemplate("👑 Громовержець Торін", 750, 58, 550, 800, True) # БОС
    ],
    4: [ # Монстри для Локації 4
        MonsterTemplate("🔥 Демон Сектора", 320, 48, 120, 200),
        MonsterTemplate("🐕 Пекельний Гончак", 260, 54, 110, 180),
        MonsterTemplate("👑 Дракон Вічності Асгарда", 1800, 95, 2000, 3000, True) # БОС
    ]
}

QUESTS_DATABASE = {
    1: Quest(1, "🧹 Безпека Пущі", "Знищіть 4 монстрів у Зеленій Пущі", 4, 150, 200, "iron_ore"),
    2: Quest(2, "🦴 Очищення Склепів", "Подолайте 6 немертвих істот у катакомбах", 6, 400, 500, "steel_ingot"),
    3: Quest(3, "🌋 Герой Альянсу", "Знищіть 12 потвор у найнебезпечніших точках світу", 12, 1500, 2500, "dragon_scale")
}

SHOP_ITEMS = {
    "potion_small": {"name": "🧪 Мале зілля (50 HP)", "cost": 30, "type": "potion", "bonus": 50, "id": "potion_hp_small"},
    "potion_big": {"name": "🧪 Велике зілля (150 HP)", "cost": 80, "type": "potion", "bonus": 150, "id": "potion_hp_big"},
    "weapon_tier1": {"name": "⚔️ Сталевий Меч (+18 АТК)", "cost": 250, "type": "weapon", "bonus": 18, "id": "wpn_steel"},
    "armor_tier1": {"name": "🛡️ Кольчуга Вартового (+12 ДЕФ)", "cost": 220, "type": "armor", "bonus": 12, "id": "arm_chainmail"},
    "weapon_tier2": {"name": "🔱 Рунічне Спис (+42 АТК)", "cost": 750, "type": "weapon", "bonus": 42, "id": "wpn_runic"},
    "armor_tier2": {"name": "🛡️ Панцир Паладіна (+30 ДЕФ)", "cost": 700, "type": "armor", "bonus": 30, "id": "arm_paladin"}
}

# ==============================================================================
# 3. КОНСТРУКТОР ДИНАМІЧНИХ ІНЛАЙН КЛАВІАТУР
# ==============================================================================
class UI:
    @staticmethod
    def main_menu(p: Dict[str, Any]) -> types.InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        loc = GAME_LOCATIONS.get(p['location_id'], GAME_LOCATIONS[1])
        kb.row(types.InlineKeyboardButton(text=f"⚔️ Полювання [{loc.name}]", callback_data="nav_hunt"))
        kb.row(types.InlineKeyboardButton(text="🗺️ Змінити локацію світу", callback_data="nav_world"))
        kb.row(types.InlineKeyboardButton(text="🎒 Мій Інвентар", callback_data="nav_inv"),
               types.InlineKeyboardButton(text="📜 Завдання", callback_data="nav_quests"))
        kb.row(types.InlineKeyboardButton(text="⛺ Торговець", callback_data="nav_shop"),
               types.InlineKeyboardButton(text="⚒️ Коваль", callback_data="nav_forge"))
        kb.row(types.InlineKeyboardButton(text="💎 Донат-Магазин Stars", callback_data="nav_stars"))
        kb.row(types.InlineKeyboardButton(text="👤 Статистика Героя", callback_data="nav_stats"))
        return kb.as_markup()

    @staticmethod
    def classes() -> types.InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="🛡️ Воїн (Збалансований Танк)", callback_data="pick_Воїн"))
        kb.row(types.InlineKeyboardButton(text="🔮 Маг (Руйнівна Магія)", callback_data="pick_Маг"))
        kb.row(types.InlineKeyboardButton(text="🏹 Слідопит (Швидкість та Крити)", callback_data="pick_Слідопит"))
        return kb.as_markup()

    @staticmethod
    def world_map() -> types.InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for lid, loc in GAME_LOCATIONS.items():
            kb.row(types.InlineKeyboardButton(text=f"{loc.name} (Lvl {loc.min_lvl}+)", callback_data=f"teleport_{lid}"))
        kb.row(types.InlineKeyboardButton(text="↩️ Повернутись", callback_data="to_menu"))
        return kb.as_markup()

    @staticmethod
    def fight(skills: List[Skill], potions_qty: int) -> types.InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for i, sk in enumerate(skills):
            kb.row(types.InlineKeyboardButton(text=f"🔥 {sk.name} [{sk.mp_cost} MP]", callback_data=f"hit_skill_{i}"))
        kb.row(types.InlineKeyboardButton(text=f"🧪 Зілля здоров'я ({potions_qty} шт.)", callback_data="hit_potion"))
        kb.row(types.InlineKeyboardButton(text="🏃 Накивати п'ятами (Втеча)", callback_data="hit_flee"))
        return kb.as_markup()

    @staticmethod
    def shop() -> types.InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        for item_key, data in SHOP_ITEMS.items():
            kb.row(types.InlineKeyboardButton(text=f"{data['name']} — {data['cost']} 💰", callback_data=f"buy_item_{item_key}"))
        kb.row(types.InlineKeyboardButton(text="↩️ Вийти з лавки", callback_data="to_menu"))
        return kb.as_markup()

    @staticmethod
    def back() -> types.InlineKeyboardMarkup:
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="↩️ Повернутись у табір", callback_data="to_menu"))
        return kb.as_markup()

# ==============================================================================
# 4. ГОЛОВНА СИСТЕМНА ЛОГІКА ТА ОБРОБКА КОМАНД І СТАНИВ (FSM)
# ==============================================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    p = Database.get_player(message.from_user.id)
    if not p:
        await message.answer("✨ **Ласкаво просимо у світ RPG Epic Universe!**\nВаше ім'я не знайдено у древніх рукописах. Оберіть ваш шлях (клас героя):", 
                             reply_markup=UI.classes())
        await state.set_state(GameStates.CHOOSE_CLASS)
    else:
        await state.set_state(GameStates.MAIN_MENU)
        await message.answer(f"⛺ **Вітаємо в таборі, {p['name']}!** Кострище палає, зброя готова. Оберіть дію:", 
                             reply_markup=UI.main_menu(p))

@dp.callback_query(F.data.startswith("pick_"), GameStates.CHOOSE_CLASS)
async def class_picked(callback: types.CallbackQuery, state: FSMContext):
    hero_class = callback.data.split("_")[1]
    p = Database.register_player(callback.from_user.id, callback.from_user.first_name, hero_class)
    await state.set_state(GameStates.MAIN_MENU)
    await callback.message.edit_text(f"⚔️ Ви обрали шлях **{hero_class}**! Стартовий лут додано в рюкзак. Починайте подорож!", 
                                     reply_markup=UI.main_menu(p))

@dp.callback_query(F.data == "to_menu")
async def return_to_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    p = Database.get_player(callback.from_user.id)
    await state.set_state(GameStates.MAIN_MENU)
    await callback.message.edit_text("⛺ Ви повернулись у безпечну зону вашого табору.", reply_markup=UI.main_menu(p))

# --- СТАТИСТИКА ГЕРОЯ ---
@dp.callback_query(F.data == "nav_stats", GameStates.MAIN_MENU)
async def show_stats(callback: types.CallbackQuery):
    p = Database.get_player(callback.from_user.id)
    atk_bonus = sum(i['stat_bonus'] for i in p['inventory'] if i['item_type'] == 'weapon' and i['is_equipped'])
    def_bonus = sum(i['stat_bonus'] for i in p['inventory'] if i['item_type'] == 'armor' and i['is_equipped'])
    next_exp = p['level'] * 150

    text = (
        f"═════════ 👤 **ЛИСТ ПЕРСОНАЖА** ═════════\n"
        f"🤴 **Ім'я:** {p['name']} | Клас: *{p['hero_class']}*\n"
        f"🚀 **Рівень:** {p['level']} | Досвід: *{p['exp']}/{next_exp} XP*\n"
        f"❤️ **Здоров'я:** {p['hp']}/{p['max_hp']} HP\n"
        f"🔮 **Мана:** {p['mp']}/{p['max_mp']} MP\n"
        f"⚔️ **Загальна Атака:** {p['base_atk'] + atk_bonus} ({p['base_atk']} + {atk_bonus} Лвл/Лут)\n"
        f"🛡️ **Загальний Захист:** {p['base_def'] + def_bonus} ({p['base_def']} + {def_bonus} Лвл/Лут)\n"
        f"💰 **Золото:** {p['gold']} 💰 | 💎 **Зірки:** {p['stars']} 💎\n"
        f"💀 **Усунуто потвор:** {p['kills']} | Босів: {p['boss_kills']}\n"
        f"═════════════════════════════════════"
    )
    await callback.message.edit_text(text, reply_markup=UI.back())

# --- ТЕЛЕПОРТАЦІЯ МІЖ ЛОКАЦІЯМИ ---
@dp.callback_query(F.data == "nav_world", GameStates.MAIN_MENU)
async def open_world_map(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.DUNG_CHOOSE)
    await callback.message.edit_text("🗺️ **ГЛОБАЛЬНА КАРТА СВІТУ**\nОберіть регіон для переміщення:", reply_markup=UI.world_map())

@dp.callback_query(F.data.startswith("teleport_"), GameStates.DUNG_CHOOSE)
async def process_teleport(callback: types.CallbackQuery, state: FSMContext):
    loc_id = int(callback.data.split("_")[1])
    p = Database.get_player(callback.from_user.id)
    target_loc = GAME_LOCATIONS[loc_id]

    if p['level'] < target_loc.min_lvl:
        return await callback.answer(f"❌ Рівень занизький! Цей регіон відкривається з {target_loc.min_lvl} рівня.", show_alert=True)

    p['location_id'] = loc_id
    Database.save_player(p)
    await state.set_state(GameStates.MAIN_MENU)
    await callback.message.edit_text(f"✨ Ви успішно перемістились у: **{target_loc.name}**\n_{target_loc.desc}_", reply_markup=UI.main_menu(p))

# --- ЛАВКА ТОРГОВЦЯ ---
@dp.callback_query(F.data == "nav_shop", GameStates.MAIN_MENU)
async def open_shop_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.SHOP)
    p = Database.get_player(callback.from_user.id)
    await callback.message.edit_text(f"⛺ **Ринкова площа табору**\n\"Купуй спорядження та зілля, не шкодуй золота!\"\n\nГаманець: {p['gold']} 💰", reply_markup=UI.shop())

@dp.callback_query(F.data.startswith("buy_item_"), GameStates.SHOP)
async def process_shop_purchase(callback: types.CallbackQuery):
    item_key = callback.data.split("_")[2]
    item_data = SHOP_ITEMS.get(item_key)
    p = Database.get_player(callback.from_user.id)

    if p['gold'] < item_data['cost']:
        return await callback.answer("❌ У вас недостатньо золота!", show_alert=True)

    p['gold'] -= item_data['cost']
    Database.save_player(p)
    Database.add_item(p['user_id'], item_data['id'], item_data['name'].split(" (")[0], item_data['type'], item_data['bonus'], 'common', 1)
    await callback.answer(f"🎉 Успішно куплено: {item_data['name']}")

# --- РЮКЗАК ТА КЕРУВАННЯ ЕКІПІРОВКОЮ ---
@dp.callback_query(F.data == "nav_inv", GameStates.MAIN_MENU)
async def open_inventory(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.INVENTORY)
    p = Database.get_player(callback.from_user.id)
    text = "🎒 **РЮКЗАК ГЕРОЯ**\n\n"
    kb = InlineKeyboardBuilder()

    if not p['inventory']:
        text += "_Ваш рюкзак абсолютно порожній._"
    else:
        for item in p['inventory']:
            eq_status = " [🛡️ ЕКІПІРОВАНО]" if item['is_equipped'] else ""
            qty_status = f" (x{item['quantity']})" if item['quantity'] > 1 else ""
            text += f"• **{item['item_name']}** | Тип: {item['item_type']} (+{item['stat_bonus']}){eq_status}{qty_status}\n"
            
            if not item['is_equipped'] and item['item_type'] in ['weapon', 'armor']:
                kb.row(types.InlineKeyboardButton(text=f"⚔️ Вдягти {item['item_name']}", callback_data=f"equip_item_{item['id']}"))

    kb.row(types.InlineKeyboardButton(text="↩️ Закрити рюкзак", callback_data="to_menu"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("equip_item_"), GameStates.INVENTORY)
async def equip_gear(callback: types.CallbackQuery):
    db_id = int(callback.data.split("_")[2])
    u_id = callback.from_user.id

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_type FROM inventory WHERE id = ?", (db_id,))
        itype = cursor.fetchone()[0]
        cursor.execute("UPDATE inventory SET is_equipped = 0 WHERE user_id = ? AND item_type = ?", (u_id, itype))
        cursor.execute("UPDATE inventory SET is_equipped = 1 WHERE id = ?", (db_id,))
        conn.commit()

    await callback.answer("🛡️ Ви змінили бойове екіпірування!")
    await open_inventory(callback, None)

# --- ДОШКА КВЕСТІВ ---
@dp.callback_query(F.data == "nav_quests", GameStates.MAIN_MENU)
async def show_quests_board(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.QUEST_BOARD)
    p = Database.get_player(callback.from_user.id)
    kb = InlineKeyboardBuilder()

    if p['active_quest_id'] != 0:
        q = QUESTS_DATABASE[p['active_quest_id']]
        text = f"📜 **АКТИВНЕ ЗАВДАННЯ:**\n\n📌 **{q.title}**\n📝 {q.desc}\n📊 Прогрес: {p['quest_progress']}/{q.req_kills} вбитих монстрів.\n\n"
        if p['quest_progress'] >= q.req_kills:
            kb.row(types.InlineKeyboardButton(text="🎁 Забрати винагороду", callback_data="quest_claim"))
        else:
            kb.row(types.InlineKeyboardButton(text="❌ Відмовитись від квесту", callback_data="quest_abandon"))
    else:
        text = "📜 **ДОШКА ОГОЛОШЕНЬ ТАБОРУ**\nОберіть доступний контракт:\n\n"
        for qid, q in QUESTS_DATABASE.items():
            text += f"🔹 **{q.title}**\n├ {q.desc}\n└ Нагорода: {q.gold_reward}💰 + {q.exp_reward}XP\n\n"
            kb.row(types.InlineKeyboardButton(text=f"Прийняти: {q.title}", callback_data=f"quest_accept_{qid}"))

    kb.row(types.InlineKeyboardButton(text="↩️ Повернутись", callback_data="to_menu"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("quest_accept_"), GameStates.QUEST_BOARD)
async def accept_quest(callback: types.CallbackQuery):
    qid = int(callback.data.split("_")[2])
    p = Database.get_player(callback.from_user.id)
    p['active_quest_id'] = qid
    p['quest_progress'] = 0
    Database.save_player(p)
    await callback.answer("📜 Контракт підписано! Рушайте на полювання.")
    await show_quests_board(callback, None)

@dp.callback_query(F.data == "quest_abandon", GameStates.QUEST_BOARD)
async def abandon_quest(callback: types.CallbackQuery):
    p = Database.get_player(callback.from_user.id)
    p['active_quest_id'] = 0
    p['quest_progress'] = 0
    Database.save_player(p)
    await callback.answer("❌ Ви скасували контракт.", show_alert=True)
    await show_quests_board(callback, None)

@dp.callback_query(F.data == "quest_claim", GameStates.QUEST_BOARD)
async def claim_quest_reward(callback: types.CallbackQuery):
    p = Database.get_player(callback.from_user.id)
    q = QUESTS_DATABASE[p['active_quest_id']]

    p['gold'] += q.gold_reward
    p['exp'] += q.exp_reward
    p['active_quest_id'] = 0
    p['quest_progress'] = 0
    
    if q.item_reward_id:
        Database.add_item(p['user_id'], q.item_reward_id, "Ковальський матеріал", "material", 0, 'rare', 1)

    Database.save_player(p)
    await callback.answer("🎁 Нагороду додано в гаманець та рюкзак!", show_alert=True)
    await show_quests_board(callback, None)

# --- ⚒️ КОВАЛЬ ТА КРАФТ/ПОКРАЩЕННЯ СПОРЯДЖЕННЯ ---
@dp.callback_query(F.data == "nav_forge", GameStates.MAIN_MENU)
async def open_forge(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.BLACKSMITH)
    p = Database.get_player(callback.from_user.id)
    
    # Шукаємо матеріали
    iron_count = sum(i['quantity'] for i in p['inventory'] if i['item_id'] == 'iron_ore')
    
    text = (
        f"⚒️ **КОВАЛЬНЯ ДВОРФА БРОККА**\n\n"
        f"\"Привіт, мандрівнику! Переплавлю твої ресурси на епічну зброю!\"\n"
        f"📦 Твої ресурси: Залізна руда: **{iron_count}** шт.\n\n"
        f"🔨 **Доступний Крафт:**\n"
        f"🗡️ *Дворфійський Сокира (+35 АТК)* — Рецепт: 2 Залізні Руди"
    )
    kb = InlineKeyboardBuilder()
    if iron_count >= 2:
        kb.row(types.InlineKeyboardButton(text="🔨 Скувати Дворфійську Сокиру", callback_data="craft_axe"))
    kb.row(types.InlineKeyboardButton(text="↩️ Залишити кузню", callback_data="to_menu"))
    await callback.message.edit_text(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "craft_axe", GameStates.BLACKSMITH)
async def craft_axe_process(callback: types.CallbackQuery):
    p = Database.get_player(callback.from_user.id)
    iron_item = next((i for i in p['inventory'] if i['item_id'] == 'iron_ore'), None)
    
    if not iron_item or iron_item['quantity'] < 2:
        return await callback.answer("❌ Недостатньо руди!")

    # Видаляємо 2 руди з бази
    for _ in range(2):
        Database.remove_item_by_id(iron_item['id'])

    Database.add_item(p['user_id'], 'dwarf_axe', 'Дворфійська Сокира', 'weapon', 35, 'rare', 1)
    await callback.answer("🔥 Коваль викував для вас Дворфійську Сокиру!", show_alert=True)
    await open_forge(callback, None)

# ==============================================================================
# 5. ГЛОБАЛЬНИЙ СИСТЕМНИЙ БОЙОВИЙ РУШІЙ (ПОВНІСТЮ НА FSM СТАТУСАХ)
# ==============================================================================
@dp.callback_query(F.data == "nav_hunt", GameStates.MAIN_MENU)
async def initiate_battle(callback: types.CallbackQuery, state: FSMContext):
    p = Database.get_player(callback.from_user.id)
    if p['hp'] <= p['max_hp'] * 0.1:
        return await callback.answer("❌ Ви надто слабкі для бою! Відпочиньте або випийте зілля.", show_alert=True)

    pool = MONSTERS_POOL.get(p['location_id'], MONSTERS_POOL[1])
    # Випадкова подія: шанс зустріти Боса або звичайного монстра
    monster_template = random.choice(pool)
    
    # Нарахування характеристик монстра залежно від рівня гравця
    modifier = 1.0 + (p['level'] - 1) * 0.25
    monster_data = {
        "name": monster_template.name,
        "hp": int(monster_template.hp * modifier),
        "max_hp": int(monster_template.hp * modifier),
        "atk": int(monster_template.atk * modifier),
        "gold": int(monster_template.gold * random.uniform(0.9, 1.2)),
        "exp": int(monster_template.exp * modifier),
        "is_boss": monster_template.is_boss
    }

    await state.update_data(monster=monster_data)
    await state.set_state(GameStates.FIGHT)

    skills = SKILLS_DATABASE.get(p['hero_class'], [])
    potions_qty = sum(i['quantity'] for i in p['inventory'] if i['item_id'] in ['potion_hp_small', 'potion_hp_big'])

    prefix = "🚨🔴 **УВАГА, НАПАД БОСА РЕГІОНУ!** 🔴🚨\n" if monster_data['is_boss'] else "⚔️ **БОЙОВА СУТИЧКА** ⚔️\n"
    await callback.message.edit_text(
        f"{prefix}Ваш супротивник: **{monster_data['name']}**\n"
        f"❤️ HP: {monster_data['hp']}/{monster_data['max_hp']} | 💥 Сила Атаки: {monster_data['atk']}\n\n"
        f"👤 Ви: {p['hp']}/{p['max_hp']} HP | 🔮 Мана: {p['mp']}/{p['max_mp']} MP",
        reply_markup=UI.fight(skills, potions_qty)
    )

@dp.callback_query(F.data.startswith("hit_"), GameStates.FIGHT)
async def process_combat_round(callback: types.CallbackQuery, state: FSMContext):
    fsm_data = await state.get_data()
    m = fsm_data.get("monster")
    if not m:
        await state.set_state(GameStates.MAIN_MENU)
        return await callback.message.edit_text("⚠️ Бій не знайдено або термін дії сесії минув.", reply_markup=UI.back())

    p = Database.get_player(callback.from_user.id)
    action = callback.data.split("_")[1]
    combat_log = []

    # Вираховуємо бонуси спорядження персонажа
    atk_bonus = sum(i['stat_bonus'] for i in p['inventory'] if i['item_type'] == 'weapon' and i['is_equipped'])
    def_bonus = sum(i['stat_bonus'] for i in p['inventory'] if i['item_type'] == 'armor' and i['is_equipped'])
    total_atk = p['base_atk'] + atk_bonus
    total_def = p['base_def'] + def_bonus

    # --- 1. Крок Героя ---
    if action == "potion":
        potion = next((i for i in p['inventory'] if i['item_id'] in ['potion_hp_small', 'potion_hp_big']), None)
        if not potion:
            return await callback.answer("❌ У вас немає жодного зілля лікування!")
        
        heal_val = potion['stat_bonus']
        p['hp'] = min(p['max_hp'], p['hp'] + heal_val)
        Database.remove_item_by_id(potion['id'])
        combat_log.append(f"🧪 Ви випили зілля та відновили {heal_val} HP.")
        
    elif action == "flee":
        if m['is_boss']:
            return await callback.answer("❌ Ви не можете втекти від Боса Локації!", show_alert=True)
        if random.random() < 0.4:
            await state.set_state(GameStates.MAIN_MENU)
            return await callback.message.edit_text("🏃 Ви кинули зброю і успішно втекли назад у табір!", reply_markup=UI.main_menu(p))
        else:
            combat_log.append("❌ Спроба втечі провалилася! Монстр заблокував вихід.")
            
    elif action == "skill":
        skill_idx = int(callback.data.split("_")[2])
        skill = SKILLS_DATABASE[p['hero_class']][skill_idx]

        if p['mp'] < skill.mp_cost:
            return await callback.answer("❌ Недостатньо одиниць мани!")

        p['mp'] -= skill.mp_cost
        damage = int(total_atk * skill.dmg_mod * random.uniform(0.9, 1.1))
        
        # Перевірка критичного удару
        if random.random() < 0.15:
            damage = int(damage * 1.7)
            combat_log.append("⚡ **КРИТИЧНИЙ УДАР ГЕРОЯ!**")

        m['hp'] -= damage
        combat_log.append(f"⚔️ Ви використали '{skill.name}' і завдали монстру {damage} шкоди.")

    # --- ПЕРЕВІРКА СМЕРТІ МОНСТРА ---
    if m['hp'] <= 0:
        p['kills'] += 1
        p['gold'] += m['gold']
        p['exp'] += m['exp']
        if m['is_boss']:
            p['boss_kills'] += 1

        # Оновлюємо прогрес квесту якщо він активний
        if p['active_quest_id'] != 0:
            p['quest_progress'] += 1

        # Система Level-Up
        next_exp = p['level'] * 150
        lvl_up_txt = ""
        if p['exp'] >= next_exp:
            p['level'] += 1
            p['exp'] -= next_exp
            p['max_hp'] += 25
            p['max_mp'] += 15
            p['hp'] = p['max_hp']
            p['mp'] = p['max_mp']
            p['base_atk'] += 5
            p['base_def'] += 3
            lvl_up_txt = f"\n\n🆙 **РІВЕНЬ ПІДНЯТО! Ви досягли {p['level']} рівня! Характеристики зросли.**"

        # Шансовий випадковий лут руди
        if random.random() < 0.35:
            Database.add_item(p['user_id'], 'iron_ore', 'Залізна руда', 'material', 0, 'common', 1)
            lvl_up_txt += "\n📦 Знайдено: *Залізна руда (Матеріал)*"

        Database.save_player(p)
        await state.set_state(GameStates.MAIN_MENU)
        return await callback.message.edit_text(
            f"🏆 **БЛИСКУЧА ПЕРЕМОГА!**\n\n"
            f"Ви здолали супротивника: {m['name']}\n"
            f"💰 Отримано золота: +{m['gold']} 💰\n"
            f"🌟 Отримано досвіду: +{m['exp']} XP{lvl_up_txt}",
            reply_markup=UI.back()
        )

    # --- 2. Крок Монстра ---
    m_raw_damage = int(m['atk'] * random.uniform(0.85, 1.15))
    final_m_damage = max(1, m_raw_damage - total_def)
    p['hp'] -= final_m_damage
    combat_log.append(f"💥 Монстр **{m['name']}** завдає вам {final_m_damage} шкоди.")

    # --- ПЕРЕВІРКА СМЕРТІ ГРАВЦЯ ---
    if p['hp'] <= 0:
        p['hp'] = int(p['max_hp'] * 0.3) # Відродження
        p['gold'] = max(0, p['gold'] - int(p['gold'] * 0.2)) # Забираємо 20% золота штрафу
        Database.save_player(p)
        await state.set_state(GameStates.MAIN_MENU)
        return await callback.message.edit_text(
            f"💀 **ВАС ПОВАЛЕНО НА ЗЕМЛЮ...**\n\n"
            f"Супротивник {m['name']} виявився занадто жорстоким. Компаньйони відтягнули вас до вогнища. "
            f"Ви втратили частину золота.",
            reply_markup=UI.back()
        )

    # Збереження проміжного стану бою
    Database.save_player(p)
    await state.update_data(monster=m)
    skills = SKILLS_DATABASE[p['hero_class']]
    potions_qty = sum(i['quantity'] for i in p['inventory'] if i['item_id'] in ['potion_hp_small', 'potion_hp_big'])

    await callback.message.edit_text(
        f"{'\n'.join(combat_log)}\n\n"
        f"👹 **{m['name']}**: {m['hp']}/{m['max_hp']} HP\n"
        f"👤 **Ви**: {p['hp']}/{p['max_hp']} HP | 🔮 {p['mp']}/{p['max_mp']} MP",
        reply_markup=UI.fight(skills, potions_qty)
    )

# ==============================================================================
# 6. ДОНАТ ТА СИСТЕМА ОПЛАТИ TELEGRAM STARS
# ==============================================================================
@dp.callback_query(F.data == "nav_stars", GameStates.MAIN_MENU)
async def open_stars_shop(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(GameStates.STARS_SHOP)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="⭐ Набір Скарбів (+1000 Золота) — 15 Stars", callback_data="stars_buy_gold"))
    kb.row(types.InlineKeyboardButton(text="⭐ Легендарний Меч Одіна (+100 АТК) — 50 Stars", callback_data="stars_buy_god_wpn"))
    kb.row(types.InlineKeyboardButton(text="↩️ Назад у табір", callback_data="to_menu"))
    await callback.message.edit_text("💎 **МАГАЗИН PREMIUM (Telegram Stars)**\nПридбайте унікальні товари за внутрішню преміум-валюту Telegram:", 
                                     reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("stars_buy_"), GameStates.STARS_SHOP)
async def create_stars_invoice(callback: types.CallbackQuery):
    pack = callback.data.split("_")[2]
    prices = []
    
    if pack == "gold":
        title, desc, payload, amount = "💰 Скриня Імперського Золота", "Дає +1000 золота", "star_pack_gold", 15
    else:
        title, desc, payload, amount = "⚔️ Меч Богів Одіна", "Епічна зброя (+100 АТК)", "star_pack_weapon", 50

    prices.append(types.LabeledPrice(label="XTR", amount=amount))
    await callback.message.delete()
    await callback.message.answer_invoice(
        title=title, description=desc, payload=payload,
        provider_token="", currency="XTR", prices=prices
    )

@dp.pre_checkout_query()
async def process_pre_checkout(query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def process_success_payment(message: types.Message, state: FSMContext):
    p = Database.get_player(message.from_user.id)
    payload = message.successful_payment.invoice_payload

    if payload == "star_pack_gold":
        p['gold'] += 1000
        msg = "🎉 Дякуємо! Вам нараховано +1000 золота!"
    elif payload == "star_pack_weapon":
        Database.add_item(p['user_id'], 'god_weapon_stars', 'Меч Богів Одіна', 'weapon', 100, 'legendary', 1)
        msg = "🎉 Дякуємо! Легендарний Меч Одіна додано у ваш інвентар!"
        
    Database.save_player(p)
    await state.set_state(GameStates.MAIN_MENU)
    await message.answer(msg, reply_markup=UI.main_menu(p))

# ==============================================================================
# 7. АСИНХРОННИЙ ПУСК ДВИГУНА
# ==============================================================================
async def main():
    Database.init()
    print("=====================================================")
    print("⚙️ RPG Epic Universe успішно підключено до серверів Telegram!")
    print("=====================================================")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
