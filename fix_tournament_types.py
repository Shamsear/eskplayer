#!/usr/bin/env python3
"""
Migration script to ensure all tournaments have a tournament_type value.
This fixes any NULL tournament_type values in existing tournaments.
"""

from database import get_db_connection

def fix_tournament_types():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Update any NULL tournament_type to 'normal'
            cursor.execute("""
                UPDATE tournaments 
                SET tournament_type = 'normal' 
                WHERE tournament_type IS NULL
            """)
            affected = cursor.rowcount
            conn.commit()
            print(f"✓ Updated {affected} tournament(s) to have tournament_type='normal'")
            
            # Check current state
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN tournament_type = 'normal' THEN 1 ELSE 0 END) as normal_count,
                    SUM(CASE WHEN tournament_type = 'division' THEN 1 ELSE 0 END) as division_count
                FROM tournaments
            """)
            result = cursor.fetchone()
            print(f"\nCurrent tournament types:")
            print(f"  Total: {result['total']}")
            print(f"  Normal: {result['normal_count']}")
            print(f"  Division: {result['division_count']}")
            
    except Exception as e:
        conn.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("Fixing tournament types...")
    fix_tournament_types()
    print("\n✓ Done!")
