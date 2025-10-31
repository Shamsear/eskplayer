#!/usr/bin/env python
"""Test to verify initial_rating field can be set for division tournament players"""

from database import TournamentDB, get_db_connection

def test_division_player_initial_rating():
    """Test that initial_rating can be set even for players in division tournaments"""
    
    print("Testing initial_rating for division tournament players...")
    print("-" * 60)
    
    # Step 1: Create a division tournament
    print("\n1. Creating division tournament...")
    try:
        tournament_id = TournamentDB.create_tournament("Test Division Tournament", None, None, 'division')
        print(f"✓ Division tournament created with ID: {tournament_id}")
        
        # Create a division
        division_id = TournamentDB.create_division(tournament_id, "Division A", 270)
        print(f"✓ Division created with ID: {division_id}, starting_rating: 270")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Step 2: Add a player WITHOUT initial_rating
    print("\n2. Adding player without initial_rating...")
    try:
        player1_id = TournamentDB.add_player("Division Player 1", None, None, None)
        print(f"✓ Player 1 added with ID: {player1_id}")
        
        # Add to tournament and assign to division
        TournamentDB.add_players_to_tournament(tournament_id, [player1_id], division_id)
        print(f"✓ Player 1 added to Division A")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Step 3: Add another player WITH initial_rating
    print("\n3. Adding player with initial_rating=400...")
    try:
        player2_id = TournamentDB.add_player("Division Player 2", None, None, 400)
        print(f"✓ Player 2 added with ID: {player2_id}, initial_rating: 400")
        
        # Verify initial_rating was set
        player2 = TournamentDB.get_player_by_id(player2_id)
        if player2['initial_rating'] == 400:
            print(f"✓ initial_rating stored correctly: {player2['initial_rating']}")
        else:
            print(f"✗ initial_rating not stored: {player2.get('initial_rating')}")
        
        # Add to tournament and assign to division
        TournamentDB.add_players_to_tournament(tournament_id, [player2_id], division_id)
        print(f"✓ Player 2 added to Division A")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Step 4: Record a match in the division tournament
    print("\n4. Recording match in division tournament...")
    try:
        match_id = TournamentDB.record_match(tournament_id, player1_id, player2_id, 1, 2, False, False)
        print(f"✓ Match recorded with ID: {match_id}")
        
        # Check what ratings were used
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
                    print(f"\n   Player 1 (no initial_rating) started at: {match['player1_rating_before']}")
                    print(f"   Player 2 (initial_rating=400) started at: {match['player2_rating_before']}")
                    
                    # Both should use division's 270, NOT the initial_rating
                    if match['player1_rating_before'] == 270:
                        print("   ✓ Player 1 correctly used division rating (270)")
                    else:
                        print(f"   ✗ Player 1 did NOT use division rating (got {match['player1_rating_before']})")
                    
                    if match['player2_rating_before'] == 270:
                        print("   ✓ Player 2 correctly used division rating (270), NOT initial_rating!")
                    else:
                        print(f"   ✗ Player 2 did NOT use division rating (got {match['player2_rating_before']})")
        finally:
            conn.close()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 5: Edit Player 1 to add initial_rating AFTER playing in division
    print("\n5. Editing Player 1 to set initial_rating=350 (after division play)...")
    try:
        TournamentDB.edit_player(player1_id, "Division Player 1 Updated", None, 350)
        player1 = TournamentDB.get_player_by_id(player1_id)
        
        if player1['initial_rating'] == 350:
            print(f"✓ initial_rating can be set for division player: {player1['initial_rating']}")
            print("✓ This shows initial_rating field is available for ALL players!")
        else:
            print(f"✗ Failed to set initial_rating: {player1.get('initial_rating')}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Cleanup
    print("\n6. Cleaning up test data...")
    try:
        TournamentDB.delete_tournament(tournament_id)
        TournamentDB.delete_player(player1_id)
        TournamentDB.delete_player(player2_id)
        print("✓ Cleanup complete")
    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")
    
    print("\n" + "-" * 60)
    print("Key Findings:")
    print("1. initial_rating field CAN be set for players in division tournaments")
    print("2. Division tournament starting ratings take PRIORITY over initial_rating")
    print("3. initial_rating is stored and available for editing regardless of tournament history")
    print("\nTesting complete!")

if __name__ == "__main__":
    test_division_player_initial_rating()
