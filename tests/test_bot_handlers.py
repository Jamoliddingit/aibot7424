"""Tests for bot handler logic using mocks."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import main as bot_main


def make_mock_message(user_id=100, text=None, photo=None, video=None, document=None):
    """Create a mock Message object."""
    msg = AsyncMock()
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.text = text
    msg.photo = photo
    msg.video = video
    msg.document = document
    msg.answer = AsyncMock()
    return msg


def make_mock_callback(user_id=100, data=""):
    """Create a mock CallbackQuery object."""
    cb = AsyncMock()
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.data = data
    cb.message = make_mock_message(user_id=user_id)
    cb.answer = AsyncMock()
    return cb


class TestCmdStart:
    @pytest.mark.asyncio
    async def test_registers_user(self):
        msg = make_mock_message(user_id=12345, text="/start")
        await bot_main.cmd_start(msg)
        assert 12345 in bot_main.registered_user_ids

    @pytest.mark.asyncio
    async def test_sends_welcome_message(self):
        msg = make_mock_message(user_id=12345, text="/start")
        await bot_main.cmd_start(msg)
        msg.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_logs_start_event(self):
        msg = make_mock_message(user_id=42, text="/start")
        await bot_main.cmd_start(msg)
        assert any("42" in entry[1] and "/start" in entry[1] for entry in bot_main.logs)


class TestStartAction:
    @pytest.mark.asyncio
    async def test_feedback_sets_pending_action(self):
        cb = make_mock_callback(user_id=200, data="action|feedback|Test Student")
        await bot_main.start_action(cb)
        assert 200 in bot_main.pending_actions
        assert bot_main.pending_actions[200]["action"] == "feedback"
        assert bot_main.pending_actions[200]["student"] == "Test Student"

    @pytest.mark.asyncio
    async def test_work_sets_pending_action(self):
        cb = make_mock_callback(user_id=300, data="action|work|Another Student")
        await bot_main.start_action(cb)
        assert 300 in bot_main.pending_actions
        assert bot_main.pending_actions[300]["action"] == "work"
        assert bot_main.pending_actions[300]["student"] == "Another Student"

    @pytest.mark.asyncio
    async def test_feedback_logs_event(self):
        cb = make_mock_callback(user_id=200, data="action|feedback|Test Student")
        await bot_main.start_action(cb)
        assert any("feedback" in entry[1] for entry in bot_main.logs)


class TestAdminPanel:
    @pytest.mark.asyncio
    async def test_non_admin_gets_rejected(self):
        cb = make_mock_callback(user_id=99999, data="admin_panel")
        await bot_main.admin_panel(cb)
        cb.answer.assert_called_with("❌ Siz admin emassiz!", show_alert=True)

    @pytest.mark.asyncio
    async def test_admin_gets_panel(self):
        admin_id = bot_main.ADMINS[0]
        cb = make_mock_callback(user_id=admin_id, data="admin_panel")
        await bot_main.admin_panel(cb)
        cb.message.answer.assert_called_once()


class TestAdminDeleteFeedback:
    @pytest.mark.asyncio
    async def test_non_admin_cannot_delete(self):
        bot_main.feedbacks.append({"id": 1, "student": "X", "type": "text"})
        cb = make_mock_callback(user_id=99999, data="admin|del_feedback|1")
        await bot_main.admin_del_feedback(cb)
        assert len(bot_main.feedbacks) == 1

    @pytest.mark.asyncio
    async def test_admin_deletes_feedback(self):
        admin_id = bot_main.ADMINS[0]
        bot_main.feedbacks.append({"id": 1, "student": "X", "type": "text"})
        cb = make_mock_callback(user_id=admin_id, data="admin|del_feedback|1")
        await bot_main.admin_del_feedback(cb)
        assert len(bot_main.feedbacks) == 0

    @pytest.mark.asyncio
    async def test_admin_delete_logs_event(self):
        admin_id = bot_main.ADMINS[0]
        bot_main.feedbacks.append({"id": 5, "student": "Y", "type": "text"})
        cb = make_mock_callback(user_id=admin_id, data="admin|del_feedback|5")
        await bot_main.admin_del_feedback(cb)
        assert any("deleted feedback 5" in entry[1] for entry in bot_main.logs)


class TestAdminDeleteWork:
    @pytest.mark.asyncio
    async def test_non_admin_cannot_delete(self):
        bot_main.works.append({"id": 1, "student": "X", "type": "text"})
        cb = make_mock_callback(user_id=99999, data="admin|del_work|1")
        await bot_main.admin_del_work(cb)
        assert len(bot_main.works) == 1

    @pytest.mark.asyncio
    async def test_admin_deletes_work(self):
        admin_id = bot_main.ADMINS[0]
        bot_main.works.append({"id": 1, "student": "X", "type": "text"})
        cb = make_mock_callback(user_id=admin_id, data="admin|del_work|1")
        await bot_main.admin_del_work(cb)
        assert len(bot_main.works) == 0


class TestAdminGradeWork:
    @pytest.mark.asyncio
    async def test_non_admin_cannot_grade(self):
        cb = make_mock_callback(user_id=99999, data="admin|grade_work|1")
        await bot_main.admin_grade_work(cb)
        assert 99999 not in bot_main.pending_actions

    @pytest.mark.asyncio
    async def test_admin_sets_pending_grade(self):
        admin_id = bot_main.ADMINS[0]
        cb = make_mock_callback(user_id=admin_id, data="admin|grade_work|3")
        await bot_main.admin_grade_work(cb)
        assert bot_main.pending_actions[admin_id]["action"] == "grade_work"
        assert bot_main.pending_actions[admin_id]["work_id"] == 3


class TestAdminGradeFeedback:
    @pytest.mark.asyncio
    async def test_non_admin_cannot_grade(self):
        cb = make_mock_callback(user_id=99999, data="admin|grade_feedback|1")
        await bot_main.admin_grade_feedback(cb)
        assert 99999 not in bot_main.pending_actions

    @pytest.mark.asyncio
    async def test_admin_sets_pending_grade(self):
        admin_id = bot_main.ADMINS[0]
        cb = make_mock_callback(user_id=admin_id, data="admin|grade_feedback|7")
        await bot_main.admin_grade_feedback(cb)
        assert bot_main.pending_actions[admin_id]["action"] == "grade_feedback"
        assert bot_main.pending_actions[admin_id]["feedback_id"] == 7


class TestHandleAllMessages:
    @pytest.mark.asyncio
    async def test_unknown_message_gets_default_reply(self):
        msg = make_mock_message(user_id=500, text="random text")
        await bot_main.handle_all_messages(msg)
        msg.answer.assert_called_once()
        call_args = msg.answer.call_args
        assert "Noma'lum xabar" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_feedback_text_submission(self):
        bot_main.pending_actions[500] = {"action": "feedback", "student": "Test Student"}
        msg = make_mock_message(user_id=500, text="Great work!")
        await bot_main.handle_all_messages(msg)
        assert len(bot_main.feedbacks) == 1
        assert bot_main.feedbacks[0]["content"] == "Great work!"
        assert bot_main.feedbacks[0]["student"] == "Test Student"
        assert bot_main.feedbacks[0]["type"] == "text"
        assert 500 not in bot_main.pending_actions

    @pytest.mark.asyncio
    async def test_feedback_no_text_rejected(self):
        bot_main.pending_actions[500] = {"action": "feedback", "student": "Test Student"}
        msg = make_mock_message(user_id=500, text=None)
        await bot_main.handle_all_messages(msg)
        assert len(bot_main.feedbacks) == 0

    @pytest.mark.asyncio
    async def test_work_text_submission(self):
        bot_main.pending_actions[600] = {"action": "work", "student": "Worker"}
        msg = make_mock_message(user_id=600, text="https://example.com/project")
        await bot_main.handle_all_messages(msg)
        assert len(bot_main.works) == 1
        assert bot_main.works[0]["content"] == "https://example.com/project"
        assert bot_main.works[0]["type"] == "text"
        assert 600 not in bot_main.pending_actions

    @pytest.mark.asyncio
    async def test_work_photo_submission(self):
        bot_main.pending_actions[600] = {"action": "work", "student": "Worker"}
        photo = MagicMock()
        photo.file_id = "photo_file_123"
        msg = make_mock_message(user_id=600, text=None, photo=[photo])
        await bot_main.handle_all_messages(msg)
        assert len(bot_main.works) == 1
        assert bot_main.works[0]["type"] == "photo"
        assert bot_main.works[0]["file_id"] == "photo_file_123"

    @pytest.mark.asyncio
    async def test_work_video_submission(self):
        bot_main.pending_actions[600] = {"action": "work", "student": "Worker"}
        video = MagicMock()
        video.file_id = "video_file_456"
        msg = make_mock_message(user_id=600, text=None, video=video)
        await bot_main.handle_all_messages(msg)
        assert len(bot_main.works) == 1
        assert bot_main.works[0]["type"] == "video"
        assert bot_main.works[0]["file_id"] == "video_file_456"

    @pytest.mark.asyncio
    async def test_work_document_submission(self):
        bot_main.pending_actions[600] = {"action": "work", "student": "Worker"}
        doc = MagicMock()
        doc.file_id = "doc_file_789"
        msg = make_mock_message(user_id=600, text=None, document=doc)
        await bot_main.handle_all_messages(msg)
        assert len(bot_main.works) == 1
        assert bot_main.works[0]["type"] == "document"
        assert bot_main.works[0]["file_id"] == "doc_file_789"

    @pytest.mark.asyncio
    async def test_work_unsupported_type_rejected(self):
        bot_main.pending_actions[600] = {"action": "work", "student": "Worker"}
        msg = make_mock_message(user_id=600, text=None)
        await bot_main.handle_all_messages(msg)
        assert len(bot_main.works) == 0

    @pytest.mark.asyncio
    @patch("main.bot")
    async def test_broadcast_sends_to_registered_users(self, mock_bot):
        admin_id = bot_main.ADMINS[0]
        bot_main.pending_actions[admin_id] = {"action": "broadcast"}
        bot_main.registered_user_ids.update([1001, 1002, 1003])
        mock_bot.send_message = AsyncMock()

        msg = make_mock_message(user_id=admin_id, text="Hello everyone!")
        await bot_main.handle_all_messages(msg)
        assert mock_bot.send_message.call_count == 3
        assert admin_id not in bot_main.pending_actions

    @pytest.mark.asyncio
    async def test_grade_work_updates_score(self):
        admin_id = bot_main.ADMINS[0]
        bot_main.works.append({
            "id": 1, "student": "S", "type": "text",
            "content": "x", "grade": None,
        })
        bot_main.pending_actions[admin_id] = {"action": "grade_work", "work_id": 1}
        msg = make_mock_message(user_id=admin_id, text="95")
        await bot_main.handle_all_messages(msg)
        assert bot_main.works[0]["grade"] == "95"
        assert admin_id not in bot_main.pending_actions

    @pytest.mark.asyncio
    async def test_grade_feedback_updates_score(self):
        admin_id = bot_main.ADMINS[0]
        bot_main.feedbacks.append({
            "id": 2, "student": "S", "type": "text",
            "content": "good", "grade": None,
        })
        bot_main.pending_actions[admin_id] = {"action": "grade_feedback", "feedback_id": 2}
        msg = make_mock_message(user_id=admin_id, text="A+")
        await bot_main.handle_all_messages(msg)
        assert bot_main.feedbacks[0]["grade"] == "A+"
        assert admin_id not in bot_main.pending_actions

    @pytest.mark.asyncio
    async def test_feedback_increments_id(self):
        bot_main.pending_actions[500] = {"action": "feedback", "student": "S1"}
        msg = make_mock_message(user_id=500, text="First")
        await bot_main.handle_all_messages(msg)

        bot_main.pending_actions[501] = {"action": "feedback", "student": "S2"}
        msg2 = make_mock_message(user_id=501, text="Second")
        await bot_main.handle_all_messages(msg2)

        assert bot_main.feedbacks[0]["id"] == 1
        assert bot_main.feedbacks[1]["id"] == 2

    @pytest.mark.asyncio
    async def test_work_increments_id(self):
        bot_main.pending_actions[600] = {"action": "work", "student": "W1"}
        msg = make_mock_message(user_id=600, text="link1")
        await bot_main.handle_all_messages(msg)

        bot_main.pending_actions[601] = {"action": "work", "student": "W2"}
        msg2 = make_mock_message(user_id=601, text="link2")
        await bot_main.handle_all_messages(msg2)

        assert bot_main.works[0]["id"] == 1
        assert bot_main.works[1]["id"] == 2
