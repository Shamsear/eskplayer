#!/usr/bin/env python3
"""Test the fixed statistics display"""

from database import TournamentDB

def test_stats_fix():
    """Test if the overall stats show correct values"""
    
    print("Testing overall player statistics...")
    overall_stats = TournamentDB.get_overall_player_stats()
    
    print(f"Found {len(overall_stats)} players with stats")
    
    # Show top 10 players with their correct stats
    for i, stat in enumerate(overall_stats[:10]):
        matches_played = stat.get('matches_played', 0)
        matches_won = stat.get('matches_won', 0)
        matches_drawn = stat.get('matches_drawn', 0)
        matches_lost = stat.get('matches_lost', 0)
        goals_scored = stat.get('goals_scored', 0)
        goals_conceded = stat.get('goals_conceded', 0)
        
        win_pct = (matches_won / matches_played * 100) if matches_played > 0 else 0
        
        print(f"{i+1:2d}. {stat['name']:20} Rating: {stat['rating']:3d} | "
              f"Matches: {matches_played:2d} | "
              f"W-D-L: {matches_won}-{matches_drawn}-{matches_lost} | "
              f"Goals: {goals_scored}-{goals_conceded} | "
              f"Win%: {win_pct:.1f}%")

if __name__ == "__main__":
    test_stats_fix()