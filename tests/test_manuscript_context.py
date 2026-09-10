from reviewdistill.context.manuscript import extract_context, split_stored_context

TEX = r"""
\section{Method}
\subsection{Interface}
We designed the interface using a wizard of forms.
This choice is never justified in the text.
See \cite{smith2020} and Figure~\ref{fig:ui}.

\section{Results}
\subsection{Accuracy}
Model A achieved higher accuracy than Model B.
Therefore, Model A is more suitable for real-world applications.
"""


def test_extracts_section_paragraph_citations_and_refs():
    line = TEX.splitlines().index("Therefore, Model A is more suitable for real-world applications.") + 1
    ctx = extract_context(TEX, line_number=line)
    assert ctx.section == "Results / Accuracy"
    assert (
        "Model A achieved higher accuracy than Model B.\n"
        "Therefore, Model A is more suitable"
        in ctx.context_text
    )
    assert "fig:ui" not in ctx.figure_table_refs

    method_line = TEX.splitlines().index("This choice is never justified in the text.") + 1
    method = extract_context(TEX, line_number=method_line)
    assert method.section == "Method / Interface"
    assert "smith2020" in method.citations
    assert "fig:ui" in method.figure_table_refs


FORM = r"""
\section{Background}
\label{sec:background}

\myremark{Need a sentence between these headings.}

\subsection{Overview}

We designed the interface using a wizard of forms.

\myremark{This heading is redundant.}

\subsection{Participants}
We recruited volunteers from a mailing list.

\subsection{Task}
See \cite{smith2020,jones2021} and \ref{fig:ui}.
"""


def test_isolated_comment_uses_nearby_text_not_distant_citations():
    lines = FORM.splitlines()
    line = next(i for i, row in enumerate(lines) if row.startswith(r"\myremark{Need a sentence")) + 1
    ctx = extract_context(FORM, line_number=line, command="myremark")
    assert "Need a sentence" not in ctx.context_text
    assert r"\myremark" not in ctx.context_text
    assert "\\section{Background}\n\\label{sec:background}" in ctx.context_text
    assert "\\subsection{Overview}\n\nWe designed the interface" in ctx.context_text
    assert "\\label{sec:background}\n\n\\subsection{Overview}" in ctx.context_text
    assert "\\section{Background} \\label" not in ctx.context_text
    assert "\\subsection{Overview} We designed" not in ctx.context_text
    assert "jones2021" not in ctx.citations
    assert "fig:ui" not in ctx.figure_table_refs
    assert "jones2021" not in ctx.context_text


USER_FORM = r"""
\section{Background}
\label{sec:background}

\myremark{Need a sentence between these headings.}

\subsection{Overview}
We designed the interface using a wizard of forms.
"""


def test_context_keeps_source_linebreaks_when_heading_meets_prose():
    lines = USER_FORM.splitlines()
    line = next(i for i, row in enumerate(lines) if row.startswith(r"\myremark{Need a sentence")) + 1
    ctx = extract_context(USER_FORM, line_number=line, command="myremark")
    assert ctx.context_text == (
        "\\section{Background}\n"
        "\\label{sec:background}\n"
        "\n"
        "\\subsection{Overview}\n"
        "We designed the interface using a wizard of forms."
    )


def test_split_stored_context_keeps_prose_newlines():
    prose, extras = split_stored_context(
        "\\section{A}\n\\label{b}\nCitations: smith2020 | Refs: fig:ui"
    )
    assert prose == "\\section{A}\n\\label{b}"
    assert extras == "Citations: smith2020 | Refs: fig:ui"
    assert split_stored_context("only prose") == ("only prose", "")
    assert split_stored_context("Refs: fig:1") == ("", "Refs: fig:1")

