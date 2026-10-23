import pytest
from playwright.sync_api import expect
from generated_tests.pages.team_page import TeamPage

def test_team_page_elements(auth_page):
    team = TeamPage(auth_page)
    team.open()
    expect(team.heading).to_be_visible()
    expect(team.member_count_input).to_be_visible()
    expect(team.enter_button).to_be_visible()
