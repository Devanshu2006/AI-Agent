from playwright.sync_api import Page, expect

class ForgotPasswordPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://denqr.onrender.com/forgot_password"
        self.email_input = page.locator("input[name='email']")
        self.reset_button = page.get_by_role("button", name="Reset Password")

    def load(self):
        self.page.goto(self.url)

    def verify_elements(self):
        expect(self.email_input).to_be_visible()
        expect(self.reset_button).to_be_visible()