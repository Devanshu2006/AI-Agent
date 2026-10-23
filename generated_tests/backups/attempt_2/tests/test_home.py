import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.home_page import HomePage

def test_homepage_elements_visible(page: Page) -> None:
    home = HomePage(page)
    home.open()
    
    expect(home.explore_heading).to_be_visible()
    expect(home.more_from_youtube_heading).to_be_visible()
    expect(home.home_link).to_be_visible()
    expect(home.subscriptions_link).to_be_visible()
    expect(home.history_link).to_be_visible()

def test_search_functionality(page: Page) -> None:
    home = HomePage(page)
    home.open()
    
    expect(home.search_input).to_be_visible()
    home.search("test query")
    expect(page).to_have_url(re.compile(r".*youtube\.com/results.*") if 're' in globals() else page.url != home.url)

def test_footer_and_secondary_links(page: Page) -> None:
    home = HomePage(page)
    home.open()
    
    expect(home.about_link).to_be_visible()
    expect(home.privacy_link).to_be_visible()
