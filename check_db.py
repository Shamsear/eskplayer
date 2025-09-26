import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
def get_db_connection():
    return psycopg2.connect(
        os.getenv('DATABASE_URL'),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# Check table structures
conn = get_db_connection()
cursor = conn.cursor()

print('=== PLAYER_MATCHES TABLE STRUCTURE ===')
cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns 
    WHERE table_name = 'player_matches'
    ORDER BY ordinal_position
""")
for row in cursor.fetchall():
    print(f'{row["column_name"]:<25} {row["data_type"]:<20} nullable={row["is_nullable"]} default={row["column_default"]}')

print('\n=== GUEST_MATCHES TABLE STRUCTURE ===')
cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns 
    WHERE table_name = 'guest_matches'
    ORDER BY ordinal_position
""")
guest_columns = cursor.fetchall()
if guest_columns:
    for row in guest_columns:
        print(f'{row["column_name"]:<25} {row["data_type"]:<20} nullable={row["is_nullable"]} default={row["column_default"]}')
else:
    print('No guest_matches table found')

print('\n=== SAMPLE PLAYER_MATCHES DATA ===')
cursor.execute('SELECT * FROM player_matches ORDER BY played_at DESC LIMIT 3')
player_matches = cursor.fetchall()
for match in player_matches:
    print(dict(match))

print('\n=== SAMPLE GUEST_MATCHES DATA ===')
cursor.execute('SELECT * FROM guest_matches ORDER BY played_at DESC LIMIT 3')
guest_matches = cursor.fetchall()
for match in guest_matches:
    print(dict(match))

print('\n=== CHECKING FOR ANY MATCHES WITH GUEST DATA ===')
cursor.execute("""
    SELECT COUNT(*) as total_player_matches FROM player_matches
""")
player_count = cursor.fetchone()['total_player_matches']

cursor.execute("""
    SELECT COUNT(*) as total_guest_matches FROM guest_matches
""")
guest_count = cursor.fetchone()['total_guest_matches']

print(f'Total player matches: {player_count}')
print(f'Total guest matches: {guest_count}')

cursor.close()
conn.close()