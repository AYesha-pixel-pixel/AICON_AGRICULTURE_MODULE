from src.knowledge_base import get_disease_knowledge


SUPPORTED_LABELS = (
    "Corn___Common_Rust",
    "Corn___Gray_Leaf_Spot",
    "Rice___Brown_Spot",
    "Rice___Leaf_Blast",
    "Wheat___Brown_Rust",
    "Wheat___Yellow_Rust",
)


def test_each_supported_disease_has_separate_evidence_aware_fields():
    fields = {
        "symptoms",
        "possible_lookalikes",
        "favourable_conditions",
        "prevention",
        "immediate_safe_actions",
        "when_to_contact_expert",
    }

    for label in SUPPORTED_LABELS:
        knowledge = get_disease_knowledge(label)

        assert knowledge is not None
        assert knowledge["label"] == label
        assert fields <= knowledge.keys()
        assert knowledge["evidence_status"] == "local_verification_required"
        for field_name in fields:
            assert knowledge[field_name]["items"]
            assert (
                knowledge[field_name]["provenance_status"]
                == "local_verification_required"
            )


def test_missing_evidence_is_explicitly_marked():
    knowledge = get_disease_knowledge("Corn___Common_Rust")

    assert knowledge is not None
    assert "has been verified" in knowledge["symptoms"]["items"][0]
    assert knowledge["symptoms"]["sources"] == []


def test_unsupported_label_returns_no_knowledge():
    assert get_disease_knowledge("Invalid") is None
    assert get_disease_knowledge("Corn___Healthy") is None


def test_malformed_label_returns_no_knowledge():
    assert get_disease_knowledge(None) is None
    assert get_disease_knowledge({"label": "Corn___Common_Rust"}) is None


def test_lookup_returns_defensive_copy():
    first = get_disease_knowledge("Wheat___Brown_Rust")
    assert first is not None
    first["symptoms"]["items"].append("test mutation")

    second = get_disease_knowledge("Wheat___Brown_Rust")
    assert second is not None
    assert "test mutation" not in second["symptoms"]["items"]
