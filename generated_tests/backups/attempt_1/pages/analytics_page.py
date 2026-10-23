from playwright.sync_api import Page, Locator

class AnalyticsPage:
    def __init__(self, page: Page):
        self.page = page
        self.performance_heading = page.get_by_role("heading", name="📊 Last 7 Days Performance")
        self.home_nav = page.get_by_role("link", name="Home")
        self.menu_nav = page.get_by_role("link", name="Menu")
        self.generate_nav = page.get_by_role("link", name="Generate")
        self.orders_nav = page.get_by_role("link", name="Orders")
        self.team_nav = page.get_by_role("link", name="Team")
        self.settings_nav = page.get_by_role("link", name="Settings")
        self.upgrade_nav = page.get_by_role("link", name="Upgrade")

    def open(self):
        self.page.goto("https://denqr.onrender.com/Analytics")
