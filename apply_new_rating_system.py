"""Apply the new rating system to all existing players"""
from database import TournamentDB, get_db_connection

def recalculate_all_ratings():
    """Recalculate overall ratings for all players using average of last 40 matches"""
    
    print("=" * 60)
    print("RECALCULATING ALL RATINGS WITH NEW SYSTEM")
    print("=" * 60)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get all players
            cursor.execute("SELECT id, name, rating as old_rating, matches_played FROM players ORDER BY matches_played DESC")
            players = cursor.fetchall()
            
            print(f"\nFound {len(players)} players")
            print("\nRecalculating ratings...")
            print("-" * 60)
            
            updated_count = 0
            for player in players:
                player_id = player['id']
                old_rating = player['old_rating']
                
                # Calculate new rating from last 40 matches
                new_rating = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player_id, limit=40)
                
                # Update the rating
                cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_rating, player_id))
                
                change = new_rating - (old_rating if old_rating else 300)
                symbol = "+" if change > 0 else ""
                
                if player['matches_played'] > 0:
                    print(f"{player['name']:20} | Matches: {player['matches_played']:3} | "
                          f"Old: {old_rating if old_rating else 300:4} → New: {new_rating:4} ({symbol}{change:+4})")
                    updated_count += 1
            
            conn.commit()
            
            print("\n" + "=" * 60)
            print(f"✅ Successfully updated {updated_count} player ratings!")
            print("=" * 60)
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    recalculate_all_ratings()
    
    print("\n\nRunning verification test...")
    print("=" * 60)
    
    # Run the test again to verify
    from test_new_rating_system import test_rating_calculation
    test_rating_calculation()
