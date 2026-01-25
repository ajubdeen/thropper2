"""
Migration script to move JSON data to PostgreSQL database.

Migrates:
1. leaderboard.json -> leaderboard_entries table
2. game_history.json -> game_histories table
"""

import json
import os
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")


def migrate_leaderboard():
    """Migrate leaderboard.json to database"""
    filepath = "game/leaderboard.json"
    if not os.path.exists(filepath):
        filepath = "leaderboard.json"
    
    if not os.path.exists(filepath):
        print("No leaderboard.json found, skipping")
        return 0
    
    with open(filepath, 'r') as f:
        scores = json.load(f)
    
    print(f"Found {len(scores)} leaderboard entries to migrate")
    
    migrated = 0
    for score in scores:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/leaderboard",
                json={
                    "userId": score.get("user_id", "migrated"),
                    "gameId": score.get("game_id", ""),
                    "playerName": score.get("player_name", "Unknown"),
                    "turnsSurvived": score.get("turns_survived", 0),
                    "erasVisited": score.get("eras_visited", 0),
                    "belongingScore": score.get("belonging", 0),
                    "legacyScore": score.get("legacy", 0),
                    "freedomScore": score.get("freedom", 0),
                    "totalScore": score.get("total", 0),
                    "endingType": score.get("ending_type", ""),
                    "finalEra": score.get("final_era", ""),
                    "blurb": score.get("blurb", ""),
                    "endingNarrative": score.get("ending_narrative", ""),
                },
                timeout=30
            )
            if response.status_code == 200:
                migrated += 1
                print(f"  Migrated: {score.get('player_name', 'Unknown')} - {score.get('total', 0)} pts")
            else:
                print(f"  Failed: {score.get('player_name', 'Unknown')} - {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f"Migrated {migrated}/{len(scores)} leaderboard entries")
    return migrated


def migrate_game_history():
    """Migrate game_history.json to database"""
    filepath = "game/game_history.json"
    if not os.path.exists(filepath):
        filepath = "game_history.json"
    
    if not os.path.exists(filepath):
        print("No game_history.json found, skipping")
        return 0
    
    with open(filepath, 'r') as f:
        games = json.load(f)
    
    print(f"Found {len(games)} game histories to migrate")
    
    migrated = 0
    for game in games:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/history",
                json={
                    "gameId": game.get("id", ""),
                    "userId": game.get("user_id", "migrated"),
                    "playerName": game.get("player_name"),
                    "startedAt": game.get("started_at"),
                    "endedAt": game.get("ended_at"),
                    "eras": game.get("eras", []),
                    "finalScore": game.get("final_score"),
                    "endingType": game.get("ending_type"),
                    "blurb": game.get("blurb"),
                },
                timeout=30
            )
            if response.status_code == 200:
                migrated += 1
                print(f"  Migrated: {game.get('player_name', 'Unknown')} - {game.get('id', '')}")
            else:
                print(f"  Failed: {game.get('player_name', 'Unknown')} - {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f"Migrated {migrated}/{len(games)} game histories")
    return migrated


def main():
    print("=" * 60)
    print("ANACHRON DATA MIGRATION")
    print("JSON Files -> PostgreSQL Database")
    print("=" * 60)
    print()
    
    print("Migrating leaderboard...")
    leaderboard_count = migrate_leaderboard()
    print()
    
    print("Migrating game history...")
    history_count = migrate_game_history()
    print()
    
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print(f"  Leaderboard entries: {leaderboard_count}")
    print(f"  Game histories: {history_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
