from reviewdistill.db.models import ISSUE_ACTIVE, IssueType
from reviewdistill.taxonomy.tree import (
    compact_positions,
    descendant_ids,
    is_under,
    next_new_code,
    subtree_count,
    types_to_forest,
)


def _t(id, *, parent=None, position=0, name="n", code=None):
    return IssueType(
        id=id,
        code=code or id,
        name=name,
        parent_id=parent,
        position=position,
        definition="",
        status=ISSUE_ACTIVE,
    )


def test_descendants_and_cycle_check():
    types = [
        _t("root"),
        _t("a", parent="root", position=0),
        _t("b", parent="a", position=0),
        _t("c", parent="root", position=1),
    ]
    assert descendant_ids(types, "root") == {"a", "b", "c"}
    assert is_under(types, child="b", ancestor="root")
    assert not is_under(types, child="root", ancestor="a")
    assert is_under(types, child="a", ancestor="a")


def test_descendant_ids_can_include_inactive():
    types = [
        _t("root"),
        _t("a", parent="root"),
    ]
    types[1].status = "inactive"
    assert descendant_ids(types, "root") == set()
    assert descendant_ids(types, "root", active_only=False) == {"a"}


def test_compact_positions_orders_siblings():
    types = [_t("b", position=9, name="B"), _t("a", position=3, name="A")]
    compact_positions(types, None)
    by_id = {row.id: row.position for row in types}
    assert by_id == {"a": 0, "b": 1}


def test_forest_and_subtree_count():
    types = [_t("root", name="Root"), _t("leaf", parent="root", name="Leaf")]
    own = {"root": 1, "leaf": 4}
    forest = types_to_forest(types, own)
    assert forest[0]["id"] == "root"
    assert forest[0]["count"] == 5
    assert forest[0]["children"][0]["count"] == 4
    assert subtree_count(own, descendant_ids(types, "root") | {"root"}) == 5


def test_next_new_code_skips_taken():
    assert next_new_code(["NEW", "NEW_2"]) == "NEW_3"
    assert next_new_code([]) == "NEW"
