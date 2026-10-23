from playwright.sync_api import Page, Locator

class HomePage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://www.myntra.com/"
        
        # Locators using Playwright recommended practices
        self.search_input: Locator = self.page.get_by_placeholder("Search for products, brands and more")
        self.myntra_insider_link: Locator = self.page.get_by_role("link", name="Myntra Insider New")
        self.gift_card_link: Locator = self.page.get_by_role("link", name="Gift Card")
        self.track_orders_link: Locator = self.page.get_by_role("link", name="Track Orders").first
        self.contact_us_link: Locator = self.page.get_by_role("link", name="Contact Us").first

    def open(self):
        self.page.goto(self.url)

    def search_product(self, query: str):
        self.search_input.fill(query)
        self.search_input.press("Enter")

    def click_myntra_insider(self):
        self.myntra_insider_link.click()

    def click_gift_card(self):
        self.gift_card_link.click()

    def click_contact_us(self):
        self.contact_us_link.click()
