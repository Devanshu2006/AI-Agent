from playwright.sync_api import Page, Locator

class SettingsPage:
    def __init__(self, page: Page):
        self.page = page
        self.payment_info_heading = page.get_by_role(
            "heading", name="Payment Information"
        )
        self.delete_heading = page.get_by_role(
            "heading", name="Delete Your Account"
        )
        self.account_info_button = page.get_by_role(
            "button", name="Account Information"
        )
        self.submit_upi_button = page.get_by_role(
            "button", name="Submit UPI ID"
        )
        self.update_upi_button = page.get_by_role(
            "button", name="Update UPI ID"
        )
        self.change_password_button = page.get_by_role(
            "button", name="Update"
        )
        self.delete_account_button = page.get_by_role(
            "button", name="Delete Account"
        )
        self.logout_link = page.get_by_role("link", name="Logout")

    def open(self):
        self.page.goto("https://denqr.onrender.com/settings")
