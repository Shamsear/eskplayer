#!/usr/bin/env python3
"""Show comparison between tournament and overall rankings"""

from database import get_db_connection

def show_comparison():
    """Display side-by-side comparison of tournament vs overall rankings"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get a specific tournament for comparison
            cursor.execute("""
                SELECT id, name FROM tournaments 
                WHERE id IN (SELECT DISTINCT tournament_id FROM player_stats WHERE matches_played > 5)
                ORDER BY created_at DESC LIMIT 1
            """)
            tournament = cursor.fetchone()
            
            if not tournament:
                print("No tournament with sufficient matches found.")
                return
            
            print("=" * 100)
            print(f"RANKING COMPARISON: {tournament['name']}")
            print("=" * 100)
            print("\nThis shows how tournament-specific rankings differ from overall rankings")
            print("Tournament Rating = Rating in this specific tournament only")
            print("Overall Rating = Cumulative rating across ALL tournaments")
            print("\n" + "=" * 100)
            
            # Get tournament rankings
            cursor.execute("""
                SELECT 
                    p.name,
                    ps.tournament_rating,
                    p.rating as overall_rating,
                    ps.matches_played as tournament_matches,
                    p.matches_played as overall_matches,
                    ps.wins as tournament_wins,
                    p.matches_won as overall_wins
                FROM player_stats ps
                JOIN players p ON ps.player_id = p.id
                WHERE ps.tournament_id = %s AND ps.matches_played > 0
                ORDER BY ps.tournament_rating DESC NULLS LAST
                LIMIT 15
            """, (tournament['id'],))
            
            players = cursor.fetchall()
            
            print(f"\n{'Rank':<5} {'Player':<20} {'T.Rating':<12} {'O.Rating':<12} {'T.Matches':<12} {'O.Matches':<12} {'Diff':<8}")
            print("-" * 100)
            
            for idx, player in enumerate(players, 1):
                t_rating = player['tournament_rating'] if player['tournament_rating'] else 0
                o_rating = player['overall_rating'] if player['overall_rating'] else 0
                diff = t_rating - o_rating
                diff_str = f"{diff:+d}" if diff != 0 else "0"
                
                print(f"{idx:<5} {player['name']:<20} {t_rating:<12} {o_rating:<12} "
                      f"{player['tournament_matches']:<12} {player['overall_matches']:<12} {diff_str:<8}")
            
            print("\n" + "=" * 100)
            print("KEY INSIGHTS:")
            print("=" * 100)
            print("• T.Rating vs O.Rating Diff shows how player performed in THIS tournament vs their overall career")
            print("• Positive diff (+) = Better performance in this tournament")
            print("• Negative diff (-) = Worse performance in this tournament compared to overall")
            print("• T.Matches shows games in this tournament only")
            print("• O.Matches shows total games across ALL tournaments")
            print("\n" + "=" * 100)
            
    finally:
        conn.close()

if __name__ == "__main__":
    show_comparison()
