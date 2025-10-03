#!/usr/bin/env python3
"""Check all players who played in multiple tournaments"""

from database import get_db_connection

conn = get_db_connection()
try:
    with conn.cursor() as cursor:
        # Find players in multiple tournaments
        cursor.execute("""
            SELECT 
                p.id,
                p.name,
                p.rating as overall_rating,
                p.matches_played as overall_matches,
                COUNT(DISTINCT ps.tournament_id) as tournament_count
            FROM players p
            JOIN player_stats ps ON p.id = ps.player_id
            WHERE ps.matches_played > 0
            GROUP BY p.id, p.name, p.rating, p.matches_played
            HAVING COUNT(DISTINCT ps.tournament_id) > 1
            ORDER BY p.name
        """)
        
        multi_tournament_players = cursor.fetchall()
        
        print("=" * 100)
        print(f"PLAYERS IN MULTIPLE TOURNAMENTS: {len(multi_tournament_players)}")
        print("=" * 100)
        
        if not multi_tournament_players:
            print("\nNo players found in multiple tournaments.")
        else:
            print(f"\n{'Player':<25} {'Overall':<10} {'Matches':<10} {'Tournaments':<12} {'Issue?'}")
            print("-" * 100)
            
            for player in multi_tournament_players:
                # Get tournament ratings
                cursor.execute("""
                    SELECT t.name, ps.tournament_rating, ps.matches_played
                    FROM player_stats ps
                    JOIN tournaments t ON ps.tournament_id = t.id
                    WHERE ps.player_id = %s
                    ORDER BY t.created_at
                """, (player['id'],))
                
                tournaments = cursor.fetchall()
                
                # Calculate expected overall (should be close to average or last match rating)
                tournament_ratings = [t['tournament_rating'] for t in tournaments if t['tournament_rating']]
                avg_tournament_rating = sum(tournament_ratings) / len(tournament_ratings) if tournament_ratings else 0
                
                # Check if there's a big discrepancy
                discrepancy = abs(player['overall_rating'] - avg_tournament_rating) if player['overall_rating'] else 0
                issue_flag = "⚠️ YES" if discrepancy > 50 else "✓ OK"
                
                print(f"{player['name']:<25} {player['overall_rating'] or 'N/A':<10} {player['overall_matches']:<10} {player['tournament_count']:<12} {issue_flag}")
                
                # Show tournament breakdown
                for t in tournaments:
                    print(f"  └─ {t['name']}: Rating {t['tournament_rating']}, {t['matches_played']} matches")
            
            # Summary statistics
            print("\n" + "=" * 100)
            print("SUMMARY:")
            print("=" * 100)
            
            issue_count = 0
            for player in multi_tournament_players:
                cursor.execute("""
                    SELECT ps.tournament_rating
                    FROM player_stats ps
                    WHERE ps.player_id = %s AND ps.tournament_rating IS NOT NULL
                """, (player['id'],))
                
                ratings = cursor.fetchall()
                if ratings:
                    avg_rating = sum(r['tournament_rating'] for r in ratings) / len(ratings)
                    if player['overall_rating'] and abs(player['overall_rating'] - avg_rating) > 50:
                        issue_count += 1
            
            print(f"Total multi-tournament players: {len(multi_tournament_players)}")
            print(f"Players with rating discrepancies (>50 points): {issue_count}")
            print(f"Percentage affected: {(issue_count / len(multi_tournament_players) * 100):.1f}%")
            
finally:
    conn.close()
