# LaTeX Exam-Paper Cleaner

Strips the **Correct Answer / Solution / Quick Tip** blocks out of a
Collegedunia-style exam-paper `.tex` file, turning a "with solutions"
paper into a bare questions-only paper — same preamble, same page
design, same macros, same everything else, untouched.

```
BEFORE (per question)                 AFTER (per question)
----------------------                ----------------------
question + options                    question + options
\bigskip                              \bigskip
% Correct Answer            --->      % Topic - ...
\textbf{Correct Answer:} ...          \hrule
% Solution
\textbf{Solution:} ...
...
\begin{quicktipbox} ... \end{quicktipbox}
% Topic - ...
\hrule
```

## Files

| File                    | What it's for                                      |
|-------------------------|-----------------------------------------------------|
| `latex_cleaner.py`      | The actual cleaner — a library + a CLI, zero deps  |
| `streamlit_app.py`      | A one-page web UI wrapping the library             |
| `test_latex_cleaner.py` | A handful of tests locking in the behavior         |
| `requirements.txt`      | Just `streamlit`, needed only for the web UI       |

## Use it from the command line (no install needed beyond Python 3)

```bash
python3 latex_cleaner.py input.tex -o cleaned.tex --stats
```

or as a pipe:

```bash
cat input.tex | python3 latex_cleaner.py > cleaned.tex
```

## Use it as a library

```python
from latex_cleaner import clean_latex

cleaned_text, stats = clean_latex(source_text)
print(stats)  # CleanStats(blocks_removed=5, chars_before=..., chars_after=...)
```

## Run the web UI locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Opens a browser page where anyone can paste or upload a `.tex` file,
see a before/after side-by-side, and download the cleaned version.

## Host it for free so others on the team can use it

**Option A — Streamlit Community Cloud (easiest, free tier)**
1. Push this folder to a GitHub repo (public or private).
2. Go to https://share.streamlit.io, sign in with GitHub.
3. Click "New app" → pick the repo/branch → set main file to
   `streamlit_app.py` → Deploy.
4. You get a public URL like `https://your-app.streamlit.app` — send
   that link to anyone, they don't need Python installed.

**Option B — Hugging Face Spaces (also free)**
1. Create a new Space, SDK = Streamlit.
2. Upload `streamlit_app.py`, `latex_cleaner.py`, `requirements.txt`.
3. It builds and gives you a public `https://huggingface.co/spaces/...` URL.

**Option C — Render / Railway free tier**
Same three files, set the start command to:
```bash
streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
```

No matter which host, only `latex_cleaner.py`, `streamlit_app.py`, and
`requirements.txt` are needed — the tool has no external LaTeX
dependency, it's pure text/regex processing, so hosting is lightweight
and free-tier-friendly.

## How the matching works

Every question in the house template emits a `% Correct Answer`
comment right before the answer, and the solution always ends with a
`\end{quicktipbox}`. The tool matches everything between those two
markers (non-greedily, per question) and deletes it — nothing before
the first marker or after the last one is touched, which is why the
preamble, macros, and page/header design survive byte-for-byte.

If a file doesn't use the `quicktipbox` environment name, a fallback
pattern kicks in that stops at the next `% Topic`, `\hrule`, or next
question number instead — so the tool degrades gracefully rather than
eating the rest of the document.
