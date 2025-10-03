#!/usr/bin/env python3
"""Recalculate all ratings with tournament-wise system"""

from database import TournamentDB, get_db_connection

def recalculate_tournament_ratings():
    """Recalculate ratings for all matches with tournament-specific tracking"""
    print("Recalculating Tournament-Wise Ratings")
    print("=" * 80)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Step 1: Reset all player overall ratings to NULL (will be recalculated)
            print("\n1. Resetting player overall stats...")
            cursor.execute("""
                UPDATE players SET
                    rating = NULL,
                    matches_played = 0,
                    matches_won = 0,
                    matches_drawn = 0,
                    matches_lost = 0,
                    goals_scored = 0,
                    goals_conceded = 0,
                    clean_sheets = 0,
                    golden_glove_points = 0
            """)
            conn.commit()
            print("   ✓ Player overall stats reset")
            
            # Step 2: Clear all tournament-specific stats
            print("\n2. Clearing tournament-specific stats...")
            cursor.execute("DELETE FROM player_stats")
            conn.commit()
            print("   ✓ Tournament stats cleared")
            
            # Step 3: Get all matches in chronological order
            print("\n3. Fetching all matches...")
            cursor.execute("""
                SELECT * FROM player_matches
                ORDER BY played_at ASC NULLS LAST, match_id ASC
            """)
            matches = cursor.fetchall()
            print(f"   ✓ Found {len(matches)} matches to process")
            
            # Step 4: Process each match
            print("\n4. Processing matches and recalculating ratings...")
            processed_count = 0
            
            for match in matches:
                p1_id = match['player1_id']
                p2_id = match['player2_id']
                t_id = match['tournament_id']
                g1 = match['player1_goals']
                g2 = match['player2_goals']
                is_walkover = match.get('is_walkover', False)
                is_null = match.get('is_null_match', False)
                p1_absent = match.get('player1_absent', False)
                p2_absent = match.get('player2_absent', False)
                is_draw = match.get('is_draw', False)
                winner_id = match.get('winner_id')
                
                # Get current tournament ratings for both players
                cursor.execute("""
                    SELECT tournament_rating FROM player_stats 
                    WHERE player_id = %s AND tournament_id = %s
                """, (p1_id, t_id))
                p1_t_rating_row = cursor.fetchone()
                p1_t_rating = p1_t_rating_row['tournament_rating'] if p1_t_rating_row else None
                
                cursor.execute("""
                    SELECT tournament_rating FROM player_stats 
                    WHERE player_id = %s AND tournament_id = %s
                """, (p2_id, t_id))
                p2_t_rating_row = cursor.fetchone()
                p2_t_rating = p2_t_rating_row['tournament_rating'] if p2_t_rating_row else None
                
                # Get current overall ratings
                cursor.execute("SELECT rating FROM players WHERE id = %s", (p1_id,))
                p1_o_rating = cursor.fetchone()['rating']
                cursor.execute("SELECT rating FROM players WHERE id = %s", (p2_id,))
                p2_o_rating = cursor.fetchone()['rating']
                
                # Use 300 as starting rating if NULL
                p1_t_rating_before = 300 if p1_t_rating is None else p1_t_rating
                p2_t_rating_before = 300 if p2_t_rating is None else p2_t_rating
                p1_o_rating_before = 300 if p1_o_rating is None else p1_o_rating
                p2_o_rating_before = 300 if p2_o_rating is None else p2_o_rating
                
                # Handle null matches (both absent)
                if is_null:
                    NULL_PENALTY = 15
                    p1_t_rating_after = max(0, min(1000, p1_t_rating_before - NULL_PENALTY))
                    p2_t_rating_after = max(0, min(1000, p2_t_rating_before - NULL_PENALTY))
                    p1_o_rating_after = max(0, min(1000, p1_o_rating_before - NULL_PENALTY))
                    p2_o_rating_after = max(0, min(1000, p2_o_rating_before - NULL_PENALTY))
                    
                    # Update ratings only (no stats)
                    cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (p1_o_rating_after, p1_id))
                    cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (p2_o_rating_after, p2_id))
                    
                    # Update match records
                    cursor.execute("""
                        UPDATE player_matches SET
                            player1_rating_before = %s,
                            player2_rating_before = %s,
                            player1_rating_after = %s,
                            player2_rating_after = %s
                        WHERE id = %s
                    """, (p1_t_rating_before, p2_t_rating_before, p1_t_rating_after, p2_t_rating_after, match['id']))
                    
                    processed_count += 1
                    if processed_count % 100 == 0:
                        print(f"   Processed {processed_count}/{len(matches)} matches...")
                    continue
                
                # Handle walkover matches
                if is_walkover:
                    # Calculate rating changes with 75% factor
                    from database import TournamentDB
                    
                    # Tournament ratings
                    if winner_id == p1_id:
                        t_change_w, t_change_l = TournamentDB.calculate_rating_change(p1_t_rating_before, p2_t_rating_before, is_draw=False)
                        t_change1 = int(t_change_w * 0.75)
                        t_change2 = int(t_change_l * 0.75)
                    else:
                        t_change_w, t_change_l = TournamentDB.calculate_rating_change(p2_t_rating_before, p1_t_rating_before, is_draw=False)
                        t_change2 = int(t_change_w * 0.75)
                        t_change1 = int(t_change_l * 0.75)
                    
                    p1_t_rating_after = max(0, min(1000, p1_t_rating_before + t_change1))
                    p2_t_rating_after = max(0, min(1000, p2_t_rating_before + t_change2))
                    
                    # Overall ratings
                    if winner_id == p1_id:
                        o_change_w, o_change_l = TournamentDB.calculate_rating_change(p1_o_rating_before, p2_o_rating_before, is_draw=False)
                        o_change1 = int(o_change_w * 0.75)
                        o_change2 = int(o_change_l * 0.75)
                    else:
                        o_change_w, o_change_l = TournamentDB.calculate_rating_change(p2_o_rating_before, p1_o_rating_before, is_draw=False)
                        o_change2 = int(o_change_w * 0.75)
                        o_change1 = int(o_change_l * 0.75)
                    
                    p1_o_rating_after = max(0, min(1000, p1_o_rating_before + o_change1))
                    p2_o_rating_after = max(0, min(1000, p2_o_rating_before + o_change2))
                    
                else:
                    # Normal match - use enhanced rating calculation
                    from database import TournamentDB
                    
                    # Tournament ratings (primary calculation)
                    t_change1, t_change2 = TournamentDB.calculate_enhanced_rating_change(
                        p1_t_rating_before, p2_t_rating_before, g1, g2, p1_absent, p2_absent
                    )
                    p1_t_rating_after = max(0, min(1000, p1_t_rating_before + t_change1))
                    p2_t_rating_after = max(0, min(1000, p2_t_rating_before + t_change2))
                    
                    # Overall ratings (use same changes as tournament)
                    # Calculate change based on overall rating to account for multi-tournament players
                    o_change1, o_change2 = TournamentDB.calculate_enhanced_rating_change(
                        p1_o_rating_before, p2_o_rating_before, g1, g2, p1_absent, p2_absent
                    )
                    p1_o_rating_after = max(0, min(1000, p1_o_rating_before + o_change1))
                    p2_o_rating_after = max(0, min(1000, p2_o_rating_before + o_change2))
                
                # Update match record with tournament ratings
                cursor.execute("""
                    UPDATE player_matches SET
                        player1_rating_before = %s,
                        player2_rating_before = %s,
                        player1_rating_after = %s,
                        player2_rating_after = %s
                    WHERE id = %s
                """, (p1_t_rating_before, p2_t_rating_before, p1_t_rating_after, p2_t_rating_after, match['id']))
                
                # Update overall player stats (use same rating as tournament rating for consistency)
                for pid, o_rating_after, t_rating_after, won, drawn, lost, gf, ga in [
                    (p1_id, p1_o_rating_after, p1_t_rating_after, 1 if winner_id == p1_id else 0, 1 if is_draw else 0, 1 if winner_id == p2_id else 0, g1, g2),
                    (p2_id, p2_o_rating_after, p2_t_rating_after, 1 if winner_id == p2_id else 0, 1 if is_draw else 0, 1 if winner_id == p1_id else 0, g2, g1)
                ]:
                    # Calculate golden glove points
                    glove_points = 0
                    if not is_null and not is_walkover:
                        glove_points = TournamentDB.calculate_golden_glove_points(
                            gf, ga, winner_id == pid, is_draw
                        )
                    
                    # Use tournament rating as overall rating if player only plays in one tournament
                    # Otherwise use calculated overall rating
                    cursor.execute("SELECT COUNT(DISTINCT tournament_id) FROM player_stats WHERE player_id = %s", (pid,))
                    tournament_count = cursor.fetchone()['count']
                    
                    # If player only in one tournament, use tournament rating; otherwise use overall calculation
                    final_rating = t_rating_after if tournament_count <= 1 else o_rating_after
                    
                    cursor.execute("""
                        UPDATE players SET
                            rating = %s,
                            matches_played = matches_played + 1,
                            matches_won = matches_won + %s,
                            matches_drawn = matches_drawn + %s,
                            matches_lost = matches_lost + %s,
                            goals_scored = goals_scored + %s,
                            goals_conceded = goals_conceded + %s,
                            clean_sheets = clean_sheets + %s,
                            golden_glove_points = golden_glove_points + %s
                        WHERE id = %s
                    """, (final_rating, won, drawn, lost, gf, ga, 1 if ga == 0 and not is_null else 0, glove_points, pid))
                
                # Update tournament-specific stats with tournament rating
                for pid, t_rating_after, won, drawn, lost, gf, ga in [
                    (p1_id, p1_t_rating_after, 1 if winner_id == p1_id else 0, 1 if is_draw else 0, 1 if winner_id == p2_id else 0, g1, g2),
                    (p2_id, p2_t_rating_after, 1 if winner_id == p2_id else 0, 1 if is_draw else 0, 1 if winner_id == p1_id else 0, g2, g1)
                ]:
                    # Calculate golden glove points
                    glove_points = 0
                    if not is_null and not is_walkover:
                        glove_points = TournamentDB.calculate_golden_glove_points(
                            gf, ga, winner_id == pid, is_draw
                        )
                    
                    cursor.execute("""
                        INSERT INTO player_stats
                            (player_id, tournament_id, tournament_rating, matches_played, wins, draws, losses, goals_scored, goals_conceded, clean_sheets, golden_glove_points)
                        VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (player_id, tournament_id)
                        DO UPDATE SET
                            tournament_rating = %s,
                            matches_played = player_stats.matches_played + 1,
                            wins = player_stats.wins + %s,
                            draws = player_stats.draws + %s,
                            losses = player_stats.losses + %s,
                            goals_scored = player_stats.goals_scored + %s,
                            goals_conceded = player_stats.goals_conceded + %s,
                            clean_sheets = player_stats.clean_sheets + %s,
                            golden_glove_points = player_stats.golden_glove_points + %s
                    """, (pid, t_id, t_rating_after, won, drawn, lost, gf, ga, 1 if ga == 0 and not is_null else 0, glove_points,
                          t_rating_after, won, drawn, lost, gf, ga, 1 if ga == 0 and not is_null else 0, glove_points))
                
                processed_count += 1
                if processed_count % 100 == 0:
                    print(f"   Processed {processed_count}/{len(matches)} matches...")
            
            conn.commit()
            print(f"   ✓ All {processed_count} matches processed successfully")
            
            # Step 5: Show summary
            print("\n5. Recalculation Summary")
            print("-" * 80)
            
            # Count players with ratings
            cursor.execute("SELECT COUNT(*) as count FROM players WHERE rating IS NOT NULL")
            players_with_rating = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(DISTINCT player_id) as count FROM player_stats WHERE tournament_rating IS NOT NULL")
            players_with_tournament_rating = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(DISTINCT tournament_id) as count FROM player_stats")
            tournaments_with_players = cursor.fetchone()['count']
            
            print(f"   • Players with overall rating: {players_with_rating}")
            print(f"   • Players with tournament ratings: {players_with_tournament_rating}")
            print(f"   • Tournaments with player data: {tournaments_with_players}")
            print(f"   • Total matches processed: {processed_count}")
            
            print("\n" + "=" * 80)
            print("✓ Tournament-wise rating recalculation completed successfully!")
            print("=" * 80)
            
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error during recalculation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    recalculate_tournament_ratings()
