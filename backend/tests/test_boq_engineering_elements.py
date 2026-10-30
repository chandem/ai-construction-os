from app.engineering_elements import engineering_elements_from_boq_items


def test_boq_rows_become_proposed_elements_without_invented_dimensions():
    rows = engineering_elements_from_boq_items(
        [
            {
                "id": "boq-1",
                "item_code": "A.01",
                "work_section": "Earthworks",
                "description": "Excavate foundation trenches",
                "element_type": None,
                "quantity": 125.5,
                "unit": "m3",
                "status": "approved",
            },
            {
                "id": "boq-2",
                "description": "Unclassified construction activity",
                "quantity": None,
                "unit": None,
            },
        ],
        project_id="project-1",
    )

    assert len(rows) == 2
    assert rows[0]["element_type"] == "foundation"
    assert rows[0]["quantity"] == 125.5
    assert rows[0]["unit"] == "m3"
    assert rows[0]["dimensions"] == {}
    assert rows[0]["status"] == "proposed"
    assert rows[0]["source"] == "boq_import"
    assert rows[0]["properties"]["source_boq_item_id"] == "boq-1"
    assert rows[1]["element_type"] == "other"
    assert rows[1]["quantity"] is None


def test_boq_rows_without_id_or_description_are_ignored():
    rows = engineering_elements_from_boq_items(
        [{"id": "missing-description"}, {"description": "No source id"}],
        project_id="project-1",
    )
    assert rows == []
