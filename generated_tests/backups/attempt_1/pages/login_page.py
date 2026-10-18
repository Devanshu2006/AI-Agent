from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.email_input = page.get_by_label("Email/Phone:")
        self.password_input = page.get_by_label("Password:")
        self.login_button = page.get_by_role("button", name="Login")

    def open(self):
        self.page.goto("https://denqr.onrender.com/login")
