from playwright.sync_api import Page

class ShippingPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Shipping & Delivery Policy")
        self.back_home_link = page.get_by_role("link", name="← Go Back Home")

    def open(self):
        self.page.goto("https://denqr.onrender.com/shipping")
