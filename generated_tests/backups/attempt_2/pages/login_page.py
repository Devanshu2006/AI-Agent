from playwright.sync_api import Page, expect

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://denqr.onrender.com/login"
        self.username_input = page.get_by_role("textbox", name="Email/Phone")
        self.password_input = page.get_by_role("textbox", name="Password")
        self.login_button = page.get_by_role("button", name="Login")
        self.forgot_password_link = page.get_by_role("link", name="Forgot Password?")
        self.staff_login_link = page.get_by_role("link", name="login")

    def load(self):
        self.page.goto(self.url)

    def verify_elements(self):
        expect(self.username_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.login_button).to_be_visible()