import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import timedelta

# ===== НАСТРОЙКИ =====
TOKEN = os.getenv("8926286755:AAHoklKvcFR3hU65aP5-__8r52-xga9SfUI")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== БАЗА ДАННЫХ =====
db = sqlite3.connect("database.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    nick TEXT DEFAULT '',
    rank TEXT DEFAULT '',
    role TEXT DEFAULT 'user'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

db.commit()

# ===== КЛАВИАТУРА =====
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📜 Правила"), KeyboardButton(text="📖 Команды")]
    ],
    resize_keyboard=True
)

# ===== ВСПОМОГАТЕЛЬНЫЕ =====
def get_user(uid):
    cursor.execute("SELECT nick, rank, role FROM users WHERE user_id=?", (uid,))
    return cursor.fetchone()

def get_role(uid):
    user = get_user(uid)
    return user[2] if user else "user"

def is_admin(uid):
    return get_role(uid) in ["admin", "creator"]

# ===== START =====
@dp.message(Command("start"))
async def start(msg: types.Message):
    uid = msg.from_user.id
    cursor.execute("SELECT role FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()

    if not row:
        cursor.execute(
            "INSERT INTO users (user_id, role) VALUES (?, 'creator')",
            (uid,)
        )
        db.commit()
        await msg.answer(
            "👑 Ты автоматически назначен *создателем бота!*",
            parse_mode="Markdown",
            reply_markup=menu
        )
    else:
        await msg.answer("🤖 Бот работает.", reply_markup=menu)

# ===== ПРОФИЛЬ =====
@dp.message(Command("profile"))
async def profile(msg: types.Message):
    uid = msg.reply_to_message.from_user.id if msg.reply_to_message else msg.from_user.id
    user = get_user(uid)

    if not user:
        return await msg.answer("❌ Профиль не найден")

    nick, rank, role = user
    await msg.answer(
        f"👤 Ник: {nick or '—'}\n"
        f"⭐ Звание: {rank or '—'}\n"
        f"🛡 Роль: {role}"
    )

# ===== НИК =====
@dp.message(Command("setnick"))
async def setnick(msg: types.Message):
    if not msg.reply_to_message:
        return await msg.answer("❌ Ответь на сообщение пользователя")

    nick = msg.text.split(maxsplit=1)[1]
    uid = msg.reply_to_message.from_user.id

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (uid,)
    )
    cursor.execute(
        "UPDATE users SET nick=? WHERE user_id=?",
        (nick, uid)
    )
    db.commit()
    await msg.answer("✅ Ник установлен")

# ===== ЗВАНИЕ =====
@dp.message(Command("setrank"))
async def setrank(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Нет прав")

    if not msg.reply_to_message:
        return await msg.answer("❌ Ответь на сообщение пользователя")

    rank = msg.text.split(maxsplit=1)[1]
    uid = msg.reply_to_message.from_user.id

    cursor.execute("UPDATE users SET rank=? WHERE user_id=?", (rank, uid))
    db.commit()
    await msg.answer("⭐ Звание установлено")

# ===== РОЛИ =====
@dp.message(Command("promote"))
async def promote(msg: types.Message):
    if get_role(msg.from_user.id) != "creator":
        return await msg.answer("⛔ Только создатель")

    if not msg.reply_to_message:
        return await msg.answer("❌ Ответь на сообщение")

    role = msg.text.split()[1]
    uid = msg.reply_to_message.from_user.id

    cursor.execute("UPDATE users SET role=? WHERE user_id=?", (role, uid))
    db.commit()
    await msg.answer(f"✅ Назначена роль: {role}")

@dp.message(Command("demote"))
async def demote(msg: types.Message):
    if get_role(msg.from_user.id) != "creator":
        return await msg.answer("⛔ Только создатель")

    uid = msg.reply_to_message.from_user.id
    cursor.execute("UPDATE users SET role='user' WHERE user_id=?", (uid,))
    db.commit()
    await msg.answer("✅ Роль снята")

# ===== МОДЕРАЦИЯ =====
@dp.message(Command("mute"))
async def mute(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Нет прав")

    uid = msg.reply_to_message.from_user.id
    await bot.restrict_chat_member(
        msg.chat.id,
        uid,
        permissions=types.ChatPermissions(),
        until_date=timedelta(minutes=10)
    )
    await msg.answer("🔇 Пользователь замучен на 10 минут")

@dp.message(Command("ban"))
async def ban(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Нет прав")

    uid = msg.reply_to_message.from_user.id
    await bot.ban_chat_member(msg.chat.id, uid)
    await msg.answer("⛔ Пользователь забанен")

@dp.message(Command("kick"))
async def kick(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Нет прав")

    uid = msg.reply_to_message.from_user.id
    await bot.ban_chat_member(msg.chat.id, uid)
    await bot.unban_chat_member(msg.chat.id, uid)
    await msg.answer("👢 Пользователь кикнут")

# ===== ПРАВИЛА =====
@dp.message(Command("rules"))
async def rules(msg: types.Message):
    cursor.execute("SELECT value FROM settings WHERE key='rules'")
    r = cursor.fetchone()
    await msg.answer(r[0] if r else "📜 Правила не установлены")

@dp.message(Command("setrules"))
async def setrules(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return await msg.answer("⛔ Нет прав")

    text = msg.text.split(maxsplit=1)[1]
    cursor.execute(
        "INSERT OR REPLACE INTO settings VALUES ('rules', ?)",
        (text,)
    )
    db.commit()
    await msg.answer("✅ Правила сохранены")

# ===== HELP =====
@dp.message(Command("help"))
async def help_command(msg: types.Message):
    await msg.answer(
        "📖 *Команды бота*\n\n"
        "/profile — профиль\n"
        "/setnick — ник (ответом)\n"
        "/setrank — звание (админ)\n"
        "/mute /kick /ban — модерация\n"
        "/promote /demote — роли\n"
        "/rules — правила\n"
        "/help — команды",
        parse_mode="Markdown"
    )

# ===== КНОПКИ =====
@dp.message(lambda m: m.text == "👤 Профиль")
async def btn_profile(msg: types.Message):
    await profile(msg)

@dp.message(lambda m: m.text == "📜 Правила")
async def btn_rules(msg: types.Message):
    await rules(msg)

@dp.message(lambda m: m.text == "📖 Команды")
async def btn_help(msg: types.Message):
    await help_command(msg)
@dp.chat_member()

async def on_user_join(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == "member":
        user = event.new_chat_member.user
        mention = user.mention_html()

        # Отримуємо правила
        cursor.execute("SELECT value FROM settings WHERE key='rules'")
        rules = cursor.fetchone()
        rules_text = rules[0] if rules else "Правила ще не встановлені."

        await bot.send_message(
            event.chat.id,
            f"👋 Вітаємо, {mention}!\n\n"
            f"📜 <b>Правила групи:</b>\n{rules_text}\n\n"
            f"✍️ Будь ласка, напиши:\n"
            f"— свій <b>ігровий нік</b>\n"
            f"— своє <b>звання</b>\n\n"
            f"Формат:\n"
            f"<code>Нік: ...\nЗвання: ...</code>",
            parse_mode="HTML"
        )


# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
