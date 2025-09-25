#!/usr/bin/env python3
"""Check player_stats table structure"""

from database import get_db_connection

def check_player_stats_table():
    """Check what columns exist in the player_stats table"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get table structure
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'player_stats'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            print("Player_stats table structure:")
            for col in columns:
                print(f"  {col['column_name']:20} {col['data_type']:15} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
                
            # Check sample data
            cursor.execute("SELECT * FROM player_stats LIMIT 5")
            samples = cursor.fetchall()
            
            if samples:
                print(f"\nSample data from player_stats:")
                for i, sample in enumerate(samples):
                    print(f"  Row {i+1}:")
                    for key, value in sample.items():
                        print(f"    {key:20}: {value}")
                    print()
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_player_stats_table()