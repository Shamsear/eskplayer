"""
Test FIFA-Style Rating System for Siraj
========================================

This shows how Siraj's rating is calculated with the new FIFA-style system:
- Time decay based on match age
- 100-match confidence system
- Formula: Final Rating = 300 + (Base Rating - 300) × Match Confidence
"""
from database import get_db_connection, TournamentDB
from datetime import datetime, timedelta

def test_siraj_fifa_rating():
    """Test the FIFA-style rating for Siraj"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Find Siraj
            cursor.execute("SELECT id, name, rating FROM players WHERE name ILIKE '%siraj%'")
            siraj_results = cursor.fetchall()
            
            if not siraj_results:
                print("❌ No player named 'Siraj' found!")
                return
            
            for player in siraj_results:
                player_id = player['id']
                player_name = player['name']
                stored_rating = player['rating']
                
                print("=" * 100)
                print("SIRAJ'S FIFA-STYLE RATING BREAKDOWN")
                print("=" * 100)
                print(f"Player: {player_name} (ID: {player_id})")
                print(f"Stored Rating: {stored_rating}")
                print()
                
                # Get matches from last 90 days with time information
                ninety_days_ago = datetime.now() - timedelta(days=90)
                
                cursor.execute("""
                    SELECT 
                        match_id,
                        CASE 
                            WHEN player1_id = %s THEN player1_rating_after
                            ELSE player2_rating_after
                        END as rating_after,
                        played_at,
                        CASE 
                            WHEN player1_id = %s THEN player1_goals
                            ELSE player2_goals
                        END as siraj_goals,
                        CASE 
                            WHEN player1_id = %s THEN player2_goals
                            ELSE player1_goals
                        END as opponent_goals,
                        winner_id,
                        is_draw,
                        is_walkover,
                        is_null_match
                    FROM player_matches
                    WHERE (player1_id = %s OR player2_id = %s)
                      AND played_at >= %s
                    ORDER BY played_at DESC, match_id DESC
                """, (player_id, player_id, player_id, player_id, player_id, ninety_days_ago))
                
                matches = cursor.fetchall()
                
                if not matches:
                    print("❌ No matches in last 90 days!")
                    print("Rating = 300 (default)")
                    continue
                
                print("📊 FIFA-STYLE CALCULATION:")
                print("-" * 100)
                print("Step 1: Time-Weighted Matches (FIFA Decay)")
                print("-" * 100)
                
                total_weighted_points = 0
                total_weight = 0
                now = datetime.now()
                
                print(f"{'#':<3} {'Match':<8} {'Days':<5} {'Weight':<8} {'Rating':<8} {'Weighted':<10} {'Score':<8} {'Result'}")
                print("-" * 100)
                
                for idx, match in enumerate(matches, 1):
                    # Calculate days since match
                    if match['played_at']:
                        days_ago = (now - match['played_at']).days
                    else:
                        days_ago = 91
                    
                    # Determine weight
                    if days_ago <= 30:
                        weight = 1.0
                        period = "0-30d"
                    elif days_ago <= 60:
                        weight = 0.5
                        period = "31-60d"
                    elif days_ago <= 90:
                        weight = 0.25
                        period = "61-90d"
                    else:
                        continue  # Skip matches older than 90 days
                    
                    weighted_points = match['rating_after'] * weight
                    total_weighted_points += weighted_points
                    total_weight += weight
                    
                    # Result
                    if match['is_null_match']:
                        result = "Null"
                    elif match['is_walkover']:
                        result = "W.O." if match['winner_id'] == player_id else "W.O.L"
                    elif match['is_draw']:
                        result = "Draw"
                    elif match['winner_id'] == player_id:
                        result = "Win"
                    else:
                        result = "Loss"
                    
                    score = f"{match['siraj_goals']}-{match['opponent_goals']}"
                    
                    print(f"{idx:<3} {match['match_id']:<8} {days_ago:<5} "
                          f"{weight:<8.2f} {match['rating_after']:<8} "
                          f"{weighted_points:<10.1f} {score:<8} {result}")
                
                print("-" * 100)
                print(f"Total Weighted Points: {total_weighted_points:.1f}")
                print(f"Total Weight: {total_weight:.2f}")
                
                # Calculate base rating
                if total_weight > 0:
                    base_rating = total_weighted_points / total_weight
                else:
                    base_rating = 300
                
                print(f"Base Rating: {total_weighted_points:.1f} / {total_weight:.2f} = {base_rating:.1f}")
                print()
                
                print("-" * 100)
                print("Step 2: Match Confidence (100-Match System)")
                print("-" * 100)
                
                match_confidence = min(total_weight / 100, 1.0)
                confidence_percent = match_confidence * 100
                
                print(f"Weighted Matches: {total_weight:.2f}")
                print(f"Required for 100%: 100 matches")
                print(f"Match Confidence: {total_weight:.2f} / 100 = {match_confidence:.3f} ({confidence_percent:.1f}%)")
                print()
                
                print("-" * 100)
                print("Step 3: Final FIFA-Style Rating")
                print("-" * 100)
                
                final_rating = 300 + (base_rating - 300) * match_confidence
                final_rating_int = int(round(final_rating))
                
                print(f"Formula: 300 + (Base - 300) × Confidence")
                print(f"Calculation: 300 + ({base_rating:.1f} - 300) × {match_confidence:.3f}")
                print(f"           = 300 + ({base_rating - 300:.1f}) × {match_confidence:.3f}")
                print(f"           = 300 + {(base_rating - 300) * match_confidence:.1f}")
                print(f"           = {final_rating:.1f}")
                print(f"Final Rating: {final_rating_int}")
                print()
                
                print("🎯 RESULT COMPARISON:")
                print(f"Calculated FIFA Rating: {final_rating_int}")
                print(f"Stored Rating: {stored_rating}")
                
                if stored_rating == final_rating_int:
                    print("✅ PERFECT MATCH! FIFA system working correctly.")
                else:
                    difference = stored_rating - final_rating_int if stored_rating else 0
                    print(f"ℹ️  Difference: {difference:+d}")
                    print("ℹ️  This is expected - new FIFA system is much stricter")
                
                print()
                print("📊 FIFA-STYLE INSIGHTS:")
                print(f"- Siraj has {total_weight:.1f} weighted matches (need 100 for full confidence)")
                print(f"- His confidence level is {confidence_percent:.1f}% (low due to FIFA strictness)")
                print(f"- Base performance: {base_rating:.1f} (good!)")
                print(f"- Final rating: {final_rating_int} (confidence-adjusted)")
                print(f"- To reach 350+ rating: Need ~{100 - total_weight:.0f} more recent matches")
                
                # Verify with actual function call
                calculated_rating = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player_id)
                print()
                print("🔍 VERIFICATION:")
                print(f"Function result: {calculated_rating}")
                print(f"Manual calculation: {final_rating_int}")
                
                if calculated_rating == final_rating_int:
                    print("✅ Function and manual calculation match!")
                else:
                    print("❌ Mismatch - function may need debugging")
                    
    finally:
        conn.close()

if __name__ == "__main__":
    test_siraj_fifa_rating()