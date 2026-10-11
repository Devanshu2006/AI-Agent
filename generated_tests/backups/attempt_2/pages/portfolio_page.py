from playwright.sync_api import Page


class PortfolioPage:

    def __init__(self, page: Page):
        self.page = page
        self.url = "https://devanshu-girare.onrender.com/"
        self.welcome_heading = page.get_by_role("heading", name="Welcome to my Portfolio.")
        self.overview_link = page.get_by_role("link", name="Overview")
        self.projects_link = page.get_by_role("link", name="Projects")
        self.skills_link = page.get_by_role("link", name="Skills")
        self.contact_link = page.get_by_role("link", name="Contact")
        self.download_resume_button = page.get_by_role("button", name="Download Resume")
        self.work_experience_heading = page.get_by_role("heading", name="Work Experience")
        self.featured_work_heading = page.get_by_role("heading", name="Featured Work")
        self.skills_heading = page.get_by_role("heading", name="My Skills")
        self.get_in_touch_heading = page.get_by_role("heading", name="Get In Touch")

    def navigate(self):
        self.page.goto(self.url)

    def get_title(self) -> str:
        return self.page.title()

    def is_welcome_visible(self) -> bool:
        return self.welcome_heading.is_visible()

    def are_nav_links_visible(self) -> bool:
        return (
            self.projects_link.is_visible()
            and self.skills_link.is_visible()
            and self.contact_link.is_visible()
        )

    def is_work_experience_visible(self) -> bool:
        return self.work_experience_heading.is_visible()

    def is_featured_work_visible(self) -> bool:
        return self.featured_work_heading.is_visible()

    def is_skills_section_visible(self) -> bool:
        return self.skills_heading.is_visible()

    def is_get_in_touch_visible(self) -> bool:
        return self.get_in_touch_heading.is_visible()