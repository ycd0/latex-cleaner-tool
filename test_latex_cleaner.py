"""
Minimal tests for latex_cleaner. Run with:  python3 -m pytest test_latex_cleaner.py
or just:  python3 test_latex_cleaner.py
"""

from latex_cleaner import clean_latex

SAMPLE = r"""
\documentclass{article}
\begin{document}

\noindent \textbf{1.}
\textbf{What is 2+2?} \\

(A) 3 \\
(B) 4 \\

\bigskip

% Correct Answer
\noindent \textbf{Correct Answer:} (B) 4

\bigskip

% Solution
\noindent \textbf{Solution:} \\
Basic arithmetic. \\

\bigskip

% Quick Tip
\begin{quicktipbox}
Addition is commutative.
\end{quicktipbox}

% Topic - Arithmetic
\hrule

\end{document}
"""


def test_removes_one_block():
    cleaned, stats = clean_latex(SAMPLE)
    assert stats.blocks_removed == 1
    assert "Correct Answer" not in cleaned
    assert "quicktipbox" not in cleaned
    assert "What is 2+2?" in cleaned          # question stays
    assert "(B) 4" in cleaned                  # option stays (it's just an option line)
    assert "% Topic - Arithmetic" in cleaned    # topic marker stays
    assert "\\documentclass{article}" in cleaned  # preamble untouched


def test_idempotent_on_already_clean_file():
    cleaned_once, _ = clean_latex(SAMPLE)
    cleaned_twice, stats2 = clean_latex(cleaned_once)
    assert cleaned_once == cleaned_twice
    assert stats2.blocks_removed == 0


def test_no_blocks_present_leaves_text_unchanged_content():
    text = "\\documentclass{article}\\begin{document}Hello\\end{document}"
    cleaned, stats = clean_latex(text)
    assert stats.blocks_removed == 0
    assert cleaned == text


def test_keep_together_wraps_question_in_minipage():
    cleaned, _ = clean_latex(SAMPLE)
    assert "\\begin{minipage}" in cleaned
    assert cleaned.count("\\begin{minipage}") == cleaned.count("\\end{minipage}")
    # the question number/options must be *inside* the minipage, the topic
    # divider must stay *outside* it (it's the break point between questions)
    begin_idx = cleaned.index("\\begin{minipage}")
    end_idx = cleaned.index("\\end{minipage}")
    assert begin_idx < cleaned.index("\\textbf{1.}") < end_idx
    assert end_idx < cleaned.index("% Topic - Arithmetic")


def test_keep_together_false_leaves_no_minipage():
    cleaned, _ = clean_latex(SAMPLE, keep_together=False)
    assert "\\begin{minipage}" not in cleaned


def test_keep_together_is_idempotent():
    once, _ = clean_latex(SAMPLE)
    twice, stats2 = clean_latex(once)
    assert once == twice
    assert stats2.blocks_removed == 0


if __name__ == "__main__":
    test_removes_one_block()
    test_idempotent_on_already_clean_file()
    test_no_blocks_present_leaves_text_unchanged_content()
    test_keep_together_wraps_question_in_minipage()
    test_keep_together_false_leaves_no_minipage()
    test_keep_together_is_idempotent()
    print("All tests passed.")
