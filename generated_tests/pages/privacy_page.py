from playwright.sync_api import Page

class PrivacyPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Our Privacy Policy")

    def open(self):
        self.page.goto("https://denqr.onrender.com/privacy")
