import pytest
from playwright.sync_api import expect
from generated_tests.pages.analytics_page import AnalyticsPage

def test_analytics_dashboard(auth_page):
    analytics = AnalyticsPage(auth_page)
    analytics.open()
    expect(analytics.performance_heading).to_be_visible()
    expect(analytics.home_nav).to_be_visible()
    expect(analytics.menu_nav).to_be_visible()
    expect(analytics.generate_nav).to_be_visible()
    expect(analytics.orders_nav).to_be_visible()
    expect(analytics.team_nav).to_be_visible()
    expect(analytics.settings_nav).to_be_visible()
    expect(analytics.upgrade_nav).to_be_visible()
