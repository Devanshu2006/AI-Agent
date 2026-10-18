from playwright.sync_api import Page

class PaymentPage:
    def __init__(self, page: Page):
        self.page = page
        self.basic_heading = page.get_by_role(
            "heading", name="Basic", exact=True
        )
        self.moderate_heading = page.get_by_role("heading", name="Moderate")

    def open(self):
        self.page.goto("https://denqr.onrender.com/payment")
