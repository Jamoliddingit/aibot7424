"""Tests for utility/helper functions and data structures."""

from datetime import datetime

import main as bot_main


class TestLogFunction:
    def test_log_appends_entry(self):
        bot_main.log("test event")
        assert len(bot_main.logs) == 1
        ts, event = bot_main.logs[0]
        assert event == "test event"

    def test_log_timestamp_format(self):
        bot_main.log("event")
        ts, _ = bot_main.logs[0]
        # Timestamp should be parseable as ISO format (space separator)
        datetime.fromisoformat(ts)

    def test_log_multiple_entries(self):
        bot_main.log("first")
        bot_main.log("second")
        bot_main.log("third")
        assert len(bot_main.logs) == 3
        assert bot_main.logs[0][1] == "first"
        assert bot_main.logs[2][1] == "third"

    def test_log_with_special_characters(self):
        bot_main.log("user 123 did something & 'weird'")
        assert bot_main.logs[0][1] == "user 123 did something & 'weird'"

    def test_log_timestamp_contains_date(self):
        bot_main.log("timed event")
        ts, _ = bot_main.logs[0]
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in ts


class TestStudentsData:
    def test_students_list_not_empty(self):
        assert len(bot_main.students) > 0

    def test_students_are_strings(self):
        for student in bot_main.students:
            assert isinstance(student, str)

    def test_students_list_has_expected_count(self):
        assert len(bot_main.students) == 25

    def test_student_projects_keys_are_in_students(self):
        for name in bot_main.student_projects:
            assert name in bot_main.students


class TestAdmins:
    def test_admins_list_not_empty(self):
        assert len(bot_main.ADMINS) > 0

    def test_admins_are_integers(self):
        for admin_id in bot_main.ADMINS:
            assert isinstance(admin_id, int)
