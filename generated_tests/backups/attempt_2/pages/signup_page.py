from playwright.sync_api import Page, expect

class SignupPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://denqr.onrender.com/Admin"
        self.name_input = page.get_by_role("textbox", name="Full Name")
        self.email_input = page.get_by_role("textbox", name="Email")
        self.password_input = page.get_by_role("textbox", name="Password", exact=True)
        self.confirm_password_input = page.get_by_role("textbox", name="Confirm Password")
        self.continue_button = page.get_by_role("button", name="Continue")

    def load(self):
        self.page.goto(self.url)

    def verify_elements(self):
        expect(self.name_input).to_be_visible()
        expect(self.email_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.confirm_password_input).to_be_visible()
        expect(self.continue_button).to_be_visible()