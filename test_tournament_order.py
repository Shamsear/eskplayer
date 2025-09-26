#!/usr/bin/env python3
"""Test tournament stats ordering fix"""

from database import TournamentDB

def test_tournament_order():
    """Test if tournament stats are now ordered correctly by rating first"""
    
    # Get all tournaments
    tournaments = TournamentDB.get_all_tournaments()
    
    if tournaments:
        tournament_id = tournaments[0]['id']
        tournament_name = tournaments[0]['name']
        
        print(f"Testing tournament stats for: {tournament_name} (ID: {tournament_id})")
        
        tournament_stats = TournamentDB.get_player_tournament_stats(tournament_id)
        
        print(f"\nTop 15 players in tournament (should be ordered by rating first):")
        print("Rank | Player                | Rating | Wins | Goals | W-D-L")
        print("-" * 68)
        
        for i, stat in enumerate(tournament_stats[:15]):
            wins = stat.get('wins', 0)
            draws = stat.get('draws', 0)
            losses = stat.get('losses', 0)
            goals_scored = stat.get('goals_scored', 0)
            goals_conceded = stat.get('goals_conceded', 0)
            rating = stat.get('rating', 0)
            
            print(f"{i+1:4d} | {stat['name']:20} | {rating:4d}   | {wins:4d} | {goals_scored:2d}-{goals_conceded:2d}  | {wins}-{draws}-{losses}")

    # Also test overall stats to compare
    print(f"\n" + "="*70)
    print("Overall stats for comparison (should match tournament order):")
    print("Rank | Player                | Rating | Wins | Goals | W-D-L")
    print("-" * 68)
    
    overall_stats = TournamentDB.get_overall_player_stats()
    for i, stat in enumerate(overall_stats[:15]):
        matches_won = stat.get('matches_won', 0)
        matches_drawn = stat.get('matches_drawn', 0)
        matches_lost = stat.get('matches_lost', 0)
        goals_scored = stat.get('goals_scored', 0)
        goals_conceded = stat.get('goals_conceded', 0)
        rating = stat.get('rating', 0)
        
        print(f"{i+1:4d} | {stat['name']:20} | {rating:4d}   | {matches_won:4d} | {goals_scored:2d}-{goals_conceded:2d}  | {matches_won}-{matches_drawn}-{matches_lost}")

if __name__ == "__main__":
    test_tournament_order()