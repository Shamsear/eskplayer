#!/usr/bin/env python3
"""Test the NULL rating system"""

from database import TournamentDB

def test_null_rating_system():
    """Test the new NULL rating system"""
    
    print("=== Testing NULL Rating System ===\n")
    
    # Step 1: Create a new test player
    print("1. Creating new test player...")
    try:
        test_player_id = TournamentDB.add_player("Test Player NULL", None, None)
        print(f"   ✅ Created test player with ID: {test_player_id}")
    except Exception as e:
        print(f"   ❌ Failed to create player: {e}")
        return
    
    # Step 2: Verify the player has NULL rating
    print("\n2. Checking player's initial rating...")
    player = TournamentDB.get_player_by_id(test_player_id)
    if player:
        if player['rating'] is None:
            print(f"   ✅ Player has NULL rating as expected")
        else:
            print(f"   ❌ Player has rating {player['rating']}, expected NULL")
    else:
        print(f"   ❌ Could not retrieve player")
        return
    
    # Step 3: Check that player doesn't appear in overall stats
    print("\n3. Checking if player appears in overall stats...")
    overall_stats = TournamentDB.get_overall_player_stats()
    test_player_in_stats = any(p['id'] == test_player_id for p in overall_stats)
    
    if not test_player_in_stats:
        print(f"   ✅ Player correctly excluded from overall stats")
    else:
        print(f"   ❌ Player incorrectly appears in overall stats")
    
    # Step 4: Check total players in all players vs stats
    all_players = TournamentDB.get_all_players()
    stats_count = len(overall_stats)
    all_count = len(all_players)
    
    print(f"\n4. Player counts:")
    print(f"   All players: {all_count}")
    print(f"   Players in stats: {stats_count}")
    if all_count > stats_count:
        print(f"   ✅ {all_count - stats_count} player(s) with NULL rating excluded from stats")
    else:
        print(f"   ⚠️  All players appear in stats")
    
    # Step 5: Find a tournament to test with
    print(f"\n5. Finding tournament for match test...")
    tournaments = TournamentDB.get_all_tournaments()
    if tournaments:
        tournament_id = tournaments[0]['id']
        print(f"   Using tournament: {tournaments[0]['name']} (ID: {tournament_id})")
        
        # Step 6: Add test player to tournament
        print(f"\n6. Adding test player to tournament...")
        try:
            TournamentDB.add_players_to_tournament(tournament_id, [test_player_id])
            print(f"   ✅ Added test player to tournament")
        except Exception as e:
            print(f"   ❌ Failed to add player to tournament: {e}")
            return
        
        # Step 7: Find another player to play against
        tournament_players = TournamentDB.get_tournament_players(tournament_id)
        opponent = None
        for p in tournament_players:
            if p['id'] != test_player_id and p['rating'] is not None:
                opponent = p
                break
        
        if opponent:
            print(f"\n7. Found opponent: {opponent['name']} (Rating: {opponent['rating']})")
            
            # Step 8: Record a match
            print(f"\n8. Recording test match...")
            try:
                match_id = TournamentDB.record_match(
                    tournament_id, test_player_id, opponent['id'], 2, 1
                )
                print(f"   ✅ Match recorded with ID: {match_id}")
                
                # Step 9: Check if test player now has a rating
                print(f"\n9. Checking if test player now has rating...")
                player_after = TournamentDB.get_player_by_id(test_player_id)
                if player_after and player_after['rating'] is not None:
                    print(f"   ✅ Player now has rating: {player_after['rating']}")
                    
                    # Step 10: Check if player appears in stats now
                    print(f"\n10. Checking if player now appears in stats...")
                    new_stats = TournamentDB.get_overall_player_stats()
                    test_player_in_new_stats = any(p['id'] == test_player_id for p in new_stats)
                    
                    if test_player_in_new_stats:
                        print(f"   ✅ Player now correctly appears in overall stats")
                        
                        # Show player's stats
                        player_stats = next((p for p in new_stats if p['id'] == test_player_id), None)
                        if player_stats:
                            print(f"   Player stats: Rating={player_stats['rating']}, Matches={player_stats['matches_played']}, W-D-L={player_stats['matches_won']}-{player_stats['matches_drawn']}-{player_stats['matches_lost']}")
                    else:
                        print(f"   ❌ Player still doesn't appear in stats")
                else:
                    print(f"   ❌ Player still has NULL rating after match")
                
            except Exception as e:
                print(f"   ❌ Failed to record match: {e}")
        else:
            print(f"   ⚠️  No suitable opponent found in tournament")
    else:
        print(f"   ❌ No tournaments available for testing")
    
    print(f"\n=== Test Complete ===")

if __name__ == "__main__":
    test_null_rating_system()