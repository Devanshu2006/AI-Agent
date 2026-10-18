from playwright.sync_api import Page

class MenuPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading_add_menu = page.get_by_text("Add Your Restaurant/Hotel Menu")
        self.input_item_count = page.get_by_label("How many items do you want to add?")
        self.button_enter = page.get_by_role("button", name="Enter..")

    def open(self):
        self.page.goto("https://denqr.onrender.com/menu")
