"""Test the new rating system - average of last 40 matches"""
from database import TournamentDB, get_db_connection

def test_rating_calculation():
    """Test that overall rating is calculated as average of last 40 matches"""
    
    print("=" * 60)
    print("TESTING NEW RATING SYSTEM")
    print("=" * 60)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get a player who has played matches
            cursor.execute("""
                SELECT p.id, p.name, p.rating as overall_rating, p.matches_played
                FROM players p
                WHERE p.matches_played > 0
                ORDER BY p.matches_played DESC
                LIMIT 1
            """)
            
            player = cursor.fetchone()
            
            if not player:
                print("❌ No players with matches found in database")
                return
            
            print(f"\nPlayer: {player['name']}")
            print(f"Current Overall Rating: {player['overall_rating']}")
            print(f"Total Matches Played: {player['matches_played']}")
            
            # Get last 40 match ratings
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
            """, (player['id'], player['id'], player['id']))
            
            matches = cursor.fetchall()
            
            if matches:
                print(f"\nLast {len(matches)} matches:")
                print("-" * 60)
                
                # Calculate average of ratings
                ratings = [m['rating_after'] for m in matches]
                avg_rating = sum(ratings) / len(ratings)
                num_matches = len(matches)
                
                print(f"Match ratings from last {num_matches} matches: {ratings[:10]}{'...' if len(ratings) > 10 else ''}")
                print(f"Average of these ratings: {avg_rating:.2f}")
                print(f"Rounded average: {int(round(avg_rating))}")
                
                # Overall rating is just the average
                calculated_rating = int(round(avg_rating))
                
                print("\n" + "=" * 60)
                if player['overall_rating'] == calculated_rating:
                    print("✅ SUCCESS: Overall rating matches average of last matches!")
                else:
                    print(f"⚠️  MISMATCH:")
                    print(f"   Expected (calculated): {calculated_rating}")
                    print(f"   Actual (in database): {player['overall_rating']}")
                    print(f"   Difference: {abs(player['overall_rating'] - calculated_rating)}")
                print("=" * 60)
            else:
                print("❌ No match data found for this player")
                
    finally:
        conn.close()

def test_division_impact():
    """Test that division ratings affect overall rating"""
    
    print("\n\n" + "=" * 60)
    print("TESTING DIVISION IMPACT ON RATINGS")
    print("=" * 60)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get players from different divisions
            cursor.execute("""
                SELECT DISTINCT
                    p.id,
                    p.name,
                    p.rating as overall_rating,
                    p.matches_played,
                    d.name as division_name,
                    d.starting_rating as division_starting_rating
                FROM players p
                JOIN tournament_players tp ON p.id = tp.player_id
                LEFT JOIN divisions d ON tp.division_id = d.id
                WHERE p.matches_played > 5 AND d.id IS NOT NULL
                ORDER BY d.starting_rating DESC
                LIMIT 5
            """)
            
            players = cursor.fetchall()
            
            if players:
                print("\nPlayers from different divisions:")
                print("-" * 60)
                for player in players:
                    print(f"{player['name']:20} | Division: {player['division_name']:15} | "
                          f"Div Start: {player['division_starting_rating']:4} | "
                          f"Overall: {player['overall_rating']:4} | "
                          f"Matches: {player['matches_played']:3}")
                
                print("\n✅ Higher division starting ratings should lead to higher overall ratings")
            else:
                print("⚠️  No players found in divisions")
                
    finally:
        conn.close()

if __name__ == "__main__":
    test_rating_calculation()
    test_division_impact()
    
    print("\n\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
