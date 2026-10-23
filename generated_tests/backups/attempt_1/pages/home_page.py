from playwright.sync_api import Page

class HomePage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://www.myntra.com/"
        self.search_input = page.get_by_placeholder("Search for products, brands and more")
        self.myntra_insider_link = page.get_by_text("Myntra Insider New", exact=True)
        self.gift_card_link = page.get_by_text("Gift Card", exact=True)
        self.contact_us_link = page.get_by_text("Contact Us", exact=True)

    def open(self):
        self.page.goto(self.url)

    def click_myntra_insider(self):
        self.myntra_insider_link.click()

    def click_gift_card(self):
        self.gift_card_link.click()

    def click_contact_us(self):
        self.contact_us_link.click()
