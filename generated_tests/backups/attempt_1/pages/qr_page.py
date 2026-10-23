from playwright.sync_api import Page, Locator

class QrPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Number of tables:")
        self.table_count_input = page.get_by_placeholder("1")
        self.generate_button = page.get_by_role("button", name="Generate")

    def open(self):
        self.page.goto("https://denqr.onrender.com/qr")
