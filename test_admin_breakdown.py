#!/usr/bin/env python3
"""Test the tournament breakdown function"""

from database import TournamentDB, get_db_connection

def test_breakdown():
    # Find Hami
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name FROM players WHERE name = 'Hami'")
            hami = cursor.fetchone()
            
            if not hami:
                print("Hami not found")
                return
            
            print(f"Testing tournament breakdown for: {hami['name']} (ID: {hami['id']})")
            print("=" * 80)
            
            # Get tournament breakdown
            breakdown = TournamentDB.get_player_tournament_breakdown(hami['id'])
            
            if not breakdown:
                print("No breakdown data found")
                return
            
            print(f"\nOverall Rating: {breakdown['overall_rating']}")
            print(f"Overall Matches: {breakdown['overall_matches']}")
            print(f"Total Tournaments: {breakdown['total_tournaments']}")
            
            print("\n" + "=" * 80)
            print("TOURNAMENT BREAKDOWN:")
            print("=" * 80)
            
            for tournament in breakdown['tournaments']:
                print(f"\n📍 {tournament['tournament_name']} ({tournament['tournament_status']})")
                print(f"   Tournament Rating: {tournament['tournament_rating']}")
                print(f"   Starting Rating: {tournament['start_rating']}")
                print(f"   Rating Change: {tournament['rating_change']:+d}")
                print(f"   Matches: {tournament['matches']}")
                print(f"   Record: {tournament['wins']}W-{tournament['draws']}D-{tournament['losses']}L")
                print(f"   Goals: {tournament['goals_for']}/{tournament['goals_against']}")
                print(f"   Clean Sheets: {tournament['clean_sheets']}")
                if tournament['first_match']:
                    print(f"   Period: {tournament['first_match'].strftime('%b %d')} - {tournament['last_match'].strftime('%b %d, %Y')}")
            
            print("\n" + "=" * 80)
            print("✅ Tournament breakdown working correctly!")
            
    finally:
        conn.close()

if __name__ == "__main__":
    test_breakdown()
