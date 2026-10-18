from playwright.sync_api import Page

class RefundPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Refund Policy")

    def open(self):
        self.page.goto("https://denqr.onrender.com/refund")
