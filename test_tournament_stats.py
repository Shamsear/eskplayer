#!/usr/bin/env python3
"""Test tournament-specific stats ordering"""

from database import TournamentDB

def test_tournament_stats():
    """Test if tournament stats are ordered correctly"""
    
    # Get all tournaments first
    tournaments = TournamentDB.get_all_tournaments()
    
    print("Available tournaments:")
    for t in tournaments:
        print(f"  ID: {t['id']} - {t['name']}")
    
    # Test with first tournament
    if tournaments:
        tournament_id = tournaments[0]['id']
        tournament_name = tournaments[0]['name']
        
        print(f"\nTesting tournament stats for: {tournament_name} (ID: {tournament_id})")
        
        tournament_stats = TournamentDB.get_player_tournament_stats(tournament_id)
        
        print(f"Found {len(tournament_stats)} players in tournament")
        print("\nTournament Rankings:")
        print("Rank | Player                | Wins | Goals | Rating | W-D-L")
        print("-" * 65)
        
        for i, stat in enumerate(tournament_stats[:15]):
            wins = stat.get('wins', 0)
            draws = stat.get('draws', 0)
            losses = stat.get('losses', 0)
            goals_scored = stat.get('goals_scored', 0)
            goals_conceded = stat.get('goals_conceded', 0)
            rating = stat.get('rating', 0)
            
            print(f"{i+1:4d} | {stat['name']:20} | {wins:4d} | {goals_scored:2d}-{goals_conceded:2d} | {rating:4d} | {wins}-{draws}-{losses}")

if __name__ == "__main__":
    test_tournament_stats()