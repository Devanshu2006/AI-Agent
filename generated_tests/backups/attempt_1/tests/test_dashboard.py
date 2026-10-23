import pytest
from playwright.sync_api import expect
from generated_tests.pages.dashboard_page import DashboardPage

def test_dashboard_navigation_flow(auth_page):
    dashboard = DashboardPage(auth_page)
    dashboard.open()
    
    dashboard.goto_menu()
    expect(auth_page).to_url("https://denqr.onrender.com/menu")
    
    dashboard.goto_generate()
    expect(auth_page).to_url("https://denqr.onrender.com/qr")
    
    dashboard.goto_orders()
    expect(auth_page).to_url("https://denqr.onrender.com/kitchen_dashboard")
    
    dashboard.goto_team()
    expect(auth_page).to_url("https://denqr.onrender.com/team")
    
    dashboard.goto_settings()
    expect(auth_page).to_url("https://denqr.onrender.com/settings")
    
    dashboard.goto_upgrade()
    expect(auth_page).to_url("https://denqr.onrender.com/payment")
