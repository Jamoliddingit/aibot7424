"""Shared utilities for aibot7424 – extracted from duplicated patterns in main.py."""

from datetime import datetime

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery


# ================== KEYBOARD HELPERS ==================


def make_back_kb(text: str, callback_data: str) -> InlineKeyboardMarkup:
    """Create a single-button 'back' keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=callback_data)]
        ]
    )


def make_item_admin_kb(item_id: int, item_type: str) -> InlineKeyboardMarkup:
    """Create delete/grade keyboard for an admin item view.

    item_type: 'feedback' or 'work'
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ O'chirish",
                    callback_data=f"admin|del_{item_type}|{item_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Baholash",
                    callback_data=f"admin|grade_{item_type}|{item_id}",
                )
            ],
        ]
    )


# ================== ADMIN GUARD ==================


def is_admin(user_id: int, admins: list[int]) -> bool:
    return user_id in admins


async def deny_non_admin(callback: CallbackQuery, admins: list[int]) -> bool:
    """Check admin access; send denial alert if not admin.

    Returns True if user is NOT admin (i.e. access denied).
    """
    if callback.from_user.id not in admins:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return True
    return False


# ================== SEND MEDIA ITEM ==================


async def send_media_item(bot, chat_id: int, item: dict, kb: InlineKeyboardMarkup):
    """Display a single feedback/work item to the admin.

    Sends the appropriate media (text/photo/video/document) followed by
    a message with the item keyboard.
    """
    label = f"#{item['id']}  {item['student']}"

    if item["type"] == "text":
        await bot.send_message(
            chat_id,
            f"{label}:\n{item['content']}",
            reply_markup=kb,
        )
    elif item["type"] == "photo":
        await bot.send_photo(
            chat_id,
            item["file_id"],
            caption=f"#{item['id']} {item['student']} yuborgan rasm",
        )
        await bot.send_message(chat_id, label, reply_markup=kb)
    elif item["type"] == "video":
        await bot.send_video(
            chat_id,
            item["file_id"],
            caption=f"#{item['id']} {item['student']} yuborgan video",
        )
        await bot.send_message(chat_id, label, reply_markup=kb)
    elif item["type"] == "document":
        await bot.send_document(
            chat_id,
            item["file_id"],
            caption=f"#{item['id']} {item['student']} yuborgan fayl",
        )
        await bot.send_message(chat_id, label, reply_markup=kb)


async def display_items(
    bot, callback: CallbackQuery, items: list[dict], item_type: str, empty_msg: str
):
    """Display a list of items (feedbacks or works) to the admin.

    item_type: 'feedback' or 'work' (used for callback_data construction).
    """
    admin_panel_kb = make_back_kb("⬅️ Admin panel", "admin_panel")

    if not items:
        await callback.message.answer(empty_msg, reply_markup=admin_panel_kb)
        return

    user_id = callback.from_user.id
    for item in items:
        kb = make_item_admin_kb(item["id"], item_type)
        await send_media_item(bot, user_id, item, kb)


# ================== DELETE ITEM ==================


async def delete_item(
    callback: CallbackQuery, items: list[dict], item_id: int, item_type: str, log_fn
):
    """Delete an item from a list by id and notify the admin.

    item_type: 'feedback' or 'work' (for display/logging).
    """
    admin_panel_kb = make_back_kb("⬅️ Admin panel", "admin_panel")
    user_id = callback.from_user.id

    for item in items:
        if item["id"] == item_id:
            items.remove(item)
            type_label = "Feedback" if item_type == "feedback" else "Ish"
            await callback.message.answer(
                f"✅ {type_label} #{item_id} o'chirildi (talaba: {item['student']}).",
                reply_markup=admin_panel_kb,
            )
            log_fn(f"admin {user_id} deleted {item_type} {item_id}")
            break
    await callback.answer()


# ================== GRADE ITEM ==================


async def prompt_grade(
    callback: CallbackQuery, item_id: int, item_type: str, pending_actions: dict
):
    """Ask admin to enter a grade for an item."""
    admin_panel_kb = make_back_kb("⬅️ Admin panel", "admin_panel")
    user_id = callback.from_user.id
    id_key = "feedback_id" if item_type == "feedback" else "work_id"

    pending_actions[user_id] = {"action": f"grade_{item_type}", id_key: item_id}

    type_label = "Feedback" if item_type == "feedback" else "Work"
    await callback.message.answer(
        f"✍️ {type_label} #{item_id} uchun bahoni yuboring (masalan: 85 yoki A):",
        reply_markup=admin_panel_kb,
    )
    await callback.answer()


async def handle_grade(
    message: types.Message, items: list[dict], item_id: int, item_type: str, log_fn
):
    """Process a grade submission from the admin."""
    user_id = message.from_user.id
    score = (message.text or "").strip()
    type_label = "Feedback" if item_type == "feedback" else "Work"

    for item in items:
        if item["id"] == item_id:
            item["grade"] = score
            await message.answer(f"✅ {type_label} #{item_id} baholandi: {score}")
            log_fn(f"admin {user_id} graded {item_type} {item_id} => {score}")
            break


# ================== SUBMISSION HELPERS ==================


def create_submission(
    student_name: str,
    user_id: int,
    next_id: int,
    msg_type: str,
    content: str | None = None,
    file_id: str | None = None,
) -> dict:
    """Create a standardized submission dict (for works or feedbacks)."""
    return {
        "id": next_id,
        "student": student_name,
        "type": msg_type,
        "content": content,
        "file_id": file_id,
        "from_user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "grade": None,
    }


async def process_work_submission(
    message: types.Message, student_name: str, works: list, next_id: int, log_fn
) -> int | None:
    """Handle a work submission message. Returns new next_id, or None if invalid.

    Supports text, photo, video, and document messages.
    """
    user_id = message.from_user.id
    msg_type = None
    content = None
    file_id = None
    ack_msg = None

    if message.text:
        msg_type = "text"
        content = message.text
        ack_msg = "✅ Ish (text/link) qabul qilindi. Rahmat!"
    elif message.photo:
        msg_type = "photo"
        file_id = message.photo[-1].file_id
        ack_msg = "✅ Rasm qabul qilindi. Rahmat!"
    elif message.video:
        msg_type = "video"
        file_id = message.video.file_id
        ack_msg = "✅ Video qabul qilindi. Rahmat!"
    elif message.document:
        msg_type = "document"
        file_id = message.document.file_id
        ack_msg = "✅ Fayl qabul qilindi. Rahmat!"
    else:
        await message.answer(
            "❌ Bu turdagi xabar qabul qilinmaydi. Iltimos fayl, rasm, video yoki link yuboring."
        )
        return None

    wk = create_submission(student_name, user_id, next_id, msg_type, content, file_id)
    works.append(wk)
    await message.answer(ack_msg)
    log_fn(f"user {user_id} submitted work #{wk['id']} for {student_name} ({msg_type})")
    return next_id + 1
