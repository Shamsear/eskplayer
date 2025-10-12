"""
Test script to verify overall rating calculation for players with varying match counts
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from database import get_db_connection, TournamentDB

def test_rating_calculation():
    """Test the rating calculation for players with different match counts"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get all players with their match counts
            cursor.execute("""
                SELECT 
                    p.id,
                    p.name,
                    p.rating as overall_rating,
                    p.matches_played,
                    COUNT(pm.match_id) as actual_matches
                FROM players p
                LEFT JOIN player_matches pm ON (pm.player1_id = p.id OR pm.player2_id = p.id)
                GROUP BY p.id, p.name, p.rating, p.matches_played
                HAVING COUNT(pm.match_id) > 0
                ORDER BY actual_matches ASC
                LIMIT 15
            """)
            
            players = cursor.fetchall()
            
            print("=" * 80)
            print("RATING VERIFICATION TEST")
            print("=" * 80)
            print()
            
            for player in players:
                player_id = player['id']
                player_name = player['name']
                stored_rating = player['overall_rating']
                match_count = player['actual_matches']
                
                print(f"\n{'=' * 80}")
                print(f"Player: {player_name} (ID: {player_id})")
                print(f"Matches Played: {match_count}")
                print(f"Stored Overall Rating: {stored_rating}")
                
                # Get last N matches (up to 40)
                cursor.execute("""
                    SELECT 
                        match_id,
                        CASE 
                            WHEN player1_id = %s THEN player1_rating_after
                            ELSE player2_rating_after
                        END as rating_after,
                        played_at
                    FROM player_matches
                    WHERE player1_id = %s OR player2_id = %s
                    ORDER BY played_at DESC, match_id DESC
                    LIMIT 40
                """, (player_id, player_id, player_id))
                
                matches = cursor.fetchall()
                
                if not matches:
                    calculated_rating = 300
                    print(f"No matches found → Default rating: 300")
                else:
                    ratings = [m['rating_after'] for m in matches]
                    calculated_rating = int(round(sum(ratings) / len(ratings)))
                    
                    print(f"Matches used in calculation: {len(matches)}")
                    print(f"Rating after values: {ratings[:5]}{'...' if len(ratings) > 5 else ''}")
                    print(f"Sum of ratings: {sum(ratings)}")
                    print(f"Average: {sum(ratings) / len(ratings):.2f}")
                    print(f"Calculated Overall Rating: {calculated_rating}")
                
                # Verify match
                if stored_rating is None:
                    print(f"⚠️  Player has NULL rating (needs initialization)")
                    print(f"   Should be: {calculated_rating}")
                elif stored_rating == calculated_rating:
                    print(f"✅ MATCH! Stored ({stored_rating}) = Calculated ({calculated_rating})")
                else:
                    print(f"❌ MISMATCH! Stored ({stored_rating}) ≠ Calculated ({calculated_rating})")
                    print(f"   Difference: {stored_rating - calculated_rating}")
            
            print("\n" + "=" * 80)
            print("TEST COMPLETE")
            print("=" * 80)
            
    finally:
        conn.close()

if __name__ == "__main__":
    test_rating_calculation()
