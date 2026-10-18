from playwright.sync_api import Page

class TermsPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Terms & Conditions")

    def open(self):
        self.page.goto("https://denqr.onrender.com/terms")
