import unittest
from unittest.mock import patch

import main


class TestMainMenu(unittest.TestCase):
    def test_menu_exit_choice_returns(self):
        with patch("builtins.input", return_value="0"):
            main.run_menu()

    def test_menu_chat_choice_dispatches_chat_then_exit(self):
        choices = iter(["1", "0"])
        with patch("builtins.input", side_effect=lambda _prompt="": next(choices)), \
             patch.object(main, "run_chat") as run_chat:
            main.run_menu()

        run_chat.assert_called_once()

    def test_main_chat_flag_bypasses_menu(self):
        with patch("sys.argv", ["main.py", "--chat"]), \
             patch.object(main, "run_chat") as run_chat, \
             patch.object(main, "run_menu") as run_menu:
            main.main()

        run_chat.assert_called_once()
        run_menu.assert_not_called()

    def test_main_seed_flag_passes_limit(self):
        with patch("sys.argv", ["main.py", "--seed", "--seed-limit", "2"]), \
             patch.object(main, "run_seed") as run_seed:
            main.main()

        run_seed.assert_called_once_with(limit=2)


if __name__ == "__main__":
    unittest.main()
