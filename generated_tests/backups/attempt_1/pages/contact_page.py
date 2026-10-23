from playwright.sync_api import Page

class ContactPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Contact Us")
        self.support_email = page.get_by_role("link", name="support@den-qr.com")

    def open(self):
        self.page.goto("https://denqr.onrender.com/contact")
