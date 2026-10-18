from playwright.sync_api import Page

class SettingsPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading_payment_info = page.get_by_text("Payment Information")
        self.heading_delete_account = page.get_by_text("Delete Your Account")
        self.input_upi_id = page.get_by_placeholder("Enter Your UPI ID").first
        self.input_current_password = page.get_by_placeholder("Current Password")
        self.input_new_password = page.get_by_placeholder("New Password")
        self.input_confirm_password = page.get_by_placeholder("Confirm Password")
        self.button_delete_account = page.get_by_role("button", name="Delete Account")

    def open(self):
        self.page.goto("https://denqr.onrender.com/settings")
