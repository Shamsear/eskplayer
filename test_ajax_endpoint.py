#!/usr/bin/env python3
"""
Quick test to verify the AJAX endpoint is working
"""

import requests

# Test tournament ID (change this to a real tournament ID in your database)
TOURNAMENT_ID = 1
BASE_URL = 'http://localhost:5000'

def test_add_division():
    url = f'{BASE_URL}/admin/tournaments/{TOURNAMENT_ID}/edit'
    
    # Login first (you'll need to add your admin credentials)
    # For now, this assumes you're already logged in via browser
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    data = {
        'action': 'add_division',
        'division_name': 'Test AJAX Division',
        'division_starting_rating': '600'
    }
    
    print(f"Testing POST to: {url}")
    print(f"Headers: {headers}")
    print(f"Data: {data}")
    print("\nNote: You need to be logged in to the admin panel in your browser first!")
    print("This test requires session cookies from your browser.")

if __name__ == '__main__':
    test_add_division()
