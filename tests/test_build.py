import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.write_private_info import escape_latex, write_private_info

ROOT = Path(__file__).resolve().parents[1]


class ContactTests(unittest.TestCase):
    def test_latex_special_characters(self):
        self.assertEqual(escape_latex(r"\{}$&#%_~^"),
                         r"\textbackslash{}\{\}\$\&\#\%\_\textasciitilde{}\textasciicircum{}")

    def test_invalid_contacts_do_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "private_info.tex"
            destination.write_text("original")
            for env in ({}, {"PHONE": "123", "EMAIL": ""}, {"PHONE": "123", "EMAIL": "a\nb"}):
                with self.subTest(env=env), self.assertRaises(ValueError):
                    write_private_info(destination, env)
                self.assertEqual(destination.read_text(), "original")

    def test_contacts_are_written_as_escaped_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "private_info.tex"
            write_private_info(destination, {"PHONE": "+1 (000) 000-0000", "EMAIL": "test_cv@example.invalid"})
            self.assertIn(r"\newcommand{\myEmail}{test\_cv@example.invalid}", destination.read_text())


class BuildTests(unittest.TestCase):
    """Exercise failure paths without needing TeX in the Python test environment."""

    def run_build(self, fail_pass="0", invalid_pdf="0", missing_pdf="0"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "bin").mkdir()
            shutil.copy(ROOT / "scripts/build_cv.sh", root / "scripts/build_cv.sh")
            (root / "cv.pdf").write_text("old PDF")
            (root / "build").mkdir()
            (root / "build/cv.pdf").write_text("stale intermediate")
            compiler = root / "bin/xelatex"
            compiler.write_text(
                '#!/usr/bin/env bash\nset -eu\n'
                'n=0\nif [ -f calls ]; then n=$(cat calls); fi\n'
                'n=$((n + 1))\necho "$n" > calls\n'
                'if [ "$n" = "$FAIL_PASS" ]; then exit 1; fi\n'
                'if [ "$MISSING_PDF" = 0 ]; then echo "new PDF" > build/cv.pdf; fi\n'
            )
            checker = root / "bin/pdfinfo"
            checker.write_text('#!/usr/bin/env bash\nexit "$INVALID_PDF"\n')
            compiler.chmod(0o755)
            checker.chmod(0o755)
            result = subprocess.run(
                ["bash", str(root / "scripts/build_cv.sh")],
                env={**os.environ, "PATH": f"{root / 'bin'}:{os.environ['PATH']}",
                     "FAIL_PASS": fail_pass, "INVALID_PDF": invalid_pdf, "MISSING_PDF": missing_pdf},
                capture_output=True, text=True,
            )
            return result.returncode, (root / "cv.pdf").read_text(), (root / "calls").read_text().strip()

    def test_latex_error_stops_build_and_preserves_previous_pdf(self):
        self.assertEqual(self.run_build(fail_pass="2"), (1, "old PDF", "2"))

    def test_invalid_pdf_is_not_published(self):
        self.assertEqual(self.run_build(invalid_pdf="1"), (1, "old PDF", "3"))

    def test_stale_pdf_cannot_satisfy_missing_output(self):
        self.assertEqual(self.run_build(missing_pdf="1"), (1, "old PDF", "3"))

    def test_success_publishes_only_after_all_passes(self):
        self.assertEqual(self.run_build(), (0, "new PDF\n", "3"))


if __name__ == "__main__":
    unittest.main()
