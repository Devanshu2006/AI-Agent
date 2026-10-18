from playwright.sync_api import Page

class AnalyticsPage:
    def __init__(self, page: Page):
        self.page = page
        self.performance_heading = page.get_by_role("heading", name="📊 Last 7 Days Performance")
        self.menu_link = page.get_by_role("link", name="Menu")

    def open(self):
        self.page.goto("https://denqr.onrender.com/Analytics")
