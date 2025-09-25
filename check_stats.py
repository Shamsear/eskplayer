#!/usr/bin/env python3
"""Check match data and statistics calculations"""

from database import TournamentDB, get_db_connection

def check_match_data():
    """Check what match data exists in the database"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Check total matches
            cursor.execute("SELECT COUNT(*) as count FROM player_matches")
            total_matches = cursor.fetchone()['count']
            print(f"Total matches in database: {total_matches}")
            
            # Check recent matches
            cursor.execute("""
                SELECT pm.*, p1.name as player1_name, p2.name as player2_name
                FROM player_matches pm
                JOIN players p1 ON pm.player1_id = p1.id
                JOIN players p2 ON pm.player2_id = p2.id
                ORDER BY pm.played_at DESC
                LIMIT 10
            """)
            matches = cursor.fetchall()
            
            print("\nRecent matches:")
            for match in matches:
                print(f"  {match['player1_name']} {match['player1_goals']}-{match['player2_goals']} {match['player2_name']}")
                
            # Check player stats for Pachu specifically
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_matches,
                    SUM(CASE 
                        WHEN (pm.player1_id = %s AND pm.player1_goals > pm.player2_goals) OR
                             (pm.player2_id = %s AND pm.player2_goals > pm.player1_goals)
                        THEN 1 ELSE 0 END) as wins,
                    SUM(CASE 
                        WHEN pm.player1_goals = pm.player2_goals
                        THEN 1 ELSE 0 END) as draws,
                    SUM(CASE 
                        WHEN (pm.player1_id = %s AND pm.player1_goals < pm.player2_goals) OR
                             (pm.player2_id = %s AND pm.player2_goals < pm.player1_goals)
                        THEN 1 ELSE 0 END) as losses
                FROM player_matches pm
                WHERE pm.player1_id = %s OR pm.player2_id = %s
            """, (1, 1, 1, 1, 1, 1))  # Assuming Pachu has ID 1
            
            stats = cursor.fetchone()
            print(f"\nPachu's stats from database:")
            print(f"  Total matches: {stats['total_matches']}")
            print(f"  Wins: {stats['wins']}")
            print(f"  Draws: {stats['draws']}")
            print(f"  Losses: {stats['losses']}")
            
    finally:
        conn.close()

def check_player_details():
    """Check how player details are calculated"""
    # Get Pachu's details using the TournamentDB method
    player = TournamentDB.get_player_details(1)  # Assuming Pachu has ID 1
    if player:
        print(f"\nPachu's details from TournamentDB.get_player_details():")
        print(f"  Name: {player['name']}")
        print(f"  Rating: {player['rating']}")
        print(f"  Total matches: {player.get('total_matches', 'N/A')}")
        print(f"  Wins: {player.get('wins', 'N/A')}")
        print(f"  Draws: {player.get('draws', 'N/A')}")
        print(f"  Losses: {player.get('losses', 'N/A')}")
        print(f"  Win percentage: {player.get('win_percentage', 'N/A')}")
    else:
        print("Could not get player details")

if __name__ == "__main__":
    check_match_data()
    check_player_details()