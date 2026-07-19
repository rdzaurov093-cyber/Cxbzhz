import os
import asyncio
import sqlite3
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, SuccessfulPayment, LabeledPrice
from aiogram.filters import Command, Filter
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
OWNER_ID = 8816073474 # Главный админ (создатель)

# --- Эмодзи константы ---
E_REG = "<tg-emoji emoji-id='5116240346656801621'>👤</tg-emoji>"
E_SUCCESS = "<tg-emoji emoji-id='5886277285035644362'>✅</tg-emoji>"
E_BONUS = "<tg-emoji emoji-id='5886632311327299282'>🎁</tg-emoji>"
E_PREM = "<tg-emoji emoji-id='4945233221584422979'>💎</tg-emoji>"
E_REF = "<tg-emoji emoji-id='4916086774649848789'>🔗</tg-emoji>"
E_PETS = "<tg-emoji emoji-id='5422857138500301305'>🐾</tg-emoji>"
E_CAT = "<tg-emoji emoji-id='5465206035729906349'>🐱</tg-emoji>"
E_GENIE = "<tg-emoji emoji-id='5465614727637919433'>🧞‍♂️</tg-emoji>"
E_TOP = "<tg-emoji emoji-id='5886223731088431288'>🏆</tg-emoji>"
E_LOOT = "<tg-emoji emoji-id='5321201786659303279'>📦</tg-emoji>"
E_R_APP = "<tg-emoji emoji-id='5323641182054540514'>🥉</tg-emoji>"
E_R_PRO = "<tg-emoji emoji-id='5321224605820543819'>🥈</tg-emoji>"
E_R_MASTER = "<tg-emoji emoji-id='5321243632525665003'>🥇</tg-emoji>"
E_ID = "<tg-emoji emoji-id='6035244918572587491'>🆔</tg-emoji>"
E_LINE = "<tg-emoji emoji-id='5467796120052706892'>➖</tg-emoji>" * 10

# ИСПРАВЛЕНО: Убран нерабочий ID, чтобы бот не падал с ошибкой DOCUMENT_INVALID
E_GIFT = "💝" 

E_EXP = "<tg-emoji emoji-id='5222187272769654422'>✨</tg-emoji>"

# Эмодзи админов и брака
E_OWNER = "<tg-emoji emoji-id='5334767264770073355'>👑</tg-emoji>"
E_ADMIN = "<tg-emoji emoji-id='5335022931288301958'>👮‍♂️</tg-emoji>"
E_PROPOSE = "<tg-emoji emoji-id='5334987944484686335'>💍</tg-emoji>"
E_ACCEPT = "<tg-emoji emoji-id='5222187272769654422'>💖</tg-emoji>"
E_DECLINE = "<tg-emoji emoji-id='5336862719184225048'>💔</tg-emoji>"

# Эмодзи для карточек и экономики
E_CARD_ROLL = "<tg-emoji emoji-id='5222187272769654422'>✨</tg-emoji>"
E_CARD_NAME = "<tg-emoji emoji-id='5465262274031659421'>👤</tg-emoji>"
E_CARD_DESC = "<tg-emoji emoji-id='5336928311924788752'>📖</tg-emoji>"
E_MY_CARDS = "<tg-emoji emoji-id='5282843764451195532'>🎴</tg-emoji>"
E_CARD_RARITY = "<tg-emoji emoji-id='5199552030615558774'>✨</tg-emoji>"
E_TOKEN = "<tg-emoji emoji-id='5417924076503062111'>🪙</tg-emoji>" 
E_NEW_CARD = "<tg-emoji emoji-id='5382357040008021292'>🆕</tg-emoji>"
E_CARD_COUNT = "<tg-emoji emoji-id='5427168083074628963'>🃏</tg-emoji>"
E_TIME = "<tg-emoji emoji-id='5440621591387980068'>⏳</tg-emoji>"
E_INVOICE = "<tg-emoji emoji-id='5339166415087757307'>🧾</tg-emoji>"
E_VIP = "<tg-emoji emoji-id='5337096146361816187'>🌟</tg-emoji>"

R_EMOJIS = {
    "Обычная": "<tg-emoji emoji-id='5366476501510270703'>⚪️</tg-emoji>",
    "Необычная": "<tg-emoji emoji-id='5366200987948166922'>🟢</tg-emoji>",
    "Редкая": "<tg-emoji emoji-id='5366071842576544364'>🔵</tg-emoji>",
    "Эпическая": "<tg-emoji emoji-id='5364134709246835717'>🟣</tg-emoji>",
    "Легендарная": "<tg-emoji emoji-id='5366177133699805697'>🟡</tg-emoji>"
}

RARITY_CHANCES = {"Обычная": 60, "Необычная": 25, "Редкая": 10, "Эпическая": 4, "Легендарная": 1}
VIP_RARITY_CHANCES = {"Обычная": 55, "Необычная": 25, "Редкая": 12, "Эпическая": 5, "Легендарная": 3}
RARITY_REWARDS = {"Обычная": (5, 25), "Необычная": (30, 80), "Редкая": (100, 300), "Эпическая": (500, 1000), "Легендарная": (1500, 5000)}

def get_rarity_display(rarity_name):
    emoji = R_EMOJIS.get(rarity_name, "✨")
    return f"{emoji} <b>{rarity_name}</b>"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# --- Состояния FSM ---
class AddCard(StatesGroup):
    waiting_for_media, waiting_for_name, waiting_for_description, waiting_for_rarity = State(), State(), State(), State()

class ManageCard(StatesGroup):
    waiting_for_edit_value = State()

class AddRP(StatesGroup):
    waiting_for_trigger, waiting_for_action = State(), State()

class AddPet(StatesGroup):
    waiting_for_media, waiting_for_name, waiting_for_description, waiting_for_price = State(), State(), State(), State()

class AddGift(StatesGroup):
    waiting_for_name, waiting_for_action, waiting_for_price, waiting_for_exp = State(), State(), State(), State()

class AdminGive(StatesGroup):
    waiting_for_user_tokens, waiting_for_amount_tokens = State(), State()
    waiting_for_user_donat, waiting_for_amount_donat = State(), State()
    waiting_for_user_vip = State()

class ConvertDonat(StatesGroup):
    waiting_for_amount = State()

# --- База Данных ---
def init_db():
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, coins INTEGER DEFAULT 0, donat_coins INTEGER DEFAULT 0,
                  pet TEXT DEFAULT 'none', last_lootbox TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cards 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, media_id TEXT, rarity TEXT DEFAULT 'Обычная')''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (user_id INTEGER, card_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rp_commands (trigger TEXT PRIMARY KEY, action TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, name TEXT, prefix TEXT DEFAULT 'Админ')''')
    
    # Новые таблицы для магазина и подарков
    c.execute('''CREATE TABLE IF NOT EXISTS pets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, media_id TEXT, price INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS gifts (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, action TEXT, price INTEGER, exp INTEGER)''')
    
    updates = [
        "ALTER TABLE admins ADD COLUMN name TEXT",
        "ALTER TABLE admins ADD COLUMN prefix TEXT DEFAULT 'Админ'",
        "ALTER TABLE users ADD COLUMN partner_id INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN partner_name TEXT DEFAULT ''",
        "ALTER TABLE cards ADD COLUMN rarity TEXT DEFAULT 'Обычная'",
        "ALTER TABLE users ADD COLUMN last_roll TIMESTAMP",
        "ALTER TABLE users ADD COLUMN username TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN pay_today INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN pay_date TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN family_exp INTEGER DEFAULT 0"
    ]
    for q in updates:
        try: c.execute(q)
        except sqlite3.OperationalError: pass
        
    conn.commit()
    conn.close()

def get_user_db(tg_user):
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    username = tg_user.username.lower() if tg_user.username else ""
    
    c.execute("""SELECT user_id, coins, donat_coins, pet, last_lootbox, partner_id, partner_name, 
                 is_vip, pay_today, pay_date, family_exp FROM users WHERE user_id = ?""", (tg_user.id,))
    row = c.fetchone()
    
    if not row:
        c.execute("INSERT INTO users (user_id, coins, donat_coins, username) VALUES (?, 2000, 50, ?)", 
                  (tg_user.id, username))
        conn.commit()
        row = (tg_user.id, 2000, 50, 'none', None, 0, '', 0, 0, '', 0)
    else:
        c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, tg_user.id))
        conn.commit()
        
    conn.close()
    return row

def get_rank(coins):
    if coins >= 50000: return f"{E_R_MASTER} Мастер"
    if coins >= 15000: return f"{E_R_PRO} Профессионал"
    return f"{E_R_APP} Ученик"

def is_admin_check(user_id):
    if user_id == OWNER_ID: return True
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return bool(res)

class IsAdmin(Filter):
    async def __call__(self, event) -> bool:
        return is_admin_check(event.from_user.id)

# --- ИНСТРУМЕНТЫ АДМИНА ---

@dp.message(Command("emojico"), IsAdmin())
async def cmd_emojico(message: Message):
    # Проверяем реплай или само сообщение
    target_message = message.reply_to_message if message.reply_to_message else message
    
    if target_message.entities:
        for entity in target_message.entities:
            if entity.type == "custom_emoji":
                return await message.answer(f"ID премиум эмодзи: <code>{entity.custom_emoji_id}</code>")
                
    await message.answer("Премиум эмодзи не найден. Отправьте команду вместе с эмодзи (например: /emojico 🎁) или сделайте реплай на сообщение с ним.")

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin_check(message.from_user.id): return await message.answer("У вас нет доступа.")
    
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎴 Добавить Карту", callback_data="panel_add_card"),
         InlineKeyboardButton(text="🗑 Изменить/Удал. Карту", callback_data="panel_manage_cards")],
        [InlineKeyboardButton(text="🎭 Добавить РП", callback_data="panel_add_rp"),
         InlineKeyboardButton(text="🎁 Добавить Подарок", callback_data="panel_add_gift")],
        [InlineKeyboardButton(text="🐾 Добавить Питомца", callback_data="panel_add_pet")],
        [InlineKeyboardButton(text="🪙 Выдать Токены", callback_data="panel_give_tokens"),
         InlineKeyboardButton(text="💎 Выдать Донат", callback_data="panel_give_donat")],
        [InlineKeyboardButton(text="🌟 Выдать VIP", callback_data="panel_give_vip")]
    ])
    await message.answer(f"{E_OWNER} <b>Главная Админ-Панель</b>\nВыберите действие:\n\n<i>💡 Подсказка: Чтобы узнать ID эмодзи для подарков и РП, используйте команду /emojico</i>", reply_markup=kb)

# --- ВЫДАЧА РЕСУРСОВ ЧЕРЕЗ АДМИНКУ ---
@dp.callback_query(F.data.startswith("panel_give_"), IsAdmin())
async def panel_give_start(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2]
    await callback.message.edit_text("Отправьте @username пользователя (без @):")
    if action == "tokens": await state.set_state(AdminGive.waiting_for_user_tokens)
    elif action == "donat": await state.set_state(AdminGive.waiting_for_user_donat)
    elif action == "vip": await state.set_state(AdminGive.waiting_for_user_vip)

async def find_user_by_username(username: str):
    username = username.replace("@", "").lower().strip()
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username FROM users WHERE username = ?", (username,))
    res = c.fetchone()
    conn.close()
    return res

@dp.message(AdminGive.waiting_for_user_tokens, IsAdmin())
async def give_tokens_user(message: Message, state: FSMContext):
    user_data = await find_user_by_username(message.text)
    if not user_data: return await message.answer("Пользователь не найден.")
    await state.update_data(target_id=user_data[0])
    await message.answer("Введите сумму токенов:")
    await state.set_state(AdminGive.waiting_for_amount_tokens)

@dp.message(AdminGive.waiting_for_amount_tokens, IsAdmin())
async def give_tokens_amount(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Сумма должна быть числом!")
    amount = int(message.text)
    data = await state.get_data()
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, data['target_id']))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"{E_SUCCESS} Выдано <b>{amount}</b> {E_TOKEN}!")

@dp.message(AdminGive.waiting_for_user_donat, IsAdmin())
async def give_donat_user(message: Message, state: FSMContext):
    user_data = await find_user_by_username(message.text)
    if not user_data: return await message.answer("Пользователь не найден.")
    await state.update_data(target_id=user_data[0])
    await message.answer("Введите количество донат-монет:")
    await state.set_state(AdminGive.waiting_for_amount_donat)

@dp.message(AdminGive.waiting_for_amount_donat, IsAdmin())
async def give_donat_amount(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Сумма должна быть числом!")
    amount = int(message.text)
    data = await state.get_data()
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("UPDATE users SET donat_coins = donat_coins + ? WHERE user_id = ?", (amount, data['target_id']))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"{E_SUCCESS} Выдано <b>{amount}</b> {E_PREM}!")

@dp.message(AdminGive.waiting_for_user_vip, IsAdmin())
async def give_vip_user(message: Message, state: FSMContext):
    user_data = await find_user_by_username(message.text)
    if not user_data: return await message.answer("Пользователь не найден.")
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (user_data[0],))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"{E_SUCCESS} Выдан статус {E_VIP} <b>VIP</b>!")

# --- ДОБАВЛЕНИЕ ПИТОМЦА ЧЕРЕЗ АДМИНКУ ---
@dp.callback_query(F.data == "panel_add_pet", IsAdmin())
async def start_add_pet(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправьте фото для нового питомца:")
    await state.set_state(AddPet.waiting_for_media)

@dp.message(AddPet.waiting_for_media, IsAdmin())
async def add_pet_media(message: Message, state: FSMContext):
    if not message.photo: return await message.answer("Пожалуйста, отправьте фото.")
    await state.update_data(media_id=message.photo[-1].file_id)
    await message.answer("Отлично. Теперь отправьте имя питомца:")
    await state.set_state(AddPet.waiting_for_name)

@dp.message(AddPet.waiting_for_name, IsAdmin())
async def add_pet_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Теперь отправьте описание питомца:")
    await state.set_state(AddPet.waiting_for_description)

@dp.message(AddPet.waiting_for_description, IsAdmin())
async def add_pet_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("И последнее: укажите стоимость питомца в токенах (число):")
    await state.set_state(AddPet.waiting_for_price)

@dp.message(AddPet.waiting_for_price, IsAdmin())
async def add_pet_price(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Укажите число!")
    data = await state.get_data()
    
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("INSERT INTO pets (name, description, media_id, price) VALUES (?, ?, ?, ?)",
              (data['name'], data['description'], data['media_id'], int(message.text)))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"{E_SUCCESS} Питомец <b>{data['name']}</b> успешно добавлен в магазин!")

# --- ДОБАВЛЕНИЕ ПОДАРКА ЧЕРЕЗ АДМИНКУ ---
@dp.callback_query(F.data == "panel_add_gift", IsAdmin())
async def start_add_gift(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название подарка (например, Роза):")
    await state.set_state(AddGift.waiting_for_name)

@dp.message(AddGift.waiting_for_name, IsAdmin())
async def add_gift_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    text = (
        "Отправьте действие при дарении.\n"
        "Используйте <code>{fam1}</code> (кто дарит) и <code>{fam2}</code> (кому дарят).\n"
        "Пример: <code>5364132471568875504 | {fam1} нежно подарил(а) розу {fam2}</code>"
    )
    await message.answer(text)
    await state.set_state(AddGift.waiting_for_action)

@dp.message(AddGift.waiting_for_action, IsAdmin())
async def add_gift_action(message: Message, state: FSMContext):
    raw_action = message.text.strip()
    action = raw_action
    if "|" in raw_action:
        parts = [p.strip() for p in raw_action.split("|", 1)]
        if parts[0].isdigit(): action = f"<tg-emoji emoji-id='{parts[0]}'>💝</tg-emoji> {parts[1]}"
        elif len(parts) > 1 and parts[1].isdigit(): action = f"{parts[0]} <tg-emoji emoji-id='{parts[1]}'>💝</tg-emoji>"

    await state.update_data(action=action)
    await message.answer("Укажите стоимость подарка (в токенах, по умолчанию 500):")
    await state.set_state(AddGift.waiting_for_price)

@dp.message(AddGift.waiting_for_price, IsAdmin())
async def add_gift_price(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Укажите число!")
    await state.update_data(price=int(message.text))
    await message.answer("Укажите сколько опыта семьи даёт этот подарок (в exp, по умолчанию 100):")
    await state.set_state(AddGift.waiting_for_exp)

@dp.message(AddGift.waiting_for_exp, IsAdmin())
async def add_gift_exp(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Укажите число!")
    data = await state.get_data()
    
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("INSERT INTO gifts (name, action, price, exp) VALUES (?, ?, ?, ?)",
              (data['name'], data['action'], data['price'], int(message.text)))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"{E_SUCCESS} Подарок <b>{data['name']}</b> успешно добавлен!")

# --- УПРАВЛЕНИЕ КАРТОЧКАМИ (ИЗМЕНИТЬ/УДАЛИТЬ) ---
@dp.callback_query(F.data == "panel_manage_cards", IsAdmin())
async def manage_cards_list(callback: CallbackQuery):
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT id, name, rarity FROM cards ORDER BY id DESC LIMIT 50")
    cards = c.fetchall()
    conn.close()
    
    if not cards: return await callback.message.edit_text("Карточек в базе пока нет.")
    
    builder = InlineKeyboardBuilder()
    for cid, cname, crarity in cards:
        builder.button(text=f"[{cid}] {cname} ({crarity})", callback_data=f"admcard_{cid}")
    builder.adjust(1)
    
    await callback.message.edit_text("Выберите карточку для управления (последние 50):", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("admcard_"), IsAdmin())
async def manage_card_actions(callback: CallbackQuery):
    card_id = int(callback.data.split("_")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить Название", callback_data=f"editcard_name_{card_id}")],
        [InlineKeyboardButton(text="🗑 Удалить Карточку", callback_data=f"deletecard_{card_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="panel_manage_cards")]
    ])
    await callback.message.edit_text(f"Управление карточкой ID: <b>{card_id}</b>", reply_markup=kb)

@dp.callback_query(F.data.startswith("deletecard_"), IsAdmin())
async def delete_card_action(callback: CallbackQuery):
    card_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    c.execute("DELETE FROM inventory WHERE card_id = ?", (card_id,)) # Удаляем у игроков тоже
    conn.commit()
    conn.close()
    await callback.message.edit_text(f"{E_SUCCESS} Карточка ID <b>{card_id}</b> полностью удалена из базы и инвентарей игроков.",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="panel_manage_cards")]]))

@dp.callback_query(F.data.startswith("editcard_name_"), IsAdmin())
async def edit_card_name_start(callback: CallbackQuery, state: FSMContext):
    card_id = int(callback.data.split("_")[2])
    await state.update_data(edit_card_id=card_id, edit_field="name")
    await callback.message.edit_text("Отправьте новое название для карточки:")
    await state.set_state(ManageCard.waiting_for_edit_value)

@dp.message(ManageCard.waiting_for_edit_value, IsAdmin())
async def edit_card_value_save(message: Message, state: FSMContext):
    data = await state.get_data()
    card_id = data['edit_card_id']
    
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("UPDATE cards SET name = ? WHERE id = ?", (message.text, card_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"{E_SUCCESS} Название карточки обновлено!")

# --- МАГАЗИН ПИТОМЦЕВ (/pets) ---
@dp.message(Command("pets"))
async def cmd_pets(message: Message):
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT id, name, price FROM pets")
    pets = c.fetchall()
    conn.close()

    if not pets: return await message.answer("Магазин питомцев пока пуст.")

    builder = InlineKeyboardBuilder()
    for pid, pname, pprice in pets:
        builder.button(text=f"🐾 {pname} | {pprice} 🪙", callback_data=f"pet_view_{pid}")
    builder.adjust(1)
    
    await message.answer(f"{E_PETS} <b>Магазин Питомцев</b>\nВыберите питомца для просмотра:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("pet_view_"))
async def view_pet_action(callback: CallbackQuery):
    pet_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT name, description, media_id, price FROM pets WHERE id = ?", (pet_id,))
    pet = c.fetchone()
    conn.close()
    
    if not pet: return await callback.answer("Питомец не найден.", show_alert=True)
    
    name, desc, media_id, price = pet
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🐾 Купить за {price} Токенов", callback_data=f"pet_buy_{pet_id}")]
    ])
    
    caption = (
        f"{E_PETS} <b>Имя Питомца:</b> {name}\n"
        f"{E_CARD_DESC} <b>Описание питомца:</b>\n"
        f"<blockquote>{desc}</blockquote>\n\n"
        f"{E_TOKEN} <b>Стоимость питомца:</b> {price}"
    )
    await callback.message.answer_photo(photo=media_id, caption=caption, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("pet_buy_"))
async def buy_pet_action(callback: CallbackQuery):
    pet_id = int(callback.data.split("_")[2])
    user = get_user_db(callback.from_user)
    
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT name, price FROM pets WHERE id = ?", (pet_id,))
    pet = c.fetchone()
    
    if not pet:
        conn.close()
        return await callback.answer("Питомец не найден.", show_alert=True)
        
    name, price = pet
    
    if user[1] < price:
        conn.close()
        return await callback.answer("Недостаточно токенов для покупки!", show_alert=True)
        
    c.execute("UPDATE users SET coins = coins - ?, pet = ? WHERE user_id = ?", (price, name, callback.from_user.id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"{E_SUCCESS} Вы успешно приобрели питомца <b>{name}</b>!")
    await callback.answer()

# --- ПОДАРКИ (БРАК) ---
@dp.message(F.text.lower().in_(["подарок", "/gift"]))
async def cmd_gift(message: Message):
    user = get_user_db(message.from_user)
    if user[5] == 0:
        return await message.answer("У вас нет партнера для подарка! Вы должны состоять в браке.")
        
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT id, name, price, exp FROM gifts")
    gifts = c.fetchall()
    conn.close()

    if not gifts: return await message.answer("Магазин подарков пока пуст.")

    builder = InlineKeyboardBuilder()
    for gid, gname, gprice, gexp in gifts:
        builder.button(text=f"🎁 {gname} ({gprice} 🪙) | +{gexp} EXP", callback_data=f"gift_buy_{gid}")
    builder.adjust(1)
    
    await message.answer(f"{E_GIFT} <b>Магазин Подарков</b>\nВыберите подарок для вашего партнера:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("gift_buy_"))
async def buy_gift_action(callback: CallbackQuery):
    gift_id = int(callback.data.split("_")[2])
    user = get_user_db(callback.from_user)
    partner_id = user[5]
    partner_name = user[6]
    
    if partner_id == 0:
        return await callback.answer("У вас нет партнера!", show_alert=True)
        
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT action, price, exp FROM gifts WHERE id = ?", (gift_id,))
    gift = c.fetchone()
    
    if not gift:
        conn.close()
        return await callback.answer("Подарок не найден.", show_alert=True)
        
    action, price, exp = gift
    
    if user[1] < price:
        conn.close()
        return await callback.answer(f"Недостаточно токенов! Нужно: {price}", show_alert=True)
        
    c.execute("UPDATE users SET coins = coins - ?, family_exp = family_exp + ? WHERE user_id = ?", (price, exp, callback.from_user.id))
    c.execute("UPDATE users SET family_exp = family_exp + ? WHERE user_id = ?", (exp, partner_id))
    conn.commit()
    conn.close()
    
    user1_link = f'<a href="tg://user?id={callback.from_user.id}">{callback.from_user.first_name}</a>'
    user2_link = f'<a href="tg://user?id={partner_id}">{partner_name}</a>'
    
    final_text = action.format(fam1=user1_link, fam2=user2_link) if "{fam1}" in action else f"{user1_link} {action} {user2_link}"
    
    await callback.message.edit_text(f"<blockquote>{final_text}</blockquote>\n\n{E_EXP} Получено: <b>+{exp} Семейного Опыта</b>!")

# --- БАЗОВЫЕ КОМАНДЫ (Обновлен Profile) ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = get_user_db(message.from_user)
    if user[1] == 2000 and user[2] == 50: 
        await message.answer(
            f"{E_REG} Регистрация прошла успешно! {E_SUCCESS}\n"
            f"{E_BONUS} Ваш бонус за старт: <b>2.000</b> {E_TOKEN} Qubino Token и <b>50</b> {E_PREM} донат-монет!"
        )
    else:
        await message.answer("С возвращением! Введите /profile для просмотра статистики.")

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user = get_user_db(message.from_user)
    user_id, coins, donat, pet, _, partner_id, partner_name, is_vip, _, _, family_exp = user
    rank = get_rank(coins)
    
    pet_text = "Нет" if pet == 'none' else f"{E_PETS} {pet}"
    
    partner_text = "Нет"
    if partner_id != 0: 
        partner_text = f'<a href="tg://user?id={partner_id}">{partner_name}</a> (Ур. {family_exp // 100} ✨)'

    vip_badge = f"{E_VIP} <b>VIP</b>\n" if is_vip else ""

    profile_text = (
        f"<b>Профиль пользователя</b>\n"
        f"{E_LINE}\n"
        f"{vip_badge}"
        f"{E_ID} <b>TG ID:</b> <code>{message.from_user.id}</code>\n"
        f"{E_REG} <b>Ранг:</b> {rank}\n"
        f"{E_TOKEN} <b>Qubino Token:</b> {coins}\n"
        f"{E_PREM} <b>Донат:</b> {donat}\n"
        f"{E_PETS} <b>Питомец:</b> {pet_text}\n"
        f"{E_PROPOSE} <b>В браке с:</b> {partner_text}\n"
        f"{E_LINE}"
    )

    photos = await bot.get_user_profile_photos(message.from_user.id, limit=1)
    if photos.total_count > 0:
        await message.answer_photo(photo=photos.photos[0][-1].file_id, caption=profile_text)
    else:
        await message.answer(profile_text)


@dp.message(Command("roll"))
async def cmd_roll(message: Message):
    user = get_user_db(message.from_user)
    is_vip = user[7]
    
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT last_roll FROM users WHERE user_id = ?", (message.from_user.id,))
    last_roll = c.fetchone()[0]
    
    now = datetime.now()
    if last_roll:
        last_time = datetime.fromisoformat(last_roll)
        if now - last_time < timedelta(hours=2):
            left = timedelta(hours=2) - (now - last_time)
            hours, remainder = divmod(left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            conn.close()
            return await message.answer(f"{E_TIME} Выбивать карточки можно раз в 2 часа!\nСледующая попытка через <b>{hours}ч {minutes}м</b>.")
            
    c.execute("SELECT id, name, media_id, rarity FROM cards")
    all_cards = c.fetchall()
    
    if not all_cards:
        await message.answer("В автомате пока нет карточек!")
        conn.close()
        return

    cards_by_rarity = {}
    for card in all_cards:
        r = card[3]
        if r not in cards_by_rarity: cards_by_rarity[r] = []
        cards_by_rarity[r].append(card)
        
    available_rarities = list(cards_by_rarity.keys())
    chance_dict = VIP_RARITY_CHANCES if is_vip else RARITY_CHANCES
    available_weights = [chance_dict.get(r, 1) for r in available_rarities]
    
    chosen_rarity = random.choices(available_rarities, weights=available_weights, k=1)[0]
    card = random.choice(cards_by_rarity[chosen_rarity])
    card_id, name, media_id, rarity = card
    
    c.execute("SELECT 1 FROM inventory WHERE user_id = ? AND card_id = ?", (message.from_user.id, card_id))
    is_new = not bool(c.fetchone())
    
    min_r, max_r = RARITY_REWARDS.get(rarity, (5, 25))
    token_reward = random.randint(min_r, max_r)
    
    if is_vip: token_reward *= 2
    
    c.execute("INSERT INTO inventory (user_id, card_id) VALUES (?, ?)", (message.from_user.id, card_id))
    c.execute("UPDATE users SET coins = coins + ?, last_roll = ? WHERE user_id = ?", (token_reward, now.isoformat(), message.from_user.id))
    
    c.execute("SELECT COUNT(*) FROM inventory WHERE user_id = ?", (message.from_user.id,))
    total_cards = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    rarity_display = get_rarity_display(rarity)
    new_badge = f"{E_NEW_CARD} <b>НОВАЯ КАРТОЧКА!</b>\n" if is_new else ""
    vip_msg = f" <i>(x2 {E_VIP})</i>" if is_vip else ""
    
    caption = (
        f"{E_CARD_ROLL} <b>ВЫ ВЫБИЛИ КАРТОЧКУ!</b>\n\n"
        f"{new_badge}"
        f"{E_CARD_NAME} <b>{name}</b>\n"
        f"{E_CARD_RARITY} <b>Редкость:</b> {rarity_display}\n\n"
        f"{E_TOKEN} <b>Награда:</b> +{token_reward}{vip_msg} Qubino Token\n"
        f"{E_CARD_COUNT} <b>Всего карточек:</b> {total_cards} шт."
    )
    
    await message.answer_photo(photo=media_id, caption=caption)

@dp.message(Command("mycards"))
async def cmd_mycards(message: Message):
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("""SELECT c.id, c.name, c.rarity 
                 FROM inventory i 
                 JOIN cards c ON i.card_id = c.id 
                 WHERE i.user_id = ?""", (message.from_user.id,))
    cards = c.fetchall()
    conn.close()

    if not cards: return await message.answer("У вас пока нет карточек.")

    unique_cards = {}
    for card_id, name, rarity in cards:
        if card_id not in unique_cards: unique_cards[card_id] = {"name": name, "rarity": rarity, "count": 1}
        else: unique_cards[card_id]["count"] += 1

    builder = InlineKeyboardBuilder()
    for c_id, data in unique_cards.items():
        btn_text = f"{data['name']} ({data['count']} шт) - {data['rarity']}"
        builder.button(text=btn_text, callback_data=f"mycard_{c_id}")
    builder.adjust(1)
    
    await message.answer(f"{E_MY_CARDS} <b>Ваша коллекция карточек:</b>\nВыберите карточку:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("mycard_"))
async def cb_mycard(callback: CallbackQuery):
    card_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT name, description, media_id, rarity FROM cards WHERE id = ?", (card_id,))
    card = c.fetchone()
    conn.close()
    
    if not card: return await callback.answer("Карточка не найдена!", show_alert=True)
        
    name, desc, media_id, rarity = card
    caption = (
        f"{E_CARD_NAME} <b>{name}</b>\n"
        f"{E_CARD_RARITY} <b>Редкость:</b> {get_rarity_display(rarity)}\n\n"
        f"{E_CARD_DESC} <b>Описание:</b>\n"
        f"<blockquote>{desc}</blockquote>"
    )
    await callback.message.answer_photo(photo=media_id, caption=caption)
    await callback.answer()

def get_card_builder_kb(card_data: dict = None):
    if card_data is None: card_data = {}
    kb = [
        [InlineKeyboardButton(text="🖼 Медиа ✅" if card_data.get('media_id') else "🖼 Добавить Медиа", callback_data="add_media")],
        [InlineKeyboardButton(text="📝 Название ✅" if card_data.get('name') else "📝 Добавить Название", callback_data="add_desc")],
        [InlineKeyboardButton(text="📖 Описание ✅" if card_data.get('description') else "📖 Добавить Описание", callback_data="add_desc")],
        [InlineKeyboardButton(text=f"✨ Редкость ({card_data.get('rarity')}) ✅" if card_data.get('rarity') else "✨ Добавить Редкость", callback_data="add_rarity")]
    ]
    if card_data.get('media_id') and card_data.get('name') and card_data.get('description') and card_data.get('rarity'):
        kb.append([InlineKeyboardButton(text="✅ Сохранить карточку", callback_data="save_card")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.callback_query(F.data == "panel_add_card", IsAdmin())
async def start_add_card(callback: CallbackQuery, state: FSMContext):
    await state.update_data(media_id=None, name=None, description=None, rarity=None)
    await callback.message.edit_text("Сборка новой карточки:", reply_markup=get_card_builder_kb({}))

@dp.callback_query(F.data.in_({"add_media", "add_name", "add_desc", "add_rarity"}), IsAdmin())
async def process_card_buttons(callback: CallbackQuery, state: FSMContext):
    if callback.data == "add_media":
        await callback.message.answer("Отправьте фото для карточки:")
        await state.set_state(AddCard.waiting_for_media)
    elif callback.data == "add_name":
        await callback.message.answer("Отправьте название карточки:")
        await state.set_state(AddCard.waiting_for_name)
    elif callback.data == "add_desc":
        await callback.message.answer("Отправьте описание карточки:")
        await state.set_state(AddCard.waiting_for_description)
    elif callback.data == "add_rarity":
        rarity_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚪️ Обычная", callback_data="setrarity_Обычная")],
            [InlineKeyboardButton(text="🟢 Необычная", callback_data="setrarity_Необычная")],
            [InlineKeyboardButton(text="🔵 Редкая", callback_data="setrarity_Редкая")],
            [InlineKeyboardButton(text="🟣 Эпическая", callback_data="setrarity_Эпическая")],
            [InlineKeyboardButton(text="🟡 Легендарная", callback_data="setrarity_Легендарная")]
        ])
        await callback.message.answer("Выберите редкость:", reply_markup=rarity_kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("setrarity_"), IsAdmin())
async def set_card_rarity(callback: CallbackQuery, state: FSMContext):
    rarity_val = callback.data.split("_")[1]
    await state.update_data(rarity=rarity_val)
    data = await state.get_data()
    await callback.message.answer(f"✅ Редкость <b>{rarity_val}</b> установлена.", reply_markup=get_card_builder_kb(data))
    await callback.answer()

@dp.message(AddCard.waiting_for_media, IsAdmin())
async def save_media(message: Message, state: FSMContext):
    if message.photo:
        await state.update_data(media_id=message.photo[-1].file_id)
        data = await state.get_data()
        await message.answer("✅ Медиа загружено.", reply_markup=get_card_builder_kb(data))
        await state.set_state(None)
    else: await message.answer("⚠️ Отправьте именно фотографию.")

@dp.message(AddCard.waiting_for_name, IsAdmin())
async def save_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()
    await message.answer("✅ Название сохранено.", reply_markup=get_card_builder_kb(data))
    await state.set_state(None)

@dp.message(AddCard.waiting_for_description, IsAdmin())
async def save_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    data = await state.get_data()
    await message.answer("✅ Описание сохранено.", reply_markup=get_card_builder_kb(data))
    await state.set_state(None)

@dp.callback_query(F.data == "save_card", IsAdmin())
async def save_card_to_db(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("INSERT INTO cards (name, description, media_id, rarity) VALUES (?, ?, ?, ?)", 
              (data['name'], data['description'], data['media_id'], data['rarity']))
    conn.commit()
    conn.close()
    await state.clear()
    await callback.message.edit_text("🎉 Карточка успешно добавлена в базу!")

# --- ДОБАВЛЕНИЕ РП КОМАНД ---
@dp.callback_query(F.data == "panel_add_rp", IsAdmin())
async def start_add_rp(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Отправь слово-триггер для РП:")
    await state.set_state(AddRP.waiting_for_trigger)

@dp.message(AddRP.waiting_for_trigger, IsAdmin())
async def rp_save_trigger(message: Message, state: FSMContext):
    await state.update_data(trigger=message.text.lower().strip())
    await message.answer("Теперь отправь шаблон действия.\nПример:\n<code>5321201786659303279 | {user1} поцеловал(а) {user2}</code>")
    await state.set_state(AddRP.waiting_for_action)

@dp.message(AddRP.waiting_for_action, IsAdmin())
async def rp_save_action(message: Message, state: FSMContext):
    data = await state.get_data()
    trigger = data['trigger']
    raw_action = message.text.strip()
    action = raw_action
    
    if "|" in raw_action:
        parts = [p.strip() for p in raw_action.split("|", 1)]
        if parts[0].isdigit(): action = f"<tg-emoji emoji-id='{parts[0]}'>🎭</tg-emoji> {parts[1]}"
        elif len(parts) > 1 and parts[1].isdigit(): action = f"{parts[0]} <tg-emoji emoji-id='{parts[1]}'>🎭</tg-emoji>"

    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("REPLACE INTO rp_commands (trigger, action) VALUES (?, ?)", (trigger, action))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"✅ РП команда <b>{trigger}</b> добавлена!")

@dp.message(~F.text.startswith('/'))
async def handle_rp_commands(message: Message):
    if not message.text or not message.reply_to_message: return
    text = message.text.lower().strip()
    conn = sqlite3.connect('qubino.db')
    c = conn.cursor()
    c.execute("SELECT action FROM rp_commands WHERE trigger = ?", (text,))
    res = c.fetchone()
    conn.close()
    
    if res:
        action = res[0]
        user1 = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
        user2 = f'<a href="tg://user?id={message.reply_to_message.from_user.id}">{message.reply_to_message.from_user.first_name}</a>'
        final_text = action.format(user1=user1, user2=user2) if "{user1}" in action else f"{user1} {action} {user2}"
        await message.answer(f"<blockquote>{final_text}</blockquote>")

async def main():
    init_db()
    print("Бот Qubino Card (Обновление: Подарки, Питомцы, Управление и Emojico) запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
