"""Write LaTeX-safe contact details without printing secret values."""

import os
from pathlib import Path


def escape_latex(value):
    escapes = {
        "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
        "$": r"\$", "&": r"\&", "#": r"\#", "%": r"\%",
        "_": r"\_", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(escapes.get(char, char) for char in value)


def write_private_info(destination, environ):
    values = {}
    for key in ("PHONE", "EMAIL"):
        value = environ.get(key, "").strip()
        if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError(f"{key} must be set to a non-empty, single-line value.")
        values[key] = escape_latex(value)
    destination.write_text(
        rf"\newcommand{{\myPhone}}{{{values['PHONE']}}}" + "\n"
        + rf"\newcommand{{\myEmail}}{{{values['EMAIL']}}}" + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    write_private_info(
        Path(__file__).resolve().parents[1] / "sections/private_info.tex", os.environ
    )
