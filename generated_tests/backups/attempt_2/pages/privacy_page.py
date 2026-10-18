from playwright.sync_api import Page, expect

class PrivacyPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://denqr.onrender.com/privacy"
        self.heading = page.get_by_role("heading", name="Our Privacy Policy")

    def load(self):
        self.page.goto(self.url)

    def verify_elements(self):
        expect(self.heading).to_be_visible()