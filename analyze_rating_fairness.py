"""
Analyze the fairness of the rating system - comparing players with different match counts
"""
from database import get_db_connection

def analyze_rating_fairness():
    """Check if players with fewer matches have unfair rating advantages"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get players grouped by match count ranges
            cursor.execute("""
                WITH player_match_counts AS (
                    SELECT 
                        p.id,
                        p.name,
                        p.rating,
                        COUNT(pm.match_id) as match_count,
                        CASE 
                            WHEN COUNT(pm.match_id) = 0 THEN '0 matches'
                            WHEN COUNT(pm.match_id) BETWEEN 1 AND 5 THEN '1-5 matches'
                            WHEN COUNT(pm.match_id) BETWEEN 6 AND 10 THEN '6-10 matches'
                            WHEN COUNT(pm.match_id) BETWEEN 11 AND 20 THEN '11-20 matches'
                            WHEN COUNT(pm.match_id) BETWEEN 21 AND 40 THEN '21-40 matches'
                            ELSE '40+ matches'
                        END as match_range
                    FROM players p
                    LEFT JOIN player_matches pm ON (pm.player1_id = p.id OR pm.player2_id = p.id)
                    GROUP BY p.id, p.name, p.rating
                    HAVING p.rating IS NOT NULL
                )
                SELECT 
                    match_range,
                    COUNT(*) as player_count,
                    AVG(rating) as avg_rating,
                    MIN(rating) as min_rating,
                    MAX(rating) as max_rating,
                    MIN(match_count) as min_matches,
                    MAX(match_count) as max_matches
                FROM player_match_counts
                GROUP BY match_range
                ORDER BY min_matches ASC
            """)
            
            ranges = cursor.fetchall()
            
            print("=" * 100)
            print("RATING SYSTEM FAIRNESS ANALYSIS")
            print("=" * 100)
            print()
            print("Question: Can a player with 5 matches have the same (or higher) rating than one with 40 matches?")
            print()
            
            print(f"{'Match Range':<20} {'Players':<10} {'Avg Rating':<15} {'Min Rating':<15} {'Max Rating':<15}")
            print("-" * 100)
            
            for r in ranges:
                print(f"{r['match_range']:<20} {r['player_count']:<10} "
                      f"{r['avg_rating']:<15.1f} {r['min_rating']:<15} {r['max_rating']:<15}")
            
            print("\n" + "=" * 100)
            print("SPECIFIC EXAMPLES - High ratings with low match counts:")
            print("=" * 100)
            
            # Find players with <10 matches but high ratings
            cursor.execute("""
                SELECT 
                    p.name,
                    p.rating,
                    COUNT(pm.match_id) as match_count
                FROM players p
                LEFT JOIN player_matches pm ON (pm.player1_id = p.id OR pm.player2_id = p.id)
                WHERE p.rating IS NOT NULL
                GROUP BY p.id, p.name, p.rating
                HAVING COUNT(pm.match_id) < 10 AND p.rating > 320
                ORDER BY p.rating DESC
                LIMIT 10
            """)
            
            high_rated_low_matches = cursor.fetchall()
            
            if high_rated_low_matches:
                print("\nPlayers with <10 matches but rating >320:")
                for p in high_rated_low_matches:
                    print(f"  {p['name']:<25} Rating: {p['rating']:<5} Matches: {p['match_count']}")
            else:
                print("\nNo players with <10 matches have rating >320")
            
            # Find comparison - players with many matches
            print("\n" + "=" * 100)
            print("COMPARISON - Experienced players with many matches:")
            print("=" * 100)
            
            cursor.execute("""
                SELECT 
                    p.name,
                    p.rating,
                    COUNT(pm.match_id) as match_count
                FROM players p
                LEFT JOIN player_matches pm ON (pm.player1_id = p.id OR pm.player2_id = p.id)
                WHERE p.rating IS NOT NULL
                GROUP BY p.id, p.name, p.rating
                HAVING COUNT(pm.match_id) >= 40
                ORDER BY p.rating DESC
                LIMIT 10
            """)
            
            experienced_players = cursor.fetchall()
            
            print("\nTop 10 players with 40+ matches:")
            for p in experienced_players:
                print(f"  {p['name']:<25} Rating: {p['rating']:<5} Matches: {p['match_count']}")
            
            print("\n" + "=" * 100)
            print("CONCLUSION:")
            print("=" * 100)
            
            if high_rated_low_matches:
                max_low_match_rating = max(p['rating'] for p in high_rated_low_matches)
                min_high_match_rating = min(p['rating'] for p in experienced_players) if experienced_players else 0
                
                if max_low_match_rating >= min_high_match_rating:
                    print("⚠️  YES - UNFAIR: Players with <10 matches CAN have ratings equal to or higher than")
                    print("    players with 40+ matches. This creates an unfair ranking system!")
                    print(f"\n    Highest rating (<10 matches): {max_low_match_rating}")
                    print(f"    Lowest rating (40+ matches): {min_high_match_rating}")
                else:
                    print("✅ FAIR: Players with fewer matches have appropriately lower ratings")
            
            print("\n" + "=" * 100)
            
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_rating_fairness()
