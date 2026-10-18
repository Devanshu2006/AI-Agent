import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.analytics_page import AnalyticsPage

def test_analytics_dashboard(auth_page: Page):
    analytics = AnalyticsPage(auth_page)
    analytics.open()
    expect(analytics.performance_heading).to_be_visible()
    expect(analytics.menu_link).to_be_visible()
