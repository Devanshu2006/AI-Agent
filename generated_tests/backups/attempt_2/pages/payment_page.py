from playwright.sync_api import Page

class PaymentPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading_journey = page.get_by_text("Your Journey Begins Here: Choose Your Plan")
        self.heading_basic = page.get_by_role("heading", name="Basic")
        self.heading_moderate = page.get_by_role("heading", name="Moderate")
        self.heading_premium = page.get_by_role("heading", name="Premium")
        self.heading_yearly = page.get_by_role("heading", name="Yearly/Premium Plan")

    def open(self):
        self.page.goto("https://denqr.onrender.com/payment")
