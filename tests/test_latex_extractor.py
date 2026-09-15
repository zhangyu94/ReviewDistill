from reviewdistill.extraction.latex import LatexCommandExtractor

TEX = r"""
\section{Results}
The results demonstrate that Model A is better.
\note{I think "demonstrate" is too strong here. The experiment only provides evidence for this claim.}

We designed the interface using a wizard.
\myremark{This paragraph does not explain why this design decision was necessary.}

\note{
Multiline comment with \emph{latex} and nested {braces}.
}

\note{Escaped brace \{ inside}
"""


def test_extracts_configured_commands_only():
    extractor = LatexCommandExtractor(commands=["note"])
    comments = extractor.extract(TEX, file_path="main.tex")
    assert [c.source_command for c in comments] == ["note", "note", "note"]
    assert comments[0].raw_text.startswith("I think")
    assert comments[0].line_number == 4
    assert comments[0].source_type == "latex_command"


def test_multiline_and_nested_braces():
    extractor = LatexCommandExtractor(commands=["note"])
    comments = extractor.extract(TEX, file_path="main.tex")
    multiline = comments[1]
    assert "Multiline comment" in multiline.raw_text
    assert "nested {braces}" in multiline.raw_text
    assert "\\emph{latex}" in multiline.raw_text


def test_escaped_brace():
    extractor = LatexCommandExtractor(commands=["note"])
    comments = extractor.extract(TEX, file_path="main.tex")
    assert "Escaped brace { inside" in comments[2].raw_text or "\\{" in comments[2].raw_text


def test_command_is_not_a_semantic_label():
    extractor = LatexCommandExtractor(commands=["myremark"])
    comments = extractor.extract(TEX, file_path="main.tex")
    assert len(comments) == 1
    assert comments[0].source_command == "myremark"
    assert "design decision" in comments[0].raw_text


def test_unclosed_brace_is_unstable_and_yields_no_comments():
    extractor = LatexCommandExtractor(commands=["myremark"])
    source = "Hello\n\\myremark{unfinished"
    comments, unstable = extractor.extract_with_status(source, file_path="main.tex")
    assert unstable is True
    assert comments == []


def test_closed_comments_are_stable():
    extractor = LatexCommandExtractor(commands=["myremark"])
    source = "Hello\n\\myremark{done.}\n"
    comments, unstable = extractor.extract_with_status(source, file_path="main.tex")
    assert unstable is False
    assert len(comments) == 1
    assert comments[0].raw_text == "done."


def test_line_commented_command_is_not_extracted():
    extractor = LatexCommandExtractor(commands=["note"])
    source = "Live text.\n% \\note{old remark}\n\\note{keep me.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [c.raw_text for c in comments] == ["keep me."]


def test_commented_multiline_command_is_not_extracted():
    extractor = LatexCommandExtractor(commands=["yzc", "myremark"])
    source = "% \\yzc{\nNeed to rewrite.\n}\n\\myremark{cite me.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [(c.source_command, c.raw_text) for c in comments] == [
        ("myremark", "cite me."),
    ]


def test_unclosed_commented_command_does_not_make_file_unstable():
    extractor = LatexCommandExtractor(commands=["yzc", "myremark"])
    source = "% \\yzc{\nno closer\n\\myremark{keep me.}\n"
    comments, unstable = extractor.extract_with_status(source, file_path="main.tex")
    assert unstable is False
    assert [c.raw_text for c in comments] == ["keep me."]


def test_escaped_percent_does_not_start_a_tex_comment():
    extractor = LatexCommandExtractor(commands=["note"])
    source = "100\\% \\note{not commented.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [c.raw_text for c in comments] == ["not commented."]


def test_percent_inside_caption_does_not_harvest_commented_command():
    extractor = LatexCommandExtractor(commands=["note"])
    source = "See Figure 1.\n\\caption{A figure. % \\note{old}}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert comments == []


def test_percent_before_closer_does_not_hide_later_command():
    extractor = LatexCommandExtractor(commands=["yzc", "myremark"])
    source = "A claim. \\yzc{tone % x} More text. \\myremark{cite me.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [(c.source_command, c.raw_text) for c in comments] == [
        ("yzc", "tone % x"),
        ("myremark", "cite me."),
    ]


def test_percent_on_multiline_closer_does_not_hide_later_command():
    extractor = LatexCommandExtractor(commands=["yzc", "myremark"])
    source = "\\yzc{foo\nbar % x} \\myremark{cite me.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [(c.source_command, c.raw_text) for c in comments] == [
        ("yzc", "foo bar % x"),
        ("myremark", "cite me."),
    ]


def test_percent_before_closer_is_still_a_complete_comment():
    extractor = LatexCommandExtractor(commands=["yzc"])
    source = "We designed the interface.\n\\yzc{Where are the tables? % check}\n"
    comments, unstable = extractor.extract_with_status(source, file_path="main.tex")
    assert unstable is False
    assert [c.raw_text for c in comments] == ["Where are the tables? % check"]


def test_optional_space_before_brace_is_extracted():
    extractor = LatexCommandExtractor(commands=["yzc"])
    source = "Hello \\yzc {Where are the tables?}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [c.raw_text for c in comments] == ["Where are the tables?"]
    assert comments[0].line_number == 1


def test_tab_before_brace_is_extracted():
    extractor = LatexCommandExtractor(commands=["note"])
    source = "Hello \\note\t{spaced.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [c.raw_text for c in comments] == ["spaced."]


def test_command_after_letter_is_extracted():
    extractor = LatexCommandExtractor(commands=["yzc"])
    source = "citation\\yzc{check this.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [c.raw_text for c in comments] == ["check this."]


def test_prefix_name_is_not_the_configured_command():
    extractor = LatexCommandExtractor(commands=["myremark"])
    source = "Hello \\notmyremark{skip} \\myremark{keep.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [c.raw_text for c in comments] == ["keep."]
