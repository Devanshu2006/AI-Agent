from playwright.sync_api import Page

class HomePage:
    def __init__(self, page: Page):
        self.page = page
        self.login_link = page.get_by_role("link", name="Login")
        self.signup_link = page.get_by_role("link", name="Sign Up")
        self.main_heading = page.get_by_role("heading", name="Make Ordering at Your Restaurant Effortless.")

    def open(self):
        self.page.goto("https://denqr.onrender.com/")
