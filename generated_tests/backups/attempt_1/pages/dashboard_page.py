from playwright.sync_api import Page

class DashboardPage:
    def __init__(self, page: Page):
        self.page = page
        self.menu_link = page.get_by_role("link", name="Menu")
        self.generate_link = page.get_by_role("link", name="Generate")
        self.orders_link = page.get_by_role("link", name="Orders")
        self.team_link = page.get_by_role("link", name="Team")
        self.settings_link = page.get_by_role("link", name="Settings")
        self.upgrade_link = page.get_by_role("link", name="Upgrade")

    def open(self):
        self.page.goto("https://denqr.onrender.com/Analytics")

    def goto_menu(self):
        self.menu_link.click()

    def goto_generate(self):
        self.generate_link.click()

    def goto_orders(self):
        self.orders_link.click()

    def goto_team(self):
        self.team_link.click()

    def goto_settings(self):
        self.settings_link.click()

    def goto_upgrade(self):
        self.upgrade_link.click()
