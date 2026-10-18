from playwright.sync_api import Page

class SignupPage:
    def __init__(self, page: Page):
        self.page = page
        self.fullname_input = page.get_by_label("Full Name")
        self.email_input = page.get_by_label("Email")
        self.password_input = page.get_by_role("textbox", name="Password", exact=True)
        self.confirm_password_input = page.get_by_label("Confirm Password")
        self.continue_button = page.get_by_role("button", name="Continue")

    def open(self):
        self.page.goto("https://denqr.onrender.com/Admin")
