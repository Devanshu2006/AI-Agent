from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.staff_login_link = page.get_by_role("link", name="login").nth(1)

    def open(self):
        self.page.goto("https://denqr.onrender.com/login")

    def click_staff_login(self):
        self.staff_login_link.click()
