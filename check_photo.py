#!/usr/bin/env python3
"""
Check player photo data in database
"""

from database import get_db_connection

def check_player_photos():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get all players with their photo info
            cursor.execute("""
                SELECT id, name, photo_url, photo_file_id
                FROM players 
                WHERE name = 'Pachu'
                ORDER BY id
            """)
            players = cursor.fetchall()
            
            print("Players with photo data:")
            print("-" * 80)
            for player in players:
                print(f"ID: {player['id']}")
                print(f"Name: {player['name']}")
                print(f"Photo URL: {player['photo_url']}")
                print(f"Photo File ID: {player['photo_file_id']}")
                print("-" * 80)
                
            if not players:
                print("No players found named 'Pachu'")
                
            # Check all players with photos
            cursor.execute("""
                SELECT id, name, photo_url, photo_file_id
                FROM players 
                WHERE photo_url IS NOT NULL
                ORDER BY id
            """)
            all_with_photos = cursor.fetchall()
            
            print(f"\nTotal players with photos: {len(all_with_photos)}")
            for player in all_with_photos:
                print(f"- {player['name']} (ID: {player['id']}) - {player['photo_url']}")
                
    finally:
        conn.close()

if __name__ == "__main__":
    check_player_photos()