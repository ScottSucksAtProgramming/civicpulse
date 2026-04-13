from civicpulse.scraper.cleaner import ContentCleaner


def test_strips_nav_and_footer(department_html):
    result = ContentCleaner().clean(department_html)
    assert "Navigation links here" not in result
    assert "Footer content here" not in result


def test_extracts_main_content(department_html):
    result = ContentCleaner().clean(department_html)
    assert "Department Directory" in result
    assert "Public Works" in result


def test_emits_markdown_headings(department_html):
    result = ContentCleaner().clean(department_html)
    assert "## Department Directory" in result or "# Department Directory" in result


def test_collapses_excess_newlines():
    html = "<html><body><main><p>A</p>\n\n\n\n\n<p>B</p></main></body></html>"
    result = ContentCleaner().clean(html)
    assert "\n\n\n" not in result
