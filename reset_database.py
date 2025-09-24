#!/usr/bin/env python3
"""
Database Reset Script - Clean slate for player-centric tournament system
This script will DROP all existing tables and recreate them with the new schema
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import hashlib

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(
            os.getenv('DATABASE_URL'),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def reset_database():
    """Drop all existing tables and recreate with new schema"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            print("🗑️  Dropping all existing tables...")
            
            # Drop all existing tables (order matters due to foreign keys)
            drop_tables = [
                'manual_qualifiers',
                'knockout_games', 
                'knockout_matches',
                'matches',
                'tournament_players',
                'player_stats',
                'player_matches',
                'players',
                'tournaments',
                'teams',
                'groups',
                'admin_users'
            ]
            
            for table in drop_tables:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                    print(f"   ✅ Dropped {table}")
                except Exception as e:
                    print(f"   ⚠️  Could not drop {table}: {e}")
            
            print("\n🏗️  Creating new player-centric tables...")
            
            # Create admin users table
            cursor.execute('''
                CREATE TABLE admin_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            print("   ✅ Created admin_users table")
            
            # Create players table
            cursor.execute('''
                CREATE TABLE players (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    rating INTEGER DEFAULT 300,
                    matches_played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    draws INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    goals_scored INTEGER DEFAULT 0,
                    goals_conceded INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            print("   ✅ Created players table")
            
            # Create tournaments table
            cursor.execute('''
                CREATE TABLE tournaments (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            print("   ✅ Created tournaments table")
            
            # Create tournament_players (many-to-many relationship)
            cursor.execute('''
                CREATE TABLE tournament_players (
                    id SERIAL PRIMARY KEY,
                    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
                    player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tournament_id, player_id)
                );
            ''')
            print("   ✅ Created tournament_players table")
            
            # Create player_matches table (1v1 matches)
            cursor.execute('''
                CREATE TABLE player_matches (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER NOT NULL,
                    tournament_id INTEGER REFERENCES tournaments(id),
                    player1_id INTEGER REFERENCES players(id),
                    player2_id INTEGER REFERENCES players(id),
                    player1_goals INTEGER DEFAULT 0,
                    player2_goals INTEGER DEFAULT 0,
                    winner_id INTEGER REFERENCES players(id),
                    is_draw BOOLEAN DEFAULT false,
                    player1_rating_before INTEGER,
                    player2_rating_before INTEGER,
                    player1_rating_after INTEGER,
                    player2_rating_after INTEGER,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            print("   ✅ Created player_matches table")
            
            # Create player_stats table (for tournament-wise stats)
            cursor.execute('''
                CREATE TABLE player_stats (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER REFERENCES players(id),
                    tournament_id INTEGER REFERENCES tournaments(id),
                    matches_played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    draws INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    goals_scored INTEGER DEFAULT 0,
                    goals_conceded INTEGER DEFAULT 0,
                    rating_change INTEGER DEFAULT 0,
                    UNIQUE(player_id, tournament_id)
                );
            ''')
            print("   ✅ Created player_stats table")
            
            print("\n📊 Creating indexes for better performance...")
            
            # Create indexes for better performance
            indexes = [
                ('idx_players_name', 'players', 'name'),
                ('idx_players_rating', 'players', 'rating'),
                ('idx_tournaments_status', 'tournaments', 'status'),
                ('idx_tournament_players_tournament', 'tournament_players', 'tournament_id'),
                ('idx_tournament_players_player', 'tournament_players', 'player_id'),
                ('idx_player_matches_tournament', 'player_matches', 'tournament_id'),
                ('idx_player_matches_players', 'player_matches', 'player1_id, player2_id'),
                ('idx_player_stats_player', 'player_stats', 'player_id'),
                ('idx_player_stats_tournament', 'player_stats', 'tournament_id'),
            ]
            
            for idx_name, table, columns in indexes:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns});')
                print(f"   ✅ Created index {idx_name}")
            
            print("\n👤 Creating default admin user...")
            
            # Create default admin user
            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)",
                ('admin', password_hash)
            )
            print("   ✅ Created admin user: username='admin', password='admin123'")
            
            conn.commit()
            print("\n🎉 Database reset completed successfully!")
            print("\n📋 Summary of created tables:")
            print("   • admin_users - Admin authentication")
            print("   • players - Individual player records with ratings")
            print("   • tournaments - Tournament containers")
            print("   • tournament_players - Many-to-many player-tournament relationship")
            print("   • player_matches - 1v1 match records with rating changes")
            print("   • player_stats - Tournament-wise player statistics")
            print("\n🚀 Ready to use! Login with admin/admin123")
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error resetting database: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    print("🔄 Starting database reset...")
    print("⚠️  WARNING: This will delete ALL existing data!")
    
    # Confirm before proceeding
    confirm = input("\nDo you want to continue? (type 'yes' to confirm): ")
    if confirm.lower() == 'yes':
        reset_database()
    else:
        print("❌ Database reset cancelled.")