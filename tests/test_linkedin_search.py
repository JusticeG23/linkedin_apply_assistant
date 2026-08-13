from linkedin_apply_assistant.linkedin_search import (
    _card_has_easy_apply_signal,
    _salary_from_text,
    _search_has_easy_apply_filter,
    _to_jobs,
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


def test_salary_range_with_year_units_is_extracted():
    text = "$180K/yr - $250K/yr On-site Full-time"
    assert _salary_from_text(text) == "$180K/yr - $250K/yr"


def test_funding_amount_is_not_extracted_as_salary():
    text = "raised more than $125M from investors. About the role"
    assert _salary_from_text(text) == ""
