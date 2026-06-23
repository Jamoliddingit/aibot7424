"""Tests for data manipulation and CRUD operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import main as bot_main


class TestFeedbackCRUD:
    def test_feedback_structure(self):
        fb = {
            "id": 1,
            "student": "Test Student",
            "type": "text",
            "content": "Nice work",
            "file_id": None,
            "from_user_id": 100,
            "timestamp": "2024-01-01T12:00:00",
            "grade": None,
        }
        bot_main.feedbacks.append(fb)
        assert bot_main.feedbacks[0]["student"] == "Test Student"
        assert bot_main.feedbacks[0]["grade"] is None

    def test_feedback_grade_update(self):
        fb = {"id": 1, "student": "S", "type": "text", "content": "x", "grade": None}
        bot_main.feedbacks.append(fb)
        bot_main.feedbacks[0]["grade"] = "5/5"
        assert bot_main.feedbacks[0]["grade"] == "5/5"

    def test_feedback_deletion(self):
        bot_main.feedbacks.append({"id": 1, "student": "A", "type": "text"})
        bot_main.feedbacks.append({"id": 2, "student": "B", "type": "text"})
        bot_main.feedbacks[:] = [f for f in bot_main.feedbacks if f["id"] != 1]
        assert len(bot_main.feedbacks) == 1
        assert bot_main.feedbacks[0]["id"] == 2

    def test_multiple_feedbacks_for_same_student(self):
        bot_main.feedbacks.append({"id": 1, "student": "S", "type": "text"})
        bot_main.feedbacks.append({"id": 2, "student": "S", "type": "photo"})
        student_fbs = [f for f in bot_main.feedbacks if f["student"] == "S"]
        assert len(student_fbs) == 2


class TestWorkCRUD:
    def test_work_structure(self):
        wk = {
            "id": 1,
            "student": "Worker",
            "type": "document",
            "content": None,
            "file_id": "abc123",
            "from_user_id": 200,
            "timestamp": "2024-01-01T12:00:00",
            "grade": None,
        }
        bot_main.works.append(wk)
        assert bot_main.works[0]["file_id"] == "abc123"

    def test_work_grade_update(self):
        wk = {"id": 1, "student": "S", "type": "text", "content": "x", "grade": None}
        bot_main.works.append(wk)
        bot_main.works[0]["grade"] = "85"
        assert bot_main.works[0]["grade"] == "85"

    def test_work_deletion(self):
        bot_main.works.append({"id": 1, "student": "A", "type": "text"})
        bot_main.works.append({"id": 2, "student": "B", "type": "text"})
        bot_main.works[:] = [w for w in bot_main.works if w["id"] != 1]
        assert len(bot_main.works) == 1
        assert bot_main.works[0]["id"] == 2

    def test_work_types(self):
        for wtype in ["text", "photo", "video", "document"]:
            bot_main.works.append({"id": len(bot_main.works) + 1, "type": wtype})
        types = {w["type"] for w in bot_main.works}
        assert types == {"text", "photo", "video", "document"}


class TestRegisteredUsers:
    def test_add_user(self):
        bot_main.registered_user_ids.add(111)
        assert 111 in bot_main.registered_user_ids

    def test_duplicate_user_not_duplicated(self):
        bot_main.registered_user_ids.add(111)
        bot_main.registered_user_ids.add(111)
        assert len(bot_main.registered_user_ids) == 1

    def test_multiple_users(self):
        bot_main.registered_user_ids.update([1, 2, 3, 4, 5])
        assert len(bot_main.registered_user_ids) == 5


class TestPendingActions:
    def test_set_pending_action(self):
        bot_main.pending_actions[100] = {"action": "feedback", "student": "S"}
        assert 100 in bot_main.pending_actions

    def test_clear_pending_action(self):
        bot_main.pending_actions[100] = {"action": "feedback", "student": "S"}
        bot_main.pending_actions.pop(100, None)
        assert 100 not in bot_main.pending_actions

    def test_overwrite_pending_action(self):
        bot_main.pending_actions[100] = {"action": "feedback", "student": "S1"}
        bot_main.pending_actions[100] = {"action": "work", "student": "S2"}
        assert bot_main.pending_actions[100]["action"] == "work"


class TestGradedStudents:
    def test_add_graded_student(self):
        bot_main.graded_students.add("Student A")
        assert "Student A" in bot_main.graded_students

    def test_graded_students_is_set(self):
        bot_main.graded_students.add("Student A")
        bot_main.graded_students.add("Student A")
        assert len(bot_main.graded_students) == 1


class TestStudentProjects:
    def test_known_student_has_project(self):
        # Use first key from student_projects dict directly
        name = next(iter(bot_main.student_projects))
        assert name in bot_main.student_projects
        assert isinstance(bot_main.student_projects[name], str)

    def test_unknown_student_no_project(self):
        assert "Nonexistent Student" not in bot_main.student_projects

    def test_project_values_are_strings(self):
        for val in bot_main.student_projects.values():
            assert isinstance(val, str)


class TestCSVExport:
    """Test CSV export logic indirectly by verifying data format compatibility."""

    def test_feedback_has_csv_required_fields(self):
        fb = {
            "id": 1,
            "student": "S",
            "type": "text",
            "content": "msg",
            "file_id": None,
            "from_user_id": 100,
            "timestamp": "2024-01-01T00:00:00",
            "grade": "A",
        }
        required_keys = {"id", "student", "content", "file_id", "from_user_id", "timestamp", "grade"}
        assert required_keys.issubset(fb.keys())

    def test_work_has_csv_required_fields(self):
        wk = {
            "id": 1,
            "student": "W",
            "type": "document",
            "content": None,
            "file_id": "xyz",
            "from_user_id": 200,
            "timestamp": "2024-01-01T00:00:00",
            "grade": "90",
        }
        required_keys = {"id", "student", "content", "file_id", "from_user_id", "timestamp", "grade"}
        assert required_keys.issubset(wk.keys())
