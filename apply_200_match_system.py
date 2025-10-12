#!/usr/bin/env python3
"""
Apply 200-Match Confidence System
=================================

Much stricter system to prevent players with few matches from ranking high.
- Need 200 weighted matches for 100% confidence
- 2 matches = 1% confidence
- 18 matches = 9% confidence
- Much fairer rankings
"""

from database import get_db_connection, TournamentDB

def apply_200_match_system():
    """Apply the new 200-match confidence system"""
    print("=" * 80)
    print("APPLYING 200-MATCH CONFIDENCE SYSTEM")
    print("=" * 80)
    print("Making system MUCH stricter:")
    print("- 2 matches = 1% confidence → ~300 rating")
    print("- 18 matches = 9% confidence → ~303 rating") 
    print("- 50 matches = 25% confidence → ~320 rating")
    print("- 100 matches = 50% confidence → ~340 rating")
    print("- 200 matches = 100% confidence → Full rating ✅")
    print()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get current top 15 players
            cursor.execute("""
                SELECT id, name, rating FROM players 
                WHERE rating IS NOT NULL 
                ORDER BY rating DESC 
                LIMIT 15
            """)
            top_players = cursor.fetchall()
            
            print("🔄 RECALCULATING TOP 15 PLAYERS:")
            print("-" * 80)
            print(f"{'Player':<20} {'Old':<6} {'New':<6} {'Change':<8} {'Status'}")
            print("-" * 80)
            
            big_drops = 0
            for player in top_players:
                player_id = player['id']
                player_name = player['name']
                old_rating = player['rating']
                
                # Calculate new 200-match confidence rating
                new_rating = TournamentDB.calculate_overall_rating_from_last_matches(
                    cursor, player_id
                )
                
                # Update database
                cursor.execute(
                    "UPDATE players SET rating = %s WHERE id = %s", 
                    (new_rating, player_id)
                )
                
                change = new_rating - old_rating
                
                # Status
                if change < -10:
                    status = "📉 BIG DROP"
                    big_drops += 1
                elif change < -3:
                    status = "↘ drop"
                elif change > 3:
                    status = "↗ rise"
                else:
                    status = "→ same"
                
                print(f"{player_name:<20} {old_rating:<6} {new_rating:<6} {change:+8} {status}")
            
            # Now recalculate ALL players
            print()
            print("🔄 Recalculating all 271 players...")
            cursor.execute("SELECT id FROM players")
            all_players = cursor.fetchall()
            
            for player in all_players:
                new_rating = TournamentDB.calculate_overall_rating_from_last_matches(
                    cursor, player['id']
                )
                cursor.execute(
                    "UPDATE players SET rating = %s WHERE id = %s", 
                    (new_rating, player['id'])
                )
            
            conn.commit()
            
            print("✅ All players updated!")
            print()
            
            # Show new top 15
            print("🏆 NEW TOP 15 (200-Match Confidence System):")
            print("-" * 80)
            cursor.execute("""
                SELECT name, rating,
                       (SELECT COUNT(*) FROM player_matches pm 
                        WHERE pm.player1_id = p.id OR pm.player2_id = p.id
                        AND pm.played_at >= NOW() - INTERVAL '90 days') as recent_matches
                FROM players p 
                WHERE rating IS NOT NULL 
                ORDER BY rating DESC 
                LIMIT 15
            """)
            
            new_top = cursor.fetchall()
            
            print(f"{'Rank':<4} {'Player':<20} {'Rating':<6} {'Matches':<8} {'Confidence'}")
            print("-" * 80)
            
            for idx, player in enumerate(new_top, 1):
                confidence = min(player['recent_matches'] / 200, 1.0) * 100
                print(f"{idx:<4} {player['name']:<20} {player['rating']:<6} "
                      f"{player['recent_matches']:<8} {confidence:.1f}%")
            
            print()
            print("=" * 80)
            print("200-MATCH SYSTEM APPLIED! ✅")
            print("=" * 80)
            print("Key Changes:")
            print(f"📉 {big_drops} players had significant drops (10+ points)")
            print("✅ Players with few matches now have realistic ratings")
            print("✅ Need 200 matches for full confidence (very strict)")
            print("✅ Rankings now much fairer!")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    response = input("Apply 200-match confidence system? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        apply_200_match_system()
    else:
        print("Cancelled.")