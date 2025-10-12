"""
Check how Siraj's overall rating is calculated
"""
from database import get_db_connection

def check_siraj_rating():
    """Show detailed breakdown of Siraj's rating calculation"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Find Siraj
            cursor.execute("""
                SELECT id, name, rating, matches_played 
                FROM players 
                WHERE name ILIKE '%siraj%'
            """)
            
            siraj_results = cursor.fetchall()
            
            if not siraj_results:
                print("❌ No player named 'Siraj' found!")
                return
            
            print("=" * 100)
            print("SIRAJ'S RATING CALCULATION BREAKDOWN")
            print("=" * 100)
            
            for player in siraj_results:
                player_id = player['id']
                player_name = player['name']
                stored_rating = player['rating']
                matches_played = player['matches_played']
                
                print(f"\n{'=' * 100}")
                print(f"Player: {player_name} (ID: {player_id})")
                print(f"Stored Overall Rating: {stored_rating}")
                print(f"Total Matches Played: {matches_played}")
                print("=" * 100)
                
                # Get last 40 matches with details
                cursor.execute("""
                    SELECT 
                        match_id,
                        tournament_id,
                        played_at,
                        CASE 
                            WHEN player1_id = %s THEN player1_rating_before
                            ELSE player2_rating_before
                        END as rating_before,
                        CASE 
                            WHEN player1_id = %s THEN player1_rating_after
                            ELSE player2_rating_after
                        END as rating_after,
                        CASE 
                            WHEN player1_id = %s THEN player1_goals
                            ELSE player2_goals
                        END as siraj_goals,
                        CASE 
                            WHEN player1_id = %s THEN player2_goals
                            ELSE player1_goals
                        END as opponent_goals,
                        CASE 
                            WHEN player1_id = %s THEN player2_id
                            ELSE player1_id
                        END as opponent_id,
                        is_draw,
                        is_walkover,
                        is_null_match,
                        winner_id
                    FROM player_matches
                    WHERE player1_id = %s OR player2_id = %s
                    ORDER BY played_at DESC, match_id DESC
                    LIMIT 40
                """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id))
                
                matches = cursor.fetchall()
                
                if not matches:
                    print("\n❌ No matches found for Siraj!")
                    print("Default rating should be: 300")
                    continue
                
                print(f"\n📊 LAST {len(matches)} MATCHES (used in calculation):")
                print("-" * 100)
                print(f"{'#':<4} {'Match ID':<10} {'Before':<8} {'After':<8} {'Change':<8} {'Score':<12} {'Result':<15}")
                print("-" * 100)
                
                total_rating = 0
                for idx, match in enumerate(matches, 1):
                    rating_change = match['rating_after'] - match['rating_before']
                    
                    # Determine result
                    if match['is_null_match']:
                        result = "Null Match"
                    elif match['is_walkover']:
                        if match['winner_id'] == player_id:
                            result = "Win (Walkover)"
                        else:
                            result = "Loss (Walkover)"
                    elif match['is_draw']:
                        result = "Draw"
                    elif match['winner_id'] == player_id:
                        result = "Win"
                    else:
                        result = "Loss"
                    
                    score = f"{match['siraj_goals']}-{match['opponent_goals']}"
                    
                    print(f"{idx:<4} {match['match_id']:<10} "
                          f"{match['rating_before']:<8} "
                          f"{match['rating_after']:<8} "
                          f"{rating_change:+8} "
                          f"{score:<12} "
                          f"{result:<15}")
                    
                    total_rating += match['rating_after']
                
                print("-" * 100)
                
                # Calculate average
                calculated_rating = total_rating / len(matches)
                rounded_rating = int(round(calculated_rating))
                
                print(f"\n📈 CALCULATION:")
                print(f"   Sum of all 'rating_after' values: {total_rating}")
                print(f"   Number of matches: {len(matches)}")
                print(f"   Average: {total_rating} / {len(matches)} = {calculated_rating:.2f}")
                print(f"   Rounded: {rounded_rating}")
                
                print(f"\n🎯 RESULT:")
                print(f"   Calculated Overall Rating: {rounded_rating}")
                print(f"   Stored Overall Rating: {stored_rating}")
                
                if stored_rating == rounded_rating:
                    print(f"   ✅ MATCH! Rating is correct.")
                elif stored_rating is None:
                    print(f"   ⚠️  Rating is NULL in database (needs to be set to {rounded_rating})")
                else:
                    difference = stored_rating - rounded_rating
                    print(f"   ❌ MISMATCH! Difference: {difference}")
                    print(f"   → Database needs recalculation")
                
                # Show stats summary
                wins = sum(1 for m in matches if m['winner_id'] == player_id and not m['is_draw'])
                draws = sum(1 for m in matches if m['is_draw'])
                losses = sum(1 for m in matches if m['winner_id'] != player_id and not m['is_draw'] and m['winner_id'] is not None)
                
                print(f"\n📊 MATCH STATS (Last {len(matches)} matches):")
                print(f"   Wins: {wins}")
                print(f"   Draws: {draws}")
                print(f"   Losses: {losses}")
                print(f"   Win Rate: {(wins/len(matches)*100):.1f}%")
                
    finally:
        conn.close()

if __name__ == "__main__":
    check_siraj_rating()
