"""Shared fixtures for aibot7424 tests."""

import os

# Set a valid-format token before importing main (aiogram validates token format)
os.environ.setdefault("TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz_012345")

import pytest

import main as bot_main


@pytest.fixture(autouse=True)
def reset_state():
    """Reset all mutable global state before each test."""
    bot_main.feedbacks.clear()
    bot_main.works.clear()
    bot_main.graded_students.clear()
    bot_main.registered_user_ids.clear()
    bot_main.pending_actions.clear()
    bot_main.logs.clear()
    bot_main._next_feedback_id = 1
    bot_main._next_work_id = 1
    yield
