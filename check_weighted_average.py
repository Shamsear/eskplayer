#!/usr/bin/env python3
"""Check weighted average calculation for Jomish"""

from database import get_db_connection

conn = get_db_connection()
try:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM players WHERE name = 'Jomish Joshy'")
        player = cursor.fetchone()
        
        cursor.execute("""
            SELECT tournament_rating, matches_played
            FROM player_stats
            WHERE player_id = %s AND tournament_rating IS NOT NULL
        """, (player['id'],))
        
        tournaments = cursor.fetchall()
        
        print("Jomish Joshy Tournament Ratings:")
        total_matches = 0
        weighted_sum = 0
        
        for t in tournaments:
            print(f"  Rating: {t['tournament_rating']}, Matches: {t['matches_played']}")
            weighted_sum += t['tournament_rating'] * t['matches_played']
            total_matches += t['matches_played']
        
        if total_matches > 0:
            calculated_average = weighted_sum / total_matches
            print(f"\nWeighted Average Calculation:")
            print(f"  Total weighted sum: {weighted_sum}")
            print(f"  Total matches: {total_matches}")
            print(f"  Average: {weighted_sum} / {total_matches} = {calculated_average:.2f}")
            print(f"  Rounded: {int(round(calculated_average))}")
        
        print(f"\nActual overall rating in DB: {player['rating']}")
        
finally:
    conn.close()
