#!/usr/bin/env python3
from database import get_db_connection

conn = get_db_connection()
try:
    with conn.cursor() as cursor:
        # Check Jomish specifically
        cursor.execute("""
            SELECT ps.*, t.name as tournament_name
            FROM player_stats ps
            JOIN players p ON ps.player_id = p.id
            JOIN tournaments t ON ps.tournament_id = t.id
            WHERE p.name = 'Jomish Joshy'
        """)
        
        stats = cursor.fetchall()
        print(f"Jomish Joshy has {len(stats)} tournament entries:")
        for s in stats:
            print(f"  - {s['tournament_name']}: {s['matches_played']} matches, Rating: {s['tournament_rating']}")
        
        # Check all players with multiple entries
        cursor.execute("""
            SELECT player_id, COUNT(*) as count
            FROM player_stats
            GROUP BY player_id
            HAVING COUNT(*) > 1
        """)
        
        multi = cursor.fetchall()
        print(f"\n{len(multi)} players have multiple tournament entries")
        
        if multi:
            for m in multi[:5]:
                cursor.execute("SELECT name FROM players WHERE id = %s", (m['player_id'],))
                player = cursor.fetchone()
                print(f"  - {player['name'] if player else 'Unknown'}: {m['count']} tournaments")
        
finally:
    conn.close()
