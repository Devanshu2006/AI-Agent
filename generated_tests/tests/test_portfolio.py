import pytest
from playwright.sync_api import Page

from generated_tests.pages.portfolio_page import PortfolioPage


def test_portfolio_title_and_welcome(page: Page):
    portfolio = PortfolioPage(page)
    portfolio.navigate()
    assert portfolio.get_title() == "portfolio"
    assert portfolio.is_welcome_visible()


def test_navigation_links(page: Page):
    portfolio = PortfolioPage(page)
    portfolio.navigate()
    assert portfolio.are_nav_links_visible()


def test_work_experience_section(page: Page):
    portfolio = PortfolioPage(page)
    portfolio.navigate()
    assert portfolio.is_work_experience_visible()
    assert page.get_by_text("DenQr").is_visible()


def test_featured_work_and_skills(page: Page):
    portfolio = PortfolioPage(page)
    portfolio.navigate()
    assert portfolio.is_featured_work_visible()
    assert page.get_by_role("heading", name="Online Food Ordering System").is_visible()
    assert page.get_by_role("heading", name="Complaint Management System").is_visible()
    assert page.get_by_role("heading", name="Mobile Sales Analysis").is_visible()
    assert portfolio.is_skills_section_visible()
    assert page.locator("#skills").get_by_text("Python").first.is_visible()


def test_footer_and_contact_section(page: Page):
    portfolio = PortfolioPage(page)
    portfolio.navigate()
    assert portfolio.is_get_in_touch_visible()
    assert page.get_by_text("© 2026 All rights are reserved.").is_visible()