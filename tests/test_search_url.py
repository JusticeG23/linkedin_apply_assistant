from linkedin_apply_assistant.search_url import build_linkedin_search_url, load_search_presets


def test_builds_linkedin_search_url_from_preset():
    preset = {
        "keywords": "software engineer backend platform",
        "location": "Mountain View, California, United States",
        "distance": 10,
        "easy_apply": True,
        "posted_within": "r604800",
        "sort_by": "DD",
        "work_type": ["onsite", "hybrid"],
        "experience": ["mid_senior"],
    }
    url = build_linkedin_search_url(preset)
    assert "keywords=software+engineer+backend+platform" in url
    assert "location=Mountain+View%2C+California%2C+United+States" in url
    assert "f_AL=true" in url
    assert "f_WT=1%2C3" in url
    assert "f_E=4" in url


def test_load_search_presets_merges_defaults(tmp_path):
    config = tmp_path / "searches.yaml"
    config.write_text(
        """
defaults:
  location: "Mountain View, California, United States"
  distance: 10
  easy_apply: true
  work_type:
    - onsite
    - hybrid
backend_platform:
  keywords: "software engineer backend"
data_platform:
  keywords: "data platform"
  distance: 25
""",
        encoding="utf-8",
    )

    presets = load_search_presets(config)

    assert "defaults" not in presets
    assert presets["backend_platform"]["location"] == "Mountain View, California, United States"
    assert presets["backend_platform"]["distance"] == 10
    assert presets["backend_platform"]["work_type"] == ["onsite", "hybrid"]
    assert presets["data_platform"]["distance"] == 25
