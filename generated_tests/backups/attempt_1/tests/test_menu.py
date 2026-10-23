import pytest
from playwright.sync_api import expect
from generated_tests.pages.menu_page import MenuPage

def test_menu_page_elements(auth_page):
    menu = MenuPage(auth_page)
    menu.open()
    expect(menu.heading).to_be_visible()
    expect(menu.item_count_input).to_be_visible()
    expect(menu.enter_button).to_be_visible()
