from linkedin_apply_assistant.linkedin_search import (
    _card_has_easy_apply_signal,
    _clean_location_text,
    _current_job_id_from_url,
    _location_from_detail_text,
    _location_from_page_header,
    _merge_raw_jobs,
    _normalize_location,
    _salary_from_text,
    _search_has_easy_apply_filter,
    _strip_linkedin_noise,
    _top_card_from_page_text,
    _to_jobs,
    _work_mode_from_text,
)


def test_easy_apply_filter_from_search_url():
    assert _search_has_easy_apply_filter("https://www.linkedin.com/jobs/search/?f_AL=true")
    assert not _search_has_easy_apply_filter("https://www.linkedin.com/jobs/search/?f_AL=false")


def test_linkedin_apply_button_marks_easy_apply():
    assert _card_has_easy_apply_signal("Apply LinkedIn Apply to this job /apply/?openSDUIApplyFlow=true")


def test_search_filter_marks_cards_easy_apply():
    jobs = list(
        _to_jobs(
            [
                {
                    "href": "https://www.linkedin.com/jobs/view/123/",
                    "title": "Software Engineer",
                    "company": "Example",
                    "location": "Mountain View, CA",
                    "text": "Software Engineer Example Mountain View",
                }
            ],
            search_is_easy_apply=True,
        )
    )
    assert jobs[0].easy_apply is True


def test_current_job_id_is_read_from_search_results_url():
    url = "https://www.linkedin.com/jobs/search-results/?currentJobId=4449213532&keywords=software"
    assert _current_job_id_from_url(url) == "4449213532"


def test_raw_job_merge_dedupes_by_job_id():
    merged = _merge_raw_jobs(
        [{"href": "https://www.linkedin.com/jobs/view/1/", "title": "A"}],
        [
            {"href": "https://www.linkedin.com/jobs/view/1/", "title": "A duplicate"},
            {"href": "https://www.linkedin.com/jobs/view/2/", "title": "B"},
        ],
    )
    assert [job["title"] for job in merged] == ["A", "B"]


def test_detail_text_is_included_in_description():
    jobs = list(
        _to_jobs(
            [
                {
                    "href": "https://www.linkedin.com/jobs/view/456/",
                    "title": "Software Engineer",
                    "company": "Example",
                    "location": "Mountain View, CA",
                    "text": "Software Engineer Example Mountain View",
                    "detail_text": "Qualifications: 8+ years of backend experience.",
                }
            ],
            search_is_easy_apply=True,
        )
    )
    assert "8+ years" in jobs[0].description


def test_detail_text_replaces_page_boilerplate_for_description():
    jobs = list(
        _to_jobs(
            [
                {
                    "href": "https://www.linkedin.com/jobs/view/789/",
                    "title": "Software Engineer",
                    "company": "Example",
                    "location": "Mountain View, CA",
                    "text": "Company profile supports Data Science and Analytics",
                    "detail_text": "About the job Build backend APIs and platform systems.",
                }
            ],
            search_is_easy_apply=True,
        )
    )
    assert "Data Science" not in jobs[0].description
    assert "Build backend APIs" in jobs[0].description


def test_require_detail_skips_card_only_jobs():
    jobs = list(
        _to_jobs(
            [
                {
                    "href": "https://www.linkedin.com/jobs/view/790/",
                    "title": "Software Engineer",
                    "company": "Example",
                    "location": "Mountain View, CA",
                    "text": "Software Engineer Example Mountain View",
                }
            ],
            search_is_easy_apply=True,
            require_detail=True,
        )
    )
    assert jobs == []


def test_linkedin_side_panels_are_stripped_from_description():
    text = (
        "About the job Build backend APIs. Requirements 3+ years Python. "
        "Set alert for similar jobs Senior Platform Engineer, San Francisco Bay Area Off "
        "See how you compare to other applicants"
    )
    cleaned = _strip_linkedin_noise(text)
    assert "Build backend APIs" in cleaned
    assert "Set alert" not in cleaned
    assert "See how you compare" not in cleaned


def test_salary_range_with_year_units_is_extracted():
    text = "$180K/yr - $250K/yr On-site Full-time"
    assert _salary_from_text(text) == "$180K/yr - $250K/yr"


def test_funding_amount_is_not_extracted_as_salary():
    text = "raised more than $125M from investors. About the role"
    assert _salary_from_text(text) == ""


def test_location_badges_are_removed():
    assert _clean_location_text("San Francisco Bay Area You’d be a top applicant Promoted") == "San Francisco Bay Area"


def test_location_is_normalized_to_structured_length():
    noisy = "San Francisco Bay Area with a lot of noisy LinkedIn badge text that should not be persisted"
    assert _normalize_location(noisy) == "San Francisco Bay Area with a lot of noisy Linked…"
    assert len(_normalize_location(noisy)) == 50


def test_precise_location_is_extracted_from_job_header():
    page_text = (
        "ByteDance Backend Software Engineer - Platforms San Jose, CA · 6 days ago · "
        "Over 100 applicants Promoted by hirer About the job"
    )
    assert _location_from_page_header("Backend Software Engineer - Platforms", page_text) == "San Jose, CA"


def test_precise_location_is_extracted_from_description_package_section():
    text = "Location & Package 📍 Location: San Francisco, CA 🏠 Working Model: Remote initially"
    assert _location_from_detail_text(text) == "San Francisco, CA"


def test_location_extraction_stops_at_plain_text_labels():
    text = (
        "Location San Francisco or New York City Company Stage: Series C "
        "Office Type: Onsite Salary: $130,000 – $400,000"
    )
    assert _location_from_detail_text(text) == "San Francisco or New York City"


def test_location_extraction_stops_at_work_model_label():
    text = "Location: San Francisco, CA Work Model: 5 Days Onsite … more Set alert"
    assert _location_from_detail_text(text) == "San Francisco, CA"


def test_location_extraction_stops_at_about_section():
    text = "Location: San Francisco About Greylock: Greylock is an early-stage investor"
    assert _location_from_detail_text(text) == "San Francisco"


def test_work_mode_prefers_hybrid_from_top_card():
    assert _work_mode_from_text("San Francisco Bay Area · $180K/yr - $210K/yr Hybrid Full-time") == "Hybrid"


def test_top_card_can_be_derived_from_page_text():
    page_text = (
        "Home Jobs FORT Senior Platform Engineer San Francisco Bay Area · 1 day ago "
        "$180K/yr - $210K/yr Hybrid Full-time Apply Save About the job Build systems."
    )
    top_card = _top_card_from_page_text("Senior Platform Engineer", page_text)
    assert "Hybrid Full-time" in top_card
    assert "About the job" not in top_card
