from playwright.sync_api import expect
from generated_tests.pages.menu_page import MenuPage

def test_menu_page(auth_page):
    menu = MenuPage(auth_page)
    menu.open()
    expect(menu.heading_add_menu).to_be_visible()
    expect(menu.input_item_count).to_be_visible()
    expect(menu.button_enter).to_be_visible()
