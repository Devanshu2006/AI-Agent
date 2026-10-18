from playwright.sync_api import expect
from generated_tests.pages.analytics_page import AnalyticsPage

def test_analytics_page(auth_page):
    analytics = AnalyticsPage(auth_page)
    analytics.open()
    expect(analytics.heading_restaurant).to_be_visible()
    expect(analytics.heading_performance).to_be_visible()
    expect(analytics.link_menu).to_be_visible()
    expect(analytics.link_generate).to_be_visible()
    expect(analytics.link_orders).to_be_visible()
    expect(analytics.link_team).to_be_visible()
    expect(analytics.link_settings).to_be_visible()
    expect(analytics.link_upgrade).to_be_visible()
