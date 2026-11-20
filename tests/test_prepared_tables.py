import json
import pytest
from application_state.play.prepared_tables import read_prepared_tables


def source(**changes):
    table = dict(schema_version="dmb_roll_table_v1", table_id="table:weather", title="Weather", die_sides=6,
                 rows=[dict(row_id="row:dry", min=1, max=2, outcome="Dry"), dict(row_id="row:rain", min=3, max=6, outcome="Rain")])
    table.update(changes)
    return '```dmb-roll-table-v1\n' + json.dumps(table) + '\n```'


def test_ranges_and_identity():
    table, = read_prepared_tables(source())
    assert [table.resolve(x).row_id for x in (1, 2, 3, 6)] == ["row:dry", "row:dry", "row:rain", "row:rain"]
    assert table.content_sha256 == read_prepared_tables(source())[0].content_sha256
    for bad in (0, 7, True, 1.5, "2"):
        with pytest.raises(ValueError):
            table.resolve(bad)


@pytest.mark.parametrize("changes", [dict(die_sides=True), dict(die_sides="6"), dict(title=" "), dict(schema_version="later"), dict(extra=1), dict(rows=[]), dict(rows=[dict(row_id="row:x", min=2, max=6, outcome="x")])])
def test_invalid(changes):
    with pytest.raises(ValueError):
        read_prepared_tables(source(**changes))


def test_examples_duplicate_keys_ids_and_unclosed():
    assert read_prepared_tables('````markdown\n' + source() + '\n````') == []
    assert read_prepared_tables('| d6 | weather |\n|---|---|\n|1-6|rain|') == []
    for invalid in (source() + '\n' + source(), source().removesuffix('```'), source().replace('"Weather"', '"Weather", "title":"Again"')):
        with pytest.raises(ValueError):
            read_prepared_tables(invalid)


def test_only_real_top_level_markdown_fences_are_members():
    block=source()
    assert read_prepared_tables('<!--\n'+block+'\n-->')==[]
    assert read_prepared_tables('- example\n\n'+ '\n'.join('  '+line for line in block.splitlines()))==[]
    assert read_prepared_tables('---\nexample: |\n'+ '\n'.join('  '+line for line in block.splitlines())+'\n---\n# Actual document')==[]
