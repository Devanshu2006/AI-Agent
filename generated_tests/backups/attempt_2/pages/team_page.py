from playwright.sync_api import Page

class TeamPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading_add_staff = page.get_by_text("Add Restaurant/Hotel Staff")
        self.input_member_count = page.get_by_label("Number of Members:")
        self.button_enter = page.get_by_role("button", name="Enter..")

    def open(self):
        self.page.goto("https://denqr.onrender.com/team")
