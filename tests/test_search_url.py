from linkedin_apply_assistant.search_url import build_linkedin_search_url


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

