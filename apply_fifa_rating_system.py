#!/usr/bin/env python3
"""
Apply FIFA-style Rating System to All Players
==============================================

This script recalculates all player overall ratings using the new FIFA-style system:
- Time decay: 0-30 days (100%), 31-60 days (50%), 61-90 days (25%), 90+ days (0%)
- Match confidence: Need 100 weighted matches for 100% confidence
- Formula: Final Rating = 300 + (Base Rating - 300) × Match Confidence

Run this after implementing the new rating calculation function.
"""

from database import get_db_connection, TournamentDB
from datetime import datetime

def apply_fifa_rating_system():
    """Apply FIFA-style rating system to all players"""
    print("=" * 80)
    print("APPLYING FIFA-STYLE RATING SYSTEM")
    print("=" * 80)
    print()
    print("System Details:")
    print("- Time Decay: 30d(100%), 31-60d(50%), 61-90d(25%), 90d+(0%)")
    print("- Confidence: 100 weighted matches for full confidence")
    print("- Formula: Final = 300 + (Base - 300) × Confidence")
    print()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get all players
            cursor.execute("SELECT id, name, rating FROM players ORDER BY name")
            players = cursor.fetchall()
            
            print(f"Found {len(players)} players to recalculate...")
            print()
            
            updated_count = 0
            total_change = 0
            
            print(f"{'Player':<25} {'Old':<8} {'New':<8} {'Change':<8} {'Status'}")
            print("-" * 80)
            
            for player in players:
                player_id = player['id']
                player_name = player['name']
                old_rating = player['rating'] if player['rating'] is not None else 300
                
                # Calculate new FIFA-style rating
                new_rating = TournamentDB.calculate_overall_rating_from_last_matches(
                    cursor, player_id, limit=40  # limit parameter not used in new system
                )
                
                # Update player rating
                cursor.execute(
                    "UPDATE players SET rating = %s WHERE id = %s", 
                    (new_rating, player_id)
                )
                
                # Calculate change
                rating_change = new_rating - old_rating
                total_change += abs(rating_change)
                updated_count += 1
                
                # Status indicator
                if rating_change > 20:
                    status = "📈 UP"
                elif rating_change < -20:
                    status = "📉 DOWN"
                elif rating_change > 5:
                    status = "↗ up"
                elif rating_change < -5:
                    status = "↘ down"
                else:
                    status = "→ same"
                
                # Display result
                print(f"{player_name:<25} {old_rating:<8} {new_rating:<8} {rating_change:+8} {status}")
            
            # Commit all changes
            conn.commit()
            
            print("-" * 80)
            print(f"✅ Successfully updated {updated_count} players")
            print(f"📊 Average rating change: {total_change / updated_count:.1f} points")
            print()
            
            # Show top 10 ratings after update
            print("🏆 TOP 10 PLAYERS (New FIFA-Style Ratings):")
            print("-" * 60)
            cursor.execute("""
                SELECT name, rating,
                       (SELECT COUNT(*) FROM player_matches pm 
                        WHERE pm.player1_id = p.id OR pm.player2_id = p.id
                        AND pm.played_at >= NOW() - INTERVAL '90 days') as recent_matches
                FROM players p 
                WHERE rating IS NOT NULL 
                ORDER BY rating DESC 
                LIMIT 10
            """)
            top_players = cursor.fetchall()
            
            print(f"{'Rank':<6} {'Player':<25} {'Rating':<8} {'Recent Matches'}")
            print("-" * 60)
            
            for idx, player in enumerate(top_players, 1):
                print(f"{idx:<6} {player['name']:<25} {player['rating']:<8} {player['recent_matches']}")
            
            print()
            print("=" * 80)
            print("FIFA-STYLE RATING SYSTEM APPLIED SUCCESSFULLY! ✅")
            print("=" * 80)
            print()
            print("Key Changes:")
            print("✅ Time-based decay: Recent matches matter more")
            print("✅ 100-match confidence: Prevents new player inflation") 
            print("✅ Fair rankings: Active veterans rewarded")
            print("✅ Inactive penalty: Old players drop naturally")
            print()
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def show_rating_examples():
    """Show examples of how the new system works"""
    print("=" * 80)
    print("FIFA-STYLE RATING EXAMPLES")
    print("=" * 80)
    print()
    
    examples = [
        ("New Player (5 matches)", 5, 380, "Only 5% confidence → ~319 rating"),
        ("Active Player (30 matches)", 30, 400, "30% confidence → ~330 rating"),
        ("Veteran (60 matches)", 60, 390, "60% confidence → ~354 rating"),
        ("Master (100+ matches)", 100, 380, "100% confidence → 380 rating ✅")
    ]
    
    for desc, matches, base, result in examples:
        confidence = min(matches / 100, 1.0)
        final = 300 + (base - 300) * confidence
        print(f"{desc:<25} → {result}")
        print(f"  Base: {base}, Confidence: {confidence:.0%}, Final: {final:.0f}")
        print()

if __name__ == "__main__":
    try:
        show_rating_examples()
        
        response = input("Apply FIFA-style rating system to all players? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            apply_fifa_rating_system()
        else:
            print("Operation cancelled.")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")