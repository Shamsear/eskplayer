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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Create tournament_players (many-to-many relationship)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tournament_players (
                    id SERIAL PRIMARY KEY,
                    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
                    player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tournament_id, player_id)
                );
            ''')
            
            # Create player_matches table (1v1 matches)
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
            
            # Migration 7: Add guest_matches table
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
    def add_player(name, photo_url=None, photo_file_id=None):
        """Add a new player with optional photo"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO players (name, rating, photo_url, photo_file_id) VALUES (%s, %s, %s, %s) RETURNING id",
                    (name, None, photo_url, photo_file_id)
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
    def create_tournament(name, tournament_photo_url=None, tournament_photo_file_id=None):
        """Create a new tournament with optional photo"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tournaments (name, tournament_photo_url, tournament_photo_file_id) VALUES (%s, %s, %s) RETURNING id",
                    (name, tournament_photo_url, tournament_photo_file_id)
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
    def add_players_to_tournament(tournament_id, player_ids):
        """Add players to a tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for player_id in player_ids:
                    try:
                        cursor.execute(
                            "INSERT INTO tournament_players (tournament_id, player_id) VALUES (%s, %s)",
                            (tournament_id, player_id)
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
        """Get all players in a tournament"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.* FROM players p
                    JOIN tournament_players tp ON p.id = tp.player_id
                    WHERE tp.tournament_id = %s
                    ORDER BY p.rating DESC, p.name ASC
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
    def update_tournament(tournament_id, name, tournament_photo_url=None, tournament_photo_file_id=None):
        """Update tournament name and photo"""
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
    def record_match(tournament_id, player1_id, player2_id, player1_goals, player2_goals, player1_absent=False, player2_absent=False):
        """Record a 1v1 match and update ratings, handling absences"""
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
        
        # Update player ratings with penalty - nullified matches count as penalty but not as played matches
        cursor.execute("""
            UPDATE players SET rating = %s WHERE id = %s
        """, (new_rating1, player1_id))
        
        cursor.execute("""
            UPDATE players SET rating = %s WHERE id = %s
        """, (new_rating2, player2_id))
        
        conn.commit()
        return match_id
    
    @staticmethod
    def _record_walkover_match(cursor, tournament_id, player1_id, player2_id, player1_absent, player2_absent, conn):
        """Record a walkover match where one player is absent"""
        # Get current ratings, initialize to 300 if NULL
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
        
        # Record the walkover match
        cursor.execute("""
            INSERT INTO player_matches 
            (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
             winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
             player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
            VALUES (%s, %s, %s, %s, %s, %s, %s, false, true, false, %s, %s, %s, %s, %s, %s)
        """, (match_id, tournament_id, player1_id, player2_id,
              3 if winner_id == player1_id else 0,  # Standard 3-0 walkover score
              3 if winner_id == player2_id else 0,
              winner_id, player1_absent, player2_absent,
              player1_rating, player2_rating, new_rating1, new_rating2))
        
        # Update player ratings and stats
        cursor.execute("""
            UPDATE players SET 
                rating = %s, 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s
            WHERE id = %s
        """, (new_rating1,
              1 if winner_id == player1_id else 0,
              1 if winner_id != player1_id else 0,
              3 if winner_id == player1_id else 0,
              3 if winner_id != player1_id else 0,
              player1_id))
        
        cursor.execute("""
            UPDATE players SET 
                rating = %s, 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s
            WHERE id = %s
        """, (new_rating2,
              1 if winner_id == player2_id else 0,
              1 if winner_id != player2_id else 0,
              3 if winner_id == player2_id else 0,
              3 if winner_id != player2_id else 0,
              player2_id))
        
        # Update tournament stats
        for player_id, goals_scored, goals_conceded, is_winner in [
            (player1_id, 3 if winner_id == player1_id else 0, 3 if winner_id != player1_id else 0, winner_id == player1_id),
            (player2_id, 3 if winner_id == player2_id else 0, 3 if winner_id != player2_id else 0, winner_id == player2_id)
        ]:
            cursor.execute("""
                INSERT INTO player_stats 
                (player_id, tournament_id, matches_played, wins, draws, losses, goals_scored, goals_conceded)
                VALUES (%s, %s, 1, %s, 0, %s, %s, %s)
                ON CONFLICT (player_id, tournament_id)
                DO UPDATE SET
                    matches_played = player_stats.matches_played + 1,
                    wins = player_stats.wins + %s,
                    losses = player_stats.losses + %s,
                    goals_scored = player_stats.goals_scored + %s,
                    goals_conceded = player_stats.goals_conceded + %s
            """, (player_id, tournament_id,
                  1 if is_winner else 0,
                  1 if not is_winner else 0,
                  goals_scored, goals_conceded,
                  1 if is_winner else 0,
                  1 if not is_winner else 0,
                  goals_scored, goals_conceded))
        
        conn.commit()
        return match_id
    
    @staticmethod
    def _record_normal_match(cursor, tournament_id, player1_id, player2_id, player1_goals, player2_goals, conn):
        """Record a normal match with both players present"""
        # Get current ratings, use 300 as base for NULL ratings but don't update yet
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_rating_result = cursor.fetchone()['rating']
        player1_rating = 300 if player1_rating_result is None else player1_rating_result
        player1_is_new = player1_rating_result is None
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_rating_result = cursor.fetchone()['rating']
        player2_rating = 300 if player2_rating_result is None else player2_rating_result
        player2_is_new = player2_rating_result is None
        
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
        
        # Calculate Golden Glove points for each player
        glove_points1 = TournamentDB.calculate_golden_glove_points(
            player1_goals, player2_goals, winner_id == player1_id, is_draw
        )
        glove_points2 = TournamentDB.calculate_golden_glove_points(
            player2_goals, player1_goals, winner_id == player2_id, is_draw
        )
        
        # Update player ratings and stats
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
        """, (new_rating1, 
              1 if winner_id == player1_id else 0,
              1 if is_draw else 0,
              1 if winner_id == player2_id else 0,
              player1_goals, player2_goals,
              1 if player2_goals == 0 else 0,
              glove_points1,
              player1_id))
        
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
        """, (new_rating2, 
              1 if winner_id == player2_id else 0,
              1 if is_draw else 0,
              1 if winner_id == player1_id else 0,
              player2_goals, player1_goals,
              1 if player1_goals == 0 else 0,
              glove_points2,
              player2_id))
        
        # Update tournament stats
        for player_id, goals_scored, goals_conceded, is_winner, glove_points in [
            (player1_id, player1_goals, player2_goals, winner_id == player1_id, glove_points1),
            (player2_id, player2_goals, player1_goals, winner_id == player2_id, glove_points2)
        ]:
            cursor.execute("""
                INSERT INTO player_stats 
                (player_id, tournament_id, matches_played, wins, draws, losses, goals_scored, goals_conceded, clean_sheets, golden_glove_points)
                VALUES (%s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (player_id, tournament_id)
                DO UPDATE SET
                    matches_played = player_stats.matches_played + 1,
                    wins = player_stats.wins + %s,
                    draws = player_stats.draws + %s,
                    losses = player_stats.losses + %s,
                    goals_scored = player_stats.goals_scored + %s,
                    goals_conceded = player_stats.goals_conceded + %s,
                    clean_sheets = player_stats.clean_sheets + %s,
                    golden_glove_points = player_stats.golden_glove_points + %s
            """, (player_id, tournament_id,
                  1 if is_winner else 0,
                  1 if is_draw else 0,
                  1 if not is_winner and not is_draw else 0,
                  goals_scored, goals_conceded,
                  1 if goals_conceded == 0 else 0,
                  glove_points,
                  1 if is_winner else 0,
                  1 if is_draw else 0,
                  1 if not is_winner and not is_draw else 0,
                  goals_scored, goals_conceded,
                  1 if goals_conceded == 0 else 0,
                  glove_points))
        
        conn.commit()
        return match_id
    
    @staticmethod
    def get_player_tournament_stats(tournament_id):
        """Get tournament-specific player statistics"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT p.name, p.photo_url, ps.*, p.rating
                    FROM player_stats ps
                    JOIN players p ON ps.player_id = p.id
                    WHERE ps.tournament_id = %s
                    ORDER BY p.rating DESC, ps.wins DESC, ps.goals_scored DESC
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
    def recalculate_all_ratings():
        """Recalculate all player ratings and stats by replaying matches with enhanced system.
        Steps:
        - Reset players table rating and cumulative stats
        - Clear player_stats (tournament-specific) aggregates
        - Iterate through player_matches ordered by played_at (then match_id) and recompute
        - Update player_matches rating_before/after to the recomputed values
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
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
                
                # 2) Clear tournament-specific aggregates
                cursor.execute("DELETE FROM player_stats")
                
                # 3) Fetch all matches in chronological order
                # Prefer played_at if available, fallback to match_id
                cursor.execute("""
                    SELECT * FROM player_matches
                    ORDER BY played_at ASC NULLS LAST, match_id ASC
                """)
                matches = cursor.fetchall()
                
                for m in matches:
                    p1 = m['player1_id']
                    p2 = m['player2_id']
                    t_id = m['tournament_id']
                    g1 = m['player1_goals']
                    g2 = m['player2_goals']
                    is_walkover = m.get('is_walkover', False)
                    is_null = m.get('is_null_match', False)
                    p1_absent = m.get('player1_absent', False)
                    p2_absent = m.get('player2_absent', False)
                    
                    # Current ratings before this match
                    cursor.execute("SELECT rating FROM players WHERE id = %s", (p1,))
                    r1_before = cursor.fetchone()['rating']
                    cursor.execute("SELECT rating FROM players WHERE id = %s", (p2,))
                    r2_before = cursor.fetchone()['rating']
                    
                    # Recalculate based on type
                    if is_null:
                        # Apply penalty only; do not count match stats
                        NULL_MATCH_PENALTY = 15
                        r1_after = max(0, min(1000, r1_before - NULL_MATCH_PENALTY))
                        r2_after = max(0, min(1000, r2_before - NULL_MATCH_PENALTY))
                        
                        # Update players ratings only
                        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (r1_after, p1))
                        cursor.execute("UPDATE players SET rating = %s WHERE id = %s", (r2_after, p2))
                        
                        # Update match stored ratings
                        cursor.execute("""
                            UPDATE player_matches SET
                                player1_rating_before = %s,
                                player2_rating_before = %s,
                                player1_rating_after = %s,
                                player2_rating_after = %s
                            WHERE match_id = %s
                        """, (r1_before, r2_before, r1_after, r2_after, m['match_id']))
                        continue
                    
                    if is_walkover:
                        # Use basic ELO with 75% factor; goals expected to be 3-0 by record
                        winner_id = m['winner_id']
                        if winner_id == p1:
                            change_w, change_l = TournamentDB.calculate_rating_change(r1_before, r2_before, is_draw=False)
                            change1 = int(change_w * 0.75)
                            change2 = int(change_l * 0.75)
                        else:
                            change_w, change_l = TournamentDB.calculate_rating_change(r2_before, r1_before, is_draw=False)
                            change2 = int(change_w * 0.75)
                            change1 = int(change_l * 0.75)
                        r1_after = max(0, min(1000, r1_before + change1))
                        r2_after = max(0, min(1000, r2_before + change2))
                        
                        # Update match stored ratings
                        cursor.execute("""
                            UPDATE player_matches SET
                                player1_rating_before = %s,
                                player2_rating_before = %s,
                                player1_rating_after = %s,
                                player2_rating_after = %s
                            WHERE match_id = %s
                        """, (r1_before, r2_before, r1_after, r2_after, m['match_id']))
                        
                        # Update cumulative player stats
                        # Determine for each player
                        for pid, rating_after, won, lost, gf, ga in [
                            (p1, r1_after, 1 if winner_id == p1 else 0, 1 if winner_id != p1 else 0, g1, g2),
                            (p2, r2_after, 1 if winner_id == p2 else 0, 1 if winner_id != p2 else 0, g2, g1),
                        ]:
                            cursor.execute("""
                                UPDATE players SET
                                    rating = %s,
                                    matches_played = matches_played + 1,
                                    matches_won = matches_won + %s,
                                    matches_lost = matches_lost + %s,
                                    goals_scored = goals_scored + %s,
                                    goals_conceded = goals_conceded + %s
                                WHERE id = %s
                            """, (rating_after, won, lost, gf, ga, pid))
                            
                            # Update tournament stats
                            cursor.execute("""
                                INSERT INTO player_stats
                                    (player_id, tournament_id, matches_played, wins, draws, losses, goals_scored, goals_conceded)
                                VALUES (%s, %s, 1, %s, 0, %s, %s, %s)
                                ON CONFLICT (player_id, tournament_id)
                                DO UPDATE SET
                                    matches_played = player_stats.matches_played + 1,
                                    wins = player_stats.wins + %s,
                                    losses = player_stats.losses + %s,
                                    goals_scored = player_stats.goals_scored + %s,
                                    goals_conceded = player_stats.goals_conceded + %s
                            """, (pid, t_id, won, lost, gf, ga, won, lost, gf, ga))
                        continue
                    
                    # Normal match: use enhanced system with constant points
                    change1, change2 = TournamentDB.calculate_enhanced_rating_change(
                        r1_before, r2_before, g1, g2, p1_absent, p2_absent
                    )
                    r1_after = max(0, min(1000, r1_before + change1))
                    r2_after = max(0, min(1000, r2_before + change2))
                    
                    # Winner/draw flags from stored row
                    is_draw = m.get('is_draw', False)
                    winner_id = m.get('winner_id')
                    
                    # Update match stored ratings
                    cursor.execute("""
                        UPDATE player_matches SET
                            player1_rating_before = %s,
                            player2_rating_before = %s,
                            player1_rating_after = %s,
                            player2_rating_after = %s
                        WHERE match_id = %s
                    """, (r1_before, r2_before, r1_after, r2_after, m['match_id']))
                    
                    # Update cumulative player stats for both players
                    for pid, rating_after, won, drawn, lost, gf, ga in [
                        (p1, r1_after, 1 if (winner_id == p1) else 0, 1 if is_draw else 0, 1 if (winner_id == p2) else 0, g1, g2),
                        (p2, r2_after, 1 if (winner_id == p2) else 0, 1 if is_draw else 0, 1 if (winner_id == p1) else 0, g2, g1),
                    ]:
                        cursor.execute("""
                            UPDATE players SET
                                rating = %s,
                                matches_played = matches_played + 1,
                                matches_won = matches_won + %s,
                                matches_drawn = matches_drawn + %s,
                                matches_lost = matches_lost + %s,
                                goals_scored = goals_scored + %s,
                                goals_conceded = goals_conceded + %s
                            WHERE id = %s
                        """, (rating_after, won, drawn, lost, gf, ga, pid))
                        
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
                        """, (pid, t_id, won, drawn, lost, gf, ga, won, drawn, lost, gf, ga))
                
                conn.commit()
        except Exception:
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
        """Record a match between a clan member and guest player. Only updates clan member stats."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get clan player details
                clan_player = TournamentDB.get_player_by_id(clan_player_id)
                if not clan_player:
                    raise ValueError("Clan player not found")
                
                # Get next match ID
                cursor.execute("SELECT COALESCE(MAX(match_id), 0) + 1 FROM guest_matches")
                next_match_id = cursor.fetchone()[0]
                
                # Record pre-match rating
                clan_rating_before = clan_player['rating'] or 300
                
                # Determine match result
                is_null_match = clan_absent and guest_absent
                is_walkover = clan_absent or guest_absent
                clan_rating_after = clan_rating_before
                
                # Only update ratings if it's not a null match
                if not is_null_match:
                    # For guest matches, assume guest has a rating of 300 for calculation purposes
                    guest_rating = 300
                    
                    if clan_absent:
                        # Clan member absent - guest wins, clan loses rating
                        rating_change = TournamentDB.calculate_rating_change(guest_rating, clan_rating_before, is_draw=False)[1]
                        clan_rating_after = clan_rating_before + rating_change
                    elif guest_absent:
                        # Guest absent - clan wins
                        rating_change = TournamentDB.calculate_rating_change(clan_rating_before, guest_rating, is_draw=False)[0]
                        clan_rating_after = clan_rating_before + rating_change
                    else:
                        # Normal match - calculate based on goals
                        if clan_goals > guest_goals:
                            rating_change = TournamentDB.calculate_rating_change(clan_rating_before, guest_rating, is_draw=False)[0]
                        elif guest_goals > clan_goals:
                            rating_change = TournamentDB.calculate_rating_change(guest_rating, clan_rating_before, is_draw=False)[1]
                        else:
                            rating_change = TournamentDB.calculate_rating_change(clan_rating_before, guest_rating, is_draw=True)[0]
                        clan_rating_after = clan_rating_before + rating_change
                    
                    # Ensure rating doesn't go below 0
                    clan_rating_after = max(0, clan_rating_after)
                    
                    # Update clan player stats
                    TournamentDB._update_player_stats_for_guest_match(clan_player_id, clan_goals, guest_goals, clan_absent, guest_absent, clan_rating_after)
                
                # Insert guest match record
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
                conn.commit()
                return guest_match_id
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
        """Record multiple matches at once"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
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
                    
                    # Handle absence scenarios
                    is_null_match = player1_absent and player2_absent
                    is_walkover = player1_absent or player2_absent
                    
                    if is_null_match:
                        # Both players absent - null match, no ratings update
                        match_id = TournamentDB._record_bulk_null_match(
                            cursor, tournament_id, player1_id, player2_id
                        )
                    elif is_walkover:
                        # One player absent - walkover win for present player
                        match_id = TournamentDB._record_bulk_walkover_match(
                            cursor, tournament_id, player1_id, player2_id, 
                            player1_absent, player2_absent
                        )
                    else:
                        # Normal match with both players present
                        match_id = TournamentDB._record_bulk_normal_match(
                            cursor, tournament_id, player1_id, player2_id,
                            player1_goals, player2_goals
                        )
                    
                    match_ids.append(match_id)
                
                conn.commit()
                return match_ids
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    @staticmethod
    def _record_bulk_null_match(cursor, tournament_id, player1_id, player2_id):
        """Record a null match in bulk operations where both players are absent"""
        # Get current ratings (for record keeping)
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_rating = cursor.fetchone()['rating']
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_rating = cursor.fetchone()['rating']
        
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
        
        # Update player ratings with penalty - nullified matches count as penalty but not as played matches
        cursor.execute("""
            UPDATE players SET rating = %s WHERE id = %s
        """, (new_rating1, player1_id))
        
        cursor.execute("""
            UPDATE players SET rating = %s WHERE id = %s
        """, (new_rating2, player2_id))
        
        return match_id
    
    @staticmethod
    def _record_bulk_walkover_match(cursor, tournament_id, player1_id, player2_id, player1_absent, player2_absent):
        """Record a walkover match in bulk operations where one player is absent"""
        # Get current ratings
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_rating = cursor.fetchone()['rating']
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_rating = cursor.fetchone()['rating']
        
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
        
        # Record the walkover match
        cursor.execute("""
            INSERT INTO player_matches 
            (match_id, tournament_id, player1_id, player2_id, player1_goals, player2_goals,
             winner_id, is_draw, is_walkover, is_null_match, player1_absent, player2_absent,
             player1_rating_before, player2_rating_before, player1_rating_after, player2_rating_after)
            VALUES (%s, %s, %s, %s, %s, %s, %s, false, true, false, %s, %s, %s, %s, %s, %s)
        """, (match_id, tournament_id, player1_id, player2_id,
              3 if winner_id == player1_id else 0,  # Standard 3-0 walkover score
              3 if winner_id == player2_id else 0,
              winner_id, player1_absent, player2_absent,
              player1_rating, player2_rating, new_rating1, new_rating2))
        
        # Update player ratings and stats
        cursor.execute("""
            UPDATE players SET 
                rating = %s, 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s
            WHERE id = %s
        """, (new_rating1,
              1 if winner_id == player1_id else 0,
              1 if winner_id != player1_id else 0,
              3 if winner_id == player1_id else 0,
              3 if winner_id != player1_id else 0,
              player1_id))
        
        cursor.execute("""
            UPDATE players SET 
                rating = %s, 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s
            WHERE id = %s
        """, (new_rating2,
              1 if winner_id == player2_id else 0,
              1 if winner_id != player2_id else 0,
              3 if winner_id == player2_id else 0,
              3 if winner_id != player2_id else 0,
              player2_id))
        
        # Update tournament stats
        for player_id, goals_scored, goals_conceded, is_winner in [
            (player1_id, 3 if winner_id == player1_id else 0, 3 if winner_id != player1_id else 0, winner_id == player1_id),
            (player2_id, 3 if winner_id == player2_id else 0, 3 if winner_id != player2_id else 0, winner_id == player2_id)
        ]:
            cursor.execute("""
                INSERT INTO player_stats 
                (player_id, tournament_id, matches_played, wins, draws, losses, goals_scored, goals_conceded)
                VALUES (%s, %s, 1, %s, 0, %s, %s, %s)
                ON CONFLICT (player_id, tournament_id)
                DO UPDATE SET
                    matches_played = player_stats.matches_played + 1,
                    wins = player_stats.wins + %s,
                    losses = player_stats.losses + %s,
                    goals_scored = player_stats.goals_scored + %s,
                    goals_conceded = player_stats.goals_conceded + %s
            """, (player_id, tournament_id,
                  1 if is_winner else 0,
                  1 if not is_winner else 0,
                  goals_scored, goals_conceded,
                  1 if is_winner else 0,
                  1 if not is_winner else 0,
                  goals_scored, goals_conceded))
        
        return match_id
    
    @staticmethod
    def _record_bulk_normal_match(cursor, tournament_id, player1_id, player2_id, player1_goals, player2_goals):
        """Record a normal match in bulk operations with both players present"""
        # Get current ratings
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player1_id,))
        player1_rating = cursor.fetchone()['rating']
        
        cursor.execute("SELECT rating FROM players WHERE id = %s", (player2_id,))
        player2_rating = cursor.fetchone()['rating']
        
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
        
        # Update player ratings and stats
        cursor.execute("""
            UPDATE players SET 
                rating = %s, 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_drawn = matches_drawn + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s
            WHERE id = %s
        """, (new_rating1, 
              1 if winner_id == player1_id else 0,
              1 if is_draw else 0,
              1 if winner_id == player2_id else 0,
              player1_goals, player2_goals, player1_id))
        
        cursor.execute("""
            UPDATE players SET 
                rating = %s, 
                matches_played = matches_played + 1,
                matches_won = matches_won + %s,
                matches_drawn = matches_drawn + %s,
                matches_lost = matches_lost + %s,
                goals_scored = goals_scored + %s,
                goals_conceded = goals_conceded + %s
            WHERE id = %s
        """, (new_rating2, 
              1 if winner_id == player2_id else 0,
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
        
        return match_id
    
    @staticmethod
    def get_all_matches(tournament_id=None, limit=None):
        """Get all matches with player details"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT pm.*, 
                           p1.name as player1_name, p2.name as player2_name,
                           t.name as tournament_name
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    JOIN players p2 ON pm.player2_id = p2.id
                    JOIN tournaments t ON pm.tournament_id = t.id
                """
                params = []
                
                if tournament_id:
                    query += " WHERE pm.tournament_id = %s"
                    params.append(tournament_id)
                
                query += " ORDER BY pm.played_at DESC"
                
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                cursor.execute(query, params)
                return cursor.fetchall()
        finally:
            conn.close()
    
    @staticmethod
    def get_match_by_id(match_id):
        """Get a specific match by its ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT pm.*, 
                           p1.name as player1_name, p2.name as player2_name,
                           t.name as tournament_name
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    JOIN players p2 ON pm.player2_id = p2.id
                    JOIN tournaments t ON pm.tournament_id = t.id
                    WHERE pm.match_id = %s
                """, (match_id,))
                return cursor.fetchone()
        finally:
            conn.close()
    
    @staticmethod
    def delete_match(match_id):
        """Delete a match and recalculate player ratings"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Get match details before deletion
                match = TournamentDB.get_match_by_id(match_id)
                if not match:
                    raise ValueError("Match not found")
                
                # Reverse the rating changes
                player1_rating_change = match['player1_rating_after'] - match['player1_rating_before']
                player2_rating_change = match['player2_rating_after'] - match['player2_rating_before']
                
                # Reverse player stats
                cursor.execute("""
                    UPDATE players SET 
                        rating = rating - %s, 
                        matches_played = matches_played - 1,
                        matches_won = matches_won - %s,
                        matches_drawn = matches_drawn - %s,
                        matches_lost = matches_lost - %s,
                        goals_scored = goals_scored - %s,
                        goals_conceded = goals_conceded - %s
                    WHERE id = %s
                """, (player1_rating_change,
                      1 if match['winner_id'] == match['player1_id'] else 0,
                      1 if match['is_draw'] else 0,
                      1 if match['winner_id'] == match['player2_id'] else 0,
                      match['player1_goals'], match['player2_goals'], match['player1_id']))
                
                cursor.execute("""
                    UPDATE players SET 
                        rating = rating - %s, 
                        matches_played = matches_played - 1,
                        matches_won = matches_won - %s,
                        matches_drawn = matches_drawn - %s,
                        matches_lost = matches_lost - %s,
                        goals_scored = goals_scored - %s,
                        goals_conceded = goals_conceded - %s
                    WHERE id = %s
                """, (player2_rating_change,
                      1 if match['winner_id'] == match['player2_id'] else 0,
                      1 if match['is_draw'] else 0,
                      1 if match['winner_id'] == match['player1_id'] else 0,
                      match['player2_goals'], match['player1_goals'], match['player2_id']))
                
                # Delete from tournament stats
                cursor.execute("""
                    UPDATE player_stats SET
                        matches_played = matches_played - 1,
                        wins = wins - %s,
                        draws = draws - %s,
                        losses = losses - %s,
                        goals_scored = goals_scored - %s,
                        goals_conceded = goals_conceded - %s
                    WHERE player_id = %s AND tournament_id = %s
                """, (1 if match['winner_id'] == match['player1_id'] else 0,
                      1 if match['is_draw'] else 0,
                      1 if match['winner_id'] == match['player2_id'] else 0,
                      match['player1_goals'], match['player2_goals'],
                      match['player1_id'], match['tournament_id']))
                
                cursor.execute("""
                    UPDATE player_stats SET
                        matches_played = matches_played - 1,
                        wins = wins - %s,
                        draws = draws - %s,
                        losses = losses - %s,
                        goals_scored = goals_scored - %s,
                        goals_conceded = goals_conceded - %s
                    WHERE player_id = %s AND tournament_id = %s
                """, (1 if match['winner_id'] == match['player2_id'] else 0,
                      1 if match['is_draw'] else 0,
                      1 if match['winner_id'] == match['player1_id'] else 0,
                      match['player2_goals'], match['player1_goals'],
                      match['player2_id'], match['tournament_id']))
                
                # Delete the match
                cursor.execute("DELETE FROM player_matches WHERE match_id = %s", (match_id,))
                
                conn.commit()
        except Exception as e:
            conn.rollback()
            raise
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
        """Get player's rating changes over time"""
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
    def edit_player(player_id, name, rating):
        """Edit player name and rating"""
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
                
                # Update the player
                cursor.execute(
                    "UPDATE players SET name = %s, rating = %s WHERE id = %s",
                    (name.strip(), rating, player_id)
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
    def edit_match(match_id, new_player1_goals, new_player2_goals, player1_absent=False, player2_absent=False):
        """Edit a match and recalculate player ratings"""
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
                
                # First, reverse the old match effects (similar to delete_match)
                old_player1_rating_change = match['player1_rating_after'] - match['player1_rating_before']
                old_player2_rating_change = match['player2_rating_after'] - match['player2_rating_before']
                
                # Only reverse stats if the old match wasn't null
                if not match.get('is_null_match', False):
                    # Reverse player stats for the old match
                    cursor.execute("""
                        UPDATE players SET 
                            rating = rating - %s, 
                            matches_played = matches_played - 1,
                            matches_won = matches_won - %s,
                            matches_drawn = matches_drawn - %s,
                            matches_lost = matches_lost - %s,
                            goals_scored = goals_scored - %s,
                            goals_conceded = goals_conceded - %s
                        WHERE id = %s
                    """, (old_player1_rating_change,
                          1 if match['winner_id'] == match['player1_id'] else 0,
                          1 if match['is_draw'] else 0,
                          1 if match['winner_id'] == match['player2_id'] else 0,
                          match['player1_goals'], match['player2_goals'], match['player1_id']))
                    
                    cursor.execute("""
                        UPDATE players SET 
                            rating = rating - %s, 
                            matches_played = matches_played - 1,
                            matches_won = matches_won - %s,
                            matches_drawn = matches_drawn - %s,
                            matches_lost = matches_lost - %s,
                            goals_scored = goals_scored - %s,
                            goals_conceded = goals_conceded - %s
                        WHERE id = %s
                    """, (old_player2_rating_change,
                          1 if match['winner_id'] == match['player2_id'] else 0,
                          1 if match['is_draw'] else 0,
                          1 if match['winner_id'] == match['player1_id'] else 0,
                          match['player2_goals'], match['player1_goals'], match['player2_id']))
                    
                    # Reverse tournament stats for the old match
                    cursor.execute("""
                        UPDATE player_stats SET
                            matches_played = matches_played - 1,
                            wins = wins - %s,
                            draws = draws - %s,
                            losses = losses - %s,
                            goals_scored = goals_scored - %s,
                            goals_conceded = goals_conceded - %s
                        WHERE player_id = %s AND tournament_id = %s
                    """, (1 if match['winner_id'] == match['player1_id'] else 0,
                          1 if match['is_draw'] else 0,
                          1 if match['winner_id'] == match['player2_id'] else 0,
                          match['player1_goals'], match['player2_goals'],
                          match['player1_id'], match['tournament_id']))
                    
                    cursor.execute("""
                        UPDATE player_stats SET
                            matches_played = matches_played - 1,
                            wins = wins - %s,
                            draws = draws - %s,
                            losses = losses - %s,
                            goals_scored = goals_scored - %s,
                            goals_conceded = goals_conceded - %s
                        WHERE player_id = %s AND tournament_id = %s
                    """, (1 if match['winner_id'] == match['player2_id'] else 0,
                          1 if match['is_draw'] else 0,
                          1 if match['winner_id'] == match['player1_id'] else 0,
                          match['player2_goals'], match['player1_goals'],
                          match['player2_id'], match['tournament_id']))
                
                # Now calculate new match results
                # Get current ratings (after reversal)
                cursor.execute("SELECT rating FROM players WHERE id = %s", (match['player1_id'],))
                current_player1_rating = cursor.fetchone()['rating']
                
                cursor.execute("SELECT rating FROM players WHERE id = %s", (match['player2_id'],))
                current_player2_rating = cursor.fetchone()['rating']
                
                # Calculate new match results
                new_is_draw = new_player1_goals == new_player2_goals
                new_winner_id = None if new_is_draw else (match['player1_id'] if new_player1_goals > new_player2_goals else match['player2_id'])
                
                # Determine new match flags first
                new_is_null_match = player1_absent and player2_absent
                new_is_walkover = player1_absent or player2_absent
                
                # Handle absence scenarios for goals and winner
                if new_is_null_match:
                    # Null match - no goals, no winner, but apply penalty
                    new_player1_goals = 0
                    new_player2_goals = 0
                    new_winner_id = None
                    new_is_draw = False
                    NULL_MATCH_PENALTY = 15
                    new_rating1 = max(0, min(1000, current_player1_rating - NULL_MATCH_PENALTY))
                    new_rating2 = max(0, min(1000, current_player2_rating - NULL_MATCH_PENALTY))
                elif new_is_walkover:
                    # Walkover - set 3-0 score and determine winner
                    winner_id = match['player2_id'] if player1_absent else match['player1_id']
                    new_player1_goals = 0 if player1_absent else 3
                    new_player2_goals = 0 if player2_absent else 3
                    new_winner_id = winner_id
                    new_is_draw = False
                    
                    # Calculate walkover rating changes (75% of normal)
                    if new_winner_id == match['player1_id']:
                        rating_change1, rating_change2 = TournamentDB.calculate_rating_change(
                            current_player1_rating, current_player2_rating, is_draw=False
                        )
                    else:
                        rating_change2, rating_change1 = TournamentDB.calculate_rating_change(
                            current_player2_rating, current_player1_rating, is_draw=False
                        )
                    
                    # Reduce for walkover
                    rating_change1 = int(rating_change1 * 0.75)
                    rating_change2 = int(rating_change2 * 0.75)
                    
                    new_rating1 = max(0, min(1000, current_player1_rating + rating_change1))
                    new_rating2 = max(0, min(1000, current_player2_rating + rating_change2))
                else:
                    # Normal match - use enhanced rating calculation with constant points
                    rating_change1, rating_change2 = TournamentDB.calculate_enhanced_rating_change(
                        current_player1_rating, current_player2_rating, new_player1_goals, new_player2_goals
                    )
                    
                    # Apply rating bounds (0-1000)
                    new_rating1 = max(0, min(1000, current_player1_rating + rating_change1))
                    new_rating2 = max(0, min(1000, current_player2_rating + rating_change2))
                
                # Update the match with new data
                cursor.execute("""
                    UPDATE player_matches SET
                        player1_goals = %s,
                        player2_goals = %s,
                        winner_id = %s,
                        is_draw = %s,
                        is_walkover = %s,
                        is_null_match = %s,
                        player1_absent = %s,
                        player2_absent = %s,
                        player1_rating_before = %s,
                        player2_rating_before = %s,
                        player1_rating_after = %s,
                        player2_rating_after = %s
                    WHERE match_id = %s
                """, (new_player1_goals, new_player2_goals, new_winner_id, new_is_draw,
                      new_is_walkover, new_is_null_match, player1_absent, player2_absent,
                      current_player1_rating, current_player2_rating, new_rating1, new_rating2, match_id))
                
                # Apply new player stats
                cursor.execute("""
                    UPDATE players SET 
                        rating = %s, 
                        matches_played = matches_played + 1,
                        matches_won = matches_won + %s,
                        matches_drawn = matches_drawn + %s,
                        matches_lost = matches_lost + %s,
                        goals_scored = goals_scored + %s,
                        goals_conceded = goals_conceded + %s
                    WHERE id = %s
                """, (new_rating1, 
                      1 if new_winner_id == match['player1_id'] else 0,
                      1 if new_is_draw else 0,
                      1 if new_winner_id == match['player2_id'] else 0,
                      new_player1_goals, new_player2_goals, match['player1_id']))
                
                cursor.execute("""
                    UPDATE players SET 
                        rating = %s, 
                        matches_played = matches_played + 1,
                        matches_won = matches_won + %s,
                        matches_drawn = matches_drawn + %s,
                        matches_lost = matches_lost + %s,
                        goals_scored = goals_scored + %s,
                        goals_conceded = goals_conceded + %s
                    WHERE id = %s
                """, (new_rating2, 
                      1 if new_winner_id == match['player2_id'] else 0,
                      1 if new_is_draw else 0,
                      1 if new_winner_id == match['player1_id'] else 0,
                      new_player2_goals, new_player1_goals, match['player2_id']))
                
                # Update tournament stats with new data
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
                """, (match['player1_id'], match['tournament_id'],
                      1 if new_winner_id == match['player1_id'] else 0,
                      1 if new_is_draw else 0,
                      1 if new_winner_id == match['player2_id'] else 0,
                      new_player1_goals, new_player2_goals,
                      1 if new_winner_id == match['player1_id'] else 0,
                      1 if new_is_draw else 0,
                      1 if new_winner_id == match['player2_id'] else 0,
                      new_player1_goals, new_player2_goals))
                
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
                """, (match['player2_id'], match['tournament_id'],
                      1 if new_winner_id == match['player2_id'] else 0,
                      1 if new_is_draw else 0,
                      1 if new_winner_id == match['player1_id'] else 0,
                      new_player2_goals, new_player1_goals,
                      1 if new_winner_id == match['player2_id'] else 0,
                      1 if new_is_draw else 0,
                      1 if new_winner_id == match['player1_id'] else 0,
                      new_player2_goals, new_player1_goals))
                
                conn.commit()
                return match_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
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
