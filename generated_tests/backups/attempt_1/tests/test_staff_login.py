import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.staff_login_page import StaffLoginPage

def test_staff_login_page_elements(page: Page):
    staff = StaffLoginPage(page)
    staff.open()
    expect(staff.name_input).to_be_visible()
    expect(staff.login_button).to_be_visible()
