from linkedin_apply_assistant.job_sections import section_headers, section_text, split_job_sections


def test_splits_linkedin_basic_and_preferred_sections():
    sections = split_job_sections(
        "About the job Build infrastructure. "
        "Basic Qualifications 2+ years with Java or Python. "
        "Preferred Qualifications Experience with PyTorch or TensorFlow. "
        "Suggested Skills Distributed Systems"
    )

    assert section_headers(sections, {"required"}) == ["Basic Qualifications"]
    assert section_headers(sections, {"preferred"}) == ["Preferred Qualifications", "Suggested Skills"]
    assert "2+ years" in section_text(sections, {"required"})
    assert "PyTorch" in section_text(sections, {"preferred"})


def test_splits_recruiter_style_sections():
    sections = split_job_sections(
        "About the Company Fast AI startup. "
        "The Role Build full-stack product surfaces. "
        "What We're Looking For 3-7 years backend or full-stack experience. "
        "Bonus Points Kubernetes experience."
    )

    assert section_headers(sections, {"responsibilities"}) == ["The Role"]
    assert section_headers(sections, {"required"}) == ["What We're Looking For"]
    assert section_headers(sections, {"preferred"}) == ["Bonus Points"]


def test_minimum_requirements_is_required_section():
    sections = split_job_sections(
        "About the job Build backend services. "
        "Minimum Requirements 3+ years with Python and distributed systems. "
        "Preferred Qualifications Kubernetes experience."
    )

    assert section_headers(sections, {"required"}) == ["Minimum Requirements"]
    assert "3+ years" in section_text(sections, {"required"})


def test_ignores_lowercase_header_words_inside_sentences():
    sections = split_job_sections(
        "Minimum Qualifications Experience with platforms required for the role. "
        "Experience depends on qualifications, skills, competencies and location."
    )

    assert section_headers(sections, {"required"}) == ["Minimum Qualifications"]
    assert section_headers(sections, {"responsibilities"}) == []
    assert section_headers(sections, {"qualifications"}) == []


def test_nested_split_recovers_sections_from_single_blob():
    sections = split_job_sections(
        "About Wealthfront Engineering We build automated financial products. "
        "You will build backend services and production automation. "
        "You have 3+ years of backend engineering experience with distributed systems. "
        "Bonus experience with financial products."
    )

    assert section_headers(sections, {"overview"}) == ["About Wealthfront Engineering"]
    assert section_headers(sections, {"responsibilities"}) == ["You will"]
    assert section_headers(sections, {"required"}) == ["You have"]
    assert section_headers(sections, {"preferred"}) == ["Bonus"]
    assert "3+ years" in section_text(sections, {"required"})


def test_nested_split_prefers_about_you_over_repeated_you_have():
    sections = split_job_sections(
        "About Wealthfront Engineering Build systems. "
        "You’ll build backend services. "
        "About You You have 2-6 years of backend experience. "
        "You have SQL experience. You have passion for testing."
    )

    assert section_headers(sections, {"required"}) == ["About You"]
    assert "2-6 years" in section_text(sections, {"required"})
    assert "SQL experience" in section_text(sections, {"required"})


def test_nested_split_avoids_sentence_fragment_matches():
    sections = split_job_sections(
        "This role is a good fit when you have curiosity and product sense. "
        "The team builds backend services for users."
    )

    assert len(sections) == 1
    assert sections[0].kind == "unknown"
