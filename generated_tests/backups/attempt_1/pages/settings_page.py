from playwright.sync_api import Page

class SettingsPage:
    def __init__(self, page: Page):
        self.page = page
        self.upi_inputs = page.get_by_placeholder("Enter Your UPI ID")
        self.current_password_input = page.get_by_placeholder("Current Password")
        self.new_password_input = page.get_by_placeholder("New Password")
        self.confirm_password_input = page.get_by_placeholder("Confirm Password")

    def open(self):
        self.page.goto("https://denqr.onrender.com/settings")
