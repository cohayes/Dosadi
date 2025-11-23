from dosadi import (
    load_industry_catalog,
    load_info_security_catalog,
    load_military_catalog,
)


def test_industry_catalog_indexes_guild_archetypes():
    catalog = load_industry_catalog()
    assert catalog.blocks, "expected industry catalog to expose YAML blocks"
    assert "SUITS_CORE" in catalog.by_id
    suits = catalog.by_id["SUITS_CORE"]
    assert suits.root_key == "GuildArchetype"


def test_military_catalog_has_force_taxonomy_entries():
    catalog = load_military_catalog()
    assert "mil_street_enforcers" in catalog.by_id
    enforcers = catalog.by_id["mil_street_enforcers"]
    assert enforcers.payload.get("class") == "garrison"


def test_info_catalog_loads_rumor_templates():
    catalog = load_info_security_catalog()
    assert "rumor_missing_barrels" in catalog.by_id
    rumor = catalog.by_id["rumor_missing_barrels"]
    assert rumor.payload.get("payload_type") == "event"


def test_military_catalog_exposes_ci_schemas():
    catalog = load_military_catalog()
    ci_blocks = catalog.filter(root_key="CIPosture")
    assert ci_blocks
    posture = ci_blocks[0]
    assert "active_assets" in posture.payload
