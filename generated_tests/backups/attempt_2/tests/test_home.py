import pytest
from playwright.sync_api import Page
from generated_tests.pages.home_page import HomePage

def test_homepage_headings(page: Page):
    home = HomePage(page)
    home.open()
    home.verify_headings()

def test_homepage_search_controls(page: Page):
    home = HomePage(page)
    home.open()
    home.verify_search_controls()

def test_homepage_navigation_links(page: Page):
    home = HomePage(page)
    home.open()
    home.verify_navigation_links()
