#!/usr/bin/env python3
"""Find Pachu's player ID and check their stats"""

from database import TournamentDB, get_db_connection

def find_pachu():
    """Find Pachu's player ID"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Find Pachu's ID
            cursor.execute("SELECT id, name, rating FROM players WHERE name ILIKE '%pachu%'")
            players = cursor.fetchall()
            
            print("Players matching 'pachu':")
            for player in players:
                print(f"  ID: {player['id']}, Name: {player['name']}, Rating: {player['rating']}")
                
                # Check stats for this player
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_matches,
                        SUM(CASE 
                            WHEN (pm.player1_id = %s AND pm.player1_goals > pm.player2_goals) OR
                                 (pm.player2_id = %s AND pm.player2_goals > pm.player1_goals)
                            THEN 1 ELSE 0 END) as wins,
                        SUM(CASE 
                            WHEN pm.player1_goals = pm.player2_goals AND (pm.player1_id = %s OR pm.player2_id = %s)
                            THEN 1 ELSE 0 END) as draws,
                        SUM(CASE 
                            WHEN (pm.player1_id = %s AND pm.player1_goals < pm.player2_goals) OR
                                 (pm.player2_id = %s AND pm.player2_goals < pm.player1_goals)
                            THEN 1 ELSE 0 END) as losses
                    FROM player_matches pm
                    WHERE pm.player1_id = %s OR pm.player2_id = %s
                """, (player['id'], player['id'], player['id'], player['id'], player['id'], player['id'], player['id'], player['id']))
                
                stats = cursor.fetchone()
                wins = stats['wins'] if stats['wins'] is not None else 0
                draws = stats['draws'] if stats['draws'] is not None else 0
                losses = stats['losses'] if stats['losses'] is not None else 0
                total = stats['total_matches']
                
                win_pct = (wins / total * 100) if total > 0 else 0
                
                print(f"    Stats: {wins}-{draws}-{losses} (Total: {total}) Win%: {win_pct:.1f}%")
                
                # Check some matches for this player
                cursor.execute("""
                    SELECT pm.*, p1.name as player1_name, p2.name as player2_name
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    JOIN players p2 ON pm.player2_id = p2.id
                    WHERE pm.player1_id = %s OR pm.player2_id = %s
                    ORDER BY pm.played_at DESC
                    LIMIT 5
                """, (player['id'], player['id']))
                
                matches = cursor.fetchall()
                print(f"    Recent matches:")
                for match in matches:
                    print(f"      {match['player1_name']} {match['player1_goals']}-{match['player2_goals']} {match['player2_name']}")
                print()
                
    finally:
        conn.close()

if __name__ == "__main__":
    find_pachu()