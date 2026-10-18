from playwright.sync_api import Page

class StaffLoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.name_input = page.get_by_label("Name:")
        self.login_button = page.get_by_role("button", name="Login")

    def open(self):
        self.page.goto("https://denqr.onrender.com/staff_login")
