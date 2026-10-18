from playwright.sync_api import Page

class TeamPage:
    def __init__(self, page: Page):
        self.page = page
        self.member_count_input = page.get_by_label("Number of Members:")
        self.enter_button = page.get_by_role("button", name="Enter..")

    def open(self):
        self.page.goto("https://denqr.onrender.com/team")
