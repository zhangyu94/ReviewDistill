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


def test_escaped_percent_does_not_start_a_tex_comment():
    extractor = LatexCommandExtractor(commands=["note"])
    source = "100\\% \\note{not commented.}\n"
    comments = extractor.extract(source, file_path="main.tex")
    assert [c.raw_text for c in comments] == ["not commented."]
