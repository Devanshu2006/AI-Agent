from playwright.sync_api import Page, expect

class StaffLoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://denqr.onrender.com/staff_login"
        self.name_input = page.get_by_role("textbox", name="Name")
        self.role_input = page.locator("input[name='role']")
        self.phone_input = page.get_by_role("spinbutton", name="phone")
        self.login_button = page.get_by_role("button", name="Login")

    def load(self):
        self.page.goto(self.url)

    def verify_elements(self):
        expect(self.name_input).to_be_visible()
        expect(self.role_input).to_be_visible()
        expect(self.phone_input).to_be_visible()
        expect(self.login_button).to_be_visible()