from playwright.sync_api import Page

class QrPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading_tables = page.get_by_text("Number of tables:")
        self.input_table_count = page.get_by_placeholder("1")
        self.button_generate = page.get_by_role("button", name="Generate")

    def open(self):
        self.page.goto("https://denqr.onrender.com/qr")
