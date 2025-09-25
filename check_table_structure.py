#!/usr/bin/env python3
"""Check the structure of the players table"""

from database import get_db_connection

def check_table_structure():
    """Check what columns exist in the players table"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get table structure
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'players'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            print("Players table structure:")
            for col in columns:
                print(f"  {col['column_name']:20} {col['data_type']:15} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
                
            # Check sample data for Pachu
            cursor.execute("SELECT * FROM players WHERE name ILIKE '%pachu%' LIMIT 1")
            sample = cursor.fetchone()
            
            if sample:
                print(f"\nSample data for Pachu:")
                for key, value in sample.items():
                    print(f"  {key:20}: {value}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_table_structure()