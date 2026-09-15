from reviewdistill.context.manuscript import (
    blank_line_blocks,
    choose_anchor,
    drop_percent_tails,
    extract_context,
    is_structural_line,
    join_source,
    strip_comment_macros,
)

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


def test_drop_percent_tails_blanks_comment_and_keeps_percent_escape():
    lines = [
        r"% – corpus",
        r"We kept 100\% of the sample. % note",
        r"Next sentence.",
    ]
    out = drop_percent_tails(lines)
    assert out == [
        "",
        r"We kept 100\% of the sample. ",
        r"Next sentence.",
    ]
    assert len(out) == 3


def test_blank_line_blocks_skip_empty_lines():
    lines = ["", r"% gone", "Hello.", "", "World."]
    cleaned = drop_percent_tails(lines)
    assert blank_line_blocks(cleaned) == [(2, 2), (4, 4)]


def test_is_structural_line_sectioning_and_label():
    assert is_structural_line(r"\section{Eval}")
    assert is_structural_line(r"\subsection*{X}")
    assert is_structural_line(r"\section[short]{Long}")
    assert is_structural_line(r"  \label{sec:eval}")
    assert is_structural_line(r"\chapter{Book}")
    assert not is_structural_line(r"\sectioning{no}")
    assert not is_structural_line("We created the corpus.")
    assert not is_structural_line(r"\begin{figure}")


def test_strip_comment_macros_keeps_rest_of_line():
    lines = [
        r"We created the evaluation corpus. \yzc{Where are the tables?}",
    ]
    out = strip_comment_macros(lines, ["yzc"])
    assert out == ["We created the evaluation corpus. "]
    assert "yzc" not in out[0]


def test_strip_comment_macros_allows_space_before_brace():
    lines = [r"Prose. \yzc {A remark.}"]
    assert strip_comment_macros(lines, ["yzc"]) == ["Prose. "]


def test_strip_comment_macros_multiline_preserves_line_count():
    lines = [
        r"Before. \yzc{",
        "body",
        "}",
        "After.",
    ]
    out = strip_comment_macros(lines, ["yzc"])
    assert len(out) == 4
    assert out[0] == "Before. "
    assert out[1] == ""
    assert out[2] == ""
    assert out[3] == "After."


def test_strip_comment_macros_strips_every_configured_command():
    lines = [r"A. \yzc{one} B. \myremark{two} C."]
    out = strip_comment_macros(lines, ["yzc", "myremark"])
    assert out == ["A.  B.  C."]


def _prepared(source: str, commands: list[str]) -> list[str]:
    lines = strip_comment_macros(source.splitlines(), commands)
    return drop_percent_tails(lines)


def test_join_source_trims_edge_blanks_keeps_internal():
    lines = ["", r"\section{A}", "", r"\label{b}", ""]
    assert join_source(lines, 0, 4) == "\\section{A}\n\n\\label{b}"


def test_choose_anchor_inline_paragraph_not_percent_divider():
    source = (
        "\\section{Eval}\n"
        "% – corpus\n"
        "\n"
        "We created the evaluation corpus. \\yzc{Where are the tables?}\n"
    )
    lines = _prepared(source, ["yzc"])
    idx = 3
    assert choose_anchor(lines, idx) == "We created the evaluation corpus."


def test_choose_anchor_walks_up_to_previous_paragraph():
    source = "The results demonstrate that X.\n\n\\yzc{Too strong.}\n"
    lines = _prepared(source, ["yzc"])
    assert choose_anchor(lines, 2) == "The results demonstrate that X."


def test_choose_anchor_heading_cluster_not_next_paragraph():
    source = (
        "\\section{Background}\n"
        "\\label{sec:background}\n"
        "\n"
        "\\subsection{Overview}\n"
        "\n"
        "\\myremark{Need a sentence between these headings.}\n"
        "\n"
        "\\subsection{Participants}\n"
        "We recruited volunteers.\n"
    )
    lines = _prepared(source, ["myremark"])
    idx = next(i for i, row in enumerate(source.splitlines()) if row.startswith(r"\myremark"))
    text = choose_anchor(lines, idx)
    assert "\\section{Background}" in text
    assert "\\label{sec:background}" in text
    assert "\\subsection{Overview}" in text
    assert "We recruited volunteers" not in text


def test_choose_anchor_empty_when_nothing_above():
    lines = _prepared("\\yzc{Only this.}\n", ["yzc"])
    assert choose_anchor(lines, 0) == ""


def test_extracts_section_and_containing_paragraph():
    line = TEX.splitlines().index("Therefore, Model A is more suitable for real-world applications.") + 1
    ctx = extract_context(TEX, line_number=line)
    assert ctx.section == "Results / Accuracy"
    assert (
        "Model A achieved higher accuracy than Model B.\n"
        "Therefore, Model A is more suitable"
        in ctx.context_text
    )
    assert not hasattr(ctx, "citations")


def test_inline_comment_keeps_paragraph_not_percent_divider():
    source = (
        "\\section{Eval}\n"
        "% – corpus\n"
        "\n"
        "We created the evaluation corpus by running the coding agent. "
        "\\yzc{1. Where are the tables for the ML tasks obtained?}\n"
    )
    ctx = extract_context(source, line_number=4, command="yzc")
    assert "We created the evaluation corpus" in ctx.context_text
    assert "% – corpus" not in ctx.context_text
    assert "yzc" not in ctx.context_text
    assert "Where are the tables" not in ctx.context_text
    assert ctx.section == "Eval"


def test_same_block_comment_on_next_line():
    source = (
        "The results demonstrate that the intervention caused the improvement.\n"
        "\\myremark{Causal language is not supported by this design.}\n"
    )
    ctx = extract_context(source, line_number=2, command="myremark")
    assert ctx.context_text == (
        "The results demonstrate that the intervention caused the improvement."
    )


def test_blank_line_then_comment_uses_previous_paragraph():
    source = "The results demonstrate that X.\n\n\\yzc{Too strong.}\n"
    ctx = extract_context(source, line_number=3, command="yzc")
    assert ctx.context_text == "The results demonstrate that X."


def test_multiline_remark_tight_stack_does_not_take_next_subsection():
    source = (
        "\\section{Background}\n"
        "\\label{sec:background}\n"
        "\\subsection{Overview}\n"
        "\\yzc{\n"
        "Need a sentence.\n"
        "}\n"
        "\\subsection{Participants}\n"
        "We recruited volunteers.\n"
    )
    ctx = extract_context(source, line_number=4, command="yzc")
    assert "Participants" not in ctx.context_text
    assert "volunteers" not in ctx.context_text
    assert "Need a sentence" not in ctx.context_text
    assert "\\subsection{Overview}" in ctx.context_text


def test_same_line_then_multiline_remark_does_not_take_following_sentence():
    source = "\\yzc{one} \\yzc{\nbody\n}\nAfter.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "After." not in ctx.context_text
    assert "yzc" not in ctx.context_text
    assert "body" not in ctx.context_text


def test_single_line_leftover_does_not_take_following_heading():
    source = (
        "Intro. \\yzc{foo}\n"
        "\\subsection{B}\n"
        "Later.\n"
    )
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "Later." not in ctx.context_text
    assert "\\subsection{B}" not in ctx.context_text
    assert "foo" not in ctx.context_text
    assert "Intro." in ctx.context_text


def test_glued_multiline_remark_does_not_take_following_heading():
    source = (
        "Intro. \\yzc{foo\n"
        "bar % x} \\myremark{cite me.}\n"
        "\\subsection{B}\n"
        "Later.\n"
    )
    ctx = extract_context(source, line_number=1, commands=["yzc", "myremark"])
    assert "Later." not in ctx.context_text
    assert "\\subsection{B}" not in ctx.context_text
    assert "cite me" not in ctx.context_text
    assert "Intro." in ctx.context_text


def test_heading_after_closer_on_same_line_is_not_neighborhood():
    source = "Intro. \\yzc{foo\nbar} \\subsection{B}\nLater.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "Later." not in ctx.context_text
    assert "\\subsection{B}" not in ctx.context_text
    assert "foo" not in ctx.context_text
    assert "Intro." in ctx.context_text


def test_one_line_heading_after_closer_is_not_neighborhood():
    source = "Intro. \\yzc{foo} \\subsection{B}\nLater.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert ctx.context_text == "Intro."
    assert ctx.section is None


def test_one_line_heading_after_standalone_closer_walks_up():
    source = "Intro.\n\n\\yzc{foo} \\subsection{B}\nLater.\n"
    ctx = extract_context(source, line_number=3, command="yzc")
    assert ctx.context_text == "Intro."
    assert ctx.section is None


def test_one_line_label_after_closer_is_not_neighborhood():
    source = "Intro.\n\\yzc{foo} \\label{sec:x}\nLater.\n"
    ctx = extract_context(source, line_number=2, command="yzc")
    assert ctx.context_text == "Intro."
    assert "Later." not in ctx.context_text
    assert "label" not in ctx.context_text


def test_pre_macro_mid_line_label_survives_closer_heading():
    source = "sentence.\\label{x} more words. \\yzc{foo} \\subsection{B}\nLater.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "sentence." in ctx.context_text
    assert "more words." in ctx.context_text
    assert "Later." not in ctx.context_text
    assert "\\subsection{B}" not in ctx.context_text
    assert "foo" not in ctx.context_text


def test_commented_macro_leftover_heading_does_not_end_block():
    source = (
        "The results demonstrate that X. % \\yzc{old} \\subsection{Ghost}\n"
        "We recruited volunteers.\n"
        "\\yzc{current}\n"
    )
    ctx = extract_context(source, line_number=3, command="yzc")
    assert "The results demonstrate that X." in ctx.context_text
    assert "We recruited volunteers." in ctx.context_text
    assert "Ghost" not in ctx.context_text


def test_heading_inside_later_same_line_remark_is_not_a_block_stop():
    source = "Intro. \\yzc{foo} \\yzc{need \\subsection{B} here}\nLater.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "Later." in ctx.context_text
    assert "Intro." in ctx.context_text
    assert "need" not in ctx.context_text


def test_heading_then_another_macro_on_closer_is_clipped():
    source = "Intro. \\yzc{foo} \\subsection{B} \\yzc{other}\nLater.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert ctx.context_text == "Intro."
    assert "\\subsection{B}" not in ctx.context_text
    assert "Later." not in ctx.context_text


def test_percent_commented_heading_after_closer_keeps_following_prose():
    source = "Intro. \\yzc{foo} % \\subsection{B}\nLater.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "Intro." in ctx.context_text
    assert "Later." in ctx.context_text
    assert "foo" not in ctx.context_text


def test_mid_line_label_does_not_split_paragraph():
    source = (
        "The intervention caused the improvement.\\label{sec:causal}\n"
        "This design does not support causal claims. \\yzc{too strong}\n"
    )
    ctx = extract_context(source, line_number=2, command="yzc")
    assert "The intervention caused the improvement." in ctx.context_text
    assert "This design does not support causal claims." in ctx.context_text
    assert "too strong" not in ctx.context_text


def test_multiline_prose_then_heading_on_closer_is_not_neighborhood():
    source = "Intro. \\yzc{foo\nbar} leftover \\subsection{B}\nLater.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "Later." not in ctx.context_text
    assert "\\subsection{B}" not in ctx.context_text
    assert "Intro." in ctx.context_text
    assert "leftover" in ctx.context_text


def test_multiline_remark_does_not_take_following_sentence():
    source = (
        "The results demonstrate that X.\n"
        "\n"
        "\\yzc{\n"
        "Too strong.\n"
        "}\n"
        "We recruited volunteers.\n"
    )
    ctx = extract_context(source, line_number=3, command="yzc")
    assert ctx.context_text == "The results demonstrate that X."
    assert "volunteers" not in ctx.context_text


def test_tight_heading_stack_does_not_take_next_subsection():
    source = (
        "\\section{Background}\n"
        "\\label{sec:background}\n"
        "\\subsection{Overview}\n"
        "\\yzc{Need a sentence.}\n"
        "\\subsection{Participants}\n"
        "We recruited volunteers.\n"
    )
    ctx = extract_context(source, line_number=4, command="yzc")
    assert ctx.context_text == (
        "\\section{Background}\n"
        "\\label{sec:background}\n"
        "\\subsection{Overview}"
    )
    assert "Participants" not in ctx.context_text
    assert "volunteers" not in ctx.context_text


def test_comment_between_headings_is_heading_cluster_only():
    source = (
        "\\section{Background}\n"
        "\\label{sec:background}\n"
        "\n"
        "\\subsection{Overview}\n"
        "\n"
        "\\myremark{Need a sentence between these headings.}\n"
        "\n"
        "\\subsection{Participants}\n"
        "We recruited volunteers from a mailing list.\n"
    )
    line = next(
        i for i, row in enumerate(source.splitlines(), start=1) if row.startswith(r"\myremark")
    )
    ctx = extract_context(source, line_number=line, command="myremark")
    assert ctx.context_text == (
        "\\section{Background}\n"
        "\\label{sec:background}\n"
        "\n"
        "\\subsection{Overview}"
    )
    assert "We recruited volunteers" not in ctx.context_text
    assert "Need a sentence" not in ctx.context_text


def test_comment_on_heading_line_keeps_heading():
    source = "\\subsection{Overview}\n\\myremark{This heading is redundant.}\n"
    ctx = extract_context(source, line_number=2, command="myremark")
    assert ctx.context_text == "\\subsection{Overview}"


def test_empty_neighborhood_is_empty_string():
    ctx = extract_context("\\yzc{Only this.}\n", line_number=1, command="yzc")
    assert ctx.context_text == ""
    assert ctx.section is None


def test_multiline_command_keeps_rest_of_same_paragraph():
    source = "Before. \\yzc{\nbody\n}\nAfter.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "Before." in ctx.context_text
    assert "After." in ctx.context_text
    assert "yzc" not in ctx.context_text
    assert "body" not in ctx.context_text


def test_blank_line_inside_command_does_not_leak_opener():
    source = (
        "The results demonstrate that X.\n"
        "\n"
        "\\yzc{\n"
        "Too strong.\n"
        "\n"
        "Only correlation.\n"
        "}\n"
    )
    ctx = extract_context(source, line_number=3, command="yzc")
    assert ctx.context_text == "The results demonstrate that X."
    assert "yzc" not in ctx.context_text
    assert "Too strong" not in ctx.context_text


def test_blank_line_inside_command_keeps_before_and_after():
    source = "Before. \\yzc{\n\nbody\n}\nAfter.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "Before." in ctx.context_text
    assert "After." in ctx.context_text
    assert "yzc" not in ctx.context_text
    assert "body" not in ctx.context_text


def test_heading_cluster_skips_empty_remark_between_headings():
    source = (
        "\\section{A}\n"
        "\n"
        "\\yzc{x}\n"
        "\n"
        "\\subsection{B}\n"
        "\n"
        "\\yzc{current}\n"
    )
    ctx = extract_context(source, line_number=7, command="yzc")
    assert ctx.context_text == "\\section{A}\n\n\\subsection{B}"
    assert "yzc" not in ctx.context_text


def test_stacked_standalone_comments_walk_up_past_previous():
    source = (
        "The results demonstrate that X.\n"
        "\n"
        "\\yzc{first}\n"
        "\n"
        "\\yzc{second}\n"
    )
    ctx = extract_context(source, line_number=5, command="yzc")
    assert ctx.context_text == "The results demonstrate that X."
    assert "yzc" not in ctx.context_text


def test_percent_before_closer_does_not_leak_opener():
    source = "We designed the interface.\n\\yzc{Where are the tables? % check}\n"
    ctx = extract_context(source, line_number=2, command="yzc")
    assert ctx.context_text == "We designed the interface."
    assert "yzc" not in ctx.context_text
    assert "Where are the tables" not in ctx.context_text


def test_percent_before_closer_does_not_hide_later_command():
    source = "A claim. \\yzc{tone % x} More text. \\myremark{cite me.}\n"
    ctx = extract_context(source, line_number=1, commands=["yzc", "myremark"])
    assert ctx.context_text == "A claim.  More text."
    assert "yzc" not in ctx.context_text
    assert "myremark" not in ctx.context_text


def test_percent_on_multiline_closer_does_not_hide_later_command():
    source = "A claim.\n\\yzc{foo\nbar % x} \\myremark{cite me.}\nAfter.\n"
    ctx = extract_context(source, line_number=2, commands=["yzc", "myremark"])
    assert "cite me" not in ctx.context_text
    assert "yzc" not in ctx.context_text
    assert "myremark" not in ctx.context_text
    assert "A claim." in ctx.context_text


def test_commented_multiline_command_is_not_next_remark_neighborhood():
    source = (
        "The results demonstrate that X.\n"
        "\n"
        "% \\yzc{\n"
        "Need to rewrite this argument.\n"
        "The current evidence is weak.\n"
        "}\n"
        "\n"
        "\\myremark{cite me.}\n"
    )
    ctx = extract_context(source, line_number=8, commands=["yzc", "myremark"])
    assert ctx.context_text == "The results demonstrate that X."
    assert "Need to rewrite" not in ctx.context_text
    assert "evidence is weak" not in ctx.context_text


def test_unclosed_commented_command_is_not_next_remark_neighborhood():
    source = (
        "The results demonstrate that X.\n"
        "\n"
        "% \\yzc{\n"
        "Need to rewrite this argument.\n"
        "The current evidence is weak.\n"
        "\n"
        "\\myremark{cite me.}\n"
    )
    ctx = extract_context(source, line_number=7, commands=["yzc", "myremark"])
    assert ctx.context_text == "The results demonstrate that X."
    assert "Need to rewrite" not in ctx.context_text
    assert "evidence is weak" not in ctx.context_text


def test_command_after_letter_is_stripped_from_context():
    source = "citation\\yzc{check this.}\nNext sentence.\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert "yzc" not in ctx.context_text
    assert "check this" not in ctx.context_text
    assert ctx.context_text == "citation\nNext sentence."


def test_two_configured_macros_in_one_paragraph_are_both_stripped():
    source = "A claim. \\yzc{tone} More text. \\myremark{cite me.}\n"
    ctx = extract_context(source, line_number=1, commands=["yzc", "myremark"])
    assert ctx.context_text == "A claim.  More text."
    assert "yzc" not in ctx.context_text
    assert "myremark" not in ctx.context_text


def test_extract_context_offset_null_without_identity():
    source = "We created the evaluation corpus. \\yzc{Where are the tables?}\n"
    ctx = extract_context(source, line_number=1, command="yzc")
    assert ctx.context_offset is None


def test_extract_context_offset_inline_end_of_sentence():
    source = "We created the evaluation corpus. \\yzc{Where are the tables?}\n"
    ctx = extract_context(
        source,
        line_number=1,
        commands=["yzc"],
        source_command="yzc",
        raw_text="Where are the tables?",
    )
    assert ctx.context_text == "We created the evaluation corpus."
    assert ctx.context_offset == len(ctx.context_text)


def test_extract_context_offset_walk_up_after_blank_line():
    source = "The results demonstrate that X.\n\n\\yzc{Too strong.}\n"
    ctx = extract_context(
        source,
        line_number=3,
        commands=["yzc"],
        source_command="yzc",
        raw_text="Too strong.",
    )
    assert ctx.context_text == "The results demonstrate that X."
    assert ctx.context_offset == len(ctx.context_text)


def test_extract_context_offset_empty_is_null():
    ctx = extract_context(
        "\\yzc{Only this.}\n",
        line_number=1,
        commands=["yzc"],
        source_command="yzc",
        raw_text="Only this.",
    )
    assert ctx.context_text == ""
    assert ctx.context_offset is None


def test_extract_context_offset_picks_this_macro_on_one_line():
    source = "A claim. \\yzc{tone} More text. \\myremark{cite me.}\n"
    yzc = extract_context(
        source,
        line_number=1,
        commands=["yzc", "myremark"],
        source_command="yzc",
        raw_text="tone",
    )
    remark = extract_context(
        source,
        line_number=1,
        commands=["yzc", "myremark"],
        source_command="myremark",
        raw_text="cite me.",
    )
    assert yzc.context_text == "A claim.  More text."
    assert remark.context_text == yzc.context_text
    assert yzc.context_offset == 9
    assert remark.context_offset == len(remark.context_text)
    assert yzc.context_text[: yzc.context_offset] == "A claim. "

