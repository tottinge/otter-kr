from otter_kr.representation_inventory import RepresentationInventory


def test_inventory_composes_measurements_without_judgment() -> None:
    report = RepresentationInventory({}, {}, {}, {})

    assert set(report.to_dict()) == {"hotspots", "duplicates", "repeated_groups", "distributions"}
