from playwright.sync_api import Page, Locator

class PaymentPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Your Journey Begins Here: Choose Your Plan")
        self.basic_heading = page.get_by_role("heading", name="Basic", exact=True)
        self.moderate_heading = page.get_by_role("heading", name="Moderate", exact=True)
        self.premium_heading = page.get_by_role("heading", name="Premium", exact=True)
        self.yearly_heading = page.get_by_role("heading", name="Yearly/Premium Plan")

    def open(self):
        self.page.goto("https://denqr.onrender.com/payment")
