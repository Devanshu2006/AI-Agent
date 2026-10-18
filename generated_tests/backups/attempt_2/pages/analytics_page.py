from playwright.sync_api import Page

class AnalyticsPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading_restaurant = page.get_by_text("Zehnaseeb")
        self.heading_performance = page.get_by_text("📊 Last 7 Days Performance")
        
        # Navigation Links
        self.link_home = page.get_by_role("link", name="Home")
        self.link_menu = page.get_by_role("link", name="Menu")
        self.link_generate = page.get_by_role("link", name="Generate")
        self.link_orders = page.get_by_role("link", name="Orders")
        self.link_team = page.get_by_role("link", name="Team")
        self.link_settings = page.get_by_role("link", name="Settings")
        self.link_upgrade = page.get_by_role("link", name="Upgrade")

    def open(self):
        self.page.goto("https://denqr.onrender.com/Analytics")
