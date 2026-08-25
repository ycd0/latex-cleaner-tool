"""
Streamlit web app for latex_cleaner.

Run locally:
    pip install streamlit
    streamlit run streamlit_app.py

Deploy for free:
    1. Push this folder to a public (or private) GitHub repo.
    2. Go to https://share.streamlit.io (Streamlit Community Cloud),
       sign in with GitHub, click "New app", pick the repo/branch and
       set the main file to `streamlit_app.py`. Deploy.
    3. You'll get a shareable https://<something>.streamlit.app URL
       anyone on your team can open — no installs needed on their end.

    (Hugging Face Spaces, Render, and Railway all work the same way if
    you'd rather host it there — see README.md.)
"""

import io

import streamlit as st

from latex_cleaner import clean_latex

st.set_page_config(page_title="LaTeX Solution Stripper", page_icon="🧹", layout="wide")

st.title("🧹 LaTeX Exam-Paper Cleaner")
st.caption(
    "Strips **Correct Answer / Solution / Quick Tip** blocks from a "
    "Collegedunia-style exam-paper `.tex` file, leaving the preamble, "
    "page design, and every question + its options untouched."
)

with st.sidebar:
    st.header("Options")
    collapse = st.checkbox("Collapse extra blank lines left behind", value=True)
    st.markdown("---")
    st.markdown(
        "**How it works**\n\n"
        "The tool looks for the `% Correct Answer` marker that starts each "
        "answer block and removes everything up to and including the "
        "closing `\\end{quicktipbox}` that follows the Quick Tip. "
        "Nothing else in the file is touched — same preamble, same macros, "
        "same fonts, same colors, same layout."
    )
    st.markdown("---")
    st.markdown("Built for internal Collegedunia handbook/paper workflows.")

uploaded = st.file_uploader("Upload a .tex file", type=["tex"])
pasted = st.text_area(
    "...or paste LaTeX source here",
    height=220,
    placeholder="\\documentclass{...} ... % Correct Answer ...",
)

source_text = None
if uploaded is not None:
    source_text = uploaded.read().decode("utf-8", errors="replace")
elif pasted.strip():
    source_text = pasted

if source_text:
    cleaned, stats = clean_latex(source_text, collapse_blank_lines=collapse)

    c1, c2, c3 = st.columns(3)
    c1.metric("Answer/Solution blocks removed", stats.blocks_removed)
    c2.metric("Characters removed", f"{stats.chars_removed:,}")
    c3.metric("Output size", f"{stats.chars_after:,} chars")

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Original")
        st.code(source_text, language="latex", line_numbers=True)
    with col_right:
        st.subheader("Cleaned")
        st.code(cleaned, language="latex", line_numbers=True)

    st.download_button(
        "⬇️ Download cleaned .tex",
        data=io.BytesIO(cleaned.encode("utf-8")),
        file_name=(uploaded.name.replace(".tex", "_cleaned.tex") if uploaded else "cleaned.tex"),
        mime="text/plain",
    )

    if stats.blocks_removed == 0:
        st.warning(
            "No `% Correct Answer` blocks were found — the file may already "
            "be a questions-only paper, or it may use a different marker. "
            "The output above is unchanged from the input."
        )
else:
    st.info("Upload a `.tex` file or paste source above to get started.")
