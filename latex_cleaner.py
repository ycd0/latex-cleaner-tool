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

__all__ = ["clean_latex", "wrap_questions_together", "CleanStats"]


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
# Each answer/solution/tip block starts at one of a known set of comment
# markers and ends at the closing \end{quicktipbox} of the Quick Tip box that
# always follows the solution. We match everything in between, non-greedily,
# so a malformed/missing quicktipbox in one question never swallows
# subsequent questions.
#
# Known start markers (extend this list if a future paper uses a new one —
# grep the source .tex for the "%"-comment that immediately precedes the
# answer key to find it):
#   - "% Correct Answer"            — standard single-answer MCQ template
#   - "% Comprehensive Answers Block" — grouped multi-part "extract" questions
#     (e.g. "Read the extract... answer (i)-(vi)"), whose answer key is a
#     series of per-part "(i) Correct Option:" / "(ii) ...:" lines instead of
#     one "Correct Answer:" line.
# ---------------------------------------------------------------------------
_ANSWER_BLOCK_MARKERS = r"Correct Answer|Comprehensive Answers Block"

# A question number label: "1.", "1. (i)", "7. (A)", etc. — the brace can
# hold anything after the digits+period, not just a bare number, since
# grouped/multi-part questions (e.g. "Read the extract... (i)-(vi)") number
# their sub-parts inside the same \textbf{...}.
_QNUM = r"\\noindent[ \t]*\\textbf\{\d+\.[^}]*\}"

_BLOCK_PATTERN = re.compile(
    r"[ \t]*%[ \t]*(?:" + _ANSWER_BLOCK_MARKERS + r").*?\\end\{quicktipbox\}[ \t]*\n?",
    re.DOTALL,
)

# Fallback pattern for files that don't use the "quicktipbox" env name but do
# use one of the answer-block markers above — stop at the next "% Topic"
# comment, next question number, or \hrule, whichever comes first. Used only
# if the primary pattern finds nothing.
_FALLBACK_BLOCK_PATTERN = re.compile(
    r"[ \t]*%[ \t]*(?:" + _ANSWER_BLOCK_MARKERS + r").*?"
    r"(?=%[ \t]*Topic|\\hrule|" + _QNUM + r"|\Z)",
    re.DOTALL,
)

# Collapse 3+ consecutive blank lines down to 2, left behind after removal.
_MULTI_BLANK = re.compile(r"\n[ \t]*\n[ \t]*\n+")

# ---------------------------------------------------------------------------
# Keep-each-question-together.
#
# A bare question (stem + options, no solution) is just flowing text/paragraphs
# with no "don't break here" hint, so LaTeX's page breaker is free to split it
# anywhere — e.g. options (A)/(B) print at the bottom of one page and (C)/(D)
# start the next. We fix that by wrapping every question (from its
# "\noindent \textbf{N.}" number up to the "% Topic" marker that always
# follows it) in a \minipage. A minipage is an atomic box to TeX's page
# builder: if it doesn't fully fit in the space left on the current page, the
# *whole* box moves to the next page instead of being split mid-question.
# This is safe here because a stem + 4 options is always short — nowhere near
# a full page tall.
# ---------------------------------------------------------------------------
_QUESTION_WRAP_OPEN = "\\begin{minipage}[t]{\\linewidth}"

_QUESTION_PATTERN = re.compile(
    _QNUM + r".*?"
    r"(?=[ \t]*%[ \t]*Topic|" + _QNUM + r"|\\end\{document\}|\Z)",
    re.DOTALL,
)


def _wrap_one_question(match: "re.Match[str]") -> str:
    body = match.group(0).rstrip("\n")
    return f"{_QUESTION_WRAP_OPEN}\n{body}\n\\end{{minipage}}\n\n"


def wrap_questions_together(text: str) -> str:
    """
    Wrap each numbered question in a \\minipage so it can't be split across a
    page break (see module notes above). Idempotent: if the text has already
    been through this pass (detected by the presence of our specific
    "\\begin{minipage}[t]{\\linewidth}" wrapper), it's returned unchanged
    rather than double-wrapped.
    """
    if _QUESTION_WRAP_OPEN in text:
        return text
    return _QUESTION_PATTERN.sub(_wrap_one_question, text)


def clean_latex(
    text: str, collapse_blank_lines: bool = True, keep_together: bool = True
) -> tuple[str, CleanStats]:
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
    keep_together : bool
        If True (default), wrap each question in a \\minipage so it can
        never be split across a page break — see `wrap_questions_together`.

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

    if keep_together:
        cleaned = wrap_questions_together(cleaned)

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
        "--no-keep-together",
        action="store_true",
        help="Do not wrap each question in a minipage to prevent it from "
        "splitting across a page break",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print removal stats to stderr",
    )
    args = parser.parse_args(argv)

    source = args.input.read()
    cleaned, stats = clean_latex(
        source,
        collapse_blank_lines=not args.no_collapse,
        keep_together=not args.no_keep_together,
    )
    args.output.write(cleaned)

    if args.stats:
        print(stats, file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
