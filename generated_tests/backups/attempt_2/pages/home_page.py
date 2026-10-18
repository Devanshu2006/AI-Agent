from playwright.sync_api import Page, expect

class HomePage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://www.youtube.com/"
        self.search_input = self.page.get_by_placeholder("Search")
        self.search_button = self.page.locator("button.ytSearchboxComponentSearchButton")
        self.explore_heading = self.page.locator("text=Explore").first
        self.more_from_youtube_heading = self.page.locator("text=More from YouTube").first
        self.try_searching_heading = self.page.get_by_text("Try searching to get started")
        self.home_link = self.page.get_by_role("link", name="Home", exact=True)
        self.subscriptions_link = self.page.get_by_role("link", name="Subscriptions")
        self.you_link = self.page.get_by_role("link", name="You")
        self.history_link = self.page.get_by_role("link", name="History")
        self.sign_in_link = self.page.get_by_role("link", name="Sign in").first

    def open(self):
        self.page.goto(self.url)

    def verify_headings(self):
        expect(self.explore_heading).to_be_visible()
        expect(self.more_from_youtube_heading).to_be_visible()
        expect(self.try_searching_heading).to_be_visible()

    def verify_search_controls(self):
        expect(self.search_input).to_be_visible()
        expect(self.search_button).to_be_visible()

    def verify_navigation_links(self):
        expect(self.home_link).to_be_visible()
        expect(self.subscriptions_link).to_be_visible()
        expect(self.you_link).to_be_visible()
        expect(self.history_link).to_be_visible()
        expect(self.sign_in_link).to_be_visible()
