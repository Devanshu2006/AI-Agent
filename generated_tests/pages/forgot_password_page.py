from playwright.sync_api import Page

class ForgotPasswordPage:
    def __init__(self, page: Page):
        self.page = page
        self.reset_button = page.get_by_role("button", name="Reset Password")

    def open(self):
        self.page.goto("https://denqr.onrender.com/forgot_password")
