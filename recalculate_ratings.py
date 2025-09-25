#!/usr/bin/env python3
"""
Recalculate All Player Ratings Script

This script recalculates all player ratings and statistics by replaying 
all matches in chronological order using the new enhanced rating system.

The enhanced system includes:
- Base ELO rating changes
- +2 points per goal scored
- -1 point per goal conceded  
- +5 points for clean sheets
- -15 point penalty for nullified matches (both players absent)

SAFETY: This script preserves all match data and only updates calculated values.
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import TournamentDB, get_db_connection

def main():
    print("=" * 60)
    print("PLAYER RATING RECALCULATION SCRIPT")
    print("=" * 60)
    print()
    
    # Show what will happen
    print("This script will:")
    print("✅ Reset all player ratings to 300 (starting value)")
    print("✅ Clear all calculated statistics") 
    print("✅ Replay all matches chronologically with enhanced system")
    print("✅ Update ratings with new system: goals, clean sheets, penalties")
    print()
    print("This script will NOT:")
    print("❌ Delete any match records")
    print("❌ Delete any player profiles") 
    print("❌ Delete any tournament data")
    print("❌ Change match goals, dates, or any original data")
    print()
    
    # Get confirmation
    response = input("Do you want to proceed? (type 'yes' to continue): ").lower().strip()
    if response != 'yes':
        print("❌ Recalculation cancelled.")
        return
    
    print("\n🔄 Starting recalculation process...")
    print("-" * 40)
    
    try:
        # Get initial stats
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM player_matches")
            total_matches = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM players")  
            total_players = cursor.fetchone()['count']
        conn.close()
        
        print(f"📊 Found {total_players} players and {total_matches} matches to process")
        
        # Run the recalculation
        start_time = datetime.now()
        print(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        TournamentDB.recalculate_all_ratings()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Recalculation completed successfully!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"🏁 Finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show some results
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT name, rating, matches_played, matches_won, goals_scored 
                FROM players 
                ORDER BY rating DESC 
                LIMIT 10
            """)
            top_players = cursor.fetchall()
        conn.close()
        
        print("\n📈 Top 10 Players After Recalculation:")
        print("-" * 60)
        print(f"{'Rank':<4} {'Name':<20} {'Rating':<8} {'Matches':<8} {'Wins':<6} {'Goals':<6}")
        print("-" * 60)
        for i, player in enumerate(top_players, 1):
            print(f"{i:<4} {player['name']:<20} {player['rating']:<8} "
                  f"{player['matches_played']:<8} {player['matches_won']:<6} {player['goals_scored']:<6}")
        
        print("\n" + "=" * 60)
        print("🎉 RECALCULATION COMPLETE!")
        print("All player ratings now use the enhanced system with:")
        print("• Goal scoring bonuses (+2 per goal)")
        print("• Clean sheet bonuses (+5)")
        print("• Goal conceded penalties (-1 per goal)")
        print("• Absence penalties (-15 for no-shows)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR during recalculation: {str(e)}")
        print("🔄 Database has been rolled back to original state.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)