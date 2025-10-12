#!/usr/bin/env python3
"""
Apply Balanced 50-Match System
==============================

Perfect balance between fairness and achievability:
- 2 matches = 4% confidence → ~301 rating
- 10 matches = 20% confidence → ~308 rating  
- 25 matches = 50% confidence → ~320 rating
- 50 matches = 100% confidence → Full rating ✅

This makes high ratings achievable while still being fair!
"""

from database import get_db_connection, TournamentDB

def apply_50_match_system():
    """Apply the balanced 50-match confidence system"""
    print("=" * 80)
    print("APPLYING BALANCED 50-MATCH SYSTEM")
    print("=" * 80)
    print("Perfect balance - Fair but achievable:")
    print("- 2 matches = 4% confidence → ~301 rating")
    print("- 10 matches = 20% confidence → ~308 rating")
    print("- 25 matches = 50% confidence → ~320 rating") 
    print("- 50 matches = 100% confidence → Full rating ✅")
    print()
    print("Timeline to 50 matches:")
    print("- 5 matches/week = 10 weeks (2.5 months)")
    print("- 10 matches/week = 5 weeks (1.25 months)")
    print("- Much more achievable! 🚀")
    print()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get all players
            cursor.execute("SELECT id, name, rating FROM players ORDER BY name")
            players = cursor.fetchall()
            
            print(f"Recalculating {len(players)} players...")
            print()
            
            # Show examples before/after for key players
            test_cases = [
                ("Fayis", 8),
                ("Tejas", 2), 
                ("Siraj", 18),
                ("Umar", 17)
            ]
            
            print("🔄 SAMPLE CALCULATIONS:")
            print("-" * 60)
            print(f"{'Player':<15} {'Matches':<8} {'Old':<6} {'New':<6} {'Confidence'}")
            print("-" * 60)
            
            for name, expected_matches in test_cases:
                cursor.execute(
                    "SELECT id, name, rating FROM players WHERE name ILIKE %s LIMIT 1", 
                    (f'%{name}%',)
                )
                player = cursor.fetchone()
                
                if player:
                    old_rating = player['rating']
                    new_rating = TournamentDB.calculate_overall_rating_from_last_matches(
                        cursor, player['id']
                    )
                    confidence = min(expected_matches / 50, 1.0) * 100
                    
                    print(f"{player['name']:<15} {expected_matches:<8} {old_rating:<6} "
                          f"{new_rating:<6} {confidence:.0f}%")
            
            print("-" * 60)
            print()
            
            # Update all players
            updated_count = 0
            for player in players:
                new_rating = TournamentDB.calculate_overall_rating_from_last_matches(
                    cursor, player['id']
                )
                cursor.execute(
                    "UPDATE players SET rating = %s WHERE id = %s", 
                    (new_rating, player['id'])
                )
                updated_count += 1
            
            conn.commit()
            
            print(f"✅ Updated {updated_count} players!")
            print()
            
            # Show new top 15
            print("🏆 NEW TOP 15 (50-Match Balanced System):")
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
            
            top_players = cursor.fetchall()
            
            print(f"{'Rank':<4} {'Player':<20} {'Rating':<6} {'Matches':<8} {'Confidence'}")
            print("-" * 80)
            
            for idx, player in enumerate(top_players, 1):
                confidence = min(player['recent_matches'] / 50, 1.0) * 100
                print(f"{idx:<4} {player['name']:<20} {player['rating']:<6} "
                      f"{player['recent_matches']:<8} {confidence:.0f}%")
            
            print()
            print("=" * 80)
            print("BALANCED 50-MATCH SYSTEM APPLIED! ✅")
            print("=" * 80)
            print("Perfect Balance Achieved:")
            print("✅ New players: Realistic ratings (can't fake skill)")
            print("✅ Active players: Can reach 350+ in 2-3 months")
            print("✅ Veterans: Full ratings at 50 matches (achievable!)")
            print("✅ Fair competition: Match count matters but not extreme")
            print()
            
            # Show rating progression examples
            print("📊 RATING PROGRESSION EXAMPLES:")
            print("-" * 80)
            examples = [
                (5, "Beginner"),
                (15, "Learning"), 
                (30, "Experienced"),
                (50, "Master")
            ]
            
            for matches, level in examples:
                confidence = min(matches / 50, 1.0)
                # Example with good performance (375 base)
                rating = 300 + (375 - 300) * confidence
                timeline = f"{matches/5:.0f} weeks" if matches <= 25 else f"{matches/10:.0f}-{matches/5:.0f} weeks"
                
                print(f"{level:<12} ({matches:>2} matches): {rating:.0f} rating "
                      f"({confidence:.0%} confidence) - {timeline}")
            
            print()
            print("🎯 To reach 350+ rating:")
            print("- Need ~25 matches (50% confidence) with good performance")
            print("- Timeline: 5-10 weeks of active play")  
            print("- Much more achievable than before! 🚀")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    response = input("Apply balanced 50-match system? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        apply_50_match_system()
    else:
        print("Cancelled.")