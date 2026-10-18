from playwright.sync_api import expect
from generated_tests.pages.team_page import TeamPage

def test_team_page(auth_page):
    team = TeamPage(auth_page)
    team.open()
    expect(team.heading_add_staff).to_be_visible()
    expect(team.input_member_count).to_be_visible()
    expect(team.button_enter).to_be_visible()
