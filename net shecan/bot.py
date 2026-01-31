import sqlite3
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)

TOKEN = "7012098115:AAHlkDnnfqsq1RY3JsgaiJzEd1dML0k8OQA"
ADMIN_ID = 6380008983
DB = "db.sqlite"


# ================= DB ==================
def init_db():
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        # کاربران
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            joined TEXT
        )""")
        # تعرفه‌ها
        c.execute("""CREATE TABLE IF NOT EXISTS tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            months INTEGER,
            traffic INTEGER,
            price INTEGER
        )""")
        # سفارش‌ها
        c.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tariff_id INTEGER,
            created TEXT
        )""")
        # کانفیگ‌ها
        c.execute("""CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            config TEXT,
            created TEXT
        )""")
        # تست رایگان
        c.execute("""CREATE TABLE IF NOT EXISTS free_test (
            user_id INTEGER PRIMARY KEY,
            created TEXT
        )""")
        # درخواست تمدید
        c.execute("""CREATE TABLE IF NOT EXISTS renew_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            created TEXT
        )""")
        conn.commit()
# ======================================


# ================= KEYBOARDS =============
def user_keyboard():
    return ReplyKeyboardMarkup(
        [["🛒 خرید VPN", "🔑 کانفیگ‌های من"], ["🧪 تست رایگان", "👤 مشخصات کاربری"]],
        resize_keyboard=True
    )

def admin_keyboard():
    return ReplyKeyboardMarkup(
        [["💰 مدیریت تعرفه‌ها", "🔑 ارسال کانفیگ"], ["📊 گزارش فروش"]],
        resize_keyboard=True
    )

def back_keyboard(uid):
    return admin_keyboard() if uid == ADMIN_ID else user_keyboard()
# ======================================


# ================= START ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users VALUES (?,?)",
                  (uid, datetime.datetime.now().isoformat()))
        conn.commit()

    if uid == ADMIN_ID:
        await update.message.reply_text("🛠 پنل ادمین", reply_markup=admin_keyboard())
    else:
        await update.message.reply_text("🏠 منوی اصلی", reply_markup=user_keyboard())
# ======================================


# ================= HANDLE MESSAGE ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    # ======== ADMIN =========
    if uid == ADMIN_ID:

        # مرحله وارد کردن کانفیگ بعد از انتخاب کاربر
        if context.user_data.get("send_cfg"):
            cfg_text = text.strip()
            target_user = context.user_data.get("target_user")
            if not target_user:
                await update.message.reply_text("❌ کاربری انتخاب نشده", reply_markup=admin_keyboard())
                context.user_data.pop("send_cfg", None)
                return
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO configs (user_id, config, created) VALUES (?,?,?)",
                    (target_user, cfg_text, datetime.datetime.now().isoformat())
                )
                conn.commit()
            try:
                await context.bot.send_message(target_user, f"🔑 کانفیگ شما:\n{cfg_text}")
            except:
                pass
            await update.message.reply_text(f"✅ کانفیگ برای کاربر {target_user} ارسال شد",
                                            reply_markup=admin_keyboard())
            context.user_data.pop("send_cfg", None)
            context.user_data.pop("target_user", None)
            return

        # گزینه‌های ادمین
        if text == "🔑 ارسال کانفیگ":
            # لیست کاربران دارای سفارش اما بدون کانفیگ
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT DISTINCT o.user_id
                    FROM orders o
                    LEFT JOIN configs cfg ON o.user_id = cfg.user_id
                    WHERE cfg.user_id IS NULL
                """)
                users = [r[0] for r in c.fetchall()]
            if not users:
                await update.message.reply_text("❌ کاربری برای ارسال کانفیگ وجود ندارد",
                                                reply_markup=admin_keyboard())
            else:
                # ایجاد دکمه‌ها برای هر کاربر
                buttons = [[InlineKeyboardButton(str(uid), callback_data=f"sendcfg:{uid}")] for uid in users]
                kb = InlineKeyboardMarkup(buttons)
                await update.message.reply_text("کاربری که می‌خواهید کانفیگ بفرستید انتخاب کنید:", reply_markup=kb)

        elif text == "📊 گزارش فروش":
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM orders")
                count = c.fetchone()[0]
            await update.message.reply_text(f"📊 گزارش فروش\n\n🧾 تعداد سفارش: {count}",
                                            reply_markup=admin_keyboard())
        elif text == "💰 مدیریت تعرفه‌ها":
            await update.message.reply_text("💰 مدیریت تعرفه‌ها هنوز فعال نشده است",
                                            reply_markup=admin_keyboard())
        elif text == "🔙 برگشت":
            await update.message.reply_text("🛠 پنل ادمین", reply_markup=admin_keyboard())

    # ======== USER =========
    else:
        if text == "🔑 کانفیگ‌های من":
            await update.message.reply_text("🔑 کانفیگ‌های من", reply_markup=ReplyKeyboardMarkup(
                [["📄 لیست کانفیگ‌ها", "♻️ تمدید اشتراک"]], resize_keyboard=True
            ))
        elif text == "📄 لیست کانفیگ‌ها":
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute("SELECT config FROM configs WHERE user_id=?", (uid,))
                rows = c.fetchall()
            txt = "\n\n".join(r[0] for r in rows) if rows else "❌ کانفیگی ندارید"
            await update.message.reply_text(txt, reply_markup=back_keyboard(uid))
        elif text == "♻️ تمدید اشتراک":
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO renew_requests (user_id, created) VALUES (?,?)",
                          (uid, datetime.datetime.now().isoformat()))
                conn.commit()
            await update.message.reply_text("✅ درخواست تمدید ثبت شد", reply_markup=back_keyboard(uid))
        elif text == "🧪 تست رایگان":
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute("SELECT 1 FROM free_test WHERE user_id=?", (uid,))
                exists = c.fetchone()
                if exists:
                    await update.message.reply_text("❌ قبلاً تست رایگان دریافت کرده‌اید",
                                                    reply_markup=back_keyboard(uid))
                else:
                    c.execute("INSERT INTO free_test VALUES (?,?)",
                              (uid, datetime.datetime.now().isoformat()))
                    conn.commit()
                    await update.message.reply_text("✅ درخواست تست ثبت شد، منتظر کانفیگ باشید",
                                                    reply_markup=back_keyboard(uid))
        elif text == "👤 مشخصات کاربری":
            await update.message.reply_text(f"👤 User ID:\n{uid}", reply_markup=back_keyboard(uid))
        elif text == "🛒 خرید VPN":
            with sqlite3.connect(DB) as conn:
                c = conn.cursor()
                c.execute("INSERT INTO orders (user_id, tariff_id, created) VALUES (?,?,?)",
                          (uid, 1, datetime.datetime.now().isoformat()))
                conn.commit()
            await update.message.reply_text("✅ سفارش شما ثبت شد", reply_markup=back_keyboard(uid))
        elif text == "🔙 برگشت":
            await update.message.reply_text("🏠 منوی اصلی", reply_markup=user_keyboard())
# ======================================


# ================= CALLBACK QUERY ==========
async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if uid != ADMIN_ID:
        await q.message.delete()
        return

    if data.startswith("sendcfg:"):
        target_user = int(data.split(":")[1])
        context.user_data["target_user"] = target_user
        context.user_data["send_cfg"] = True
        await q.message.reply_text(f"✍️ حالا کانفیگ را برای کاربر {target_user} وارد کنید",
                                   reply_markup=admin_keyboard())
# ======================================


# ================= MAIN =================
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(CallbackQueryHandler(callback_query))

    print("Bot Running...")
    app.run_polling()
# ======================================


if __name__ == "__main__":
    main()
