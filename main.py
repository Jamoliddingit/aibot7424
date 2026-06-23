import asyncio
import os
import csv
import io
from datetime import datetime
import threading

from fastapi import FastAPI
import uvicorn

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from utils import (
    make_back_kb,
    deny_non_admin,
    display_items,
    delete_item,
    prompt_grade,
    handle_grade,
    create_submission,
    process_work_submission,
)

# ================== CONFIG ==================
# Render'da TOKEN env var bo'ladi
TOKEN = os.getenv("TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMINS = [327276782, 7998617969]  # Admin Telegram ID larini shu yerga yoz

# ================== FASTAPI HEALTH CHECK ==================

app = FastAPI()

from fastapi.responses import JSONResponse

# GET so'rovlar uchun
@app.get("/")
def alive():
    return {"status": "AIBOT OK", "ping": True}

# HEAD so'rovlar uchun (UptimeRobot kere)
@app.head("/")
def alive_head():
    return JSONResponse(content={"status": "AIBOT OK"}, status_code=200)

# Qo'shimcha: UptimeRobot ba'zan /ping ga GET yuboradi
@app.get("/ping")
def ping():
    return {"pong": True}

def start_web():
    """
    FastAPI serverni alohida thread'da ishga tushiramiz.
    Render 'PORT' env var beradi, bo'lmasa 10000 ni olamiz.
    """
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ================== DATA STORES ==================

students = [
    "Abdullayev Ulug'bek O'tkir o'g'li",
    "Abdurasulov Xondamir Nozimjon o'g'li",
    "Abdusalamov Suxrob Tulqin o'g'li",
    "Absalamova Zilolaxon Ergashxo'ja qizi",
    "Ahmadaliyev Muhammadjon Abduxalil o'g'li",
    "Allayev Yoqubjon Rayimjon o'g'li",
    "Boxodirov Nazarbek Qobuljon o'g'li",
    "Davlatboyev Bunyod Rashid o'g'li",
    "Davlatova Sevinch Faxriddin qizi",
    "Doniyorbekov Rashidbek Xurshidbek o'g'li",
    "Hakimov Oybek Obid o'g'li",
    "Ismoilov Jamoliddin Kamoliddin o'g'li",
    "Jabborqulov Otabek Ulug'bek o'g'li",
    "Maxmudova Zulayho Jumanazar qizi",
    "Murodullayev Javohir Akmal o'g'li",
    "Ongarbaev Quralbay Baxadírovich",
    "Ozodova Malikaxon Ravshan qizi",
    "Pulatov Dilshod Dilmurod o'g'li",
    "Qayumjonov Mahmudjon Mahkamjon o'g'li",
    "Saatbayev Sherzod Farxadovich",
    "Sheraliyev O'tkirbek Alisher o'g'li",
    "Sobirqulov Baxodir Zoir o'g'li",
    "Sodiqov Xudoyberdi Ato o'g'li",
    "Suyundiqov Abdulazizjon Alisher o'g'li",
    "Vaxobov Ismoil Vaxob o'g'li",
]

student_projects = {
    "Davlatboyev Bunyod Rashid o'g'li": "Bot: @all_animetopBot",
    "Vaxobov Ismoil Vaxob o'g'li": "Bot: @minimarket_probot",
    "Absalamova Zilolaxon Ergashxo'ja qizi": "Sayt: https://e-commerce-one-omega-68.vercel.app/",
}

graded_students = set()

# feedbacks: har bitta element:
# {
#   "id": int, "student": str, "type": "text"/"photo"/"video"/"document",
#   "content": str|None, "file_id": str|None,
#   "from_user_id": int, "timestamp": str, "grade": str|None
# }
feedbacks = []

# works xuddi shunday formatda
works = []

_next_feedback_id = 1
_next_work_id = 1

# /start bosgan userlar – broadcast uchun
registered_user_ids = set()

# Pending actions: { user_id: {"action": "..", ...} }
pending_actions: dict[int, dict] = {}

# Logs
logs: list[tuple[str, str]] = []  # (timestamp, text)


def log(event: str):
    ts = datetime.now().isoformat(sep=" ", timespec="seconds")
    logs.append((ts, event))


# ================== KEYBOARDS ==================

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🌐 Saytga o'tish",
                url="https://studentlar.netlify.app/"
            )],
            [InlineKeyboardButton(
                text="📋 Talabalar ro'yxati",
                callback_data="royhat"
            )],
            [InlineKeyboardButton(
                text="🛠 Admin panel",
                callback_data="admin_panel"
            )],
        ]
    )


def back_to_start_kb() -> InlineKeyboardMarkup:
    return make_back_kb("⬅️ Ortga", "back|start")


def back_to_royhat_kb() -> InlineKeyboardMarkup:
    return make_back_kb("⬅️ Ortga", "back|royhat")


def back_to_admin_panel_kb() -> InlineKeyboardMarkup:
    return make_back_kb("⬅️ Admin panel", "admin_panel")


# ================== HANDLERS ==================

# /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    registered_user_ids.add(message.from_user.id)
    await message.answer(
        "👋 <b>Salom!</b>\nQuyida loyihani ko'rish yoki talabalar ro'yxatini ochish mumkin 👇",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )
    log(f"/start from {message.from_user.id}")


# Talabalar ro'yxati
@dp.callback_query(F.data == "royhat")
async def show_students(callback: CallbackQuery):
    rows = []
    for name in students:
        rows.append([InlineKeyboardButton(text=name, callback_data=f"student|{name}")])
    rows.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="back|start")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await callback.message.answer(
        "📋 <b>Talabalar ro'yxati:</b>",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()


# Talaba sahifasi
@dp.callback_query(F.data.startswith("student|"))
async def student_page(callback: CallbackQuery):
    name = callback.data.split("|", 1)[1]
    project_text = student_projects.get(
        name,
        f"📂 {name}ning mustaqil ishi hozircha yuklanmagan ❌",
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="💬 Fikr bildirish",
                callback_data=f"action|feedback|{name}"
            )],
            [InlineKeyboardButton(
                text="📂 Ishini yuborish",
                callback_data=f"action|work|{name}"
            )],
            [InlineKeyboardButton(
                text="⬅️ Ortga (ro'yxat)",
                callback_data="royhat"
            )],
        ]
    )

    await callback.message.answer(project_text, reply_markup=kb)
    graded_students.add(name)
    await callback.answer()


# Fikr / Ish flow boshlash
@dp.callback_query(F.data.startswith("action|"))
async def start_action(callback: CallbackQuery):
    _, action, name = callback.data.split("|", 2)
    user_id = callback.from_user.id

    if action == "feedback":
        pending_actions[user_id] = {"action": "feedback", "student": name}
        await callback.message.answer(
            f"💬 {name}, fikringizni matn yoki link shaklida yuboring:",
            reply_markup=back_to_royhat_kb(),
        )
        log(f"user {user_id} started feedback for {name}")

    elif action == "work":
        pending_actions[user_id] = {"action": "work", "student": name}
        await callback.message.answer(
            f"📂 {name}, ishini (link, fayl, rasm yoki video) yuboring:",
            reply_markup=back_to_royhat_kb(),
        )
        log(f"user {user_id} started work for {name}")

    await callback.answer()


# Ortga tugmalar
@dp.callback_query(F.data.startswith("back|"))
async def handle_back(callback: CallbackQuery):
    target = callback.data.split("|", 1)[1]
    if target == "start":
        await cmd_start(callback.message)
    elif target == "royhat":
        await show_students(callback)
    await callback.answer()


# Admin panel
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if await deny_non_admin(callback, ADMINS):
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📝 Fikrlarni ko'rish va boshqarish",
                callback_data="admin|view_feedbacks"
            )],
            [InlineKeyboardButton(
                text="📂 Ishlarni ko'rish va boshqarish",
                callback_data="admin|view_works"
            )],
            [InlineKeyboardButton(
                text="📊 Statistikalar",
                callback_data="admin|stats"
            )],
            [InlineKeyboardButton(
                text="📥 Export CSV",
                callback_data="admin|export"
            )],
            [InlineKeyboardButton(
                text="📣 Broadcast / Eslatma yuborish",
                callback_data="admin|broadcast"
            )],
            [InlineKeyboardButton(
                text="📜 Logs",
                callback_data="admin|logs"
            )],
            [InlineKeyboardButton(
                text="⬅️ Ortga",
                callback_data="back|start"
            )],
        ]
    )
    await callback.message.answer("👑 Admin panel:", reply_markup=kb)
    await callback.answer()


# Admin: view / stats / export / broadcast / logs
@dp.callback_query(
    F.data.in_(
        [
            "admin|view_feedbacks",
            "admin|view_works",
            "admin|stats",
            "admin|export",
            "admin|broadcast",
            "admin|logs",
        ]
    )
)
async def admin_actions(callback: CallbackQuery):
    if await deny_non_admin(callback, ADMINS):
        return

    user_id = callback.from_user.id
    cmd = callback.data

    # ----- Fikrlar -----
    if cmd == "admin|view_feedbacks":
        await display_items(
            bot, callback, feedbacks, "feedback",
            "📝 Hozircha hech qanday fikr yo'q.",
        )

    # ----- Ishlar -----
    elif cmd == "admin|view_works":
        await display_items(
            bot, callback, works, "work",
            "📂 Hozircha ish yo'q.",
        )

    # ----- Statistikalar -----
    elif cmd == "admin|stats":
        total = len(students)
        submitted_works = len(works)
        submitted_feedbacks = len(feedbacks)
        users_registered = len(registered_user_ids)
        msg = (
            "📊 Statistikalar:\n\n"
            f"Umumiy talabalar: {total}\n"
            f"Ish yuborganlar: {submitted_works}\n"
            f"Fikr yuborganlar: {submitted_feedbacks}\n"
            f"/start bosgan foydalanuvchilar: {users_registered}"
        )
        await callback.message.answer(msg, reply_markup=back_to_admin_panel_kb())

    # ----- Export CSV -----
    elif cmd == "admin|export":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "type",
                "id",
                "student",
                "content_or_fileid",
                "from_user",
                "timestamp",
                "grade",
            ]
        )
        for fb in feedbacks:
            writer.writerow(
                [
                    "feedback",
                    fb["id"],
                    fb["student"],
                    fb.get("content") or fb.get("file_id"),
                    fb.get("from_user_id"),
                    fb.get("timestamp"),
                    fb.get("grade", ""),
                ]
            )
        for wk in works:
            writer.writerow(
                [
                    "work",
                    wk["id"],
                    wk["student"],
                    wk.get("content") or wk.get("file_id"),
                    wk.get("from_user_id"),
                    wk.get("timestamp"),
                    wk.get("grade", ""),
                ]
            )
        output.seek(0)
        await bot.send_document(
            user_id,
            (io.BytesIO(output.getvalue().encode()), "export.csv"),
        )
        await callback.answer("📥 Export yuborildi.")
        log(f"admin {user_id} exported data")

    # ----- Broadcast -----
    elif cmd == "admin|broadcast":
        pending_actions[user_id] = {"action": "broadcast"}
        await callback.message.answer(
            "📣 Eslatma matnini yuboring — u /start bosgan foydalanuvchilarga jo'natiladi.",
            reply_markup=back_to_admin_panel_kb(),
        )
        log(f"admin {user_id} started broadcast")

    # ----- Logs -----
    elif cmd == "admin|logs":
        if not logs:
            await callback.message.answer(
                "📜 Hozircha log yo'q.",
                reply_markup=back_to_admin_panel_kb(),
            )
        else:
            text = "📜 Logs (oxirgi 100):\n\n" + "\n".join(
                [f"{t} — {e}" for t, e in logs[-100:]]
            )
            if len(text) > 4000:
                await bot.send_document(
                    user_id,
                    (io.BytesIO(text.encode()), "logs.txt"),
                )
            else:
                await callback.message.answer(
                    text, reply_markup=back_to_admin_panel_kb()
                )

    await callback.answer()


# Admin delete
@dp.callback_query(F.data.startswith("admin|del_feedback|"))
async def admin_del_feedback(callback: CallbackQuery):
    if await deny_non_admin(callback, ADMINS):
        return
    fb_id = int(callback.data.split("|")[-1])
    await delete_item(callback, feedbacks, fb_id, "feedback", log)


@dp.callback_query(F.data.startswith("admin|del_work|"))
async def admin_del_work(callback: CallbackQuery):
    if await deny_non_admin(callback, ADMINS):
        return
    wk_id = int(callback.data.split("|")[-1])
    await delete_item(callback, works, wk_id, "work", log)


# Admin grade
@dp.callback_query(F.data.startswith("admin|grade_work|"))
async def admin_grade_work(callback: CallbackQuery):
    if await deny_non_admin(callback, ADMINS):
        return
    wk_id = int(callback.data.split("|")[-1])
    await prompt_grade(callback, wk_id, "work", pending_actions)


@dp.callback_query(F.data.startswith("admin|grade_feedback|"))
async def admin_grade_feedback(callback: CallbackQuery):
    if await deny_non_admin(callback, ADMINS):
        return
    fb_id = int(callback.data.split("|")[-1])
    await prompt_grade(callback, fb_id, "feedback", pending_actions)


# Barcha xabarlar – pending_actions uchun
@dp.message()
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id

    # /start bo'lsa – alohida ishlov
    if message.text and message.text.startswith("/start"):
        await cmd_start(message)
        return

    # Pending action bormi?
    if user_id in pending_actions:
        action = pending_actions[user_id]
        a = action.get("action")

        # --- Broadcast ---
        if a == "broadcast" and user_id in ADMINS:
            text = message.text or ""
            if not text:
                await message.answer("❌ Iltimos matn yuboring.")
                return
            count = 0
            for uid in list(registered_user_ids):
                try:
                    await bot.send_message(
                        uid,
                        f"📣 Eslatma (admin):\n\n{text}",
                    )
                    count += 1
                except Exception:
                    pass
            await message.answer(f"📤 Eslatma yuborildi: {count} foydalanuvchiga.")
            log(f"admin {user_id} broadcast to {count} users")
            pending_actions.pop(user_id, None)
            return

        # --- Work baholash ---
        if a == "grade_work" and user_id in ADMINS:
            await handle_grade(message, works, action["work_id"], "work", log)
            pending_actions.pop(user_id, None)
            return

        # --- Feedback baholash ---
        if a == "grade_feedback" and user_id in ADMINS:
            await handle_grade(message, feedbacks, action["feedback_id"], "feedback", log)
            pending_actions.pop(user_id, None)
            return

        # --- Student feedback ---
        if a == "feedback":
            global _next_feedback_id
            student_name = action["student"]
            if message.text:
                fb = create_submission(
                    student_name, user_id, _next_feedback_id, "text",
                    content=message.text,
                )
                feedbacks.append(fb)
                _next_feedback_id += 1
                await message.answer("✅ Fikringiz qabul qilindi. Rahmat!")
                log(
                    f"user {user_id} submitted feedback #{fb['id']} for {student_name}"
                )
            else:
                await message.answer("❌ Fikr faqat matn yoki link bo'lishi mumkin.")
            pending_actions.pop(user_id, None)
            return

        # --- Student work ---
        if a == "work":
            global _next_work_id
            student_name = action["student"]
            result = await process_work_submission(
                message, student_name, works, _next_work_id, log
            )
            if result is not None:
                _next_work_id = result
            pending_actions.pop(user_id, None)
            return

    # Hech qanday pending bo'lmasa:
    await message.answer(
        "❓ Noma'lum xabar. /start tugmasini bosing yoki menyudan tanlang.",
        reply_markup=main_keyboard(),
    )


# ================== RUN BOT ==================

async def main():
    print("🤖 AIBOT ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    # FastAPI serverni alohida thread'da ishga tushiramiz
    threading.Thread(target=start_web, daemon=True).start()
    # Aiogram pollingni asosiy event loop'da ishlatamiz
    asyncio.run(main())
