import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime
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

def init_db():
    """Initialize database with required tables"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Create admin users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create players table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    rating INTEGER DEFAULT 300,
                    matches_played INTEGER DEFAULT 0,
                    matches_won INTEGER DEFAULT 0,
                    matches_drawn INTEGER DEFAULT 0,
                    matches_lost INTEGER DEFAULT 0,
                    goals_scored INTEGER DEFAULT 0,
                    goals_conceded INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Add columns to existing players table if they don't exist (migration)
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='players' AND column_name='matches_won') THEN
                        ALTER TABLE players ADD COLUMN matches_won INTEGER DEFAULT 0;
                        UPDATE players SET matches_won = wins WHERE wins IS NOT NULL;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='players' AND column_name='matches_drawn') THEN
                        ALTER TABLE players ADD COLUMN matches_drawn INTEGER DEFAULT 0;
                        UPDATE players SET matches_drawn = draws WHERE draws IS NOT NULL;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='players' AND column_name='matches_lost') THEN
                        ALTER TABLE players ADD COLUMN matches_lost INTEGER DEFAULT 0;
                        UPDATE players SET matches_lost = losses WHERE losses IS NOT NULL;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='players' AND column_name='clean_sheets') THEN
                        ALTER TABLE players ADD COLUMN clean_sheets INTEGER DEFAULT 0;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='players' AND column_name='golden_glove_points') THEN
                        ALTER TABLE players ADD COLUMN golden_glove_points INTEGER DEFAULT 0;
                    END IF;
                END $$;
            """)
            
            # Create tournaments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tournaments (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived')),
                    tournament_type VARCHAR(20) DEFAULT 'normal' CHECK (tournament_type IN ('normal', 'division')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Add tournament_type column if it doesn't exist (migration)
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tournaments' AND column_name='tournament_type') THEN
                        ALTER TABLE tournaments ADD COLUMN tournament_type VARCHAR(20) DEFAULT 'normal' CHECK (tournament_type IN ('normal', 'division'));
                    END IF;
                END $$;
            """)
            
            # Create divisions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS divisions (
                    id SERIAL PRIMARY KEY,
                    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    starting_rating INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tournament_id, name)
                );
            ''')
            
            # Create tournament_players (many-to-many relationship)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tournament_players (
                    id SERIAL PRIMARY KEY,
                    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
                    player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
                    division_id INTEGER REFERENCES divisions(id) ON DELETE SET NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tournament_id, player_id)
                );
            ''')
            
            # Add division_id column if it doesn't exist (migration)
            cursor.execute('''
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tournament_players' AND column_name='division_id') THEN
                        ALTER TABLE tournament_players ADD COLUMN division_id INTEGER REFERENCES divisions(id) ON DELETE SET NULL;
                    END IF;
                END $$;
            ''')
            
            # Create player_matches table (one-on-one matches)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_matches (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER NOT NULL,
                    tournament_id INTEGER REFERENCES tournaments(id),
                    player1_id INTEGER REFERENCES players(id),
                    player2_id INTEGER REFERENCES players(id),
                    player1_goals INTEGER DEFAULT 0,
                    player2_goals INTEGER DEFAULT 0,
                    winner_id INTEGER REFERENCES players(id),
                    is_draw BOOLEAN DEFAULT false,
                    is_walkover BOOLEAN DEFAULT false,
                    is_null_match BOOLEAN DEFAULT false,
                    player1_absent BOOLEAN DEFAULT false,
                    player2_absent BOOLEAN DEFAULT false,
                    player1_rating_before INTEGER,
                    player2_rating_before INTEGER,
                    player1_rating_after INTEGER,
                    player2_rating_after INTEGER,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create player_stats table (for tournament-wise stats)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_stats (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER REFERENCES players(id),
                    tournament_id INTEGER REFERENCES tournaments(id),
                    tournament_rating INTEGER,
                    matches_played INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    draws INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    goals_scored INTEGER DEFAULT 0,
                    goals_conceded INTEGER DEFAULT 0,
                    rating_change INTEGER DEFAULT 0,
                    clean_sheets INTEGER DEFAULT 0,
                    golden_glove_points INTEGER DEFAULT 0,
                    UNIQUE(player_id, tournament_id)
                );
            ''')
            # Groups and teams tables removed - system is now player-centric
            
            # Create matches table (Group Stage)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER NOT NULL,
                    date TIMESTAMP NOT NULL,
                    round VARCHAR(50) DEFAULT 'Group Stage',
                    club VARCHAR(100) NOT NULL,
                    player VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    goals INTEGER DEFAULT 0,
                    goals_conceded INTEGER DEFAULT 0,
                    clean_sheet INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create knockout_matches table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knockout_matches (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER NOT NULL,
                    date TIMESTAMP NOT NULL,
                    stage VARCHAR(50) NOT NULL,
                    club VARCHAR(100) NOT NULL,
                    player VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    goals INTEGER DEFAULT 0,
                    goals_conceded INTEGER DEFAULT 0,
                    clean_sheet INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    winner VARCHAR(100),
                    match_number INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create knockout_games table for individual game results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knockout_games (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER NOT NULL,
                    date TIMESTAMP NOT NULL,
                    stage VARCHAR(50) NOT NULL,
                    club1 VARCHAR(100) NOT NULL,
                    player1 VARCHAR(100) NOT NULL,
                    role1 VARCHAR(20) NOT NULL,
                    club2 VARCHAR(100) NOT NULL,
                    player2 VARCHAR(100) NOT NULL,
                    role2 VARCHAR(20) NOT NULL,
                    club1_goals INTEGER DEFAULT 0,
                    club2_goals INTEGER DEFAULT 0,
                    game_result DECIMAL(2,1) DEFAULT 0,  -- 1 = club1 win, 0 = club2 win, 0.5 = draw
                    match_winner VARCHAR(100),
                    match_number INTEGER,
                    game_number INTEGER,  -- 1=Cap vs Cap, 2=Cap vs Mem, 3=Mem vs Cap, 4=Mem vs Mem
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')            
            
            # Create manual_qualifiers table for manually selected knockout qualifiers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS manual_qualifiers (
                    id SERIAL PRIMARY KEY,
                    team_name VARCHAR(100) NOT NULL,
                    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(team_name)
                );
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_match_id ON matches(match_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_club ON matches(club);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_player ON matches(player);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knockout_match_id ON knockout_matches(match_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knockout_club ON knockout_matches(club);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knockout_player ON knockout_matches(player);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knockout_stage ON knockout_matches(stage);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knockout_games_match_id ON knockout_games(match_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knockout_games_stage ON knockout_games(stage);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_manual_qualifiers_team ON manual_qualifiers(team_name);')
            
            # New indexes for player-centric system
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_rating ON players(rating);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournament_players_tournament ON tournament_players(tournament_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tournament_players_player ON tournament_players(player_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_tournament ON player_matches(tournament_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_players ON player_matches(player1_id, player2_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_stats(player_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_stats_tournament ON player_stats(tournament_id);')
            
            # Groups removed - no longer needed
            
            conn.commit()
            print("Database initialized successfully!")
            
            # Run migrations
            migrate_database(conn)
            
            # Create default admin user
            create_default_admin(conn)
            
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        conn.close()

def create_default_admin(conn):
    """Create default admin user"""
    import hashlib
    try:
        with conn.cursor() as cursor:
            # Check if admin already exists
            cursor.execute("SELECT id FROM admin_users WHERE username = %s", ('admin',))
            if not cursor.fetchone():
                # Create default admin with password 'admin123'
                password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)",
                    ('admin', password_hash)
                )
                conn.commit()
                print("Default admin user created: username='admin', password='admin123'")
            else:
                print("Admin user already exists")
    except Exception as e:
        print(f"Error creating admin user: {e}")

def migrate_database(conn):
    """Run database migrations"""
    try:
        with conn.cursor() as cursor:
            # Migration 1: Add points column to knockout_matches if it doesn't exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='knockout_matches' AND column_name='points'
            """)
            points_column_exists = cursor.fetchone()
            
            if not points_column_exists:
                print("Adding points column to knockout_matches table...")
                cursor.execute("ALTER TABLE knockout_matches ADD COLUMN points INTEGER DEFAULT 0")
                conn.commit()
                print("Points column added successfully!")
            else:
                print("Points column already exists in knockout_matches table")
            
            # Migration 2: Update default rating from 600 to 300
            cursor.execute("""
                SELECT column_default 
                FROM information_schema.columns 
                WHERE table_name='players' AND column_name='rating'
            """)
            rating_default = cursor.fetchone()
            
            if rating_default and '600' in str(rating_default['column_default']):
                print("Updating default player rating from 600 to 300...")
                cursor.execute("ALTER TABLE players ALTER COLUMN rating SET DEFAULT 300")
                conn.commit()
                print("Player default rating updated successfully!")
            else:
                print("Player rating default is already set correctly")
            
            # Migration 3: Add absence tracking columns to player_matches
            absence_columns = ['is_walkover', 'is_null_match', 'player1_absent', 'player2_absent']
            for column_name in absence_columns:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='player_matches' AND column_name=%s
                """, (column_name,))
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    print(f"Adding {column_name} column to player_matches table...")
                    cursor.execute(f"ALTER TABLE player_matches ADD COLUMN {column_name} BOOLEAN DEFAULT false")
                    conn.commit()
                    print(f"{column_name} column added successfully!")
                else:
                    print(f"{column_name} column already exists in player_matches table")
            
            # Migration 4: Reset rating to NULL for players who haven't played any matches
            print("Checking for players with rating=300 but no matches played...")
            cursor.execute("""
                SELECT COUNT(*) as count FROM players 
                WHERE rating = 300 AND matches_played = 0
            """)
            unplayed_count = cursor.fetchone()['count']
            
            if unplayed_count > 0:
                print(f"Found {unplayed_count} players with rating=300 but no matches played. Updating to NULL...")
                cursor.execute("""
                    UPDATE players 
                    SET rating = NULL 
                    WHERE rating = 300 AND matches_played = 0
                """)
                conn.commit()
                print(f"Updated {unplayed_count} players' ratings to NULL successfully!")
            else:
                print("No unplayed players with rating=300 found")
            
            # Migration 5: Add photo columns to players table
            photo_columns = ['photo_url', 'photo_file_id']
            for column_name in photo_columns:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='players' AND column_name=%s
                """, (column_name,))
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    print(f"Adding {column_name} column to players table...")
                    if column_name == 'photo_url':
                        cursor.execute("ALTER TABLE players ADD COLUMN photo_url TEXT")
                    elif column_name == 'photo_file_id':
                        cursor.execute("ALTER TABLE players ADD COLUMN photo_file_id VARCHAR(255)")
                    conn.commit()
                    print(f"{column_name} column added successfully!")
                else:
                    print(f"{column_name} column already exists in players table")
            
            # Migration 6: Add photo columns to tournaments table
            tournament_photo_columns = ['tournament_photo_url', 'tournament_photo_file_id']
            for column_name in tournament_photo_columns:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='tournaments' AND column_name=%s
                """, (column_name,))
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    print(f"Adding {column_name} column to tournaments table...")
                    if column_name == 'tournament_photo_url':
                        cursor.execute("ALTER TABLE tournaments ADD COLUMN tournament_photo_url TEXT")
                    elif column_name == 'tournament_photo_file_id':
                        cursor.execute("ALTER TABLE tournaments ADD COLUMN tournament_photo_file_id VARCHAR(255)")
                    conn.commit()
                    print(f"{column_name} column added successfully!")
                else:
                    print(f"{column_name} column already exists in tournaments table")
            
            # Migration 7: Add tournament_rating column to player_stats
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='player_stats' AND column_name='tournament_rating'
            """)
            tournament_rating_exists = cursor.fetchone()
            
            if not tournament_rating_exists:
                print("Adding tournament_rating column to player_stats table...")
                cursor.execute("ALTER TABLE player_stats ADD COLUMN tournament_rating INTEGER")
                conn.commit()
                print("tournament_rating column added successfully!")
            else:
                print("tournament_rating column already exists in player_stats table")
            
            # Migration 8: Add initial_rating column to players table
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='players' AND column_name='initial_rating'
            """)
            initial_rating_exists = cursor.fetchone()
            
            if not initial_rating_exists:
                print("Adding initial_rating column to players table...")
                cursor.execute("ALTER TABLE players ADD COLUMN initial_rating INTEGER")
                conn.commit()
                print("initial_rating column added successfully!")
            else:
                print("initial_rating column already exists in players table")
            
            # Migration 9: Add guest_matches table
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='guest_matches'
            """)
            guest_table_exists = cursor.fetchone()
            
            if not guest_table_exists:
                print("Creating guest_matches table...")
                cursor.execute('''
                    CREATE TABLE guest_matches (
                        id SERIAL PRIMARY KEY,
                        match_id INTEGER NOT NULL,
                        tournament_id INTEGER REFERENCES tournaments(id),
                        clan_player_id INTEGER REFERENCES players(id),
                        guest_name VARCHAR(100) NOT NULL,
                        clan_goals INTEGER DEFAULT 0,
                        guest_goals INTEGER DEFAULT 0,
                        clan_absent BOOLEAN DEFAULT false,
                        guest_absent BOOLEAN DEFAULT false,
                        is_null_match BOOLEAN DEFAULT false,
                        is_walkover BOOLEAN DEFAULT false,
                        clan_rating_before INTEGER,
                        clan_rating_after INTEGER,
                        played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''');
                
                # Add indexes for guest matches
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_guest_matches_clan_player ON guest_matches(clan_player_id);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_guest_matches_tournament ON guest_matches(tournament_id);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_guest_matches_played_at ON guest_matches(played_at DESC);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_guest_matches_match_id ON guest_matches(match_id);')
                
                # Add indexes for player_matches table for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_played_at ON player_matches(played_at DESC);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_tournament ON player_matches(tournament_id);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_player1 ON player_matches(player1_id);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_player2 ON player_matches(player2_id);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_match_id ON player_matches(match_id);')
                
                # Add indexes for players table for search performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_rating ON players(rating DESC);')
                
                conn.commit()
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_played_at ON player_matches(played_at DESC);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_tournament ON player_matches(tournament_id);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_player1 ON player_matches(player1_id);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_player2 ON player_matches(player2_id);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_matches_match_id ON player_matches(match_id);')
                
                # Add indexes for players table for search performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_rating ON players(rating DESC);')
                
                conn.commit()
                print("guest_matches table created successfully!")
            else:
                print("guest_matches table already exists")
                
    except Exception as e:
        print(f"Migration error (non-critical): {e}")
        # Don't raise - migrations should be non-breaking

# Team population removed - system is now player-centric

class TournamentDB:
    """Database operations for tournament management"""
    
    @staticmethod
    def get_next_match_id():
        """Get the next match ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 as next_id FROM matches")
                result = cursor.fetchone()
                return result['next_id'] if result else 1
        finally:
            conn.close()
    
    @staticmethod
    def get_next_knockout_match_id():
        """Get the next knockout match ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 as next_id FROM knockout_matches")
                result = cursor.fetchone()
                return result['next_id'] if result else 1
        finally:
            conn.close()
    
    @staticmethod
    def insert_match(match_data):
        """Insert regular match data"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO matches 
                    (match_id, date, round, club, player, role, goals, goals_conceded, clean_sheet, points)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', match_data)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def insert_knockout_match(match_data):
        """Insert knockout match data"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO knockout_matches 
                    (match_id, date, stage, club, player, role, goals, goals_conceded, clean_sheet, points, winner, match_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', match_data)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def insert_knockout_game(game_data):
        """Insert individual knockout game data"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO knockout_games 
                    (match_id, date, stage, club1, player1, role1, club2, player2, role2, 
                     club1_goals, club2_goals, game_result, match_winner, match_number, game_number)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', game_data)
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # @staticmethod
    # def get_all_matches():
    #     """Get all regular matches as DataFrame - DISABLED (pandas removed)"""
    #     pass
    
    # @staticmethod
    # def get_all_knockout_matches():
    #     """Get all knockout matches as DataFrame - DISABLED (pandas removed)"""
    #     pass
    
    # @staticmethod
    # def get_all_knockout_games():
    #     """Get all individual knockout games - DISABLED (pandas removed)"""
    #     pass
    
    # @staticmethod
    # def get_knockout_individual_game_stats():
    #     """Convert knockout individual games to match-like format for stats - DISABLED (pandas removed)"""
    #     pass
    
    # @staticmethod
    # def get_combined_match_data():
    #     """Get combined data - DISABLED (pandas removed)"""
    #     pass
    
    # Old team-related methods removed - system is now player-centric
    # New methods for player-centric system
    
    @staticmethod
    def authenticate_admin(username, password):
        """Authenticate admin user"""
        import hashlib
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                cursor.execute(
                    "SELECT id FROM admin_users WHERE username = %s AND password_hash = %s",
                    (username, password_hash)
                )
                return cursor.fetchone() is not None
        finally:
            conn.close()
    
    @staticmethod
    def add_player(name, photo_url=None, photo_file_id=None, initial_rating=None):
        """Add a new player with optional photo and initial rating"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO players (name, rating, photo_url, photo_file_id, initial_rating) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (name, None, photo_url, photo_file_id, initial_rating)
                )
                player_id = cursor.fetchone()['id']
                conn.commit()
                return player_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def add_players_bulk(player_names):
        """Add multiple players at once"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                added_players = []
                for name in player_names:
                    try:
                        cursor.execute(
                            "INSERT INTO players (name, rating) VALUES (%s, %s) RETURNING id, name",
                            (name.strip(), None)
                        )
                        result = cursor.fetchone()
                        added_players.append(result)
                    except Exception as e:
                        print(f"Skipping duplicate player: {name}")
                conn.commit()
                return added_players
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_all_players(search=None, limit=None):
        """Get all players with optional search and limit"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                query = "SELECT * FROM players"
                params = []
                
                if search:
                    query += " WHERE name ILIKE %s"
                    params.append(f"%{search}%")
                
                query += " ORDER BY rating DESC NULLS LAST, name ASC"
                
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def create_tournament(name, tournament_photo_url=None, tournament_photo_file_id=None, tournament_type='normal'):
        """Create a new tournament with optional photo and type"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tournaments (name, tournament_photo_url, tournament_photo_file_id, tournament_type) VALUES (%s, %s, %s, %s) RETURNING id",
                    (name, tournament_photo_url, tournament_photo_file_id, tournament_type)
                )
                tournament_id = cursor.fetchone()['id']
                conn.commit()
                return tournament_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_all_tournaments():
        """Get all tournaments"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM tournaments ORDER BY created_at DESC"
                )
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def add_players_to_tournament(tournament_id, player_ids, division_id=None):
        """Add players to a tournament, optionally with a division"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for player_id in player_ids:
                    try:
                        cursor.execute(
                            "INSERT INTO tournament_players (tournament_id, player_id, division_id) VALUES (%s, %s, %s)",
                            (tournament_id, player_id, division_id)
                        )
                    except Exception:
                        # Skip if already exists
                        pass
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_tournament_players(tournament_id):
        """Get all players in a tournament with their division info and tournament-specific rating"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.*, 
                        tp.division_id, 
                        d.name as division_name, 
                        d.starting_rating as division_starting_rating,
                        ps.tournament_rating,
                        COALESCE(ps.tournament_rating, p.rating) as display_rating
                    FROM players p
                    JOIN tournament_players tp ON p.id = tp.player_id
                    LEFT JOIN divisions d ON tp.division_id = d.id
                    LEFT JOIN player_stats ps ON p.id = ps.player_id AND ps.tournament_id = tp.tournament_id
                    WHERE tp.tournament_id = %s
                    ORDER BY COALESCE(ps.tournament_rating, p.rating) DESC NULLS LAST, p.name ASC
                """, (tournament_id,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_tournament_by_id(tournament_id):
        """Get a specific tournament by ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM tournaments WHERE id = %s", (tournament_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def update_tournament_photo(tournament_id, tournament_photo_url, tournament_photo_file_id):
        """Update tournament photo information"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if tournament exists
                cursor.execute("SELECT * FROM tournaments WHERE id = %s", (tournament_id,))
                tournament = cursor.fetchone()
                if not tournament:
                    raise ValueError("Tournament not found")
                
                # Update photo fields
                cursor.execute(
                    "UPDATE tournaments SET tournament_photo_url = %s, tournament_photo_file_id = %s WHERE id = %s",
                    (tournament_photo_url, tournament_photo_file_id, tournament_id)
                )
                conn.commit()
                return tournament_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def update_tournament(tournament_id, name, tournament_photo_url=None, tournament_photo_file_id=None, tournament_type=None):
        """Update tournament name, photo, and optionally type"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if tournament exists
                cursor.execute("SELECT * FROM tournaments WHERE id = %s", (tournament_id,))
                tournament = cursor.fetchone()
                if not tournament:
                    raise ValueError("Tournament not found")
                
                # Check if name already exists for another tournament
                cursor.execute("SELECT id FROM tournaments WHERE name = %s AND id != %s", (name, tournament_id))
                existing_tournament = cursor.fetchone()
                if existing_tournament:
                    raise ValueError(f"A tournament with the name '{name}' already exists")
                
                # Update the tournament
                if tournament_type is not None:
                    cursor.execute(
                        "UPDATE tournaments SET name = %s, tournament_photo_url = %s, tournament_photo_file_id = %s, tournament_type = %s WHERE id = %s",
                        (name.strip(), tournament_photo_url, tournament_photo_file_id, tournament_type, tournament_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE tournaments SET name = %s, tournament_photo_url = %s, tournament_photo_file_id = %s WHERE id = %s",
                        (name.strip(), tournament_photo_url, tournament_photo_file_id, tournament_id)
                    )
                conn.commit()
                return tournament_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def delete_division(division_id):
        """Delete a division"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM divisions WHERE id = %s", (division_id,))
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def update_division(division_id, name, starting_rating):
        """Update a division's name and starting rating"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE divisions SET name = %s, starting_rating = %s WHERE id = %s",
                    (name, starting_rating, division_id)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def create_division(tournament_id, name, starting_rating):
        """Create a new division for a tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO divisions (tournament_id, name, starting_rating) VALUES (%s, %s, %s) RETURNING id",
                    (tournament_id, name, starting_rating)
                )
                division_id = cursor.fetchone()['id']
                conn.commit()
                return division_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_divisions_by_tournament(tournament_id):
        """Get all divisions for a tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM divisions WHERE tournament_id = %s ORDER BY starting_rating DESC, name ASC",
                    (tournament_id,)
                )
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_division_by_id(division_id):
        """Get a specific division by ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM divisions WHERE id = %s", (division_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def assign_player_to_division(tournament_id, player_id, division_id):
        """Assign a player to a division in a tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE tournament_players SET division_id = %s WHERE tournament_id = %s AND player_id = %s",
                    (division_id, tournament_id, player_id)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_player_division(tournament_id, player_id):
        """Get the division a player is assigned to in a tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT d.* FROM divisions d
                    JOIN tournament_players tp ON d.id = tp.division_id
                    WHERE tp.tournament_id = %s AND tp.player_id = %s
                """, (tournament_id, player_id))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def calculate_rating_change(winner_rating, loser_rating, is_draw=False):
        """Calculate rating change based on ELO-like system"""
        # K-factor (maximum rating change)
        K = 32
        
        # Expected scores
        expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
        expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))
        
        if is_draw:
            # Draw: both players get 0.5 points
            winner_change = K * (0.5 - expected_winner)
            loser_change = K * (0.5 - expected_loser)
        else:
            # Win/Loss: winner gets 1 point, loser gets 0
            winner_change = K * (1 - expected_winner)
            loser_change = K * (0 - expected_loser)
        
        return int(round(winner_change)), int(round(loser_change))
    
    @staticmethod
    def calculate_enhanced_rating_change(player1_rating, player2_rating, player1_goals, player2_goals, 
                                       player1_absent=False, player2_absent=False):
        """Calculate enhanced rating change with constant points for goals and clean sheets"""
        # Constant point values
        GOAL_SCORED_POINTS = 2      # +2 points per goal scored
        GOAL_CONCEDED_PENALTY = -1  # -1 point per goal conceded
        CLEAN_SHEET_BONUS = 5       # +5 points for clean sheet
        
        is_draw = player1_goals == player2_goals
        
        # Get base ELO rating changes
        if is_draw:
            base_change1, base_change2 = TournamentDB.calculate_rating_change(
                player1_rating, player2_rating, is_draw=True
            )
        else:
            winner_rating = player1_rating if player1_goals > player2_goals else player2_rating
            loser_rating = player2_rating if player1_goals > player2_goals else player1_rating
            winner_change, loser_change = TournamentDB.calculate_rating_change(
                winner_rating, loser_rating, is_draw=False
            )
            if player1_goals > player2_goals:
                base_change1, base_change2 = winner_change, loser_change
            else:
                base_change1, base_change2 = loser_change, winner_change
        
        # Calculate constant points for player 1
        constant_points1 = 0
        if not player1_absent:
            constant_points1 += player1_goals * GOAL_SCORED_POINTS  # Points for goals scored
            constant_points1 += player2_goals * GOAL_CONCEDED_PENALTY  # Penalty for goals conceded
            if player2_goals == 0:  # Clean sheet bonus
                constant_points1 += CLEAN_SHEET_BONUS
        
        # Calculate constant points for player 2
        constant_points2 = 0
        if not player2_absent:
            constant_points2 += player2_goals * GOAL_SCORED_POINTS  # Points for goals scored
            constant_points2 += player1_goals * GOAL_CONCEDED_PENALTY  # Penalty for goals conceded
            if player1_goals == 0:  # Clean sheet bonus
                constant_points2 += CLEAN_SHEET_BONUS
        
        # Combine base ELO change with constant points
        total_change1 = base_change1 + constant_points1
        total_change2 = base_change2 + constant_points2
        
        return int(round(total_change1)), int(round(total_change2))
    
    @staticmethod
    def calculate_overall_rating_from_last_matches(cursor, player_id, limit=40):
        """Calculate overall rating as cumulative sum of tournament rating changes.
        
        The overall rating starts at:
        1. First tournament's starting rating (division-based) if available
        2. Player's initial_rating if set and no division tournament
        3. Default 300 if neither is available
        
        Args:
            cursor: Database cursor
            player_id: Player ID
            limit: Not used (kept for compatibility)
            
        Returns:
            Cumulative overall rating
        """
        # Get all matches for this player in chronological order
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN player1_id = %s THEN player1_rating_before
                    ELSE player2_rating_before
                END as tournament_rating_before,
                CASE 
                    WHEN player1_id = %s THEN player1_rating_after
                    ELSE player2_rating_after
                END as tournament_rating_after
            FROM player_matches
            WHERE (player1_id = %s OR player2_id = %s)
            ORDER BY played_at ASC, match_id ASC
        """, (player_id, player_id, player_id, player_id))
        
        matches = cursor.fetchall()
        
        if not matches:
            # No matches played, return default rating
            return 300
        
        # Start from the first tournament's starting rating (rating_before of first match)
        cumulative_rating = matches[0]['tournament_rating_before']
        
        # Calculate cumulative overall rating by applying all tournament rating changes
        for match in matches:
            # Calculate the tournament rating change for this match
            tournament_change = match['tournament_rating_after'] - match['tournament_rating_before']
            # Apply the change to cumulative overall rating
            cumulative_rating += tournament_change
        
        # Ensure rating stays within bounds
        cumulative_rating = max(0, min(1000, cumulative_rating))
        
        return int(round(cumulative_rating))
    
    @staticmethod
    def record_match(tournament_id, player1_id, player2_id, player1_goals, player2_goals, player1_absent=False, player2_absent=False):
        """Record a one-on-one match and update ratings, handling absences"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Handle absence scenarios
                is_null_match = player1_absent and player2_absent
                is_walkover = player1_absent or player2_absent
                
                if is_null_match:
                    # Both players absent - null match, no ratings update
                    return TournamentDB._record_null_match(
                        cursor, tournament_id, player1_id, player2_id, conn
                    )
                elif is_walkover:
                    # One player absent - walkover win for present player
                    return TournamentDB._record_walkover_match(
                        cursor, tournament_id, player1_id, player2_id, 
                        player1_absent, player2_absent, conn
                    )
                else:
                    # Normal match with both players present
                    return TournamentDB._record_normal_match(
                        cursor, tournament_id, player1_id, player2_id,
                        player1_goals, player2_goals, conn
                    )
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def _record_null_match(cursor, tournament_id, player1_id, player2_id, conn):
        """Record a null match where both players are absent"""
        # Get current ratings (for record keeping), initialize to 300 if NULL
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_rating = cursor.fetchone()['rating']
        if player1_rating is None:
            player1_rating = 300
            cursor.execute("UPDATE players SET rating = 300 WHERE id = %s", (player1_id,))
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_rating = cursor.fetchone()['rating']
        if player2_rating is None:
            player2_rating = 300
            cursor.execute("UPDATE players SET rating = 300 WHERE id = %s", (player2_id,))
        
        # Apply negative points for both absent players (penalty: -15 rating points)
        NULL_MATCH_PENALTY = 15
        new_rating1 = max(0, min(1000, player1_rating - NULL_MATCH_PENALTY))
        new_rating2 = max(0, min(1000, player2_rating - NULL_MATCH_PENALTY))
        
        # Get next match ID
        cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 as next_id FROM player_matches")
        match_id = cursor.fetchone()['next_id']
        
        # Record the null match with negative penalty applied
        cursor.execute("""
            INSERT INTO player_matches 
            (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
             winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
             player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
            VALUES (%s, %s, %s, %s, 0, 0, NULL, false, false, true, true, true, %s, %s, %s, %s)
        """, (match_id, tournament_id, player1_id, player2_id, 
              player1_rating, player2_rating, new_rating1, new_rating2))
        
        # Calculate and update overall ratings for both players
        # Null matches apply penalty so they affect cumulative rating
        new_overall_rating1 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player1_id, limit=40)
        new_overall_rating2 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player2_id, limit=40)
        
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating1, player1_id))
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating2, player2_id))
        
        conn.commit()
        return match_id
    
    @staticmethod
    def _record_walkover_match(cursor, tournament_id, player1_id, player2_id, player1_absent, player2_absent, conn):
        """Record a walkover match where one player is absent"""
        # Get tournament type and division info
        cursor.execute("SELECT tournament_type FROM tournaments WHERE id = %s", (tournament_id,))
        tournament = cursor.fetchone()
        tournament_type = tournament['tournament_type'] if tournament else 'normal'
        
        # Determine default starting ratings based on tournament type, divisions, and initial_rating
        # Get player's initial_rating if set
        cursor.execute("SELECT initial_rating FROM players WHERE id = %s", (player1_id,))
        player1_initial = cursor.fetchone()
        default_rating1 = player1_initial['initial_rating'] if player1_initial and player1_initial['initial_rating'] is not None else 300
        
        cursor.execute("SELECT initial_rating FROM players WHERE id = %s", (player2_id,))
        player2_initial = cursor.fetchone()
        default_rating2 = player2_initial['initial_rating'] if player2_initial and player2_initial['initial_rating'] is not None else 300
        
        if tournament_type == 'division':
            # Get division starting ratings for each player (overrides initial_rating)
            cursor.execute("""
                SELECT d.starting_rating FROM divisions d
                JOIN tournament_players tp ON d.id = tp.division_id
                WHERE tp.tournament_id = %s AND tp.player_id = %s
            """, (tournament_id, player1_id))
            p1_division = cursor.fetchone()
            if p1_division:
                default_rating1 = p1_division['starting_rating']
            
            cursor.execute("""
                SELECT d.starting_rating FROM divisions d
                JOIN tournament_players tp ON d.id = tp.division_id
                WHERE tp.tournament_id = %s AND tp.player_id = %s
            """, (tournament_id, player2_id))
            p2_division = cursor.fetchone()
            if p2_division:
                default_rating2 = p2_division['starting_rating']
        
        # Get tournament-specific ratings for both players
        cursor.execute("""
            SELECT tournament_rating FROM player_stats 
            WHERE player_id = %s AND tournament_id = %s
        """, (player1_id, tournament_id))
        p1_tournament_rating = cursor.fetchone()
        player1_tournament_rating = p1_tournament_rating['tournament_rating'] if p1_tournament_rating and p1_tournament_rating['tournament_rating'] is not None else None
        
        cursor.execute("""
            SELECT tournament_rating FROM player_stats 
            WHERE player_id = %s AND tournament_id = %s
        """, (player2_id, tournament_id))
        p2_tournament_rating = cursor.fetchone()
        player2_tournament_rating = p2_tournament_rating['tournament_rating'] if p2_tournament_rating and p2_tournament_rating['tournament_rating'] is not None else None
        
        # Use tournament rating if exists, otherwise use division/default starting rating
        player1_rating = default_rating1 if player1_tournament_rating is None else player1_tournament_rating
        player2_rating = default_rating2 if player2_tournament_rating is None else player2_tournament_rating
        
        # Get overall ratings
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_overall_rating = cursor.fetchone()['rating']
        if player1_overall_rating is None:
            player1_overall_rating = 300
            cursor.execute("UPDATE players SET rating = 300 WHERE id = %s", (player1_id,))
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_overall_rating = cursor.fetchone()['rating']
        if player2_overall_rating is None:
            player2_overall_rating = 300
            cursor.execute("UPDATE players SET rating = 300 WHERE id = %s", (player2_id,))
        
        # Determine winner (present player wins by walkover)
        winner_id = player2_id if player1_absent else player1_id
        loser_id = player1_id if player1_absent else player2_id
        winner_tournament_rating = player2_rating if player1_absent else player1_rating
        loser_tournament_rating = player1_rating if player1_absent else player2_rating
        
        # Calculate tournament rating changes (smaller changes for walkover)
        rating_change_winner, rating_change_loser = TournamentDB.calculate_rating_change(
            winner_tournament_rating, loser_tournament_rating, is_draw=False
        )
        
        # Reduce rating changes for walkover (75% of normal change)
        rating_change_winner = int(rating_change_winner * 0.75)
        rating_change_loser = int(rating_change_loser * 0.75)
        
        # Apply rating bounds (0-1000) for tournament ratings
        new_winner_tournament_rating = max(0, min(1000, winner_tournament_rating + rating_change_winner))
        new_loser_tournament_rating = max(0, min(1000, loser_tournament_rating + rating_change_loser))
        
        new_tournament_rating1 = new_winner_tournament_rating if winner_id == player1_id else new_loser_tournament_rating
        new_tournament_rating2 = new_winner_tournament_rating if winner_id == player2_id else new_loser_tournament_rating
        
        # Get next match ID
        cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 as next_id FROM player_matches")
        match_id = cursor.fetchone()['next_id']
        
        # Record the walkover match (store tournament-specific ratings)
        # Walkover matches: 0-0 score, update ratings, matches_played, wins/losses but NO goals
        cursor.execute("""
            INSERT INTO player_matches 
            (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
             winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
             player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
            VALUES (%s, %s, %s, %s, 0, 0, %s, false, true, false, %s, %s, %s, %s, %s, %s)
        """, (match_id, tournament_id, player1_id, player2_id,
              winner_id, player1_absent, player2_absent,
              player1_rating, player2_rating, new_tournament_rating1, new_tournament_rating2))
        
        # Update player stats: matches_played, wins/losses (but NO goals for walkover)
        cursor.execute("""
            UPDATE players SET 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_lost = matches_lost + %s
            WHERE id = %s
        """, (1 if winner_id == player1_id else 0,
              1 if winner_id != player1_id else 0,
              player1_id))
        
        cursor.execute("""
            UPDATE players SET 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_lost = matches_lost + %s
            WHERE id = %s
        """, (1 if winner_id == player2_id else 0,
              1 if winner_id != player2_id else 0,
              player2_id))
        
        # Update tournament stats with tournament-specific rating, matches_played, wins/losses (but NO goals)
        for player_id, is_winner, new_tournament_rating in [
            (player1_id, winner_id == player1_id, new_tournament_rating1),
            (player2_id, winner_id == player2_id, new_tournament_rating2)
        ]:
            cursor.execute("""
                INSERT INTO player_stats 
                (player_id, tournament_id, tournament_rating, matches_played, wins, draws, losses, goals_scored, goals_conceded)
                VALUES (%s, %s, %s, 1, %s, 0, %s, 0, 0)
                ON CONFLICT (player_id, tournament_id)
                DO UPDATE SET
                    tournament_rating = %s,
                    matches_played = player_stats.matches_played + 1,
                    wins = player_stats.wins + %s,
                    losses = player_stats.losses + %s
            """, (player_id, tournament_id, new_tournament_rating,
                  1 if is_winner else 0,
                  1 if not is_winner else 0,
                  new_tournament_rating,
                  1 if is_winner else 0,
                  1 if not is_winner else 0))
        
        # Calculate and update overall ratings for both players
        new_overall_rating1 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player1_id, limit=40)
        new_overall_rating2 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player2_id, limit=40)
        
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating1, player1_id))
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating2, player2_id))
        
        conn.commit()
        return match_id
    
    @staticmethod
    def _record_normal_match(cursor, tournament_id, player1_id, player2_id, player1_goals, player2_goals, conn):
        """Record a normal match with both players present"""
        # Get tournament type and division info
        cursor.execute("SELECT tournament_type FROM tournaments WHERE id = %s", (tournament_id,))
        tournament = cursor.fetchone()
        tournament_type = tournament['tournament_type'] if tournament else 'normal'
        
        # Determine default starting ratings based on tournament type, divisions, and initial_rating
        # Get player's initial_rating if set
        cursor.execute("SELECT initial_rating FROM players WHERE id = %s", (player1_id,))
        player1_initial = cursor.fetchone()
        default_rating1 = player1_initial['initial_rating'] if player1_initial and player1_initial['initial_rating'] is not None else 300
        
        cursor.execute("SELECT initial_rating FROM players WHERE id = %s", (player2_id,))
        player2_initial = cursor.fetchone()
        default_rating2 = player2_initial['initial_rating'] if player2_initial and player2_initial['initial_rating'] is not None else 300
        
        if tournament_type == 'division':
            # Get division starting ratings for each player
            cursor.execute("""
                SELECT d.starting_rating FROM divisions d
                JOIN tournament_players tp ON d.id = tp.division_id
                WHERE tp.tournament_id = %s AND tp.player_id = %s
            """, (tournament_id, player1_id))
            p1_division = cursor.fetchone()
            if p1_division:
                default_rating1 = p1_division['starting_rating']
            
            cursor.execute("""
                SELECT d.starting_rating FROM divisions d
                JOIN tournament_players tp ON d.id = tp.division_id
                WHERE tp.tournament_id = %s AND tp.player_id = %s
            """, (tournament_id, player2_id))
            p2_division = cursor.fetchone()
            if p2_division:
                default_rating2 = p2_division['starting_rating']
        
        # Get tournament-specific ratings for both players
        cursor.execute("""
            SELECT tournament_rating FROM player_stats 
            WHERE player_id = %s AND tournament_id = %s
        """, (player1_id, tournament_id))
        p1_tournament_rating = cursor.fetchone()
        player1_tournament_rating = p1_tournament_rating['tournament_rating'] if p1_tournament_rating and p1_tournament_rating['tournament_rating'] is not None else None
        
        cursor.execute("""
            SELECT tournament_rating FROM player_stats 
            WHERE player_id = %s AND tournament_id = %s
        """, (player2_id, tournament_id))
        p2_tournament_rating = cursor.fetchone()
        player2_tournament_rating = p2_tournament_rating['tournament_rating'] if p2_tournament_rating and p2_tournament_rating['tournament_rating'] is not None else None
        
        # Use tournament rating if exists, otherwise use division/default starting rating
        player1_rating = default_rating1 if player1_tournament_rating is None else player1_tournament_rating
        player2_rating = default_rating2 if player2_tournament_rating is None else player2_tournament_rating
        
        # Get overall ratings for display purposes
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_overall_rating = cursor.fetchone()['rating']
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_overall_rating = cursor.fetchone()['rating']
        
        # Determine winner and calculate enhanced rating changes with goals and clean sheets
        is_draw = player1_goals == player2_goals
        winner_id = None if is_draw else (player1_id if player1_goals > player2_goals else player2_id)
        
        # Use enhanced rating calculation that includes goal scoring bonuses
        rating_change1, rating_change2 = TournamentDB.calculate_enhanced_rating_change(
            player1_rating, player2_rating, player1_goals, player2_goals
        )
        
        # Apply rating bounds (0-1000) for tournament-specific ratings
        new_tournament_rating1 = max(0, min(1000, player1_rating + rating_change1))
        new_tournament_rating2 = max(0, min(1000, player2_rating + rating_change2))
        
        # Get next match ID
        cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 as next_id FROM player_matches")
        match_id = cursor.fetchone()['next_id']
        
        # Record the match (store tournament-specific ratings)
        cursor.execute("""
            INSERT INTO player_matches 
            (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
             winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
             player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false, false, false, false, %s, %s, %s, %s)
        """, (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
              winner_id, is_draw, player1_rating, player2_rating, new_tournament_rating1, new_tournament_rating2))
        
        # Calculate Golden Glove points for each player
        glove_points1 = TournamentDB.calculate_golden_glove_points(
            player1_goals, player2_goals, winner_id == player1_id, is_draw
        )
        glove_points2 = TournamentDB.calculate_golden_glove_points(
            player2_goals, player1_goals, winner_id == player2_id, is_draw
        )
        
        # Update player stats (cumulative across all tournaments) - without rating first
        cursor.execute("""
            UPDATE players SET 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_drawn = matches_drawn + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s,
                clean_sheets = clean_sheets + %s,
                golden_glove_points = golden_glove_points + %s
            WHERE id = %s
        """, (1 if winner_id == player1_id else 0,
              1 if is_draw else 0,
              1 if winner_id == player2_id else 0,
              player1_goals, player2_goals,
              1 if player2_goals == 0 else 0,
              glove_points1,
              player1_id))
        
        cursor.execute("""
            UPDATE players SET 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_drawn = matches_drawn + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s,
                clean_sheets = clean_sheets + %s,
                golden_glove_points = golden_glove_points + %s
            WHERE id = %s
        """, (1 if winner_id == player2_id else 0,
              1 if is_draw else 0,
              1 if winner_id == player1_id else 0,
              player2_goals, player1_goals,
              1 if player1_goals == 0 else 0,
              glove_points2,
              player2_id))
        
        # Update tournament stats with tournament-specific rating
        for player_id, goals_scored, goals_conceded, is_winner, glove_points, new_tournament_rating in [
            (player1_id, player1_goals, player2_goals, winner_id == player1_id, glove_points1, new_tournament_rating1),
            (player2_id, player2_goals, player1_goals, winner_id == player2_id, glove_points2, new_tournament_rating2)
        ]:
            cursor.execute("""
                INSERT INTO player_stats 
                (player_id, tournament_id, tournament_rating, matches_played, wins, draws, losses, goals_scored, goals_conceded, clean_sheets, golden_glove_points)
                VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (player_id, tournament_id)
                DO UPDATE SET
                    tournament_rating = %s,
                    matches_played = player_stats.matches_played + 1,
                    wins = player_stats.wins + %s,
                    draws = player_stats.draws + %s,
                    losses = player_stats.losses + %s,
                    goals_scored = player_stats.goals_scored + %s,
                    goals_conceded = player_stats.goals_conceded + %s,
                    clean_sheets = player_stats.clean_sheets + %s,
                    golden_glove_points = player_stats.golden_glove_points + %s
            """, (player_id, tournament_id, new_tournament_rating,
                  1 if is_winner else 0,
                  1 if is_draw else 0,
                  1 if not is_winner and not is_draw else 0,
                  goals_scored, goals_conceded,
                  1 if goals_conceded == 0 else 0,
                  glove_points,
                  new_tournament_rating,
                  1 if is_winner else 0,
                  1 if is_draw else 0,
                  1 if not is_winner and not is_draw else 0,
                  goals_scored, goals_conceded,
                  1 if goals_conceded == 0 else 0,
                  glove_points))
        
        # Calculate and update overall ratings for both players
        new_overall_rating1 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player1_id, limit=40)
        new_overall_rating2 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player2_id, limit=40)
        
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating1, player1_id))
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating2, player2_id))
        
        conn.commit()
        return match_id
    
    @staticmethod
    def get_player_tournament_stats(tournament_id):
        """Get tournament-specific player statistics with division information"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.name, 
                        p.photo_url, 
                        ps.*, 
                        p.rating as overall_rating,
                        tp.division_id,
                        d.name as division_name,
                        d.starting_rating as division_starting_rating
                    FROM player_stats ps
                    JOIN players p ON ps.player_id = p.id
                    LEFT JOIN tournament_players tp ON ps.player_id = tp.player_id AND ps.tournament_id = tp.tournament_id
                    LEFT JOIN divisions d ON tp.division_id = d.id
                    WHERE ps.tournament_id = %s
                    ORDER BY ps.tournament_rating DESC NULLS LAST, ps.wins DESC, ps.goals_scored DESC
                """, (tournament_id,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_overall_player_stats():
        """Get overall player statistics across all tournaments"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM players
                    WHERE rating IS NOT NULL
                    ORDER BY rating DESC, matches_won DESC, goals_scored DESC
                """)
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_player_tournament_breakdown(player_id):
        """Get detailed tournament-wise breakdown for a player including rating changes"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get player overall info
                cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
                player = cursor.fetchone()
                
                if not player:
                    return None
                
                # Get tournament-specific stats with match details
                cursor.execute("""
                    SELECT 
                        t.id as tournament_id,
                        t.name as tournament_name,
                        t.status as tournament_status,
                        ps.tournament_rating,
                        ps.matches_played as tournament_matches,
                        ps.wins as tournament_wins,
                        ps.draws as tournament_draws,
                        ps.losses as tournament_losses,
                        ps.goals_scored as tournament_goals_for,
                        ps.goals_conceded as tournament_goals_against,
                        ps.clean_sheets as tournament_clean_sheets,
                        ps.golden_glove_points as tournament_glove_points
                    FROM player_stats ps
                    JOIN tournaments t ON ps.tournament_id = t.id
                    WHERE ps.player_id = %s
                    ORDER BY t.created_at DESC
                """, (player_id,))
                
                tournaments = cursor.fetchall()
                
                # Calculate rating contributions
                tournament_breakdown = []
                for tournament in tournaments:
                    # Get first and last match ratings in this tournament
                    cursor.execute("""
                        SELECT 
                            MIN(played_at) as first_match,
                            MAX(played_at) as last_match
                        FROM player_matches
                        WHERE tournament_id = %s 
                        AND (player1_id = %s OR player2_id = %s)
                    """, (tournament['tournament_id'], player_id, player_id))
                    
                    match_dates = cursor.fetchone()
                    
                    # Get all matches in this tournament with rating changes
                    cursor.execute("""
                        SELECT 
                            pm.match_id,
                            pm.played_at,
                            CASE 
                                WHEN pm.player1_id = %s THEN p2.name 
                                ELSE p1.name 
                            END as opponent_name,
                            CASE 
                                WHEN pm.player1_id = %s THEN pm.player1_goals
                                ELSE pm.player2_goals
                            END as goals_for,
                            CASE 
                                WHEN pm.player1_id = %s THEN pm.player2_goals
                                ELSE pm.player1_goals
                            END as goals_against,
                            CASE 
                                WHEN pm.player1_id = %s THEN pm.player1_rating_before
                                ELSE pm.player2_rating_before
                            END as tournament_rating_before,
                            CASE 
                                WHEN pm.player1_id = %s THEN pm.player1_rating_after
                                ELSE pm.player2_rating_after
                            END as tournament_rating_after,
                            pm.winner_id,
                            pm.is_draw,
                            pm.is_walkover,
                            pm.is_null_match,
                            CASE 
                                WHEN pm.player1_id = %s THEN pm.player1_absent
                                ELSE pm.player2_absent
                            END as player_absent,
                            CASE 
                                WHEN pm.player1_id = %s THEN pm.player2_absent
                                ELSE pm.player1_absent
                            END as opponent_absent
                        FROM player_matches pm
                        JOIN players p1 ON pm.player1_id = p1.id
                        JOIN players p2 ON pm.player2_id = p2.id
                        WHERE pm.tournament_id = %s 
                        AND (pm.player1_id = %s OR pm.player2_id = %s)
                        ORDER BY pm.played_at ASC, pm.match_id ASC
                    """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, 
                          tournament['tournament_id'], player_id, player_id))
                    
                    tournament_matches = cursor.fetchall()
                    
                    # Get rating at start of tournament (first match rating_before)
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN player1_id = %s THEN player1_rating_before
                                ELSE player2_rating_before
                            END as rating_before
                        FROM player_matches
                        WHERE tournament_id = %s 
                        AND (player1_id = %s OR player2_id = %s)
                        ORDER BY played_at ASC, match_id ASC
                        LIMIT 1
                    """, (player_id, tournament['tournament_id'], player_id, player_id))
                    
                    start_rating_result = cursor.fetchone()
                    start_rating = start_rating_result['rating_before'] if start_rating_result else 300
                    
                    # Calculate rating change in this tournament
                    current_rating = tournament['tournament_rating'] if tournament['tournament_rating'] else start_rating
                    rating_change = current_rating - start_rating
                    
                    # Process each match to get overall rating progression
                    matches_with_overall = []
                    for match in tournament_matches:
                        # Get overall rating at this point (from players table)
                        # We need to get this from a separate overall rating history
                        tournament_rating_change = match['tournament_rating_after'] - match['tournament_rating_before']
                        
                        # Determine result
                        if match['is_null_match']:
                            result = 'NULL'
                        elif match['is_draw']:
                            result = 'DRAW'
                        elif match['winner_id'] == player_id:
                            result = 'WIN'
                        else:
                            result = 'LOSS'
                        
                        matches_with_overall.append({
                            'match_id': match['match_id'],
                            'played_at': match['played_at'],
                            'opponent': match['opponent_name'],
                            'score': f"{match['goals_for']}-{match['goals_against']}",
                            'goals_for': match['goals_for'],
                            'goals_against': match['goals_against'],
                            'result': result,
                            'is_walkover': match['is_walkover'],
                            'player_absent': match['player_absent'],
                            'opponent_absent': match['opponent_absent'],
                            'tournament_rating_before': match['tournament_rating_before'],
                            'tournament_rating_after': match['tournament_rating_after'],
                            'tournament_rating_change': tournament_rating_change
                        })
                    
                    tournament_breakdown.append({
                        'tournament_id': tournament['tournament_id'],
                        'tournament_name': tournament['tournament_name'],
                        'tournament_status': tournament['tournament_status'],
                        'tournament_rating': current_rating,
                        'start_rating': start_rating,
                        'rating_change': rating_change,
                        'matches': tournament['tournament_matches'],
                        'wins': tournament['tournament_wins'],
                        'draws': tournament['tournament_draws'],
                        'losses': tournament['tournament_losses'],
                        'goals_for': tournament['tournament_goals_for'],
                        'goals_against': tournament['tournament_goals_against'],
                        'clean_sheets': tournament['tournament_clean_sheets'],
                        'glove_points': tournament['tournament_glove_points'],
                        'first_match': match_dates['first_match'] if match_dates else None,
                        'last_match': match_dates['last_match'] if match_dates else None,
                        'match_history': matches_with_overall
                    })
                
                # Get all matches for overall rating progression
                cursor.execute("""
                    SELECT 
                        pm.match_id,
                        pm.tournament_id,
                        pm.played_at,
                        t.name as tournament_name,
                        CASE 
                            WHEN pm.player1_id = %s THEN p2.name 
                            ELSE p1.name 
                        END as opponent_name,
                        CASE 
                            WHEN pm.player1_id = %s THEN pm.player1_goals
                            ELSE pm.player2_goals
                        END as goals_for,
                        CASE 
                            WHEN pm.player1_id = %s THEN pm.player2_goals
                            ELSE pm.player1_goals
                        END as goals_against,
                        CASE 
                            WHEN pm.player1_id = %s THEN pm.player1_rating_before
                            ELSE pm.player2_rating_before
                        END as tournament_rating_before,
                        CASE 
                            WHEN pm.player1_id = %s THEN pm.player1_rating_after
                            ELSE pm.player2_rating_after
                        END as tournament_rating_after,
                        pm.winner_id,
                        pm.is_draw,
                        pm.is_null_match
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    JOIN players p2 ON pm.player2_id = p2.id
                    JOIN tournaments t ON pm.tournament_id = t.id
                    WHERE pm.player1_id = %s OR pm.player2_id = %s
                    ORDER BY pm.played_at ASC, pm.match_id ASC
                """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id))
                
                overall_matches = cursor.fetchall()
                
                # Calculate overall rating progression using cumulative Elo
                # Overall rating starts at 300 and applies all rating changes sequentially
                overall_rating_history = []
                cumulative_overall_rating = 300  # Start from 300
                
                for match in overall_matches:
                    # Calculate rating change for this match (from tournament rating changes)
                    tournament_change = match['tournament_rating_after'] - match['tournament_rating_before']
                    
                    # For overall rating, we apply the change cumulatively
                    rating_before_match = cumulative_overall_rating
                    cumulative_overall_rating += tournament_change  # Apply the change to cumulative rating
                    
                    # Determine result
                    if match['is_null_match']:
                        result = 'NULL'
                    elif match['is_draw']:
                        result = 'DRAW'
                    elif match['winner_id'] == player_id:
                        result = 'WIN'
                    else:
                        result = 'LOSS'
                    
                    overall_rating_history.append({
                        'match_id': match['match_id'],
                        'tournament_name': match['tournament_name'],
                        'opponent': match['opponent_name'],
                        'score': f"{match['goals_for']}-{match['goals_against']}",
                        'result': result,
                        'rating_before': rating_before_match,
                        'rating_after': cumulative_overall_rating,
                        'rating_change': tournament_change,
                        'played_at': match['played_at']
                    })
                
                return {
                    'player': player,
                    'tournaments': tournament_breakdown,
                    'total_tournaments': len(tournament_breakdown),
                    'overall_rating': player['rating'],
                    'overall_matches': player['matches_played'],
                    'overall_rating_history': overall_rating_history
                }
        finally:
            conn.close()
    
    @staticmethod
    def recalculate_all_ratings():
        """Recalculate all player ratings and stats by replaying ALL tournaments.
        Uses tournament-specific ratings for each tournament, then calculates cumulative overall ratings.
        Optimized to prevent hanging on large datasets.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                print("Step 1: Resetting player stats...")
                # 1) Reset all players to initial state
                cursor.execute("""
                    UPDATE players SET
                        rating = 300,
                        matches_played = 0,
                        matches_won = 0,
                        matches_drawn = 0,
                        matches_lost = 0,
                        goals_scored = 0,
                        goals_conceded = 0,
                        clean_sheets = 0,
                        golden_glove_points = 0
                """)
                conn.commit()
                print("  ✓ Players reset")
                
                print("\nStep 2: Clearing tournament stats...")
                # 2) Clear tournament-specific aggregates
                cursor.execute("DELETE FROM player_stats")
                conn.commit()
                print("  ✓ Tournament stats cleared")
                
                print("\nStep 3: Fetching tournaments...")
                # 3) Get all tournaments in chronological order
                cursor.execute("""
                    SELECT id, tournament_type FROM tournaments
                    ORDER BY created_at ASC, id ASC
                """)
                tournaments = cursor.fetchall()
                print(f"  ✓ Found {len(tournaments)} tournaments")
                
                # Pre-fetch division data to avoid repeated queries
                cursor.execute("""
                    SELECT id, starting_rating FROM divisions
                """)
                divisions_data = {row['id']: row['starting_rating'] for row in cursor.fetchall()}
                
                print("\nStep 4: Processing tournaments...")
                # 4) Process each tournament separately
                for idx, tournament in enumerate(tournaments):
                    t_id = tournament['id']
                    is_division = tournament.get('tournament_type') == 'division'
                    print(f"\nTournament {idx+1}/{len(tournaments)} (ID: {t_id})...")
                    
                    # Get all players in this tournament with their divisions
                    cursor.execute("""
                        SELECT player_id, division_id FROM tournament_players
                        WHERE tournament_id = %s
                    """, (t_id,))
                    tournament_players = cursor.fetchall()
                    
                    # Initialize tournament ratings for each player (using pre-fetched division data)
                    tournament_ratings = {}
                    for tp in tournament_players:
                        player_id = tp['player_id']
                        if is_division and tp['division_id'] and tp['division_id'] in divisions_data:
                            tournament_ratings[player_id] = divisions_data[tp['division_id']]
                        else:
                            tournament_ratings[player_id] = 300
                    
                    # Get all matches for this tournament
                    cursor.execute("""
                        SELECT * FROM player_matches
                        WHERE tournament_id = %s
                        ORDER BY played_at ASC NULLS LAST, match_id ASC
                    """, (t_id,))
                    matches = cursor.fetchall()
                    print(f"  - {len(matches)} matches to process")
                    
                    # Prepare batch data structures
                    match_updates = []
                    player_stats_cache = {}
                    
                    # Process each match in this tournament
                    for match_idx, m in enumerate(matches):
                        # Show progress every 100 matches
                        if match_idx > 0 and match_idx % 100 == 0:
                            print(f"    Progress: {match_idx}/{len(matches)} matches...")
                        
                        p1 = m['player1_id']
                        p2 = m['player2_id']
                        g1 = m['player1_goals']
                        g2 = m['player2_goals']
                        is_walkover = m.get('is_walkover', False)
                        is_null = m.get('is_null_match', False)
                        p1_absent = m.get('player1_absent', False)
                        p2_absent = m.get('player2_absent', False)
                        winner_id = m.get('winner_id')
                        is_draw = m.get('is_draw', False)
                        
                        # Get tournament ratings before this match
                        t_r1_before = tournament_ratings.get(p1, 300)
                        t_r2_before = tournament_ratings.get(p2, 300)
                        
                        # Calculate rating changes based on match type
                        if is_null:
                            NULL_PENALTY = 15
                            t_r1_after = max(0, min(1000, t_r1_before - NULL_PENALTY))
                            t_r2_after = max(0, min(1000, t_r2_before - NULL_PENALTY))
                        elif is_walkover:
                            if winner_id == p1:
                                change_w, change_l = TournamentDB.calculate_rating_change(t_r1_before, t_r2_before, is_draw=False)
                                t_change1 = int(change_w * 0.75)
                                t_change2 = int(change_l * 0.75)
                            else:
                                change_w, change_l = TournamentDB.calculate_rating_change(t_r2_before, t_r1_before, is_draw=False)
                                t_change2 = int(change_w * 0.75)
                                t_change1 = int(change_l * 0.75)
                            t_r1_after = max(0, min(1000, t_r1_before + t_change1))
                            t_r2_after = max(0, min(1000, t_r2_before + t_change2))
                        else:
                            t_change1, t_change2 = TournamentDB.calculate_enhanced_rating_change(
                                t_r1_before, t_r2_before, g1, g2, p1_absent, p2_absent
                            )
                            t_r1_after = max(0, min(1000, t_r1_before + t_change1))
                            t_r2_after = max(0, min(1000, t_r2_before + t_change2))
                        
                        # Update tournament ratings
                        tournament_ratings[p1] = t_r1_after
                        tournament_ratings[p2] = t_r2_after
                        
                        # Store match update for batch processing
                        match_updates.append((t_r1_before, t_r2_before, t_r1_after, t_r2_after, m['id']))
                        
                        # Update player stats cache (only if not null match)
                        if not is_null:
                            for pid, t_rating_after, won, drawn, lost, gf, ga in [
                                (p1, t_r1_after, 1 if winner_id == p1 else 0, 1 if is_draw else 0, 1 if winner_id == p2 else 0, g1, g2),
                                (p2, t_r2_after, 1 if winner_id == p2 else 0, 1 if is_draw else 0, 1 if winner_id == p1 else 0, g2, g1)
                            ]:
                                # Calculate golden glove points
                                glove_points = 0
                                if not is_walkover:
                                    glove_points = TournamentDB.calculate_golden_glove_points(
                                        gf, ga, winner_id == pid, is_draw
                                    )
                                
                                # Accumulate stats in cache
                                if pid not in player_stats_cache:
                                    player_stats_cache[pid] = {
                                        'rating': t_rating_after,
                                        'matches': 0, 'wins': 0, 'draws': 0, 'losses': 0,
                                        'gf': 0, 'ga': 0, 'cs': 0, 'glove': 0
                                    }
                                
                                player_stats_cache[pid]['rating'] = t_rating_after
                                player_stats_cache[pid]['matches'] += 1
                                player_stats_cache[pid]['wins'] += won
                                player_stats_cache[pid]['draws'] += drawn
                                player_stats_cache[pid]['losses'] += lost
                                player_stats_cache[pid]['gf'] += gf
                                player_stats_cache[pid]['ga'] += ga
                                player_stats_cache[pid]['cs'] += (1 if ga == 0 else 0)
                                player_stats_cache[pid]['glove'] += glove_points
                        
                        # Commit every 200 matches to prevent timeout
                        if (match_idx + 1) % 200 == 0:
                            # Execute batch updates for matches
                            cursor.executemany("""
                                UPDATE player_matches SET
                                    player1_rating_before = %s,
                                    player2_rating_before = %s,
                                    player1_rating_after = %s,
                                    player2_rating_after = %s
                                WHERE id = %s
                            """, match_updates)
                            match_updates = []
                            conn.commit()
                    
                    # Final batch update for remaining matches
                    if match_updates:
                        print(f"    Updating match ratings...")
                        cursor.executemany("""
                            UPDATE player_matches SET
                                player1_rating_before = %s,
                                player2_rating_before = %s,
                                player1_rating_after = %s,
                                player2_rating_after = %s
                            WHERE id = %s
                        """, match_updates)
                    
                    # Update player_stats from cache
                    print(f"    Updating player stats for {len(player_stats_cache)} players...")
                    for pid, stats in player_stats_cache.items():
                        cursor.execute("""
                            INSERT INTO player_stats
                                (player_id, tournament_id, tournament_rating, matches_played, wins, draws, losses, 
                                 goals_scored, goals_conceded, clean_sheets, golden_glove_points)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (player_id, tournament_id)
                            DO UPDATE SET
                                tournament_rating = %s,
                                matches_played = %s,
                                wins = %s,
                                draws = %s,
                                losses = %s,
                                goals_scored = %s,
                                goals_conceded = %s,
                                clean_sheets = %s,
                                golden_glove_points = %s
                        """, (pid, t_id, stats['rating'], stats['matches'], stats['wins'], stats['draws'], stats['losses'],
                              stats['gf'], stats['ga'], stats['cs'], stats['glove'],
                              stats['rating'], stats['matches'], stats['wins'], stats['draws'], stats['losses'],
                              stats['gf'], stats['ga'], stats['cs'], stats['glove']))
                    
                    # Commit after each tournament to prevent timeout
                    conn.commit()
                    print(f"  ✓ Tournament {idx+1} complete")
                
                # After processing all tournaments, calculate cumulative overall ratings and stats for each player
                print("\nStep 5: Calculating overall player ratings and stats...")
                cursor.execute("SELECT id FROM players WHERE id IN (SELECT DISTINCT player1_id FROM player_matches UNION SELECT DISTINCT player2_id FROM player_matches)")
                all_players = cursor.fetchall()
                total_players = len(all_players)
                print(f"  - {total_players} players with matches")
                
                # Process in batches and commit periodically
                batch_size = 50
                for batch_start in range(0, total_players, batch_size):
                    batch_end = min(batch_start + batch_size, total_players)
                    print(f"  - Processing players {batch_start+1}-{batch_end}/{total_players}...")
                    
                    for player_idx in range(batch_start, batch_end):
                        player = all_players[player_idx]
                        player_id = player['id']
                        
                        # Get all matches for this player in chronological order
                        cursor.execute("""
                            SELECT * FROM player_matches
                            WHERE player1_id = %s OR player2_id = %s
                            ORDER BY played_at ASC NULLS LAST, match_id ASC
                        """, (player_id, player_id))
                        player_matches = cursor.fetchall()
                        
                        if not player_matches:
                            continue
                        
                        # Initialize counters
                        first_match = player_matches[0]
                        if first_match['player1_id'] == player_id:
                            cumulative_rating = first_match['player1_rating_before']
                        else:
                            cumulative_rating = first_match['player2_rating_before']
                        
                        matches_played = 0
                        matches_won = 0
                        matches_drawn = 0
                        matches_lost = 0
                        goals_scored = 0
                        goals_conceded = 0
                        clean_sheets = 0
                        golden_glove_points = 0
                        
                        # Aggregate all stats
                        for pm in player_matches:
                            is_p1 = (pm['player1_id'] == player_id)
                            is_null = pm.get('is_null_match', False)
                            is_draw = pm.get('is_draw', False)
                            is_walkover = pm.get('is_walkover', False)
                            winner_id = pm.get('winner_id')
                            
                            # Calculate rating change
                            if is_p1:
                                rating_change = pm['player1_rating_after'] - pm['player1_rating_before']
                                gf = pm['player1_goals']
                                ga = pm['player2_goals']
                            else:
                                rating_change = pm['player2_rating_after'] - pm['player2_rating_before']
                                gf = pm['player2_goals']
                                ga = pm['player1_goals']
                            
                            cumulative_rating += rating_change
                            
                            # Aggregate stats (only if not null match)
                            if not is_null:
                                matches_played += 1
                                if winner_id == player_id:
                                    matches_won += 1
                                elif is_draw:
                                    matches_drawn += 1
                                else:
                                    matches_lost += 1
                                
                                goals_scored += gf
                                goals_conceded += ga
                                if ga == 0:
                                    clean_sheets += 1
                                
                                if not is_walkover:
                                    golden_glove_points += TournamentDB.calculate_golden_glove_points(
                                        gf, ga, winner_id == player_id, is_draw
                                    )
                        
                        # Single update with all calculated values
                        cursor.execute("""
                            UPDATE players SET
                                rating = %s,
                                matches_played = %s,
                                matches_won = %s,
                                matches_drawn = %s,
                                matches_lost = %s,
                                goals_scored = %s,
                                goals_conceded = %s,
                                clean_sheets = %s,
                                golden_glove_points = %s
                            WHERE id = %s
                        """, (cumulative_rating, matches_played, matches_won, matches_drawn, matches_lost,
                              goals_scored, goals_conceded, clean_sheets, golden_glove_points, player_id))
                    
                    # Commit after each batch
                    conn.commit()
                
                print("  ✓ Overall ratings calculated")
                print("\n" + "=" * 80)
                print("✓ RECALCULATION COMPLETE!")
                print("=" * 80)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def recalculate_tournament_ratings(tournament_id):
        """Recalculate ratings and stats for a specific tournament only.
        This processes all matches in the tournament chronologically and recalculates:
        - Tournament-specific ratings (player_stats.tournament_rating)
        - Tournament-specific stats (player_stats table)
        - Overall player ratings and stats (players table) by applying cumulative changes
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get tournament info to check if it's a division tournament
                cursor.execute("SELECT * FROM tournaments WHERE id = %s", (tournament_id,))
                tournament = cursor.fetchone()
                if not tournament:
                    raise ValueError(f"Tournament with ID {tournament_id} not found")
                
                is_division_tournament = tournament.get('tournament_type') == 'division'
                
                # Step 1: Get all players in this tournament
                cursor.execute("""
                    SELECT DISTINCT player_id, division_id
                    FROM tournament_players
                    WHERE tournament_id = %s
                """, (tournament_id,))
                tournament_players = cursor.fetchall()
                
                if not tournament_players:
                    return {'success': True, 'message': 'No players in this tournament', 'matches_processed': 0}
                
                # Step 2: Clear tournament-specific stats for these players
                cursor.execute("""
                    DELETE FROM player_stats
                    WHERE tournament_id = %s
                """, (tournament_id,))
                
                # Step 3: Initialize tournament ratings based on division (for division tournaments)
                player_initial_ratings = {}
                if is_division_tournament:
                    for tp in tournament_players:
                        player_id = tp['player_id']
                        division_id = tp['division_id']
                        if division_id:
                            cursor.execute("SELECT starting_rating FROM divisions WHERE id = %s", (division_id,))
                            division = cursor.fetchone()
                            player_initial_ratings[player_id] = division['starting_rating'] if division else 300
                        else:
                            player_initial_ratings[player_id] = 300
                else:
                    # For non-division tournaments, start at 300
                    for tp in tournament_players:
                        player_initial_ratings[tp['player_id']] = 300
                
                # Step 4: Track current tournament ratings for each player
                current_tournament_ratings = player_initial_ratings.copy()
                
                # Step 5: Get all matches for this tournament in chronological order
                cursor.execute("""
                    SELECT * FROM player_matches
                    WHERE tournament_id = %s
                    ORDER BY played_at ASC NULLS LAST, match_id ASC
                """, (tournament_id,))
                matches = cursor.fetchall()
                
                matches_processed = 0
                
                # Step 6: Process each match
                for match in matches:
                    p1_id = match['player1_id']
                    p2_id = match['player2_id']
                    g1 = match['player1_goals']
                    g2 = match['player2_goals']
                    is_walkover = match.get('is_walkover', False)
                    is_null = match.get('is_null_match', False)
                    p1_absent = match.get('player1_absent', False)
                    p2_absent = match.get('player2_absent', False)
                    is_draw = match.get('is_draw', False)
                    winner_id = match.get('winner_id')
                    
                    # Get tournament ratings before this match
                    p1_t_rating_before = current_tournament_ratings.get(p1_id, 300)
                    p2_t_rating_before = current_tournament_ratings.get(p2_id, 300)
                    
                    # Calculate rating changes
                    if is_null:
                        # Null match: apply penalty
                        NULL_PENALTY = 15
                        p1_t_rating_after = max(0, min(1000, p1_t_rating_before - NULL_PENALTY))
                        p2_t_rating_after = max(0, min(1000, p2_t_rating_before - NULL_PENALTY))
                    elif is_walkover:
                        # Walkover: use basic ELO with 75% factor
                        if winner_id == p1_id:
                            t_change_w, t_change_l = TournamentDB.calculate_rating_change(p1_t_rating_before, p2_t_rating_before, is_draw=False)
                            t_change1 = int(t_change_w * 0.75)
                            t_change2 = int(t_change_l * 0.75)
                        else:
                            t_change_w, t_change_l = TournamentDB.calculate_rating_change(p2_t_rating_before, p1_t_rating_before, is_draw=False)
                            t_change2 = int(t_change_w * 0.75)
                            t_change1 = int(t_change_l * 0.75)
                        p1_t_rating_after = max(0, min(1000, p1_t_rating_before + t_change1))
                        p2_t_rating_after = max(0, min(1000, p2_t_rating_before + t_change2))
                    else:
                        # Normal match: use enhanced rating calculation
                        t_change1, t_change2 = TournamentDB.calculate_enhanced_rating_change(
                            p1_t_rating_before, p2_t_rating_before, g1, g2, p1_absent, p2_absent
                        )
                        p1_t_rating_after = max(0, min(1000, p1_t_rating_before + t_change1))
                        p2_t_rating_after = max(0, min(1000, p2_t_rating_before + t_change2))
                    
                    # Update current tournament ratings
                    current_tournament_ratings[p1_id] = p1_t_rating_after
                    current_tournament_ratings[p2_id] = p2_t_rating_after
                    
                    # Update match records with new ratings
                    cursor.execute("""
                        UPDATE player_matches SET
                            player1_rating_before = %s,
                            player2_rating_before = %s,
                            player1_rating_after = %s,
                            player2_rating_after = %s
                        WHERE id = %s
                    """, (p1_t_rating_before, p2_t_rating_before, p1_t_rating_after, p2_t_rating_after, match['id']))
                    
                    # Update tournament-specific stats (only if not a null match)
                    if not is_null:
                        for pid, t_rating_after, won, drawn, lost, gf, ga in [
                            (p1_id, p1_t_rating_after, 1 if winner_id == p1_id else 0, 1 if is_draw else 0, 1 if winner_id == p2_id else 0, g1, g2),
                            (p2_id, p2_t_rating_after, 1 if winner_id == p2_id else 0, 1 if is_draw else 0, 1 if winner_id == p1_id else 0, g2, g1)
                        ]:
                            # Calculate golden glove points
                            glove_points = 0
                            if not is_walkover:
                                glove_points = TournamentDB.calculate_golden_glove_points(
                                    gf, ga, winner_id == pid, is_draw
                                )
                            
                            cursor.execute("""
                                INSERT INTO player_stats
                                    (player_id, tournament_id, tournament_rating, matches_played, wins, draws, losses, 
                                     goals_scored, goals_conceded, clean_sheets, golden_glove_points)
                                VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (player_id, tournament_id)
                                DO UPDATE SET
                                    tournament_rating = %s,
                                    matches_played = player_stats.matches_played + 1,
                                    wins = player_stats.wins + %s,
                                    draws = player_stats.draws + %s,
                                    losses = player_stats.losses + %s,
                                    goals_scored = player_stats.goals_scored + %s,
                                    goals_conceded = player_stats.goals_conceded + %s,
                                    clean_sheets = player_stats.clean_sheets + %s,
                                    golden_glove_points = player_stats.golden_glove_points + %s
                            """, (pid, tournament_id, t_rating_after, won, drawn, lost, gf, ga, 1 if ga == 0 else 0, glove_points,
                                  t_rating_after, won, drawn, lost, gf, ga, 1 if ga == 0 else 0, glove_points))
                    
                    matches_processed += 1
                
                # Step 7: Recalculate overall player ratings from ALL tournaments
                # We need to recalculate overall ratings for affected players by summing up all their tournament changes
                affected_player_ids = [tp['player_id'] for tp in tournament_players]
                
                for player_id in affected_player_ids:
                    # Reset player overall stats
                    cursor.execute("""
                        UPDATE players SET
                            rating = 300,
                            matches_played = 0,
                            matches_won = 0,
                            matches_drawn = 0,
                            matches_lost = 0,
                            goals_scored = 0,
                            goals_conceded = 0,
                            clean_sheets = 0,
                            golden_glove_points = 0
                        WHERE id = %s
                    """, (player_id,))
                    
                    # Get all matches for this player across all tournaments in chronological order
                    cursor.execute("""
                        SELECT * FROM player_matches
                        WHERE player1_id = %s OR player2_id = %s
                        ORDER BY played_at ASC NULLS LAST, match_id ASC
                    """, (player_id, player_id))
                    all_player_matches = cursor.fetchall()
                    
                    # Determine starting rating from first match (will be division rating if first tournament is division)
                    if all_player_matches:
                        first_match = all_player_matches[0]
                        if first_match['player1_id'] == player_id:
                            cumulative_overall_rating = first_match['player1_rating_before']  # Use initial tournament rating
                        else:
                            cumulative_overall_rating = first_match['player2_rating_before']  # Use initial tournament rating
                    else:
                        cumulative_overall_rating = 300  # Default if no matches
                    
                    for pm in all_player_matches:
                        is_p1 = (pm['player1_id'] == player_id)
                        is_null = pm.get('is_null_match', False)
                        is_draw = pm.get('is_draw', False)
                        winner_id = pm.get('winner_id')
                        
                        # Calculate rating change from tournament ratings (cumulative)
                        if is_p1:
                            rating_change = pm['player1_rating_after'] - pm['player1_rating_before']
                            gf = pm['player1_goals']
                            ga = pm['player2_goals']
                        else:
                            rating_change = pm['player2_rating_after'] - pm['player2_rating_before']
                            gf = pm['player2_goals']
                            ga = pm['player1_goals']
                        
                        # Apply rating change cumulatively
                        cumulative_overall_rating += rating_change
                        
                        # Update overall stats (only if not null match)
                        if not is_null:
                            won = 1 if winner_id == player_id else 0
                            drawn = 1 if is_draw else 0
                            lost = 1 if (not is_draw and winner_id != player_id) else 0
                            
                            glove_points = 0
                            if not pm.get('is_walkover', False):
                                glove_points = TournamentDB.calculate_golden_glove_points(
                                    gf, ga, winner_id == player_id, is_draw
                                )
                            
                            cursor.execute("""
                                UPDATE players SET
                                    rating = %s,
                                    matches_played = matches_played + 1,
                                    matches_won = matches_won + %s,
                                    matches_drawn = matches_drawn + %s,
                                    matches_lost = matches_lost + %s,
                                    goals_scored = goals_scored + %s,
                                    goals_conceded = goals_conceded + %s,
                                    clean_sheets = clean_sheets + %s,
                                    golden_glove_points = golden_glove_points + %s
                                WHERE id = %s
                            """, (cumulative_overall_rating, won, drawn, lost, gf, ga, 1 if ga == 0 else 0, glove_points, player_id))
                    
                    # Final update to ensure rating is set correctly
                    cursor.execute("""
                        UPDATE players SET rating = %s WHERE id = %s
                    """, (cumulative_overall_rating, player_id))
                
                conn.commit()
                return {
                    'success': True,
                    'message': f'Successfully recalculated stats for {len(tournament_players)} players across {matches_processed} matches',
                    'players_updated': len(tournament_players),
                    'matches_processed': matches_processed
                }
                
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def remove_player_from_tournament(tournament_id, player_id):
        """Remove a player from a tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM tournament_players WHERE tournament_id = %s AND player_id = %s",
                    (tournament_id, player_id)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def remove_all_players_from_tournament(tournament_id):
        """Remove all players from a tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM tournament_players WHERE tournament_id = %s",
                    (tournament_id,)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def record_guest_match(tournament_id, clan_player_id, guest_name, clan_goals, guest_goals, clan_absent=False, guest_absent=False):
        """Record a match between a clan member and guest player.
        Creates entries in BOTH guest_matches and player_matches tables.
        Only updates clan member stats (guest player is not in the system).
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get clan player details
                clan_player = TournamentDB.get_player_by_id(clan_player_id)
                if not clan_player:
                    raise ValueError("Clan player not found")
                
                # Get next match ID - use the shared match_id from player_matches
                cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 AS next_id FROM player_matches")
                next_match_id = cursor.fetchone()['next_id']
                
                # Get tournament type and division info
                cursor.execute("SELECT tournament_type FROM tournaments WHERE id = %s", (tournament_id,))
                tournament = cursor.fetchone()
                tournament_type = tournament['tournament_type'] if tournament else 'normal'
                
                # Get clan player's tournament rating
                cursor.execute("""
                    SELECT tournament_rating FROM player_stats 
                    WHERE player_id = %s AND tournament_id = %s
                """, (clan_player_id, tournament_id))
                clan_tournament_rating_row = cursor.fetchone()
                
                # Determine default starting rating based on tournament type
                default_rating = 300
                if tournament_type == 'division':
                    cursor.execute("""
                        SELECT d.starting_rating FROM divisions d
                        JOIN tournament_players tp ON d.id = tp.division_id
                        WHERE tp.tournament_id = %s AND tp.player_id = %s
                    """, (tournament_id, clan_player_id))
                    division_row = cursor.fetchone()
                    if division_row:
                        default_rating = division_row['starting_rating']
                
                # Use tournament rating if exists, otherwise use division/default starting rating
                clan_rating_before = default_rating if (clan_tournament_rating_row is None or clan_tournament_rating_row['tournament_rating'] is None) else clan_tournament_rating_row['tournament_rating']
                
                # Guest player always assumed to have 300 rating
                guest_rating = 300
                
                # Determine match result
                is_null_match = clan_absent and guest_absent
                is_walkover = clan_absent or guest_absent
                is_draw = (clan_goals == guest_goals) and not is_null_match and not is_walkover
                
                # Determine winner
                winner_id = None
                if not is_null_match:
                    if is_walkover:
                        winner_id = clan_player_id if guest_absent else None  # None means guest won
                    elif clan_goals > guest_goals:
                        winner_id = clan_player_id
                    elif guest_goals > clan_goals:
                        winner_id = None  # Guest won (represented as NULL)
                    # If draw, winner_id remains None
                
                # Calculate rating changes
                clan_rating_after = clan_rating_before
                guest_rating_after = guest_rating
                
                if is_null_match:
                    # Both absent - penalty
                    NULL_PENALTY = 15
                    clan_rating_after = max(0, min(1000, clan_rating_before - NULL_PENALTY))
                    guest_rating_after = max(0, min(1000, guest_rating - NULL_PENALTY))
                elif is_walkover:
                    # Walkover - reduced rating change (75%)
                    if guest_absent:
                        # Clan wins
                        rating_change = TournamentDB.calculate_rating_change(clan_rating_before, guest_rating, is_draw=False)[0]
                        clan_rating_after = max(0, min(1000, clan_rating_before + int(rating_change * 0.75)))
                    else:
                        # Clan absent, guest wins
                        rating_change = TournamentDB.calculate_rating_change(guest_rating, clan_rating_before, is_draw=False)[1]
                        clan_rating_after = max(0, min(1000, clan_rating_before + int(rating_change * 0.75)))
                else:
                    # Normal match - use enhanced rating calculation
                    clan_rating_change, _ = TournamentDB.calculate_enhanced_rating_change(
                        clan_rating_before, guest_rating, clan_goals, guest_goals, False, False
                    )
                    clan_rating_after = max(0, min(1000, clan_rating_before + clan_rating_change))
                
                # Insert into guest_matches table (for backward compatibility)
                cursor.execute(
                    """
                    INSERT INTO guest_matches 
                    (match_id, tournament_id, clan_player_id, guest_name, clan_goals, guest_goals, 
                     clan_absent, guest_absent, is_null_match, is_walkover, clan_rating_before, clan_rating_after)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (next_match_id, tournament_id, clan_player_id, guest_name, clan_goals, guest_goals,
                     clan_absent, guest_absent, is_null_match, is_walkover, clan_rating_before, clan_rating_after)
                )
                guest_match_id = cursor.fetchone()['id']
                
                # Insert into player_matches table (treating guest as NULL player2_id)
                cursor.execute("""
                    INSERT INTO player_matches 
                    (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
                     winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
                     player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
                    VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (next_match_id, tournament_id, clan_player_id, clan_goals, guest_goals,
                      winner_id, is_draw, is_walkover, is_null_match, clan_absent, guest_absent,
                      clan_rating_before, guest_rating, clan_rating_after, guest_rating_after))
                
                # Update clan player's tournament stats (only if not null match)
                if not is_null_match:
                    won = 1 if winner_id == clan_player_id else 0
                    drawn = 1 if is_draw else 0
                    lost = 1 if (not is_draw and winner_id != clan_player_id) else 0
                    
                    glove_points = 0
                    if not is_walkover:
                        glove_points = TournamentDB.calculate_golden_glove_points(
                            clan_goals, guest_goals, winner_id == clan_player_id, is_draw
                        )
                    
                    cursor.execute("""
                        INSERT INTO player_stats 
                        (player_id, tournament_id, tournament_rating, matches_played, wins, draws, losses, goals_scored, goals_conceded, clean_sheets, golden_glove_points)
                        VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (player_id, tournament_id)
                        DO UPDATE SET
                            tournament_rating = %s,
                            matches_played = player_stats.matches_played + 1,
                            wins = player_stats.wins + %s,
                            draws = player_stats.draws + %s,
                            losses = player_stats.losses + %s,
                            goals_scored = player_stats.goals_scored + %s,
                            goals_conceded = player_stats.goals_conceded + %s,
                            clean_sheets = player_stats.clean_sheets + %s,
                            golden_glove_points = player_stats.golden_glove_points + %s
                    """, (clan_player_id, tournament_id, clan_rating_after, won, drawn, lost, clan_goals, guest_goals, 1 if guest_goals == 0 else 0, glove_points,
                          clan_rating_after, won, drawn, lost, clan_goals, guest_goals, 1 if guest_goals == 0 else 0, glove_points))
                    
                    # Update overall player stats
                    cursor.execute("""
                        UPDATE players SET 
                            matches_played = matches_played + 1,
                            matches_won = matches_won + %s,
                            matches_drawn = matches_drawn + %s,
                            matches_lost = matches_lost + %s,
                            goals_scored = goals_scored + %s,
                            goals_conceded = goals_conceded + %s,
                            clean_sheets = clean_sheets + %s,
                            golden_glove_points = golden_glove_points + %s
                        WHERE id = %s
                    """, (won, drawn, lost, clan_goals, guest_goals, 1 if guest_goals == 0 else 0, glove_points, clan_player_id))
                
                # Calculate and update overall rating from all matches
                new_overall_rating = TournamentDB.calculate_overall_rating_from_last_matches(cursor, clan_player_id, limit=40)
                cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating, clan_player_id))
                
                conn.commit()
                return next_match_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def _update_player_stats_for_guest_match(player_id, player_goals, opponent_goals, player_absent, opponent_absent, new_rating):
        """Update player stats after a guest match"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Determine match outcome
                if player_absent and opponent_absent:
                    # Null match - no stats update
                    return
                elif player_absent:
                    # Player absent - loss
                    matches_won = 0
                    matches_drawn = 0
                    matches_lost = 1
                elif opponent_absent:
                    # Opponent absent - win
                    matches_won = 1
                    matches_drawn = 0
                    matches_lost = 0
                else:
                    # Normal match
                    if player_goals > opponent_goals:
                        matches_won = 1
                        matches_drawn = 0
                        matches_lost = 0
                    elif opponent_goals > player_goals:
                        matches_won = 0
                        matches_drawn = 0
                        matches_lost = 1
                    else:
                        matches_won = 0
                        matches_drawn = 1
                        matches_lost = 0
                
                # Update player stats
                cursor.execute(
                    """
                    UPDATE players 
                    SET matches_played = matches_played + 1,
                        matches_won = matches_won + %s,
                        matches_drawn = matches_drawn + %s,
                        matches_lost = matches_lost + %s,
                        goals_scored = goals_scored + %s,
                        goals_conceded = goals_conceded + %s,
                        rating = %s
                    WHERE id = %s
                    """,
                    (matches_won, matches_drawn, matches_lost, player_goals, opponent_goals, new_rating, player_id)
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def record_bulk_matches(matches_data):
        """Record multiple matches at once - uses regular record_match to ensure consistency"""
        match_ids = []
        
        for match_data in matches_data:
            tournament_id = match_data['tournament_id']
            player1_id = match_data['player1_id']
            player2_id = match_data['player2_id']
            player1_goals = match_data['player1_goals']
            player2_goals = match_data['player2_goals']
            player1_absent = match_data.get('player1_absent', False)
            player2_absent = match_data.get('player2_absent', False)
            
            # Validate different players
            if player1_id == player2_id:
                raise ValueError(f"Cannot record match between same player")
            
            # Use the regular record_match function to ensure consistency
            match_id = TournamentDB.record_match(
                tournament_id, player1_id, player2_id,
                player1_goals, player2_goals,
                player1_absent, player2_absent
            )
            
            match_ids.append(match_id)
        
        return match_ids
    
    @staticmethod
    def _record_bulk_null_match(cursor, tournament_id, player1_id, player2_id):
        """Record a null match in bulk operations where both players are absent"""
        # Get current ratings (for record keeping, handle null ratings for new players)
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_rating_result = cursor.fetchone()['rating']
        player1_rating = 300 if player1_rating_result is None else player1_rating_result
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_rating_result = cursor.fetchone()['rating']
        player2_rating = 300 if player2_rating_result is None else player2_rating_result
        
        # Apply negative points for both absent players (penalty: -15 rating points)
        NULL_MATCH_PENALTY = 15
        new_rating1 = max(0, min(1000, player1_rating - NULL_MATCH_PENALTY))
        new_rating2 = max(0, min(1000, player2_rating - NULL_MATCH_PENALTY))
        
        # Get next match ID
        cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 as next_id FROM player_matches")
        match_id = cursor.fetchone()['next_id']
        
        # Record the null match with negative penalty applied
        cursor.execute("""
            INSERT INTO player_matches 
            (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
             winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
             player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
            VALUES (%s, %s, %s, %s, 0, 0, NULL, false, false, true, true, true, %s, %s, %s, %s)
        """, (match_id, tournament_id, player1_id, player2_id, 
              player1_rating, player2_rating, new_rating1, new_rating2))
        
        # Calculate and update overall ratings for both players
        # Null matches apply penalty so they affect cumulative rating
        new_overall_rating1 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player1_id, limit=40)
        new_overall_rating2 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player2_id, limit=40)
        
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating1, player1_id))
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating2, player2_id))
        
        return match_id
    
    @staticmethod
    def _record_bulk_walkover_match(cursor, tournament_id, player1_id, player2_id, player1_absent, player2_absent):
        """Record a walkover match in bulk operations where one player is absent"""
        # Get current ratings (handle null ratings for new players)
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_rating_result = cursor.fetchone()['rating']
        player1_rating = 300 if player1_rating_result is None else player1_rating_result
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_rating_result = cursor.fetchone()['rating']
        player2_rating = 300 if player2_rating_result is None else player2_rating_result
        
        # Determine winner (present player wins by walkover)
        winner_id = player2_id if player1_absent else player1_id
        loser_id = player1_id if player1_absent else player2_id
        winner_rating = player2_rating if player1_absent else player1_rating
        loser_rating = player1_rating if player1_absent else player2_rating
        
        # Calculate rating changes (smaller changes for walkover)
        rating_change_winner, rating_change_loser = TournamentDB.calculate_rating_change(
            winner_rating, loser_rating, is_draw=False
        )
        
        # Reduce rating changes for walkover (75% of normal change)
        rating_change_winner = int(rating_change_winner * 0.75)
        rating_change_loser = int(rating_change_loser * 0.75)
        
        # Apply rating bounds (0-1000)
        new_winner_rating = max(0, min(1000, winner_rating + rating_change_winner))
        new_loser_rating = max(0, min(1000, loser_rating + rating_change_loser))
        
        new_rating1 = new_winner_rating if winner_id == player1_id else new_loser_rating
        new_rating2 = new_winner_rating if winner_id == player2_id else new_loser_rating
        
        # Get next match ID
        cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 as next_id FROM player_matches")
        match_id = cursor.fetchone()['next_id']
        
        # Record the walkover match (0-0 score, update ratings, matches_played, wins/losses but NO goals)
        cursor.execute("""
            INSERT INTO player_matches 
            (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
             winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
             player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
            VALUES (%s, %s, %s, %s, 0, 0, %s, false, true, false, %s, %s, %s, %s, %s, %s)
        """, (match_id, tournament_id, player1_id, player2_id,
              winner_id, player1_absent, player2_absent,
              player1_rating, player2_rating, new_rating1, new_rating2))
        
        # Update player stats, matches_played, wins/losses (but NO goals for walkover)
        cursor.execute("""
            UPDATE players SET 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_lost = matches_lost + %s
            WHERE id = %s
        """, (1 if winner_id == player1_id else 0,
              1 if winner_id != player1_id else 0,
              player1_id))
        
        cursor.execute("""
            UPDATE players SET 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_lost = matches_lost + %s
            WHERE id = %s
        """, (1 if winner_id == player2_id else 0,
              1 if winner_id != player2_id else 0,
              player2_id))
        
        # Update tournament stats - matches_played, wins/losses (but NO goals)
        for player_id, is_winner in [
            (player1_id, winner_id == player1_id),
            (player2_id, winner_id == player2_id)
        ]:
            cursor.execute("""
                INSERT INTO player_stats 
                (player_id, tournament_id, matches_played, wins, draws, losses, goals_scored, goals_conceded)
                VALUES (%s, %s, 1, %s, 0, %s, 0, 0)
                ON CONFLICT (player_id, tournament_id)
                DO UPDATE SET
                    matches_played = player_stats.matches_played + 1,
                    wins = player_stats.wins + %s,
                    losses = player_stats.losses + %s
            """, (player_id, tournament_id,
                  1 if is_winner else 0,
                  1 if not is_winner else 0,
                  1 if is_winner else 0,
                  1 if not is_winner else 0))
        
        # Calculate and update overall ratings for both players
        new_overall_rating1 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player1_id, limit=40)
        new_overall_rating2 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player2_id, limit=40)
        
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating1, player1_id))
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating2, player2_id))
        
        return match_id
    
    @staticmethod
    def _record_bulk_normal_match(cursor, tournament_id, player1_id, player2_id, player1_goals, player2_goals):
        """Record a normal match in bulk operations with both players present"""
        # Get current ratings (handle null ratings for new players)
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_rating_result = cursor.fetchone()['rating']
        player1_rating = 300 if player1_rating_result is None else player1_rating_result
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_rating_result = cursor.fetchone()['rating']
        player2_rating = 300 if player2_rating_result is None else player2_rating_result
        
        # Determine winner and calculate enhanced rating changes with goals and clean sheets
        is_draw = player1_goals == player2_goals
        winner_id = None if is_draw else (player1_id if player1_goals > player2_goals else player2_id)
        
        # Use enhanced rating calculation that includes goal scoring bonuses
        rating_change1, rating_change2 = TournamentDB.calculate_enhanced_rating_change(
            player1_rating, player2_rating, player1_goals, player2_goals
        )
        
        # Apply rating bounds (0-1000)
        new_rating1 = max(0, min(1000, player1_rating + rating_change1))
        new_rating2 = max(0, min(1000, player2_rating + rating_change2))
        
        # Get next match ID
        cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 as next_id FROM player_matches")
        match_id = cursor.fetchone()['next_id']
        
        # Record the match
        cursor.execute("""
            INSERT INTO player_matches 
            (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
             winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
             player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false, false, false, false, %s, %s, %s, %s)
        """, (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
              winner_id, is_draw, player1_rating, player2_rating, new_rating1, new_rating2))
        
        # Update player stats (without rating first)
        cursor.execute("""
            UPDATE players SET 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_drawn = matches_drawn + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s
            WHERE id = %s
        """, (1 if winner_id == player1_id else 0,
              1 if is_draw else 0,
              1 if winner_id == player2_id else 0,
              player1_goals, player2_goals, player1_id))
        
        cursor.execute("""
            UPDATE players SET 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_drawn = matches_drawn + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s
            WHERE id = %s
        """, (1 if winner_id == player2_id else 0,
              1 if is_draw else 0,
              1 if winner_id == player1_id else 0,
              player2_goals, player1_goals, player2_id))
        
        # Update tournament stats
        for player_id, goals_scored, goals_conceded, is_winner in [
            (player1_id, player1_goals, player2_goals, winner_id == player1_id),
            (player2_id, player2_goals, player1_goals, winner_id == player2_id)
        ]:
            cursor.execute("""
                INSERT INTO player_stats 
                (player_id, tournament_id, matches_played, wins, draws, losses, goals_scored, goals_conceded)
                VALUES (%s, %s, 1, %s, %s, %s, %s, %s)
                ON CONFLICT (player_id, tournament_id)
                DO UPDATE SET
                    matches_played = player_stats.matches_played + 1,
                    wins = player_stats.wins + %s,
                    draws = player_stats.draws + %s,
                    losses = player_stats.losses + %s,
                    goals_scored = player_stats.goals_scored + %s,
                    goals_conceded = player_stats.goals_conceded + %s
            """, (player_id, tournament_id,
                  1 if is_winner else 0,
                  1 if is_draw else 0,
                  1 if not is_winner and not is_draw else 0,
                  goals_scored, goals_conceded,
                  1 if is_winner else 0,
                  1 if is_draw else 0,
                  1 if not is_winner and not is_draw else 0,
                  goals_scored, goals_conceded))
        
        # Calculate and update overall ratings for both players
        new_overall_rating1 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player1_id, limit=40)
        new_overall_rating2 = TournamentDB.calculate_overall_rating_from_last_matches(cursor, player2_id, limit=40)
        
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating1, player1_id))
        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating2, player2_id))
        
        return match_id
    
    @staticmethod
    def get_all_matches(tournament_id=None, limit=None, offset=0, search_query=None):
        """Get all matches (both regular and guest) with player details, with pagination and search support"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Union query to get both regular and guest matches with division info
                query = """
                    (
                        SELECT pm.match_id, pm.tournament_id, pm.played_at,
                               p1.name as player1_name, p2.name as player2_name,
                               t.name as tournament_name,
                               pm.player1_goals, pm.player2_goals,
                               pm.winner_id, pm.is_draw, pm.is_walkover, pm.is_null_match,
                               pm.player1_absent, pm.player2_absent,
                               pm.player1_rating_before, pm.player2_rating_before,
                               pm.player1_rating_after, pm.player2_rating_after,
                               'regular' as match_type,
                               pm.player1_id, pm.player2_id,
                               pm.id as record_id,
                               t.tournament_type,
                               tp1.division_id as player1_division_id,
                               d1.name as player1_division_name,
                               tp2.division_id as player2_division_id,
                               d2.name as player2_division_name
                        FROM player_matches pm
                        JOIN players p1 ON pm.player1_id = p1.id
                        JOIN players p2 ON pm.player2_id = p2.id
                        JOIN tournaments t ON pm.tournament_id = t.id
                        LEFT JOIN tournament_players tp1 ON pm.player1_id = tp1.player_id AND pm.tournament_id = tp1.tournament_id
                        LEFT JOIN divisions d1 ON tp1.division_id = d1.id
                        LEFT JOIN tournament_players tp2 ON pm.player2_id = tp2.player_id AND pm.tournament_id = tp2.tournament_id
                        LEFT JOIN divisions d2 ON tp2.division_id = d2.id
                        {tournament_filter_regular}
                    )
                    UNION ALL
                    (
                        SELECT gm.match_id, gm.tournament_id, gm.played_at,
                               p.name as player1_name, gm.guest_name as player2_name,
                               t.name as tournament_name,
                               gm.clan_goals as player1_goals, gm.guest_goals as player2_goals,
                               CASE WHEN gm.clan_goals > gm.guest_goals THEN gm.clan_player_id
                                    WHEN gm.guest_goals > gm.clan_goals THEN NULL
                                    ELSE NULL END as winner_id,
                               CASE WHEN gm.clan_goals = gm.guest_goals THEN true ELSE false END as is_draw,
                               gm.is_walkover, gm.is_null_match,
                               gm.clan_absent as player1_absent, gm.guest_absent as player2_absent,
                               gm.clan_rating_before as player1_rating_before,
                               300 as player2_rating_before,
                               gm.clan_rating_after as player1_rating_after,
                               300 as player2_rating_after,
                               'guest' as match_type,
                               gm.clan_player_id as player1_id, NULL as player2_id,
                               gm.id as record_id,
                               t.tournament_type,
                               tp.division_id as player1_division_id,
                               d.name as player1_division_name,
                               NULL as player2_division_id,
                               NULL as player2_division_name
                        FROM guest_matches gm
                        JOIN players p ON gm.clan_player_id = p.id
                        JOIN tournaments t ON gm.tournament_id = t.id
                        LEFT JOIN tournament_players tp ON gm.clan_player_id = tp.player_id AND gm.tournament_id = tp.tournament_id
                        LEFT JOIN divisions d ON tp.division_id = d.id
                        {tournament_filter_guest}
                    )
                    ORDER BY played_at DESC
                """
                
                params = []
                
                # Build WHERE clauses for tournament and search filters
                conditions_regular = []
                conditions_guest = []
                
                if tournament_id:
                    conditions_regular.append("pm.tournament_id = %s")
                    conditions_guest.append("gm.tournament_id = %s")
                    params.extend([tournament_id, tournament_id])
                
                if search_query:
                    search_pattern = f"%{search_query.lower()}%"
                    conditions_regular.append("(LOWER(p1.name) LIKE %s OR LOWER(p2.name) LIKE %s)")
                    conditions_guest.append("(LOWER(p.name) LIKE %s OR LOWER(gm.guest_name) LIKE %s)")
                    params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
                
                tournament_filter_regular = "WHERE " + " AND ".join(conditions_regular) if conditions_regular else ""
                tournament_filter_guest = "WHERE " + " AND ".join(conditions_guest) if conditions_guest else ""
                
                query = query.format(
                    tournament_filter_regular=tournament_filter_regular,
                    tournament_filter_guest=tournament_filter_guest
                )
                
                if limit:
                    query += f" LIMIT %s OFFSET %s"
                    params.extend([limit, offset])
                
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_matches_count(tournament_id=None, search_query=None):
        """Get total count of matches for pagination"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Count query for both regular and guest matches
                query = """
                    SELECT COUNT(*) as total FROM (
                        (
                            SELECT pm.match_id
                            FROM player_matches pm
                            JOIN players p1 ON pm.player1_id = p1.id
                            JOIN players p2 ON pm.player2_id = p2.id
                            {tournament_filter_regular}
                        )
                        UNION ALL
                        (
                            SELECT gm.match_id
                            FROM guest_matches gm
                            JOIN players p ON gm.clan_player_id = p.id
                            {tournament_filter_guest}
                        )
                    ) as all_matches
                """
                
                params = []
                
                # Build WHERE clauses for tournament and search filters
                conditions_regular = []
                conditions_guest = []
                
                if tournament_id:
                    conditions_regular.append("pm.tournament_id = %s")
                    conditions_guest.append("gm.tournament_id = %s")
                    params.extend([tournament_id, tournament_id])
                
                if search_query:
                    search_pattern = f"%{search_query.lower()}%"
                    conditions_regular.append("(LOWER(p1.name) LIKE %s OR LOWER(p2.name) LIKE %s)")
                    conditions_guest.append("(LOWER(p.name) LIKE %s OR LOWER(gm.guest_name) LIKE %s)")
                    params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
                
                tournament_filter_regular = "WHERE " + " AND ".join(conditions_regular) if conditions_regular else ""
                tournament_filter_guest = "WHERE " + " AND ".join(conditions_guest) if conditions_guest else ""
                
                query = query.format(
                    tournament_filter_regular=tournament_filter_regular,
                    tournament_filter_guest=tournament_filter_guest
                )
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result['total'] if result else 0
        finally:
            conn.close()
    
    @staticmethod
    def get_match_by_id(match_id):
        """Get a specific match by its ID (checks both player_matches and guest_matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # First check player_matches table
                cursor.execute("""
                    SELECT pm.*, 
                           p1.name as player1_name, p2.name as player2_name,
                           t.name as tournament_name,
                           'regular' as match_type
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    JOIN players p2 ON pm.player2_id = p2.id
                    JOIN tournaments t ON pm.tournament_id = t.id
                    WHERE pm.match_id = %s
                """, (match_id,))
                regular_match = cursor.fetchone()
                if regular_match:
                    return regular_match
                
                # If not found, check guest_matches table
                cursor.execute("""
                    SELECT gm.*,
                           p.name as player1_name, gm.guest_name as player2_name,
                           t.name as tournament_name,
                           'guest' as match_type,
                           gm.clan_player_id as player1_id, NULL as player2_id,
                           gm.clan_goals as player1_goals, gm.guest_goals as player2_goals,
                           CASE WHEN gm.clan_goals > gm.guest_goals THEN gm.clan_player_id
                                WHEN gm.guest_goals > gm.clan_goals THEN NULL
                                ELSE NULL END as winner_id,
                           CASE WHEN gm.clan_goals = gm.guest_goals THEN true ELSE false END as is_draw,
                           gm.clan_rating_before as player1_rating_before,
                           300 as player2_rating_before,
                           gm.clan_rating_after as player1_rating_after,
                           300 as player2_rating_after,
                           gm.clan_absent as player1_absent,
                           gm.guest_absent as player2_absent
                    FROM guest_matches gm
                    JOIN players p ON gm.clan_player_id = p.id
                    JOIN tournaments t ON gm.tournament_id = t.id
                    WHERE gm.match_id = %s
                """, (match_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def delete_match(match_id):
        """Delete a match and recalculate player ratings (handles both regular and guest matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get match details before deletion
                match = TournamentDB.get_match_by_id(match_id)
                if not match:
                    raise ValueError("Match not found")
                
                # Check if this is a guest match
                if match.get('match_type') == 'guest':
                    return TournamentDB._delete_guest_match(match_id)
                else:
                    return TournamentDB._delete_regular_match(match_id)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def _delete_regular_match(match_id):
        """Delete a regular player vs player match"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get match details before deletion
                match = TournamentDB.get_match_by_id(match_id)
                if not match:
                    raise ValueError("Match not found")
                
                tournament_id = match['tournament_id']
                
                # Delete the match
                cursor.execute("DELETE FROM player_matches WHERE match_id = %s", (match_id,))
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
        
        # Recalculate tournament and overall ratings for the affected tournament
        TournamentDB.recalculate_tournament_ratings(tournament_id)
    
    @staticmethod
    def _delete_guest_match(match_id):
        """Delete a guest match (clan player vs external guest)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get guest match details before deletion
                cursor.execute("""
                    SELECT gm.*, p.name as clan_player_name, t.name as tournament_name
                    FROM guest_matches gm
                    JOIN players p ON gm.clan_player_id = p.id
                    JOIN tournaments t ON gm.tournament_id = t.id
                    WHERE gm.match_id = %s
                """, (match_id,))
                match = cursor.fetchone()
                if not match:
                    raise ValueError("Guest match not found")
                
                tournament_id = match['tournament_id']
                clan_player_id = match['clan_player_id']
                
                # Delete the guest match
                cursor.execute("DELETE FROM guest_matches WHERE match_id = %s", (match_id,))
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
        
        # Recalculate overall rating for clan player from remaining matches (guest matches don't have tournament ratings)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                new_overall_rating = TournamentDB.calculate_overall_rating_from_last_matches(cursor, clan_player_id, limit=40)
                cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating, clan_player_id))
                conn.commit()
        finally:
            conn.close()
    
    @staticmethod
    def get_player_details(player_id):
        """Get detailed player information"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_player_match_history(player_id):
        """Get all matches for a specific player"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT pm.*, 
                           p1.name as player1_name, p2.name as player2_name,
                           t.name as tournament_name,
                           CASE 
                               WHEN pm.player1_id = %s THEN p2.name
                               ELSE p1.name
                           END as opponent_name,
                           CASE 
                               WHEN pm.player1_id = %s THEN pm.player1_goals
                               ELSE pm.player2_goals
                           END as player_goals,
                           CASE 
                               WHEN pm.player1_id = %s THEN pm.player2_goals
                               ELSE pm.player1_goals
                           END as opponent_goals,
                           CASE 
                               WHEN pm.player1_id = %s THEN pm.player1_rating_before
                               ELSE pm.player2_rating_before
                           END as rating_before,
                           CASE 
                               WHEN pm.player1_id = %s THEN pm.player1_rating_after
                               ELSE pm.player2_rating_after
                           END as rating_after,
                           CASE 
                               WHEN pm.is_null_match THEN 'Null Match'
                               WHEN pm.is_walkover AND pm.winner_id = %s THEN 'Win (W.O.)'
                               WHEN pm.is_walkover AND pm.winner_id != %s THEN 'Loss (W.O.)'
                               WHEN pm.is_draw THEN 'Draw'
                               WHEN pm.winner_id = %s THEN 'Win'
                               ELSE 'Loss'
                           END as result
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    JOIN players p2 ON pm.player2_id = p2.id
                    JOIN tournaments t ON pm.tournament_id = t.id
                    WHERE pm.player1_id = %s OR pm.player2_id = %s
                    ORDER BY pm.played_at DESC
                """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_player_tournament_participation(player_id):
        """Get all tournaments a player has participated in with their stats"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT t.*, ps.*,
                           CASE WHEN ps.matches_played > 0 
                                THEN ROUND(ps.wins * 100.0 / ps.matches_played, 1) 
                                ELSE 0 END as win_percentage
                    FROM tournaments t
                    LEFT JOIN player_stats ps ON t.id = ps.tournament_id AND ps.player_id = %s
                    WHERE EXISTS (
                        SELECT 1 FROM tournament_players tp 
                        WHERE tp.tournament_id = t.id AND tp.player_id = %s
                    )
                    ORDER BY t.created_at DESC
                """, (player_id, player_id))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_player_rating_history(player_id):
        """Get player rating changes over time"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get initial rating (300 by default)
                cursor.execute("""
                    SELECT 300 as rating, created_at as date, 'Player Created' as event
                    FROM players WHERE id = %s
                    UNION ALL
                    SELECT 
                        CASE 
                            WHEN player1_id = %s THEN player1_rating_after
                            ELSE player2_rating_after
                        END as rating,
                        played_at as date,
                        CONCAT('Match vs ', 
                            CASE 
                                WHEN player1_id = %s THEN p2.name
                                ELSE p1.name
                            END
                        ) as event
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    JOIN players p2 ON pm.player2_id = p2.id
                    WHERE player1_id = %s OR player2_id = %s
                    ORDER BY date ASC
                """, (player_id, player_id, player_id, player_id, player_id))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_player_by_id(player_id):
        """Get a specific player by ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def edit_player(player_id, name, rating, initial_rating=None):
        """Edit player name, rating and initial rating"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if player exists
                cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
                player = cursor.fetchone()
                if not player:
                    raise ValueError("Player not found")
                
                # Check if name already exists for another player
                cursor.execute("SELECT id FROM players WHERE name = %s AND id != %s", (name, player_id))
                existing_player = cursor.fetchone()
                if existing_player:
                    raise ValueError(f"A player with the name '{name}' already exists")
                
                # Validate rating range if rating is provided
                if rating is not None and (rating < 0 or rating > 1000):
                    raise ValueError("Rating must be between 0 and 1000")
                
                # Validate initial_rating range if provided
                if initial_rating is not None and (initial_rating < 0 or initial_rating > 1000):
                    raise ValueError("Initial rating must be between 0 and 1000")
                
                # Update the player
                cursor.execute(
                    "UPDATE players SET name = %s, rating = %s, initial_rating = %s WHERE id = %s",
                    (name.strip(), rating, initial_rating, player_id)
                )
                conn.commit()
                return player_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def update_player_photo(player_id, photo_url, photo_file_id):
        """Update player photo information"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if player exists
                cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
                player = cursor.fetchone()
                if not player:
                    raise ValueError("Player not found")
                
                # Update photo fields
                cursor.execute(
                    "UPDATE players SET photo_url = %s, photo_file_id = %s WHERE id = %s",
                    (photo_url, photo_file_id, player_id)
                )
                conn.commit()
                return player_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def remove_player_photo(player_id):
        """Remove player photo information"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if player exists
                cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
                player = cursor.fetchone()
                if not player:
                    raise ValueError("Player not found")
                
                # Get current photo info for cleanup
                old_file_id = player.get('photo_file_id')
                
                # Clear photo fields
                cursor.execute(
                    "UPDATE players SET photo_url = NULL, photo_file_id = NULL WHERE id = %s",
                    (player_id,)
                )
                conn.commit()
                return old_file_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_players_with_photos():
        """Get all players that have photos"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name, photo_url, photo_file_id FROM players WHERE photo_url IS NOT NULL ORDER BY name"
                )
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def delete_player(player_id):
        """Delete a player and all associated data"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if player exists
                cursor.execute("SELECT * FROM players WHERE id = %s", (player_id,))
                player = cursor.fetchone()
                if not player:
                    raise ValueError("Player not found")
                
                # Get photo info for cleanup before deletion
                photo_file_id = player.get('photo_file_id')
                
                # Delete in correct order to maintain referential integrity
                # 1. Delete player stats
                cursor.execute("DELETE FROM player_stats WHERE player_id = %s", (player_id,))
                
                # 2. Delete player matches
                cursor.execute("DELETE FROM player_matches WHERE player1_id = %s OR player2_id = %s", (player_id, player_id))
                
                # 3. Remove player from tournaments
                cursor.execute("DELETE FROM tournament_players WHERE player_id = %s", (player_id,))
                
                # 4. Finally delete the player
                cursor.execute("DELETE FROM players WHERE id = %s", (player_id,))
                
                conn.commit()
                
                # Return photo_file_id for cleanup by the calling code
                return {'success': True, 'photo_file_id': photo_file_id}
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def delete_tournament(tournament_id):
        """Delete a tournament and all associated data"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check if tournament exists
                cursor.execute("SELECT * FROM tournaments WHERE id = %s", (tournament_id,))
                tournament = cursor.fetchone()
                if not tournament:
                    raise ValueError("Tournament not found")
                
                # Get photo info for cleanup before deletion
                tournament_photo_file_id = tournament.get('tournament_photo_file_id')
                
                # Delete in correct order to maintain referential integrity
                # 1. Delete tournament-specific player stats
                cursor.execute("DELETE FROM player_stats WHERE tournament_id = %s", (tournament_id,))
                
                # 2. Delete player matches in this tournament
                cursor.execute("DELETE FROM player_matches WHERE tournament_id = %s", (tournament_id,))
                
                # 3. Delete guest matches in this tournament
                cursor.execute("DELETE FROM guest_matches WHERE tournament_id = %s", (tournament_id,))
                
                # 4. Remove tournament players associations
                cursor.execute("DELETE FROM tournament_players WHERE tournament_id = %s", (tournament_id,))
                
                # 5. Finally delete the tournament itself
                cursor.execute("DELETE FROM tournaments WHERE id = %s", (tournament_id,))
                
                conn.commit()
                
                # Return photo_file_id for cleanup by the calling code
                return {'success': True, 'tournament_photo_file_id': tournament_photo_file_id}
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_player_vs_opponents(player_id):
        """Get head-to-head records against all opponents"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN pm.player1_id = %s THEN p2.name
                            ELSE p1.name
                        END as opponent_name,
                        CASE 
                            WHEN pm.player1_id = %s THEN p2.id
                            ELSE p1.id
                        END as opponent_id,
                        COUNT(*) as total_matches,
                        SUM(CASE WHEN pm.winner_id = %s THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN pm.is_draw THEN 1 ELSE 0 END) as draws,
                        SUM(CASE WHEN pm.winner_id != %s AND NOT pm.is_draw THEN 1 ELSE 0 END) as losses,
                        SUM(CASE 
                            WHEN pm.player1_id = %s THEN pm.player1_goals
                            ELSE pm.player2_goals
                        END) as goals_for,
                        SUM(CASE 
                            WHEN pm.player1_id = %s THEN pm.player2_goals
                            ELSE pm.player1_goals
                        END) as goals_against
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    JOIN players p2 ON pm.player2_id = p2.id
                    WHERE pm.player1_id = %s OR pm.player2_id = %s
                    GROUP BY opponent_name, opponent_id
                    ORDER BY total_matches DESC, wins DESC
                """, (player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def edit_match(match_id, new_player1_goals, new_player2_goals, player1_absent=False, player2_absent=False, new_guest_name=None):
        """Edit a match and recalculate player ratings (handles both regular and guest matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get match details before editing
                match = TournamentDB.get_match_by_id(match_id)
                if not match:
                    raise ValueError("Match not found")
                
                # Check if this is a guest match
                if match.get('match_type') == 'guest':
                    return TournamentDB._edit_guest_match(match_id, new_player1_goals, new_player2_goals, player1_absent, player2_absent, new_guest_name)
                else:
                    return TournamentDB._edit_regular_match(match_id, new_player1_goals, new_player2_goals, player1_absent, player2_absent)
                
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def _edit_regular_match(match_id, new_player1_goals, new_player2_goals, player1_absent=False, player2_absent=False):
        """Edit a regular player vs player match"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get match details before editing
                match = TournamentDB.get_match_by_id(match_id)
                if not match:
                    raise ValueError("Match not found")
                
                # Check if anything actually changed
                current_absence_state = (match.get('player1_absent', False), match.get('player2_absent', False))
                new_absence_state = (player1_absent, player2_absent)
                goals_changed = match['player1_goals'] != new_player1_goals or match['player2_goals'] != new_player2_goals
                absence_changed = current_absence_state != new_absence_state
                
                if not goals_changed and not absence_changed:
                    return match_id
                
                tournament_id = match['tournament_id']
                
                # Calculate new match properties
                new_is_null_match = player1_absent and player2_absent
                new_is_walkover = (player1_absent or player2_absent) and not new_is_null_match
                new_is_draw = new_player1_goals == new_player2_goals and not new_is_walkover and not new_is_null_match
                
                if new_is_null_match:
                    new_winner_id = None
                    new_player1_goals = 0
                    new_player2_goals = 0
                elif new_is_walkover:
                    new_winner_id = match['player2_id'] if player1_absent else match['player1_id']
                    new_player1_goals = 0
                    new_player2_goals = 0
                elif new_is_draw:
                    new_winner_id = None
                else:
                    new_winner_id = match['player1_id'] if new_player1_goals > new_player2_goals else match['player2_id']
                
                # Update only the match data (goals, winner, flags)
                cursor.execute("""
                    UPDATE player_matches SET
                        player1_goals = %s,
                        player2_goals = %s,
                        winner_id = %s,
                        is_draw = %s,
                        is_walkover = %s,
                        is_null_match = %s,
                        player1_absent = %s,
                        player2_absent = %s
                    WHERE match_id = %s
                """, (new_player1_goals, new_player2_goals, new_winner_id, new_is_draw,
                      new_is_walkover, new_is_null_match, player1_absent, player2_absent, match_id))
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
        
        # Recalculate tournament and overall ratings for the affected tournament
        TournamentDB.recalculate_tournament_ratings(tournament_id)
        return match_id
    
    @staticmethod
    def _edit_guest_match(match_id, new_clan_goals, new_guest_goals, clan_absent=False, guest_absent=False, new_guest_name=None):
        """Edit a guest match (clan player vs external guest)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get guest match details before editing
                cursor.execute("""
                    SELECT gm.*, p.name as clan_player_name, t.name as tournament_name
                    FROM guest_matches gm
                    JOIN players p ON gm.clan_player_id = p.id
                    JOIN tournaments t ON gm.tournament_id = t.id
                    WHERE gm.match_id = %s
                """, (match_id,))
                match = cursor.fetchone()
                if not match:
                    raise ValueError("Guest match not found")
                
                # Check if anything actually changed
                current_absence_state = (match.get('clan_absent', False), match.get('guest_absent', False))
                new_absence_state = (clan_absent, guest_absent)
                goals_changed = match['clan_goals'] != new_clan_goals or match['guest_goals'] != new_guest_goals
                absence_changed = current_absence_state != new_absence_state
                guest_name_changed = new_guest_name and match['guest_name'] != new_guest_name
                
                if not goals_changed and not absence_changed and not guest_name_changed:
                    return match_id
                
                clan_player_id = match['clan_player_id']
                
                # Calculate new match properties
                new_is_null_match = clan_absent and guest_absent
                new_is_walkover = (clan_absent or guest_absent) and not new_is_null_match
                
                if new_is_null_match or new_is_walkover:
                    new_clan_goals = 0
                    new_guest_goals = 0
                
                # Update only the match data (goals, flags, guest name)
                if new_guest_name:
                    cursor.execute("""
                        UPDATE guest_matches SET
                            clan_goals = %s,
                            guest_goals = %s,
                            clan_absent = %s,
                            guest_absent = %s,
                            is_null_match = %s,
                            is_walkover = %s,
                            guest_name = %s
                        WHERE match_id = %s
                    """, (new_clan_goals, new_guest_goals, clan_absent, guest_absent,
                          new_is_null_match, new_is_walkover, new_guest_name, match_id))
                else:
                    cursor.execute("""
                        UPDATE guest_matches SET
                            clan_goals = %s,
                            guest_goals = %s,
                            clan_absent = %s,
                            guest_absent = %s,
                            is_null_match = %s,
                            is_walkover = %s
                        WHERE match_id = %s
                    """, (new_clan_goals, new_guest_goals, clan_absent, guest_absent,
                          new_is_null_match, new_is_walkover, match_id))
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
        
        # Recalculate overall rating for clan player from remaining matches (guest matches don't affect tournament ratings)
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                new_overall_rating = TournamentDB.calculate_overall_rating_from_last_matches(cursor, clan_player_id, limit=40)
                cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (new_overall_rating, clan_player_id))
                conn.commit()
        finally:
            conn.close()
        
        return match_id
    
    @staticmethod
    def get_golden_ball_overall():
        """Get overall Golden Ball winner (best overall player based on rating and performance)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.rating, p.matches_played,
                           p.matches_won, p.matches_drawn, p.matches_lost,
                           p.goals_scored, p.goals_conceded,
                           CASE WHEN p.matches_played > 0 
                                THEN ROUND((p.matches_won * 100.0 / p.matches_played), 1) 
                                ELSE 0 END as win_percentage,
                           ROUND(p.goals_scored::decimal / GREATEST(p.matches_played, 1), 2) as goals_per_match,
                           ROUND(p.goals_conceded::decimal / GREATEST(p.matches_played, 1), 2) as goals_conceded_per_match
                    FROM players p
                    WHERE p.matches_played >= 5
                    ORDER BY p.rating DESC, win_percentage DESC, p.matches_played DESC
                    LIMIT 1
                """)
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_ball_tournament(tournament_id):
        """Get Golden Ball winner for a specific tournament (best overall player)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.rating, ps.matches_played,
                           ps.wins, ps.draws, ps.losses,
                           ps.goals_scored, ps.goals_conceded,
                           CASE WHEN ps.matches_played > 0 
                                THEN ROUND((ps.wins * 100.0 / ps.matches_played), 1) 
                                ELSE 0 END as win_percentage,
                           ROUND(ps.goals_scored::decimal / GREATEST(ps.matches_played), 2) as goals_per_match,
                           ROUND(ps.goals_conceded::decimal / GREATEST(ps.matches_played, 1), 2) as goals_conceded_per_match
                    FROM players p
                    JOIN player_stats ps ON p.id = ps.player_id
                    WHERE ps.tournament_id = %s AND ps.matches_played >= 3
                    ORDER BY win_percentage DESC, ps.goals_scored DESC, ps.goals_conceded ASC
                    LIMIT 1
                """, (tournament_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_ball_top_players(limit=10, tournament_id=None):
        """Get top Golden Ball candidates (best overall players)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if tournament_id:
                    cursor.execute("""
                        SELECT p.id, p.name, p.rating, ps.matches_played,
                               ps.wins, ps.draws, ps.losses,
                               ps.goals_scored, ps.goals_conceded,
                               CASE WHEN ps.matches_played > 0 
                                    THEN ROUND((ps.wins * 100.0 / ps.matches_played), 1) 
                                    ELSE 0 END as win_percentage,
                               ROUND(ps.goals_scored::decimal / GREATEST(ps.matches_played, 1), 2) as goals_per_match,
                               ROUND(ps.goals_conceded::decimal / GREATEST(ps.matches_played, 1), 2) as goals_conceded_per_match
                        FROM players p
                        JOIN player_stats ps ON p.id = ps.player_id
                        WHERE ps.tournament_id = %s AND ps.matches_played >= 3
                        ORDER BY win_percentage DESC, ps.goals_scored DESC, ps.goals_conceded ASC
                        LIMIT %s
                    """, (tournament_id, limit))
                else:
                    cursor.execute("""
                        SELECT p.id, p.name, p.rating, p.matches_played,
                               p.matches_won, p.matches_drawn, p.matches_lost,
                               p.goals_scored, p.goals_conceded,
                               CASE WHEN p.matches_played > 0 
                                    THEN ROUND((p.matches_won * 100.0 / p.matches_played), 1) 
                                    ELSE 0 END as win_percentage,
                               ROUND(p.goals_scored::decimal / GREATEST(p.matches_played, 1), 2) as goals_per_match,
                               ROUND(p.goals_conceded::decimal / GREATEST(p.matches_played, 1), 2) as goals_conceded_per_match
                        FROM players p
                        WHERE p.matches_played >= 5
                        ORDER BY p.rating DESC, win_percentage DESC, p.matches_played DESC
                        LIMIT %s
                    """, (limit,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_boot_overall():
        """Get overall Golden Boot winner (most goals scored)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.goals_scored, p.matches_played,
                           ROUND(p.goals_scored::decimal / GREATEST(p.matches_played, 1), 2) as goals_per_match
                    FROM players p
                    WHERE p.matches_played > 0
                    ORDER BY p.goals_scored DESC, goals_per_match DESC
                    LIMIT 1
                """)
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_glove_overall():
        """Get overall Golden Glove winner (best goals conceded per match, min 10 matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.goals_conceded, p.matches_played,
                           ROUND(p.goals_conceded::decimal / p.matches_played, 2) as goals_conceded_per_match,
                           p.matches_played - (p.matches_won + p.matches_drawn + p.matches_lost) as clean_sheets
                    FROM players p
                    WHERE p.matches_played >= 10
                    ORDER BY goals_conceded_per_match ASC, p.goals_conceded ASC
                    LIMIT 1
                """)
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_boot_tournament(tournament_id):
        """Get Golden Boot winner for a specific tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, ps.goals_scored, ps.matches_played,
                           ROUND(ps.goals_scored::decimal / GREATEST(ps.matches_played, 1), 2) as goals_per_match
                    FROM players p
                    JOIN player_stats ps ON p.id = ps.player_id
                    WHERE ps.tournament_id = %s AND ps.matches_played > 0
                    ORDER BY ps.goals_scored DESC, goals_per_match DESC
                    LIMIT 1
                """, (tournament_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_glove_tournament(tournament_id):
        """Get Golden Glove winner for a specific tournament (min 10 matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, ps.goals_conceded, ps.matches_played,
                           ROUND(ps.goals_conceded::decimal / ps.matches_played, 2) as goals_conceded_per_match
                    FROM players p
                    JOIN player_stats ps ON p.id = ps.player_id
                    WHERE ps.tournament_id = %s AND ps.matches_played >= 10
                    ORDER BY goals_conceded_per_match ASC, ps.goals_conceded ASC
                    LIMIT 1
                """, (tournament_id,))
                return cursor.fetchone()
        finally:
            conn.close()
                             
    def get_golden_ball_overall():
        """Get overall Golden Ball winner (best overall player based on rating and performance)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.rating, p.matches_played,
                           p.matches_won, p.matches_drawn, p.matches_lost,
                           p.goals_scored, p.goals_conceded,
                           CASE WHEN p.matches_played > 0 
                                THEN ROUND((p.matches_won * 100.0 / p.matches_played), 1) 
                                ELSE 0 END as win_percentage,
                           ROUND(p.goals_scored::decimal / GREATEST(p.matches_played, 1), 2) as goals_per_match,
                           ROUND(p.goals_conceded::decimal / GREATEST(p.matches_played, 1), 2) as goals_conceded_per_match
                    FROM players p
                    WHERE p.matches_played >= 5
                    ORDER BY p.rating DESC, win_percentage DESC, p.matches_played DESC
                    LIMIT 1
                """)
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_ball_tournament(tournament_id):
        """Get Golden Ball winner for a specific tournament (best overall player)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.rating, ps.matches_played,
                           ps.wins, ps.draws, ps.losses,
                           ps.goals_scored, ps.goals_conceded,
                           CASE WHEN ps.matches_played > 0 
                                THEN ROUND((ps.wins * 100.0 / ps.matches_played), 1) 
                                ELSE 0 END as win_percentage,
                           ROUND(ps.goals_scored::decimal / GREATEST(ps.matches_played, 1), 2) as goals_per_match,
                           ROUND(ps.goals_conceded::decimal / GREATEST(ps.matches_played, 1), 2) as goals_conceded_per_match
                    FROM players p
                    JOIN player_stats ps ON p.id = ps.player_id
                    WHERE ps.tournament_id = %s AND ps.matches_played >= 3
                    ORDER BY win_percentage DESC, ps.goals_scored DESC, ps.goals_conceded ASC
                    LIMIT 1
                """, (tournament_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_ball_top_players(limit=10, tournament_id=None):
        """Get top Golden Ball candidates (best overall players)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if tournament_id:
                    cursor.execute("""
                        SELECT p.id, p.name, p.rating, ps.matches_played,
                               ps.wins, ps.draws, ps.losses,
                               ps.goals_scored, ps.goals_conceded,
                               CASE WHEN ps.matches_played > 0 
                                    THEN ROUND((ps.wins * 100.0 / ps.matches_played), 1) 
                                    ELSE 0 END as win_percentage,
                               ROUND(ps.goals_scored::decimal / GREATEST(ps.matches_played, 1), 2) as goals_per_match,
                               ROUND(ps.goals_conceded::decimal / GREATEST(ps.matches_played, 1), 2) as goals_conceded_per_match
                        FROM players p
                        JOIN player_stats ps ON p.id = ps.player_id
                        WHERE ps.tournament_id = %s AND ps.matches_played >= 3
                        ORDER BY win_percentage DESC, ps.goals_scored DESC, ps.goals_conceded ASC
                        LIMIT %s
                    """, (tournament_id, limit))
                else:
                    cursor.execute("""
                        SELECT p.id, p.name, p.rating, p.matches_played,
                               p.matches_won, p.matches_drawn, p.matches_lost,
                               p.goals_scored, p.goals_conceded,
                               CASE WHEN p.matches_played > 0 
                                    THEN ROUND((p.matches_won * 100.0 / p.matches_played), 1) 
                                    ELSE 0 END as win_percentage,
                               ROUND(p.goals_scored::decimal / GREATEST(p.matches_played, 1), 2) as goals_per_match,
                               ROUND(p.goals_conceded::decimal / GREATEST(p.matches_played, 1), 2) as goals_conceded_per_match
                        FROM players p
                        WHERE p.matches_played >= 5
                        ORDER BY p.rating DESC, win_percentage DESC, p.matches_played DESC
                        LIMIT %s
                    """, (limit,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_boot_overall():
        """Get overall Golden Boot winner (most goals scored)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.goals_scored, p.matches_played,
                           ROUND(p.goals_scored::decimal / GREATEST(p.matches_played, 1), 2) as goals_per_match
                    FROM players p
                    WHERE p.matches_played > 0
                    ORDER BY p.goals_scored DESC, goals_per_match DESC
                    LIMIT 1
                """)
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_glove_overall():
        """Get overall Golden Glove winner (best goals conceded per match, min 10 matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.goals_conceded, p.matches_played,
                           ROUND(p.goals_conceded::decimal / p.matches_played, 2) as goals_conceded_per_match,
                           p.matches_played - (p.matches_won + p.matches_drawn + p.matches_lost) as clean_sheets
                    FROM players p
                    WHERE p.matches_played >= 10
                    ORDER BY goals_conceded_per_match ASC, p.goals_conceded ASC
                    LIMIT 1
                """)
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_boot_tournament(tournament_id):
        """Get Golden Boot winner for a specific tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, ps.goals_scored, ps.matches_played,
                           ROUND(ps.goals_scored::decimal / GREATEST(ps.matches_played, 1), 2) as goals_per_match
                    FROM players p
                    JOIN player_stats ps ON p.id = ps.player_id
                    WHERE ps.tournament_id = %s AND ps.matches_played > 0
                    ORDER BY ps.goals_scored DESC, goals_per_match DESC
                    LIMIT 1
                """, (tournament_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_glove_tournament(tournament_id):
        """Get Golden Glove winner for a specific tournament (min 10 matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, ps.goals_conceded, ps.matches_played,
                           ROUND(ps.goals_conceded::decimal / ps.matches_played, 2) as goals_conceded_per_match
                    FROM players p
                    JOIN player_stats ps ON p.id = ps.player_id
                    WHERE ps.tournament_id = %s AND ps.matches_played >= 10
                    ORDER BY goals_conceded_per_match ASC, ps.goals_conceded ASC
                    LIMIT 1
                """, (tournament_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_boot_top_players(limit=10, tournament_id=None):
        """Get top Golden Boot candidates"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if tournament_id:
                    cursor.execute("""
                        SELECT p.id, p.name, ps.goals_scored, ps.matches_played,
                               ROUND(ps.goals_scored::decimal / GREATEST(ps.matches_played, 1), 2) as goals_per_match
                        FROM players p
                        JOIN player_stats ps ON p.id = ps.player_id
                        WHERE ps.tournament_id = %s AND ps.matches_played > 0
                        ORDER BY ps.goals_scored DESC, goals_per_match DESC
                        LIMIT %s
                    """, (tournament_id, limit))
                else:
                    cursor.execute("""
                        SELECT p.id, p.name, p.goals_scored, p.matches_played,
                               ROUND(p.goals_scored::decimal / GREATEST(p.matches_played, 1), 2) as goals_per_match
                        FROM players p
                        WHERE p.matches_played > 0
                        ORDER BY p.goals_scored DESC, goals_per_match DESC
                        LIMIT %s
                    """, (limit,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_glove_top_players(limit=10, tournament_id=None):
        """Get top Golden Glove candidates (min 10 matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if tournament_id:
                    cursor.execute("""
                        SELECT p.id, p.name, ps.goals_conceded, ps.matches_played,
                               ROUND(ps.goals_conceded::decimal / ps.matches_played, 2) as goals_conceded_per_match
                        FROM players p
                        JOIN player_stats ps ON p.id = ps.player_id
                        WHERE ps.tournament_id = %s AND ps.matches_played >= 10
                        ORDER BY goals_conceded_per_match ASC, ps.goals_conceded ASC
                        LIMIT %s
                    """, (tournament_id, limit))
                else:
                    cursor.execute("""
                        SELECT p.id, p.name, p.goals_conceded, p.matches_played,
                               ROUND(p.goals_conceded::decimal / p.matches_played, 2) as goals_conceded_per_match
                        FROM players p
                        WHERE p.matches_played >= 10
                        ORDER BY goals_conceded_per_match ASC, p.goals_conceded ASC
                        LIMIT %s
                    """, (limit,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def calculate_golden_glove_points(player_goals, opponent_goals, is_winner, is_draw):
        """Calculate Golden Glove points for a match based on the new system:
        - Clean Sheet (+5) + Win bonus (+2) = 7 pts (if win with clean sheet)
        - Clean Sheet (+5) = 5 pts (if draw with clean sheet)
        - Goal conceded penalty (-1 per goal)
        - Win bonus (+2) if winner
        """
        points = 0
        
        # Clean sheet bonus
        if opponent_goals == 0:
            points += 5
        
        # Win bonus
        if is_winner:
            points += 2
        
        # Goal conceded penalty
        points -= opponent_goals
        
        return points
    
    @staticmethod
    def get_golden_glove_points_overall():
        """Get overall Golden Glove winner by points (min 4 matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, p.golden_glove_points, p.matches_played, p.clean_sheets,
                           ROUND(p.golden_glove_points::decimal / p.matches_played, 2) as points_per_match
                    FROM players p
                    WHERE p.matches_played >= 4
                    ORDER BY p.golden_glove_points DESC, points_per_match DESC
                    LIMIT 1
                """)
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_glove_points_tournament(tournament_id):
        """Get Golden Glove winner for a specific tournament by points (min 4 matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.id, p.name, ps.golden_glove_points, ps.matches_played, ps.clean_sheets,
                           ROUND(ps.golden_glove_points::decimal / ps.matches_played, 2) as points_per_match
                    FROM players p
                    JOIN player_stats ps ON p.id = ps.player_id
                    WHERE ps.tournament_id = %s AND ps.matches_played >= 4
                    ORDER BY ps.golden_glove_points DESC, points_per_match DESC
                    LIMIT 1
                """, (tournament_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def get_golden_glove_points_top_players(limit=10, tournament_id=None):
        """Get top Golden Glove candidates by points (min 4 matches)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if tournament_id:
                    cursor.execute("""
                        SELECT p.id, p.name, ps.golden_glove_points, ps.matches_played, ps.clean_sheets,
                               ROUND(ps.golden_glove_points::decimal / ps.matches_played, 2) as points_per_match
                        FROM players p
                        JOIN player_stats ps ON p.id = ps.player_id
                        WHERE ps.tournament_id = %s AND ps.matches_played >= 4
                        ORDER BY ps.golden_glove_points DESC, points_per_match DESC
                        LIMIT %s
                    """, (tournament_id, limit))
                else:
                    cursor.execute("""
                        SELECT p.id, p.name, p.golden_glove_points, p.matches_played, p.clean_sheets,
                               ROUND(p.golden_glove_points::decimal / p.matches_played, 2) as points_per_match
                        FROM players p
                        WHERE p.matches_played >= 4
                        ORDER BY p.golden_glove_points DESC, points_per_match DESC
                        LIMIT %s
                    """, (limit,))
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_player_awards(player_id):
        """Get all Golden Boot and Golden Glove awards for a player"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                awards = []
                
                # Check overall Golden Ball
                golden_ball_overall = TournamentDB.get_golden_ball_overall()
                if golden_ball_overall and golden_ball_overall['id'] == player_id:
                    awards.append({
                        'type': 'Golden Ball',
                        'scope': 'Overall',
                        'tournament': None,
                        'value': golden_ball_overall['rating'],
                        'description': f"Best overall player - {golden_ball_overall['rating']} rating, {golden_ball_overall['win_percentage']}% win rate"
                    })
                
                # Check overall Golden Boot
                golden_boot_overall = TournamentDB.get_golden_boot_overall()
                if golden_boot_overall and golden_boot_overall['id'] == player_id:
                    awards.append({
                        'type': 'Golden Boot',
                        'scope': 'Overall',
                        'tournament': None,
                        'value': golden_boot_overall['goals_scored'],
                        'description': f"{golden_boot_overall['goals_scored']} goals in {golden_boot_overall['matches_played']} matches"
                    })
                
                # Check overall Golden Glove
                golden_glove_overall = TournamentDB.get_golden_glove_overall()
                if golden_glove_overall and golden_glove_overall['id'] == player_id:
                    awards.append({
                        'type': 'Golden Glove',
                        'scope': 'Overall',
                        'tournament': None,
                        'value': golden_glove_overall['goals_conceded_per_match'],
                        'description': f"{golden_glove_overall['goals_conceded_per_match']} goals conceded per match"
                    })
                
                # Check tournament-specific awards
                cursor.execute("""
                    SELECT DISTINCT t.id, t.name
                    FROM tournaments t
                    JOIN player_stats ps ON t.id = ps.tournament_id
                    WHERE ps.player_id = %s
                """, (player_id,))
                tournaments = cursor.fetchall()
                
                for tournament in tournaments:
                    # Check Golden Ball for this tournament
                    golden_ball_tournament = TournamentDB.get_golden_ball_tournament(tournament['id'])
                    if golden_ball_tournament and golden_ball_tournament['id'] == player_id:
                        awards.append({
                            'type': 'Golden Ball',
                            'scope': 'Tournament',
                            'tournament': tournament['name'],
                            'value': golden_ball_tournament['win_percentage'],
                            'description': f"Best overall player in {tournament['name']} - {golden_ball_tournament['win_percentage']}% win rate"
                        })
                    
                    # Check Golden Boot for this tournament
                    golden_boot_tournament = TournamentDB.get_golden_boot_tournament(tournament['id'])
                    if golden_boot_tournament and golden_boot_tournament['id'] == player_id:
                        awards.append({
                            'type': 'Golden Boot',
                            'scope': 'Tournament',
                            'tournament': tournament['name'],
                            'value': golden_boot_tournament['goals_scored'],
                            'description': f"{golden_boot_tournament['goals_scored']} goals in {tournament['name']}"
                        })
                    
                    # Check Golden Glove for this tournament
                    golden_glove_tournament = TournamentDB.get_golden_glove_tournament(tournament['id'])
                    if golden_glove_tournament and golden_glove_tournament['id'] == player_id:
                        awards.append({
                            'type': 'Golden Glove',
                            'scope': 'Tournament',
                            'tournament': tournament['name'],
                            'value': golden_glove_tournament['goals_conceded_per_match'],
                            'description': f"{golden_glove_tournament['goals_conceded_per_match']} goals conceded per match in {tournament['name']}"
                        })
                
                return awards
        finally:
            conn.close()
