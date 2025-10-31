#!/usr/bin/env python
"""Test script to verify initial_rating functionality"""

from database import TournamentDB, get_db_connection

def test_initial_rating():
    """Test the initial_rating feature"""
    
    print("Testing initial_rating feature...")
    print("-" * 50)
    
    # Test 1: Add a player with initial_rating
    print("\n1. Adding test player with initial_rating=350...")
    try:
        player_id = TournamentDB.add_player("Test Player Initial Rating", None, None, 350)
        print(f"✓ Player added with ID: {player_id}")
        
        # Verify player was added with correct initial_rating
        player = TournamentDB.get_player_by_id(player_id)
        if player and player['initial_rating'] == 350:
            print(f"✓ initial_rating set correctly: {player['initial_rating']}")
        else:
            print(f"✗ initial_rating not set correctly: {player.get('initial_rating') if player else 'Player not found'}")
    except Exception as e:
        print(f"✗ Error adding player: {e}")
        return
    
    # Test 2: Edit player's initial_rating
    print("\n2. Editing player's initial_rating to 400...")
    try:
        TournamentDB.edit_player(player_id, "Test Player Updated", None, 400)
        player = TournamentDB.get_player_by_id(player_id)
        if player and player['initial_rating'] == 400:
            print(f"✓ initial_rating updated correctly: {player['initial_rating']}")
        else:
            print(f"✗ initial_rating not updated correctly: {player.get('initial_rating') if player else 'Player not found'}")
    except Exception as e:
        print(f"✗ Error editing player: {e}")
    
    # Test 3: Create a normal tournament and add the player
    print("\n3. Creating normal tournament and adding player...")
    try:
        tournament_id = TournamentDB.create_tournament("Test Tournament Normal", None, None, 'normal')
        print(f"✓ Tournament created with ID: {tournament_id}")
        
        TournamentDB.add_players_to_tournament(tournament_id, [player_id])
        print(f"✓ Player added to tournament")
    except Exception as e:
        print(f"✗ Error creating tournament: {e}")
        return
    
    # Test 4: Record a match and verify initial_rating is used
    print("\n4. Recording a match to verify initial_rating is used...")
    try:
        # Create another player without initial_rating
        player2_id = TournamentDB.add_player("Test Player 2", None, None, None)
        TournamentDB.add_players_to_tournament(tournament_id, [player2_id])
        
        # Record a match
        match_id = TournamentDB.record_match(tournament_id, player_id, player2_id, 2, 1, False, False)
        print(f"✓ Match recorded with ID: {match_id}")
        
        # Check the match details
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT player1_rating_before, player2_rating_before 
                    FROM player_matches 
                    WHERE match_id = %s
                """, (match_id,))
                match = cursor.fetchone()
                
                if match:
                    print(f"✓ Player 1 (with initial_rating=400) started at: {match['player1_rating_before']}")
                    print(f"✓ Player 2 (default) started at: {match['player2_rating_before']}")
                    
                    # Player 1 should start at 400 (their initial_rating)
                    if match['player1_rating_before'] == 400:
                        print("✓ Player 1's initial_rating (400) was correctly used!")
                    else:
                        print(f"✗ Player 1's initial_rating was NOT used (got {match['player1_rating_before']} instead of 400)")
                    
                    # Player 2 should start at 300 (default)
                    if match['player2_rating_before'] == 300:
                        print("✓ Player 2's default rating (300) was correctly used!")
                    else:
                        print(f"✗ Player 2's default rating was NOT used (got {match['player2_rating_before']} instead of 300)")
                else:
                    print("✗ Match not found")
        finally:
            conn.close()
    except Exception as e:
        print(f"✗ Error recording match: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    print("\n5. Cleaning up test data...")
    try:
        TournamentDB.delete_tournament(tournament_id)
        TournamentDB.delete_player(player_id)
        TournamentDB.delete_player(player2_id)
        print("✓ Cleanup complete")
    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")
    
    print("\n" + "-" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    test_initial_rating()
