"""Render real zsh themes without loading user rc files or starting gitstatusd."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ZSH = shutil.which("zsh")
THEMES = ("default", "pure", "bracketed", "nerd-font", "jetpack", "tokyo-night")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
SCRIPT = r'''
source "$DOTFILES_ROOT/home/dot-config/zsh/prompt-engine.zsh"
PROMPT_GIT_REPO=1
PROMPT_GIT_BRANCH=main
source "$DOTFILES_ROOT/prompt-$PROMPT_THEME/dot-config/zsh/prompt.zsh"
print -Pn -- "$PROMPT"
printf '\0'
print -Pn -- "$RPROMPT"
'''


@unittest.skipUnless(ZSH, "zsh is required to render prompt themes")
class PromptRenderingTest(unittest.TestCase):
    def render(self, theme, **settings):
        with tempfile.TemporaryDirectory(prefix="prompt-render-") as directory:
            # Keep the displayed hour below ten, independently of the machine's timezone.
            offset = datetime.now(timezone.utc).hour - 3
            env = {
                "HOME": directory, "PATH": "/usr/bin:/bin", "TERM": "xterm-256color",
                "HOMEBREW_PREFIX": directory, "DOTFILES_ROOT": str(ROOT),
                "PROMPT_THEME": theme, "TZ": f"UTC{offset:+d}", **settings,
            }
            result = subprocess.run(
                [ZSH, "-dfi", "-c", SCRIPT], env=env,
                capture_output=True, text=True, timeout=10, check=True,
            )
            left, right = result.stdout.split("\0")
            return ANSI.sub("", left), ANSI.sub("", right)

    def test_layout_and_time_are_independent_for_every_theme(self):
        for theme in THEMES:
            for multiline in (False, True):
                for show_time in (False, True):
                    with self.subTest(theme=theme, multiline=multiline, show_time=show_time):
                        left, right = self.render(
                            theme, KAISIAN_PROMPT_MULTILINE=str(multiline).lower(),
                            KAISIAN_PROMPT_SHOW_TIME=str(show_time).lower(),
                        )
                        self.assertEqual(left.count("\n"), int(multiline))
                        self.assertIn("main", left)
                        self.assertNotRegex(left, r"\d{1,2}:\d{2}")
                        if show_time:
                            self.assertRegex(right, r"^0\d:\d{2}:\d{2}$")
                        else:
                            self.assertEqual(right, "")

    def test_native_defaults_and_ssh_indicator_survive(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                left, right = self.render(theme)
                self.assertEqual(left.count("\n"), 0 if theme == "default" else 1)
                if theme == "tokyo-night":
                    self.assertRegex(left, r" \d{1,2}:\d{2}")
                    self.assertEqual(right, "")
                elif theme in ("default", "jetpack"):
                    self.assertRegex(right, r"\d{1,2}:\d{2}")
                else:
                    self.assertEqual(right, "")
        for theme in ("tokyo-night", "jetpack"):
            with self.subTest(theme=theme, switch_to_single_line=True):
                left, right = self.render(theme, KAISIAN_PROMPT_MULTILINE="false")
                self.assertEqual(left.count("\n"), 0)
                self.assertNotRegex(left, r"\d{1,2}:\d{2}")
                self.assertRegex(right, r"^0\d:\d{2}:\d{2}$")
        _, right = self.render(
            "default", KAISIAN_PROMPT_SHOW_TIME="false", SSH_CLIENT="127.0.0.1 12345 22",
        )
        self.assertEqual(right, "⇄")


if __name__ == "__main__":
    unittest.main()
