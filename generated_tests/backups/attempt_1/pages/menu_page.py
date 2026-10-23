from playwright.sync_api import Page, Locator

class MenuPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Add Your Restaurant/Hotel Menu")
        self.item_count_input = page.get_by_label("How many items do you want to add?")
        self.enter_button = page.get_by_role("button", name="Enter..")

    def open(self):
        self.page.goto("https://denqr.onrender.com/menu")
