#!/usr/bin/env python3
"""Check current player rankings"""

from database import TournamentDB

def check_rankings():
    players = TournamentDB.get_all_players()
    print('Current player rankings:')
    for i, player in enumerate(players[:15], 1):
        print(f'{i:2d}. {player["name"]:20} - Rating: {player["rating"]}')

if __name__ == "__main__":
    check_rankings()