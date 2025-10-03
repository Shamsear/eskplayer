#!/usr/bin/env python3
"""Test tournament-wise ranking system"""

from database import TournamentDB, get_db_connection

def test_tournament_rankings():
    """Test that tournament rankings are tracked separately"""
    print("Testing Tournament-Wise Ranking System")
    print("=" * 60)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get all tournaments
            cursor.execute("SELECT id, name FROM tournaments ORDER BY created_at DESC LIMIT 5")
            tournaments = cursor.fetchall()
            
            if not tournaments:
                print("No tournaments found. Please create tournaments first.")
                return
            
            print(f"\nFound {len(tournaments)} tournament(s)")
            print("-" * 60)
            
            for tournament in tournaments:
                print(f"\nTournament: {tournament['name']} (ID: {tournament['id']})")
                print("-" * 60)
                
                # Get tournament-specific stats
                cursor.execute("""
                    SELECT 
                        p.name,
                        ps.tournament_rating,
                        ps.matches_played,
                        ps.wins,
                        ps.draws,
                        ps.losses,
                        ps.goals_scored,
                        ps.goals_conceded,
                        p.rating as overall_rating
                    FROM player_stats ps
                    JOIN players p ON ps.player_id = p.id
                    WHERE ps.tournament_id = %s
                    ORDER BY ps.tournament_rating DESC NULLS LAST, ps.wins DESC
                    LIMIT 10
                """, (tournament['id'],))
                
                tournament_players = cursor.fetchall()
                
                if not tournament_players:
                    print("  No players have played in this tournament yet.")
                    continue
                
                print(f"\n  {'Rank':<6} {'Player':<20} {'T.Rating':<10} {'Overall':<10} {'MP':<5} {'W-D-L':<10} {'Goals':<8}")
                print("  " + "-" * 90)
                
                for idx, player in enumerate(tournament_players, 1):
                    t_rating = player['tournament_rating'] if player['tournament_rating'] is not None else 'N/A'
                    o_rating = player['overall_rating'] if player['overall_rating'] is not None else 'N/A'
                    wdl = f"{player['wins']}-{player['draws']}-{player['losses']}"
                    goals = f"{player['goals_scored']}/{player['goals_conceded']}"
                    
                    print(f"  {idx:<6} {player['name']:<20} {str(t_rating):<10} {str(o_rating):<10} {player['matches_played']:<5} {wdl:<10} {goals:<8}")
            
            # Show overall rankings for comparison
            print("\n" + "=" * 60)
            print("Overall Rankings (Across All Tournaments)")
            print("=" * 60)
            
            cursor.execute("""
                SELECT 
                    name,
                    rating,
                    matches_played,
                    matches_won,
                    matches_drawn,
                    matches_lost,
                    goals_scored,
                    goals_conceded
                FROM players
                WHERE rating IS NOT NULL
                ORDER BY rating DESC, matches_won DESC
                LIMIT 10
            """)
            
            overall_players = cursor.fetchall()
            
            if overall_players:
                print(f"\n{'Rank':<6} {'Player':<20} {'Rating':<10} {'MP':<5} {'W-D-L':<10} {'Goals':<8}")
                print("-" * 80)
                
                for idx, player in enumerate(overall_players, 1):
                    rating = player['rating'] if player['rating'] is not None else 'N/A'
                    wdl = f"{player['matches_won']}-{player['matches_drawn']}-{player['matches_lost']}"
                    goals = f"{player['goals_scored']}/{player['goals_conceded']}"
                    
                    print(f"{idx:<6} {player['name']:<20} {str(rating):<10} {player['matches_played']:<5} {wdl:<10} {goals:<8}")
            else:
                print("No players found.")
            
            # Check for players with NULL tournament ratings (new players in tournaments)
            print("\n" + "=" * 60)
            print("Players with NULL Tournament Ratings")
            print("=" * 60)
            
            cursor.execute("""
                SELECT 
                    p.name,
                    t.name as tournament_name,
                    ps.matches_played,
                    ps.tournament_rating
                FROM player_stats ps
                JOIN players p ON ps.player_id = p.id
                JOIN tournaments t ON ps.tournament_id = t.id
                WHERE ps.tournament_rating IS NULL
                ORDER BY t.name, p.name
            """)
            
            null_ratings = cursor.fetchall()
            
            if null_ratings:
                print(f"\nFound {len(null_ratings)} player(s) with NULL tournament ratings:")
                for player in null_ratings:
                    print(f"  - {player['name']} in {player['tournament_name']} (Matches: {player['matches_played']})")
            else:
                print("\nAll players have tournament ratings assigned.")
                
    finally:
        conn.close()

if __name__ == "__main__":
    test_tournament_rankings()
