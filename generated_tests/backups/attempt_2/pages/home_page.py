from playwright.sync_api import Page, Locator

class HomePage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://www.youtube.com/"
        
        # Locators using Playwright best practices (roles, placeholders, text)
        self.search_input: Locator = self.page.get_by_placeholder("Search")
        self.search_button: Locator = self.page.locator("button.ytSearchboxComponentSearchButton")
        self.skip_nav_button: Locator = self.page.get_by_text("Skip navigation")
        self.home_link: Locator = self.page.get_by_role("link", name="Home")
        self.subscriptions_link: Locator = self.page.get_by_role("link", name="Subscriptions")
        self.history_link: Locator = self.page.get_by_role("link", name="History")
        self.explore_heading: Locator = self.page.get_by_text("Explore")
        self.more_from_youtube_heading: Locator = self.page.get_by_text("More from YouTube")
        self.about_link: Locator = self.page.get_by_role("link", name="About")
        self.privacy_link: Locator = self.page.get_by_role("link", name="Privacy")

    def open(self) -> None:
        self.page.goto(self.url)

    def search(self, query: str) -> None:
        self.search_input.fill(query)
        self.search_button.click()
