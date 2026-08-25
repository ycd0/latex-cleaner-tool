"""
latex_cleaner.py
=================
A small, dependency-free tool for cleaning Collegedunia-style exam-paper
LaTeX files: it strips out the "Correct Answer / Solution / Quick Tip"
blocks that follow each question, leaving a bare question-paper (question
+ options only) while leaving the preamble, macros, page design, and every
other piece of the document completely untouched.

Works on ANY LaTeX file that follows this per-question pattern:

    ... question + options ...
    \\bigskip
    % Correct Answer
    \\noindent \\textbf{Correct Answer:} ...
    \\bigskip
    % Solution
    \\noindent \\textbf{Solution:} ...
    ...
    \\begin{quicktipbox}
    ...
    \\end{quicktipbox}
    % Topic - ...

-> becomes ->

    ... question + options ...
    \\bigskip
    % Topic - ...

Usage as a library:
    from latex_cleaner import clean_latex
    cleaned = clean_latex(source_text)

Usage as a CLI:
    python latex_cleaner.py input.tex -o output.tex
    cat input.tex | python latex_cleaner.py > output.tex
"""

from __future__ import annotations

import argparse
import re
import sys

__all__ = ["clean_latex", "CleanStats"]


class CleanStats:
    """Small report object so callers/UI can show what happened."""

    def __init__(self, blocks_removed: int, chars_before: int, chars_after: int):
        self.blocks_removed = blocks_removed
        self.chars_before = chars_before
        self.chars_after = chars_after

    @property
    def chars_removed(self) -> int:
        return self.chars_before - self.chars_after

    def __repr__(self) -> str:
        return (
            f"CleanStats(blocks_removed={self.blocks_removed}, "
            f"chars_before={self.chars_before}, chars_after={self.chars_after}, "
            f"chars_removed={self.chars_removed})"
        )


# ---------------------------------------------------------------------------
# The core pattern.
#
# Each answer/solution/tip block starts at a "% Correct Answer" comment (the
# marker the template always emits right before \textbf{Correct Answer:})
# and ends at the closing \end{quicktipbox} of the Quick Tip box that always
# follows the solution. We match everything in between, non-greedily, so a
# malformed/missing quicktipbox in one question never swallows subsequent
# questions.
# ---------------------------------------------------------------------------
_BLOCK_PATTERN = re.compile(
    r"[ \t]*%[ \t]*Correct Answer.*?\\end\{quicktipbox\}[ \t]*\n?",
    re.DOTALL,
)

# Fallback pattern for files that don't use the "quicktipbox" env name but do
# use the \textbf{Correct Answer:} / \textbf{Solution:} markers — stop at the
# next "% Topic" comment, next question number, or \hrule, whichever comes
# first. Used only if the primary pattern finds nothing.
_FALLBACK_BLOCK_PATTERN = re.compile(
    r"[ \t]*%[ \t]*Correct Answer.*?(?=%[ \t]*Topic|\\hrule|\\noindent[ \t]*\\textbf\{\d+\.\}|\Z)",
    re.DOTALL,
)

# Collapse 3+ consecutive blank lines down to 2, left behind after removal.
_MULTI_BLANK = re.compile(r"\n[ \t]*\n[ \t]*\n+")


def clean_latex(text: str, collapse_blank_lines: bool = True) -> tuple[str, CleanStats]:
    """
    Strip Correct-Answer / Solution / Quick-Tip blocks from LaTeX source,
    leaving the preamble, document structure, questions, and options intact.

    Parameters
    ----------
    text : str
        Full LaTeX source (preamble + body).
    collapse_blank_lines : bool
        If True (default), collapse runs of 3+ blank lines left behind by
        the removal down to a single blank line, purely cosmetic.

    Returns
    -------
    (cleaned_text, stats) : tuple[str, CleanStats]
    """
    chars_before = len(text)

    matches = list(_BLOCK_PATTERN.finditer(text))
    pattern_used = _BLOCK_PATTERN
    if not matches:
        matches = list(_FALLBACK_BLOCK_PATTERN.finditer(text))
        pattern_used = _FALLBACK_BLOCK_PATTERN

    cleaned = pattern_used.sub("", text)

    if collapse_blank_lines:
        cleaned = _MULTI_BLANK.sub("\n\n", cleaned)

    stats = CleanStats(
        blocks_removed=len(matches),
        chars_before=chars_before,
        chars_after=len(cleaned),
    )
    return cleaned, stats


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Strip Correct Answer / Solution / Quick Tip blocks from "
        "an exam-paper LaTeX file, keeping the preamble and question text intact."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=argparse.FileType("r", encoding="utf-8"),
        default=sys.stdin,
        help="Input .tex file (default: stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w", encoding="utf-8"),
        default=sys.stdout,
        help="Output .tex file (default: stdout)",
    )
    parser.add_argument(
        "--no-collapse",
        action="store_true",
        help="Do not collapse blank lines left behind by removal",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print removal stats to stderr",
    )
    args = parser.parse_args(argv)

    source = args.input.read()
    cleaned, stats = clean_latex(source, collapse_blank_lines=not args.no_collapse)
    args.output.write(cleaned)

    if args.stats:
        print(stats, file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
