import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.home_page import HomePage

def test_myntra_insider_navigation(page: Page):
    home = HomePage(page)
    home.open()
    home.click_myntra_insider()
    expect(page).to_have_url("https://www.myntra.com/myntrainsider?cache=false")

def test_gift_card_navigation(page: Page):
    home = HomePage(page)
    home.open()
    home.click_gift_card()
    expect(page).to_have_url("https://www.myntra.com/giftcard")

def test_contact_us_navigation(page: Page):
    home = HomePage(page)
    home.open()
    home.click_contact_us()
    expect(page).to_have_url("https://www.myntra.com/contactus")
