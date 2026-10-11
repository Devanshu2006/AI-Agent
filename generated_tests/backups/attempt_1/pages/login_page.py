from playwright.sync_api import Page, Locator


class LoginPage:

    def __init__(self, page: Page):
        self.page = page
        self.username_input: Locator = page.get_by_placeholder("INVALID_USERNAME")
        self.password_input: Locator = page.get_by_placeholder("Password")
        self.login_button: Locator = page.get_by_role("button", name="Login")
        self.app_logo: Locator = page.get_by_text("Swag Labs")
        self.credentials_heading: Locator = page.get_by_text("Accepted usernames are:")

    def navigate(self):
        self.page.goto("https://www.saucedemo.com/")

    def login(self, username: str, password: str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def get_title(self) -> str:
        return self.page.title()