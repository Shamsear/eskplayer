#!/usr/bin/env python3
"""
Script to fix player ratings in the Neon database.
Updates players who have rating=300 but matches_played=0 to have rating=NULL.

This ensures that only players who have actually played matches have a rating,
while new/unplayed players have NULL rating until their first match.
"""

import os
import sys
from database import get_db_connection
from dotenv import load_dotenv

def fix_unplayed_ratings():
    """Fix ratings for players who haven't played any matches"""
    load_dotenv()
    
    print("Connecting to Neon database...")
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # First, check how many players need fixing
            cursor.execute("""
                SELECT COUNT(*) as count FROM players 
                WHERE rating = 300 AND matches_played = 0
            """)
            unplayed_count = cursor.fetchone()['count']
            
            if unplayed_count == 0:
                print("✅ No players need fixing. All unplayed players already have NULL rating.")
                return
            
            print(f"Found {unplayed_count} players with rating=300 but no matches played.")
            
            # Show the players that will be updated
            cursor.execute("""
                SELECT id, name, rating, matches_played, created_at 
                FROM players 
                WHERE rating = 300 AND matches_played = 0
                ORDER BY created_at DESC
            """)
            players_to_fix = cursor.fetchall()
            
            print("\nPlayers to be updated:")
            print("ID\tName\t\tRating\tMatches\tCreated")
            print("-" * 60)
            for player in players_to_fix:
                print(f"{player['id']}\t{player['name'][:15]:<15}\t{player['rating']}\t{player['matches_played']}\t{player['created_at'].strftime('%Y-%m-%d')}")
            
            # Confirm before proceeding
            response = input(f"\nUpdate {unplayed_count} players' ratings to NULL? (y/N): ").strip().lower()
            if response != 'y':
                print("Operation cancelled.")
                return
            
            # Perform the update
            cursor.execute("""
                UPDATE players 
                SET rating = NULL 
                WHERE rating = 300 AND matches_played = 0
            """)
            
            updated_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ Successfully updated {updated_count} players' ratings to NULL!")
            
            # Verify the update
            cursor.execute("""
                SELECT COUNT(*) as count FROM players 
                WHERE rating = 300 AND matches_played = 0
            """)
            remaining_count = cursor.fetchone()['count']
            
            if remaining_count == 0:
                print("✅ Verification: All unplayed players now have NULL rating.")
            else:
                print(f"⚠️  Warning: {remaining_count} players still have rating=300 with no matches.")
            
            # Show summary statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_players,
                    COUNT(rating) as players_with_rating,
                    COUNT(*) - COUNT(rating) as players_null_rating,
                    AVG(rating) as avg_rating
                FROM players
            """)
            stats = cursor.fetchone()
            
            print(f"\nDatabase Summary:")
            print(f"- Total players: {stats['total_players']}")
            print(f"- Players with rating: {stats['players_with_rating']}")
            print(f"- Players with NULL rating: {stats['players_null_rating']}")
            if stats['avg_rating']:
                print(f"- Average rating: {stats['avg_rating']:.1f}")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    fix_unplayed_ratings()