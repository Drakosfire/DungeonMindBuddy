"""Fixture parity at conservative table-caption admission boundaries."""
from evals.inline_prose_targeting.native_fixture import catalog_for

def text(kind, value, **attrs):
    return dict(type=kind, attrs=attrs, content=[dict(type="text", text=value)])

def test_caption_heading_is_not_a_section_and_caption_paragraph_not_a_target():
    doc=dict(type="doc", content=[text("heading","Preparation",level=2),
        text("heading","Table title",level=2),dict(type="table",content=[]),
        text("paragraph","Caption paragraph"),dict(type="table",content=[]),
        text("paragraph","Eligible passage")])
    choices, targets=catalog_for(doc)
    assert len(choices)==3
    assert {choice["section"] for choice in choices}=={"Preparation"}
    assert choices[0]["selector"]=="passage2:replace_paragraph"
    assert {choice["passage"] for choice in choices}=={"Eligible passage"}

def test_marked_or_identified_heading_is_not_plain_table_caption():
    heading=text("heading","Real section",level=2,id="stable")
    choices,_=catalog_for(dict(type="doc",content=[heading,dict(type="table",content=[]),text("paragraph","Prose")]))
    assert choices[0]["section"]=="Real section"
