from playwright.sync_api import Page

class ContactPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Contact Us")

    def open(self):
        self.page.goto("https://denqr.onrender.com/contact")
