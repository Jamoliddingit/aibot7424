"""Tests for keyboard builder functions."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from main import (
    main_keyboard,
    back_to_start_kb,
    back_to_royhat_kb,
    back_to_admin_panel_kb,
)


class TestMainKeyboard:
    def test_returns_inline_keyboard_markup(self):
        kb = main_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_has_three_rows(self):
        kb = main_keyboard()
        assert len(kb.inline_keyboard) == 3

    def test_first_button_is_url_button(self):
        kb = main_keyboard()
        btn = kb.inline_keyboard[0][0]
        assert btn.url == "https://studentlar.netlify.app/"

    def test_second_button_has_royhat_callback(self):
        kb = main_keyboard()
        btn = kb.inline_keyboard[1][0]
        assert btn.callback_data == "royhat"

    def test_third_button_has_admin_panel_callback(self):
        kb = main_keyboard()
        btn = kb.inline_keyboard[2][0]
        assert btn.callback_data == "admin_panel"


class TestBackToStartKb:
    def test_returns_inline_keyboard_markup(self):
        kb = back_to_start_kb()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_has_one_button(self):
        kb = back_to_start_kb()
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 1

    def test_button_callback_data(self):
        kb = back_to_start_kb()
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "back|start"


class TestBackToRoyhatKb:
    def test_returns_inline_keyboard_markup(self):
        kb = back_to_royhat_kb()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_button_callback_data(self):
        kb = back_to_royhat_kb()
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "back|royhat"


class TestBackToAdminPanelKb:
    def test_returns_inline_keyboard_markup(self):
        kb = back_to_admin_panel_kb()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_button_callback_data(self):
        kb = back_to_admin_panel_kb()
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "admin_panel"
