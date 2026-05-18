import asyncio
import random
import logging
import sqlite3
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

# --- КОНФІГУРАЦІЯ (ЗАПОВНІТЬ ТОКЕН) ---
API_TOKEN = '8427031492:AAFFuyxxzMrIP5ACuToEYJ5Ep_48dDFC9nU'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- РОБОТА З БАЗОЮ ДАНИХ (SQLite) ---
DB_FILE = "rpg_game.db"


def init_db():
    """Створює таблиці, якщо вони не існують"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS players
                   (
                       user_id
                       INTEGER
                       PRIMARY
                       KEY,
                       name
                       TEXT,
                       hp
                       INTEGER,
                       max_hp
                       INTEGER,
                       level
                       INTEGER,
                       exp
                       INTEGER,
                       exp_to_next
                       INTEGER,
                       potions
                       INTEGER,
                       gold
                       INTEGER,
                       kills
                       INTEGER,
                       skills_json
                       TEXT
                   )
                   ''')
    conn.commit()
    conn.close()


def get_player(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'user_id': row[0], 'name': row[1], 'hp': row[2], 'max_hp': row[3],
        'level': row[4], 'exp': row[5], 'exp_to_next': row[6],
        'potions': row[7], 'gold': row[8], 'kills': row[9],
        'skills': json.loads(row[10]), 'in_fight': False, 'enemy': None
    }


def save_player(p):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO players 
        (user_id, name, hp, max_hp, level, exp, exp_to_next, potions, gold, kills, skills_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        p['user_id'], p['name'], p['hp'], p['max_hp'], p['level'],
        p['exp'], p['exp_to_next'], p['potions'], p['gold'], p['kills'],
        json.dumps(p['skills'])
    ))
    conn.commit()
    conn.close()


# Тимчасове сховище для статусів бою (бо в БД недоцільно тримати параметри поточного ворога)
active_fights = {}


# --- ДИНАМІЧНИЙ ДИЗАЙН МОНСТРІВ ---
class GameEngine:
    @staticmethod
    def get_monster(player_level, is_boss=False):
        if is_boss:
            boss_data = [
                {'name': '👑 Дракон Пустоти', 'hp': 250, 'damage': 35, 'exp': 160, 'gold': 120},
                {'name': '👑 Повелитель Демонів', 'hp': 300, 'damage': 30, 'exp': 190, 'gold': 150}
            ]
            monster = random.choice(boss_data)
            mult = 1 + (player_level - 5) * 0.25
        else:
            monster_data = [
                {'name': '🎭 Проклятий Мімік', 'hp': 40, 'damage': 14, 'exp': 30, 'gold': 40},
                {'name': '🧟 Лісовий Гоблін', 'hp': 50, 'damage': 12, 'exp': 25, 'gold': 15},
                {'name': '🐗 Дикий Лютобор', 'hp': 75, 'damage': 20, 'exp': 45, 'gold': 25},
                {'name': '⚔️ Орк-Найманець', 'hp': 95, 'damage': 25, 'exp': 60, 'gold': 35},
                {'name': '💀 Лицар Смерті', 'hp': 130, 'damage': 22, 'exp': 80, 'gold': 55}
            ]
            monster = random.choice(monster_data)
            mult = 1 + (player_level - 1) * 0.18

        return {
            'name': monster['name'],
            'hp': int(monster['hp'] * mult),
            'max_hp': int(monster['hp'] * mult),
            'power': int(monster['damage'] * mult),
            'exp_reward': int(monster['exp'] * mult),
            'gold_reward': int(monster['gold'] * random.uniform(0.8, 1.2)),
            'is_boss': is_boss
        }


# --- ГЕНЕРАЦІЯ КНОПОК ---
def get_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⚔️ Вирушити у бій", callback_data="menu_fight"))
    builder.row(types.InlineKeyboardButton(text="⛺ Торговець (Золото)", callback_data="menu_shop"))
    builder.row(types.InlineKeyboardButton(text="💎 Донат-Магазин (Зірки)", callback_data="menu_donate"))
    builder.row(types.InlineKeyboardButton(text="👤 Профіль Героя", callback_data="menu_profile"))
    return builder.as_markup()


def get_fight_kb(p):
    builder = InlineKeyboardBuilder()
    for i, skill in enumerate(p['skills']):
        builder.row(types.InlineKeyboardButton(text=f"🔥 {skill['name']}", callback_data=f"hit_{i}"))
    builder.row(types.InlineKeyboardButton(text="🧪 Випити зілля", callback_data="hit_heal"))
    builder.row(types.InlineKeyboardButton(text="🏃 Накивати п'ятами", callback_data="hit_flee"))
    return builder.as_markup()


def get_shop_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🧪 Цілюще зілля — 25 💰", callback_data="buy_potion"))
    builder.row(types.InlineKeyboardButton(text="❤️ Гартування тіла (+15 HP) — 45 💰", callback_data="buy_hp"))
    builder.row(types.InlineKeyboardButton(text="↩️ Повернутись у табір", callback_data="menu_main"))
    return builder.as_markup()


def get_donate_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⭐ Набір Новачка (5 Зірок)", callback_data="don_pack"))
    builder.row(types.InlineKeyboardButton(text="⭐ Скриня Золота +500 (15 Зірок)", callback_data="don_gold"))
    builder.row(types.InlineKeyboardButton(text="↩️ Повернутись у табір", callback_data="menu_main"))
    return builder.as_markup()


def get_back_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="↩️ Назад у табір", callback_data="menu_main"))
    return builder.as_markup()


# --- ОБРОБНИКИ КОМАНД ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    p = get_player(user_id)

    if not p:
        p = {
            'user_id': user_id, 'name': message.from_user.first_name,
            'hp': 120, 'max_hp': 120, 'level': 1, 'exp': 0, 'exp_to_next': 100,
            'potions': 3, 'gold': 50, 'kills': 0,
            'skills': [
                {'name': 'Швидкий удар', 'min': 12, 'max': 17, 'chance': 0.9, 'crit': 0.1},
                {'name': 'Потужний удар', 'min': 28, 'max': 42, 'chance': 0.5, 'crit': 0.2}
            ]
        }
        save_player(p)
        welcome_text = f"✨ **Ласкаво просимо, {p['name']}!** Ваші дані успішно внесено до літопису бази даних!\n\n"
    else:
        welcome_text = f"✨ **З поверненням, {p['name']}!** Ваші збереження успішно завантажено з бази даних.\n\n"

    await message.answer(f"{welcome_text}⛺ Ви стоїте посеред безпечного табору. Готові до нових подвигів?",
                         reply_markup=get_main_kb())


@dp.callback_query(F.data == "menu_main")
async def go_to_main(callback: types.CallbackQuery):
    active_fights.pop(callback.from_user.id, None)
    await callback.message.edit_text("⛺ Ви перебуваєте в безпечній зоні. Оберіть наступний крок:",
                                     reply_markup=get_main_kb())


@dp.callback_query(F.data == "menu_profile")
async def show_profile(callback: types.CallbackQuery):
    p = get_player(callback.from_user.id)
    if not p: return await callback.answer("Напишіть /start")

    # Авто-левелап
    lvl_up = ""
    if p['exp'] >= p['exp_to_next']:
        p['level'] += 1;
        p['exp'] -= p['exp_to_next']
        p['exp_to_next'] = int(p['exp_to_next'] * 1.3)
        p['max_hp'] += 25;
        p['hp'] = p['max_hp'];
        p['potions'] += 1
        for s in p['skills']:
            s['min'] = int(s['min'] * 1.15);
            s['max'] = int(s['max'] * 1.15)
        save_player(p)
        lvl_up = "\n\n🆙 **НОВИЙ РІВЕНЬ!** Ваші характеристики та навички зросли!"

    text = (
        f"═════════ 👤 **ПРОФІЛЬ** ═════════\n"
        f"🤴 **Ім'я героя:** {p['name']}\n"
        f"🚀 **Рівень:** {p['level']} | 🌟 **Досвід:** {p['exp']}/{p['exp_to_next']} XP\n"
        f"❤️ **Здоров'я:** {p['hp']}/{p['max_hp']} HP\n"
        f"💰 **Золото в гаманці:** {p['gold']} 💰\n"
        f"🧪 **Запас зілль:** {p['potions']} шт.\n"
        f"💀 **Знищено потвор:** {p['kills']}"
        f"{lvl_up}\n"
        f"══════════════════════════"
    )
    await callback.message.edit_text(text, reply_markup=get_back_kb())


# --- МАГАЗИН ЗА ЗОЛОТО ---
@dp.callback_query(F.data == "menu_shop")
async def open_shop(callback: types.CallbackQuery):
    p = get_player(callback.from_user.id)
    await callback.message.edit_text(
        f"⛺ **Мандрівний Торговець**\n\"Вітаю! Продаю зілля та покращення за золото.\"\n\n💰 Твоє золото: {p['gold']}",
        reply_markup=get_shop_kb())


@dp.callback_query(F.data.startswith("buy_"))
async def process_buying(callback: types.CallbackQuery):
    p = get_player(callback.from_user.id)
    item = callback.data.split("_")[1]

    if item == "potion" and p['gold'] >= 25:
        p['gold'] -= 25;
        p['potions'] += 1
        await callback.answer("Придбано зілля! 🧪")
    elif item == "hp" and p['gold'] >= 45:
        p['gold'] -= 45;
        p['max_hp'] += 15;
        p['hp'] += 15
        await callback.answer("Максимальне здоров'я збільшено! ❤️")
    else:
        await callback.answer("❌ Тобі бракує золота!")
        return

    save_player(p)
    await callback.message.edit_text(
        f"⛺ **Мандрівний Торговець**\n\"Дякую за угоду! Щось ще?\"\n\n💰 Твоє золото: {p['gold']}",
        reply_markup=get_shop_kb())


# --- 💎 ДОНАТ-МАГАЗИН (TELEGRAM STARS) ---
@dp.callback_query(F.data == "menu_donate")
async def open_donate(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💎 **ДОНАТ-МАГАЗИН (Telegram Stars)**\n\n"
        "Підтримайте розробку гри та отримайте епічні бонуси миттєво!\n\n"
        "📦 **Набір Новачка** — 5 зірок (+5 зілль лікування, +100 золота)\n"
        "💰 **Скриня Золота** — 15 зірок (+500 золота в гаманець)",
        reply_markup=get_donate_kb()
    )


@dp.callback_query(F.data.startswith("don_"))
async def create_invoice(callback: types.CallbackQuery):
    pack = callback.data.split("_")[1]

    prices = []
    title = ""
    description = ""
    payload = ""

    if pack == "pack":
        title = "📦 Пакет Новачка"
        description = "Дає +5 Зілль лікування та +100 Золота"
        payload = "donate_pack_novice"
        prices.append(types.LabeledPrice(label="XTR", amount=5))  # 5 Telegram Stars
    elif pack == "gold":
        title = "💰 Скриня Золота"
        description = "Миттєво додає +500 золота на ваш баланс"
        payload = "donate_gold_chest"
        prices.append(types.LabeledPrice(label="XTR", amount=15))  # 15 Telegram Stars

    await callback.message.delete()  # Видаляємо старе меню перед інвойсом
    await callback.message.answer_invoice(
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # Для Telegram Stars поле повинно бути порожнім!
        currency="XTR",
        prices=prices
    )


# --- ПІДТВЕРДЖЕННЯ ОПЛАТИ (STARS) ---
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    # Завжди підтверджуємо, що готові прийняти оплату
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    user_id = message.from_user.id
    p = get_player(user_id)
    payload = message.successful_payment.invoice_payload

    if payload == "donate_pack_novice":
        p['potions'] += 5
        p['gold'] += 100
        text = "🎉 **Дякуємо!** Ви придбали 'Пакет Новачка'! (+5 зілль, +100 💰)"
    elif payload == "donate_gold_chest":
        p['gold'] += 500
        text = "🎉 **Дякуємо!** Ви придбали 'Скриню Золота'! (+500 💰)"
    else:
        text = "🎉 Оплата пройшла успішно!"

    save_player(p)
    await message.answer(text, reply_markup=get_main_kb())


# --- СИСТЕМА АВТОМАТИЧНОГО БОЮ ---
@dp.callback_query(F.data == "menu_fight")
async def start_fight(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)

    if p['hp'] <= 0:
        return await callback.message.edit_text("💀 Ви мертві. Введіть /start для відродження.")

    is_boss = p['kills'] > 0 and (p['kills'] + 1) % 5 == 0
    enemy = GameEngine.get_monster(p['level'], is_boss)

    # Зберігаємо ворога в оперативну пам'ять для поточного бою
    active_fights[user_id] = enemy

    boss_alert = "🚨🚨🚨 **НАПАД БОСА** 🚨🚨🚨\n" if is_boss else "⚔️ **ПОЧАТОК БОЮ** ⚔️\n"
    await callback.message.edit_text(
        f"{boss_alert}"
        f"👹 **Ворог:** {enemy['name']}\n"
        f"❤️ **HP ворога:** {enemy['hp']}/{enemy['max_hp']} | 💥 **Сила:** {enemy['power']}\n\n"
        f"🛡️ **Ви:** {p['hp']}/{p['max_hp']} HP | 🧪 **Зілля:** {p['potions']}",
        reply_markup=get_fight_kb(p)
    )


@dp.callback_query(F.data.startswith("hit_"))
async def fight_turn(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    p = get_player(user_id)
    enemy = active_fights.get(user_id)

    if not enemy:
        return await callback.answer("Бій закінчився або не знайдений.")

    action = callback.data.split("_")[1]
    log = []

    # 1. Хід гравця
    if action == "heal":
        if p['potions'] > 0:
            heal_val = 40 + (p['level'] * 8)
            p['hp'] = min(p['max_hp'], p['hp'] + heal_val)
            p['potions'] -= 1
            log.append(f"🧪 Ви випили зілля лікування (+{heal_val} HP).")
        else:
            return await callback.answer("Немає зілля! ❌")
    elif action == "flee":
        if enemy['is_boss']:
            return await callback.answer("Втеча від БОСА неможлива!")
        if random.random() < 0.5:
            active_fights.pop(user_id, None)
            return await callback.message.edit_text("🏃💨 Ви успішно втекли від монстра назад у табір!",
                                                    reply_markup=get_back_kb())
        else:
            log.append("❌ Спроба втечі провалилась! Ворог затис вас у кут.")
    else:
        skill = p['skills'][int(action)]
        if random.random() <= skill['chance']:
            dmg = random.randint(skill['min'], skill['max'])
            if random.random() <= skill['crit']:
                dmg = int(dmg * 1.8)
                log.append("⚡ **КРИТИЧНИЙ УДАР!** ⚡")
            enemy['hp'] -= dmg
            log.append(f"🎯 Скілом '{skill['name']}' ви нанесли {dmg} шкоди.")
        else:
            log.append(f"💨 Ви промахнулися атакою '{skill['name']}'.")

    # Перевірка смерті ворога
    if enemy['hp'] <= 0:
        active_fights.pop(user_id, None)
        p['kills'] += 1
        p['gold'] += enemy['gold_reward']
        p['exp'] += enemy['exp_reward']

        bonus = ""
        if random.random() < 0.35:
            p['potions'] += 1
            bonus = "\n🧪 Знайдено трофейне зілля лікування!"

        save_player(p)
        await callback.message.edit_text(
            f"🏆 **ПЕРЕМОГА!**\n\n"
            f"Ви здолали потвору {enemy['name']}.\n"
            f"💰 Золото: +{enemy['gold_reward']}\n"
            f"🌟 Досвід: +{enemy['exp_reward']}{bonus}",
            reply_markup=get_back_kb()
        )
        return

    # 2. Хід монстра
    m_dmg = random.randint(int(enemy['power'] * 0.85), int(enemy['power'] * 1.15))
    if random.random() < 0.1:
        m_dmg = int(m_dmg * 1.5)
        log.append("⚠️ **Лютий крит від монстра!**")
    p['hp'] -= m_dmg
    log.append(f"🔥 {enemy['name']} вдарив вас на {m_dmg} одиниць шкоди.")

    # Перевірка смерті гравця
    if p['hp'] <= 0:
        p['hp'] = 0
        active_fights.pop(user_id, None)
        save_player(p)
        await callback.message.edit_text(
            f"💀 **ВАС УБИТО...** 💀\n\n"
            f"Монстр {enemy['name']} виявився занадто сильним.\n"
            f"Ваш фінальний рівень: {p['level']}\n"
            f"Напишіть /start, щоб почати життя спочатку.",
            reply_markup=None
        )
        return

    # Якщо всі живі — оновлюємо інтерфейс бою
    save_player(p)
    await callback.message.edit_text(
        f"{'\n'.join(log)}\n\n"
        f"👹 **{enemy['name']}**: {enemy['hp']}/{enemy['max_hp']} HP\n"
        f"⚔️ **Ви**: {p['hp']}/{p['max_hp']} HP | 🧪 {p['potions']} шт.",
        reply_markup=get_fight_kb(p)
    )


# --- ЗАПУСК ---
async def main():
    init_db()  # Ініціалізуємо БД при старті скрипта
    print("Бот з підтримкою СУБД SQLite та Telegram Stars успішно запущений!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
