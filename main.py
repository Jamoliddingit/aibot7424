import asyncio
import logging
import os
import csv
import io
import sys
from datetime import datetime
import threading

from fastapi import FastAPI
import uvicorn

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

logger = logging.getLogger(__name__)

# ================== CONFIG ==================
# Render’da TOKEN env var bo‘ladi
TOKEN = os.getenv("TOKEN", "")
if not TOKEN:
    logger.critical("TOKEN environment variable is not set. Exiting.")
    sys.exit(1)

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
    FastAPI serverni alohida thread’da ishga tushiramiz.
    Render 'PORT' env var beradi, bo‘lmasa 10000 ni olamiz.
    """
    raw_port = os.getenv("PORT", "10000")
    try:
        port = int(raw_port)
    except ValueError:
        logger.error("Invalid PORT value '%s', falling back to 10000", raw_port)
        port = 10000
    uvicorn.run(app, host="0.0.0.0", port=port)

# ================== DATA STORES ==================

students = [
    "Abdullayev Ulug‘bek O‘tkir o‘g‘li",
    "Abdurasulov Xondamir Nozimjon o‘g‘li",
    "Abdusalamov Suxrob Tulqin o‘g‘li",
    "Absalamova Zilolaxon Ergashxo‘ja qizi",
    "Ahmadaliyev Muhammadjon Abduxalil o‘g‘li",
    "Allayev Yoqubjon Rayimjon o‘g‘li",
    "Boxodirov Nazarbek Qobuljon o‘g‘li",
    "Davlatboyev Bunyod Rashid o‘g‘li",
    "Davlatova Sevinch Faxriddin qizi",
    "Doniyorbekov Rashidbek Xurshidbek o‘g‘li",
    "Hakimov Oybek Obid o‘g‘li",
    "Ismoilov Jamoliddin Kamoliddin o‘g‘li",
    "Jabborqulov Otabek Ulug‘bek o‘g‘li",
    "Maxmudova Zulayho Jumanazar qizi",
    "Murodullayev Javohir Akmal o‘g‘li",
    "Ongarbaev Quralbay Baxadírovich",
    "Ozodova Malikaxon Ravshan qizi",
    "Pulatov Dilshod Dilmurod o‘g‘li",
    "Qayumjonov Mahmudjon Mahkamjon o‘g‘li",
    "Saatbayev Sherzod Farxadovich",
    "Sheraliyev O‘tkirbek Alisher o‘g‘li",
    "Sobirqulov Baxodir Zoir o‘g‘li",
    "Sodiqov Xudoyberdi Ato o‘g‘li",
    "Suyundiqov Abdulazizjon Alisher o‘g‘li",
    "Vaxobov Ismoil Vaxob o‘g‘li",
]

student_projects = {
    "Davlatboyev Bunyod Rashid o‘g‘li": "Bot: @all_animetopBot",
    "Vaxobov Ismoil Vaxob o‘g‘li": "Bot: @minimarket_probot",
    "Absalamova Zilolaxon Ergashxo‘ja qizi": "Sayt: https://e-commerce-one-omega-68.vercel.app/",
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
                text="📋 Talabalar ro‘yxati",
                callback_data="royhat"
            )],
            [InlineKeyboardButton(
                text="🛠 Admin panel",
                callback_data="admin_panel"
            )],
        ]
    )


def back_to_start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Ortga", callback_data="back|start")]
        ]
    )


def back_to_royhat_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Ortga", callback_data="back|royhat")]
        ]
    )


def back_to_admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin_panel")]
        ]
    )


# ================== HANDLERS ==================

# /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    registered_user_ids.add(message.from_user.id)
    await message.answer(
        "👋 <b>Salom!</b>\nQuyida loyihani ko‘rish yoki talabalar ro‘yxatini ochish mumkin 👇",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )
    log(f"/start from {message.from_user.id}")


# Talabalar ro‘yxati
@dp.callback_query(F.data == "royhat")
async def show_students(callback: CallbackQuery):
    rows = []
    for name in students:
        rows.append([InlineKeyboardButton(text=name, callback_data=f"student|{name}")])
    rows.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="back|start")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await callback.message.answer(
        "📋 <b>Talabalar ro‘yxati:</b>",
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
                text="⬅️ Ortga (ro‘yxat)",
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
    parts = callback.data.split("|", 2)
    if len(parts) < 3:
        logger.warning("Malformed action callback data: %s", callback.data)
        await callback.answer("Xatolik: noto\u2018g\u2018ri ma\u2018lumot.", show_alert=True)
        return
    _, action, name = parts
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
    user_id = callback.from_user.id
    if user_id not in ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📝 Fikrlarni ko‘rish va boshqarish",
                callback_data="admin|view_feedbacks"
            )],
            [InlineKeyboardButton(
                text="📂 Ishlarni ko‘rish va boshqarish",
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
    user_id = callback.from_user.id
    if user_id not in ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    cmd = callback.data
    # ----- Fikrlar -----
    if cmd == "admin|view_feedbacks":
        if not feedbacks:
            await callback.message.answer(
                "📝 Hozircha hech qanday fikr yo‘q.",
                reply_markup=back_to_admin_panel_kb(),
            )
        else:
            for fb in feedbacks:
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="❌ O‘chirish",
                                callback_data=f"admin|del_feedback|{fb['id']}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="📊 Baholash",
                                callback_data=f"admin|grade_feedback|{fb['id']}",
                            )
                        ],
                    ]
                )
                try:
                    if fb["type"] == "text":
                        await callback.message.answer(
                            f"#{fb['id']}  {fb['student']}:\n{fb['content']}",
                            reply_markup=kb,
                        )
                    elif fb["type"] == "photo":
                        await bot.send_photo(
                            user_id,
                            fb["file_id"],
                            caption=f"#{fb['id']} {fb['student']} yuborgan rasm",
                        )
                        await callback.message.answer(
                            f"#{fb['id']}  {fb['student']}", reply_markup=kb
                        )
                    elif fb["type"] == "video":
                        await bot.send_video(
                            user_id,
                            fb["file_id"],
                            caption=f"#{fb['id']} {fb['student']} yuborgan video",
                        )
                        await callback.message.answer(
                            f"#{fb['id']}  {fb['student']}", reply_markup=kb
                        )
                    elif fb["type"] == "document":
                        await bot.send_document(
                            user_id,
                            fb["file_id"],
                            caption=f"#{fb['id']} {fb['student']} yuborgan fayl",
                        )
                        await callback.message.answer(
                            f"#{fb['id']}  {fb['student']}", reply_markup=kb
                        )
                except Exception:
                    logger.error(
                        "Failed to send feedback #%s to admin %s",
                        fb["id"], user_id, exc_info=True,
                    )
                    await callback.message.answer(
                        f"⚠️ Feedback #{fb['id']} yuborishda xatolik.",
                        reply_markup=kb,
                    )

    # ----- Ishlar -----
    elif cmd == "admin|view_works":
        if not works:
            await callback.message.answer(
                "📂 Hozircha ish yo‘q.",
                reply_markup=back_to_admin_panel_kb(),
            )
        else:
            for wk in works:
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="❌ O‘chirish",
                                callback_data=f"admin|del_work|{wk['id']}",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="📊 Baholash",
                                callback_data=f"admin|grade_work|{wk['id']}",
                            )
                        ],
                    ]
                )
                try:
                    if wk["type"] == "text":
                        await callback.message.answer(
                            f"#{wk['id']}  {wk['student']}:\n{wk['content']}",
                            reply_markup=kb,
                        )
                    elif wk["type"] == "photo":
                        await bot.send_photo(
                            user_id,
                            wk["file_id"],
                            caption=f"#{wk['id']} {wk['student']} yuborgan rasm",
                        )
                        await callback.message.answer(
                            f"#{wk['id']}  {wk['student']}", reply_markup=kb
                        )
                    elif wk["type"] == "video":
                        await bot.send_video(
                            user_id,
                            wk["file_id"],
                            caption=f"#{wk['id']} {wk['student']} yuborgan video",
                        )
                        await callback.message.answer(
                            f"#{wk['id']}  {wk['student']}", reply_markup=kb
                        )
                    elif wk["type"] == "document":
                        await bot.send_document(
                            user_id,
                            wk["file_id"],
                            caption=f"#{wk['id']} {wk['student']} yuborgan fayl",
                        )
                        await callback.message.answer(
                            f"#{wk['id']}  {wk['student']}", reply_markup=kb
                        )
                except Exception:
                    logger.error(
                        "Failed to send work #%s to admin %s",
                        wk["id"], user_id, exc_info=True,
                    )
                    await callback.message.answer(
                        f"⚠️ Ish #{wk['id']} yuborishda xatolik.",
                        reply_markup=kb,
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
        try:
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
        except Exception:
            logger.error("CSV export failed for admin %s", user_id, exc_info=True)
            await callback.message.answer(
                "❌ Export paytida xatolik yuz berdi.",
                reply_markup=back_to_admin_panel_kb(),
            )

    # ----- Broadcast -----
    elif cmd == "admin|broadcast":
        pending_actions[user_id] = {"action": "broadcast"}
        await callback.message.answer(
            "📣 Eslatma matnini yuboring — u /start bosgan foydalanuvchilarga jo‘natiladi.",
            reply_markup=back_to_admin_panel_kb(),
        )
        log(f"admin {user_id} started broadcast")

    # ----- Logs -----
    elif cmd == "admin|logs":
        if not logs:
            await callback.message.answer(
                "📜 Hozircha log yo‘q.",
                reply_markup=back_to_admin_panel_kb(),
            )
        else:
            text = "📜 Logs (oxirgi 100):\n\n" + "\n".join(
                [f"{t} — {e}" for t, e in logs[-100:]]
            )
            try:
                if len(text) > 4000:
                    await bot.send_document(
                        user_id,
                        (io.BytesIO(text.encode()), "logs.txt"),
                    )
                else:
                    await callback.message.answer(
                        text, reply_markup=back_to_admin_panel_kb()
                    )
            except Exception:
                logger.error("Failed to send logs to admin %s", user_id, exc_info=True)
                await callback.message.answer(
                    "❌ Loglarni yuborishda xatolik yuz berdi.",
                    reply_markup=back_to_admin_panel_kb(),
                )

    await callback.answer()


# Admin delete / grade
@dp.callback_query(F.data.startswith("admin|del_feedback|"))
async def admin_del_feedback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return
    try:
        fb_id = int(callback.data.split("|")[-1])
    except ValueError:
        logger.warning("Invalid feedback id in callback: %s", callback.data)
        await callback.answer("Xatolik: noto‘g‘ri ID.", show_alert=True)
        return
    found = False
    for fb in feedbacks:
        if fb["id"] == fb_id:
            feedbacks.remove(fb)
            await callback.message.answer(
                f"✅ Feedback #{fb_id} o‘chirildi (talaba: {fb['student']}).",
                reply_markup=back_to_admin_panel_kb(),
            )
            log(f"admin {user_id} deleted feedback {fb_id}")
            found = True
            break
    if not found:
        await callback.message.answer(
            f"⚠️ Feedback #{fb_id} topilmadi.",
            reply_markup=back_to_admin_panel_kb(),
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin|del_work|"))
async def admin_del_work(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return
    try:
        wk_id = int(callback.data.split("|")[-1])
    except ValueError:
        logger.warning("Invalid work id in callback: %s", callback.data)
        await callback.answer("Xatolik: noto‘g‘ri ID.", show_alert=True)
        return
    found = False
    for wk in works:
        if wk["id"] == wk_id:
            works.remove(wk)
            await callback.message.answer(
                f"✅ Ish #{wk_id} o‘chirildi (talaba: {wk['student']}).",
                reply_markup=back_to_admin_panel_kb(),
            )
            log(f"admin {user_id} deleted work {wk_id}")
            found = True
            break
    if not found:
        await callback.message.answer(
            f"⚠️ Ish #{wk_id} topilmadi.",
            reply_markup=back_to_admin_panel_kb(),
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin|grade_work|"))
async def admin_grade_work(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return
    try:
        wk_id = int(callback.data.split("|")[-1])
    except ValueError:
        logger.warning("Invalid work id in callback: %s", callback.data)
        await callback.answer("Xatolik: noto‘g‘ri ID.", show_alert=True)
        return
    pending_actions[user_id] = {"action": "grade_work", "work_id": wk_id}
    await callback.message.answer(
        f"✍️ Work #{wk_id} uchun bahoni yuboring (masalan: 85 yoki A):",
        reply_markup=back_to_admin_panel_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin|grade_feedback|"))
async def admin_grade_feedback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return
    try:
        fb_id = int(callback.data.split("|")[-1])
    except ValueError:
        logger.warning("Invalid feedback id in callback: %s", callback.data)
        await callback.answer("Xatolik: noto‘g‘ri ID.", show_alert=True)
        return
    pending_actions[user_id] = {"action": "grade_feedback", "feedback_id": fb_id}
    await callback.message.answer(
        f"✍️ Feedback #{fb_id} uchun bahoni yuboring (masalan: 5/5 yoki A):",
        reply_markup=back_to_admin_panel_kb(),
    )
    await callback.answer()


# Barcha xabarlar – pending_actions uchun
@dp.message()
async def handle_all_messages(message: types.Message):
    user_id = message.from_user.id

    # /start bo‘lsa – alohida ishlov
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
            failed = 0
            for uid in list(registered_user_ids):
                try:
                    await bot.send_message(
                        uid,
                        f"📣 Eslatma (admin):\n\n{text}",
                    )
                    count += 1
                except Exception:
                    failed += 1
                    logger.warning("Failed to send broadcast to user %s", uid, exc_info=True)
            result_msg = f"📤 Eslatma yuborildi: {count} foydalanuvchiga."
            if failed:
                result_msg += f"\n⚠️ {failed} foydalanuvchiga yuborib bo‘lmadi."
            await message.answer(result_msg)
            log(f"admin {user_id} broadcast to {count} users, {failed} failed")
            pending_actions.pop(user_id, None)
            return

        # --- Work baholash ---
        if a == "grade_work" and user_id in ADMINS:
            score = (message.text or "").strip()
            if not score:
                await message.answer("❌ Iltimos baho matnini yuboring.")
                return
            wk_id = action["work_id"]
            found = False
            for wk in works:
                if wk["id"] == wk_id:
                    wk["grade"] = score
                    await message.answer(f"✅ Work #{wk_id} baholandi: {score}")
                    log(f"admin {user_id} graded work {wk_id} => {score}")
                    found = True
                    break
            if not found:
                await message.answer(
                    f"⚠️ Work #{wk_id} topilmadi (o‘chirilgan bo‘lishi mumkin).",
                    reply_markup=back_to_admin_panel_kb(),
                )
            pending_actions.pop(user_id, None)
            return

        # --- Feedback baholash ---
        if a == "grade_feedback" and user_id in ADMINS:
            score = (message.text or "").strip()
            if not score:
                await message.answer("❌ Iltimos baho matnini yuboring.")
                return
            fb_id = action["feedback_id"]
            found = False
            for fb in feedbacks:
                if fb["id"] == fb_id:
                    fb["grade"] = score
                    await message.answer(f"✅ Feedback #{fb_id} baholandi: {score}")
                    log(f"admin {user_id} graded feedback {fb_id} => {score}")
                    found = True
                    break
            if not found:
                await message.answer(
                    f"⚠️ Feedback #{fb_id} topilmadi (o‘chirilgan bo‘lishi mumkin).",
                    reply_markup=back_to_admin_panel_kb(),
                )
            pending_actions.pop(user_id, None)
            return

        # --- Student feedback ---
        if a == "feedback":
            global _next_feedback_id
            student_name = action["student"]
            if message.text:
                fb = {
                    "id": _next_feedback_id,
                    "student": student_name,
                    "type": "text",
                    "content": message.text,
                    "file_id": None,
                    "from_user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "grade": None,
                }
                feedbacks.append(fb)
                _next_feedback_id += 1
                await message.answer("✅ Fikringiz qabul qilindi. Rahmat!")
                log(
                    f"user {user_id} submitted feedback #{fb['id']} for {student_name}"
                )
            else:
                await message.answer("❌ Fikr faqat matn yoki link bo‘lishi mumkin.")
            pending_actions.pop(user_id, None)
            return

        # --- Student work ---
        if a == "work":
            global _next_work_id
            student_name = action["student"]
            wk = {
                "id": _next_work_id,
                "student": student_name,
                "type": None,
                "content": None,
                "file_id": None,
                "from_user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "grade": None,
            }

            if message.text:
                wk["type"] = "text"
                wk["content"] = message.text
                works.append(wk)
                _next_work_id += 1
                await message.answer("✅ Ish (text/link) qabul qilindi. Rahmat!")
                log(
                    f"user {user_id} submitted work #{wk['id']} for {student_name} (text)"
                )
            elif message.photo:
                wk["type"] = "photo"
                wk["file_id"] = message.photo[-1].file_id
                works.append(wk)
                _next_work_id += 1
                await message.answer("✅ Rasm qabul qilindi. Rahmat!")
                log(
                    f"user {user_id} submitted work #{wk['id']} for {student_name} (photo)"
                )
            elif message.video:
                wk["type"] = "video"
                wk["file_id"] = message.video.file_id
                works.append(wk)
                _next_work_id += 1
                await message.answer("✅ Video qabul qilindi. Rahmat!")
                log(
                    f"user {user_id} submitted work #{wk['id']} for {student_name} (video)"
                )
            elif message.document:
                wk["type"] = "document"
                wk["file_id"] = message.document.file_id
                works.append(wk)
                _next_work_id += 1
                await message.answer("✅ Fayl qabul qilindi. Rahmat!")
                log(
                    f"user {user_id} submitted work #{wk['id']} for {student_name} (document)"
                )
            else:
                await message.answer(
                    "❌ Bu turdagi xabar qabul qilinmaydi. Iltimos fayl, rasm, video yoki link yuboring."
                )

            pending_actions.pop(user_id, None)
            return

    # Hech qanday pending bo‘lmasa:
    await message.answer(
        "❓ Noma'lum xabar. /start tugmasini bosing yoki menyudan tanlang.",
        reply_markup=main_keyboard(),
    )


# ================== RUN BOT ==================

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("AIBOT ishga tushmoqda...")
    try:
        await dp.start_polling(bot)
    except Exception:
        logger.critical("Bot polling failed", exc_info=True)
        raise


if __name__ == "__main__":
    # FastAPI serverni alohida thread’da ishga tushiramiz
    threading.Thread(target=start_web, daemon=True).start()
    # Aiogram pollingni asosiy event loop’da ishlatamiz
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception:
        logger.critical("Unexpected error at startup", exc_info=True)
        sys.exit(1)
