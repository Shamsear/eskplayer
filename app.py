from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from functools import wraps
import os
from datetime import datetime
import time
from dotenv import load_dotenv
from database import TournamentDB, init_db, get_db_connection
from imagekit_config import PhotoManager, upload_player_photo, delete_player_photo

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure session and security
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tournament_secret_key_2024')
app.config['SESSION_TYPE'] = 'filesystem'

# Disable caching in development
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Cache buster for static files
@app.context_processor
def inject_cache_buster():
    def cache_buster(filename):
        # Add timestamp to static file URLs
        return f"{filename}?v={int(time.time())}"
    
    def moment():
        # Simple moment-like function that returns current timestamp
        class MomentObj:
            def timestamp(self):
                return int(time.time())
        return MomentObj()
    
    return dict(cache_buster=cache_buster, moment=moment)

# Decorator to prevent caching
def no_cache(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return decorated_function

# Decorator to require admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin Authentication Routes
@app.route('/admin/login', methods=['GET', 'POST'])
@no_cache
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if TournamentDB.authenticate_admin(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid username or password')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@no_cache
def admin_logout():
    """Admin logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/')
@app.route('/admin')
@admin_required
@no_cache
def admin_dashboard():
    """Admin dashboard - now the main entry point"""
    # Get statistics for dashboard
    players = TournamentDB.get_all_players(limit=10)
    tournaments = TournamentDB.get_all_tournaments()
    
    # Get comprehensive statistics
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Total players
            cursor.execute("SELECT COUNT(*) as count FROM players")
            total_players = cursor.fetchone()['count']
            
            # Total tournaments
            total_tournaments = len(tournaments)
            
            # Active tournaments
            active_tournaments = len([t for t in tournaments if t['status'] == 'active'])
            
            # Total matches
            cursor.execute("SELECT COUNT(*) as count FROM player_matches")
            total_matches = cursor.fetchone()['count']
            
            # Average rating
            cursor.execute("SELECT AVG(rating) as avg_rating FROM players")
            avg_rating_result = cursor.fetchone()
            average_rating = int(avg_rating_result['avg_rating']) if avg_rating_result['avg_rating'] else 300
            
            # Recent matches for activity feed
            cursor.execute("""
                SELECT pm.*, p1.name as player1_name, p2.name as player2_name
                FROM player_matches pm
                JOIN players p1 ON pm.player1_id = p1.id
                JOIN players p2 ON pm.player2_id = p2.id
                ORDER BY pm.played_at DESC
                LIMIT 10
            """)
            recent_matches = cursor.fetchall()
    except Exception as e:
        total_players = len(players)
        total_tournaments = len(tournaments)
        active_tournaments = len([t for t in tournaments if t['status'] == 'active'])
        total_matches = 0
        average_rating = 300
        recent_matches = []
    finally:
        conn.close()
    
    # Create stats object
    stats = {
        'total_players': total_players,
        'total_tournaments': total_tournaments,
        'active_tournaments': active_tournaments,
        'total_matches': total_matches,
        'average_rating': average_rating
    }
    
    return render_template('admin_dashboard.html', 
                         players=players,
                         tournaments=tournaments,
                         stats=stats,
                         recent_matches=recent_matches)

# Player Management Routes
@app.route('/admin/players/add', methods=['GET', 'POST'])
@admin_required
@no_cache
def add_player():
    """Add single player with optional photo"""
    if request.method == 'POST':
        player_name = request.form['name'].strip()
        photo_file = request.files.get('photo')
        cropped_image_data = request.form.get('cropped_image_data')
        
        if player_name:
            try:
                photo_url = None
                photo_file_id = None
                
                # Handle cropped photo upload if provided
                if cropped_image_data:
                    import base64
                    import io
                    
                    try:
                        # Remove data URL prefix if present
                        if cropped_image_data.startswith('data:image/'):
                            cropped_image_data = cropped_image_data.split(',')[1]
                        
                        # Decode base64 image
                        image_data = base64.b64decode(cropped_image_data)
                        
                        # Create a file-like object that works exactly like a Flask upload
                        class MockFileStorage:
                            def __init__(self, data, filename):
                                self.data = io.BytesIO(data)
                                self.filename = filename
                            
                            def read(self, size=-1):
                                return self.data.read(size)
                            
                            def seek(self, pos, whence=0):
                                return self.data.seek(pos, whence)
                            
                            def tell(self):
                                return self.data.tell()
                        
                        # Create mock file object
                        mock_file = MockFileStorage(image_data, f'{player_name.replace(" ", "_").lower()}_cropped.jpg')
                        
                        # Use existing working upload function
                        upload_result = upload_player_photo(mock_file, player_name, 0)  # Temp ID, will update
                        if upload_result['success']:
                            photo_url = upload_result['url']
                            photo_file_id = upload_result['file_id']
                        else:
                            flash(f'Cropped photo upload failed: {upload_result["error"]}', 'error')
                            return render_template('add_player.html')
                    except Exception as e:
                        flash(f'Photo processing failed: {str(e)}', 'error')
                        return render_template('add_player.html')
                # Handle regular photo upload if provided (fallback)
                elif photo_file and photo_file.filename:
                    upload_result = upload_player_photo(photo_file, player_name, 0)  # Temp ID, will update
                    if upload_result['success']:
                        photo_url = upload_result['url']
                        photo_file_id = upload_result['file_id']
                    else:
                        flash(f'Photo upload failed: {upload_result["error"]}', 'error')
                        return render_template('add_player.html')
                
                # Add player to database
                player_id = TournamentDB.add_player(player_name, photo_url, photo_file_id)
                
                # Update ImageKit tags with actual player ID if photo was uploaded
                if photo_file_id:
                    try:
                        # Re-upload with correct player ID in metadata
                        from imagekit_config import imagekit
                        imagekit.update_file_details(photo_file_id, {
                            'custom_metadata': {
                                'player_id': str(player_id),
                                'player_name': player_name
                            }
                        })
                    except Exception as e:
                        print(f"Warning: Could not update photo metadata: {e}")
                
                success_msg = f'Player "{player_name}" added successfully with rating 300!'
                if photo_url:
                    success_msg += ' Photo uploaded.'
                    
                flash(success_msg, 'success')
                return redirect(url_for('add_player'))
            except Exception as e:
                # If player creation failed and photo was uploaded, clean up
                if photo_file_id:
                    try:
                        delete_player_photo(photo_file_id)
                    except:
                        pass
                flash(f'Error adding player: {str(e)}', 'error')
        else:
            flash('Player name cannot be empty', 'error')
    
    return render_template('add_player.html')

@app.route('/admin/players/bulk', methods=['GET', 'POST'])
@admin_required
@no_cache
def bulk_add_players():
    """Bulk add players"""
    if request.method == 'POST':
        players_text = request.form['players'].strip()
        if players_text:
            # Split by newlines and remove empty lines
            player_names = [name.strip() for name in players_text.split('\n') if name.strip()]
            if player_names:
                try:
                    added_players = TournamentDB.add_players_bulk(player_names)
                    flash(f'Successfully added {len(added_players)} players!', 'success')
                    return redirect(url_for('bulk_add_players'))
                except Exception as e:
                    flash(f'Error adding players: {str(e)}', 'error')
            else:
                flash('No valid player names provided', 'error')
        else:
            flash('Please enter player names', 'error')
    
    return render_template('bulk_add_players.html')

@app.route('/admin/players')
@admin_required
@no_cache
def view_all_players():
    """View all players with search"""
    search = request.args.get('search', '')
    players = TournamentDB.get_all_players(search=search if search else None)
    return render_template('view_players.html', players=players, search=search)

@app.route('/admin/players/<int:player_id>/edit', methods=['GET', 'POST'])
@admin_required
@no_cache
def edit_player(player_id):
    """Edit a player's information including photo"""
    player = TournamentDB.get_player_by_id(player_id)
    if not player:
        flash('Player not found', 'error')
        return redirect(url_for('view_all_players'))
    
    if request.method == 'POST':
        try:
            name = request.form['name'].strip()
            rating = int(request.form['rating'])
            photo_file = request.files.get('photo')
            cropped_image_data = request.form.get('cropped_image_data')
            remove_photo = request.form.get('remove_photo') == 'true'
            
            if not name:
                flash('Player name cannot be empty', 'error')
            elif rating < 0 or rating > 1000:
                flash('Rating must be between 0 and 1000', 'error')
            else:
                # Update basic player info first
                TournamentDB.edit_player(player_id, name, rating)
                
                # Handle photo operations
                current_photo_file_id = player.get('photo_file_id')
                
                if remove_photo and current_photo_file_id:
                    # Remove current photo
                    try:
                        delete_player_photo(current_photo_file_id)
                        TournamentDB.update_player_photo(player_id, None, None)
                        flash(f'Player "{name}" updated successfully! Photo removed.', 'success')
                    except Exception as e:
                        flash(f'Player updated but photo removal failed: {str(e)}', 'error')
                elif cropped_image_data:
                    # Handle cropped image data (base64) - use existing working upload function
                    import base64
                    import io
                    
                    try:
                        # Remove data URL prefix if present
                        if cropped_image_data.startswith('data:image/'):
                            cropped_image_data = cropped_image_data.split(',')[1]
                        
                        # Decode base64 image
                        image_data = base64.b64decode(cropped_image_data)
                        
                        # Create a file-like object that works exactly like a Flask upload
                        class MockFileStorage:
                            def __init__(self, data, filename):
                                self.data = io.BytesIO(data)
                                self.filename = filename
                            
                            def read(self, size=-1):
                                return self.data.read(size)
                            
                            def seek(self, pos, whence=0):
                                return self.data.seek(pos, whence)
                            
                            def tell(self):
                                return self.data.tell()
                        
                        # Create mock file object
                        mock_file = MockFileStorage(image_data, f'{name.replace(" ", "_").lower()}_cropped.jpg')
                        
                        # Use existing working upload function
                        upload_result = upload_player_photo(mock_file, name, player_id)
                        if upload_result['success']:
                            # Delete old photo if it exists
                            if current_photo_file_id:
                                try:
                                    delete_player_photo(current_photo_file_id)
                                except:
                                    pass  # Don't fail if old photo deletion fails
                            
                            # Update database with new photo info
                            TournamentDB.update_player_photo(player_id, upload_result['url'], upload_result['file_id'])
                            flash(f'Player "{name}" updated successfully! Cropped photo uploaded.', 'success')
                        else:
                            flash(f'Player updated but photo upload failed: {upload_result["error"]}', 'error')
                    except Exception as e:
                        flash(f'Player updated but photo processing failed: {str(e)}', 'error')
                elif photo_file and photo_file.filename:
                    # Upload new photo (fallback for direct file upload)
                    upload_result = upload_player_photo(photo_file, name, player_id)
                    if upload_result['success']:
                        # Delete old photo if it exists
                        if current_photo_file_id:
                            try:
                                delete_player_photo(current_photo_file_id)
                            except:
                                pass  # Don't fail if old photo deletion fails
                        
                        # Update database with new photo info
                        TournamentDB.update_player_photo(player_id, upload_result['url'], upload_result['file_id'])
                        flash(f'Player "{name}" updated successfully! Photo uploaded.', 'success')
                    else:
                        flash(f'Player updated but photo upload failed: {upload_result["error"]}', 'error')
                else:
                    flash(f'Player "{name}" updated successfully!', 'success')
                
                return redirect(url_for('view_all_players'))
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Error updating player: {str(e)}', 'error')
    
    return render_template('edit_player.html', player=player)

@app.route('/admin/players/<int:player_id>/delete', methods=['POST'])
@admin_required
@no_cache
def delete_player(player_id):
    """Delete a player and cleanup their photo"""
    try:
        player = TournamentDB.get_player_by_id(player_id)
        if not player:
            flash('Player not found', 'error')
        else:
            player_name = player['name']
            photo_file_id = player.get('photo_file_id')
            
            # Delete player from database (returns photo info for cleanup)
            delete_result = TournamentDB.delete_player(player_id)
            
            # Clean up photo if it exists
            if photo_file_id:
                try:
                    delete_player_photo(photo_file_id)
                except Exception as e:
                    print(f"Warning: Failed to delete photo for player {player_name}: {e}")
            
            flash(f'Player "{player_name}" has been deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting player: {str(e)}', 'error')
    
    return redirect(url_for('view_all_players'))

# Tournament Management Routes
@app.route('/admin/tournaments/create', methods=['GET', 'POST'])
@admin_required
@no_cache
def create_tournament():
    """Create new tournament"""
    if request.method == 'POST':
        tournament_name = request.form['name'].strip()
        if tournament_name:
            try:
                tournament_id = TournamentDB.create_tournament(tournament_name)
                flash(f'Tournament "{tournament_name}" created successfully!', 'success')
                return redirect(url_for('manage_tournament', tournament_id=tournament_id))
            except Exception as e:
                flash(f'Error creating tournament: {str(e)}', 'error')
        else:
            flash('Tournament name cannot be empty', 'error')
    
    return render_template('create_tournament.html')

@app.route('/admin/tournaments')
@admin_required
@no_cache
def manage_tournaments():
    """Manage all tournaments"""
    tournaments = TournamentDB.get_all_tournaments()
    return render_template('manage_tournaments.html', tournaments=tournaments)

@app.route('/admin/tournaments/<int:tournament_id>', methods=['GET', 'POST'])
@admin_required
@no_cache
def manage_tournament(tournament_id):
    """Manage specific tournament"""
    tournaments = TournamentDB.get_all_tournaments()
    tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('manage_tournaments'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_players':
            player_ids = request.form.getlist('player_ids')
            if player_ids:
                try:
                    TournamentDB.add_players_to_tournament(tournament_id, [int(pid) for pid in player_ids])
                    flash(f'Added {len(player_ids)} players to tournament!', 'success')
                except Exception as e:
                    flash(f'Error adding players: {str(e)}', 'error')
            else:
                flash('No players selected', 'error')
        elif action == 'remove_player':
            player_id = int(request.form.get('player_id'))
            try:
                TournamentDB.remove_player_from_tournament(tournament_id, player_id)
                flash('Player removed from tournament!', 'success')
            except Exception as e:
                flash(f'Error removing player: {str(e)}', 'error')
        elif action == 'remove_all_players':
            try:
                TournamentDB.remove_all_players_from_tournament(tournament_id)
                flash('All players removed from tournament!', 'success')
            except Exception as e:
                flash(f'Error removing players: {str(e)}', 'error')
        
        return redirect(url_for('manage_tournament', tournament_id=tournament_id))
    
    tournament_players = TournamentDB.get_tournament_players(tournament_id)
    all_players = TournamentDB.get_all_players()
    
    # Get available players (not in tournament)
    tournament_player_ids = {p['id'] for p in tournament_players}
    available_players = [p for p in all_players if p['id'] not in tournament_player_ids]
    
    return render_template('manage_tournament.html', 
                         tournament=tournament, 
                         tournament_players=tournament_players,
                         available_players=available_players)

@app.route('/admin/tournaments/<int:tournament_id>/add-players', methods=['POST'])
@admin_required
@no_cache
def add_players_to_tournament(tournament_id):
    """Add players to tournament"""
    player_ids = request.form.getlist('player_ids')
    if player_ids:
        try:
            TournamentDB.add_players_to_tournament(tournament_id, [int(pid) for pid in player_ids])
            flash(f'Added {len(player_ids)} players to tournament!', 'success')
        except Exception as e:
            flash(f'Error adding players: {str(e)}', 'error')
    else:
        flash('No players selected', 'error')
    
    return redirect(url_for('manage_tournament', tournament_id=tournament_id))

# Match Recording Routes
@app.route('/admin/matches/record', methods=['GET', 'POST'])
@admin_required
@no_cache
def record_match():
    """Record a 1v1 match"""
    if request.method == 'POST':
        tournament_id = int(request.form['tournament_id'])
        player1_id = int(request.form['player1_id'])
        player2_id = int(request.form['player2_id'])
        player1_goals = int(request.form.get('player1_goals', 0))
        player2_goals = int(request.form.get('player2_goals', 0))
        player1_absent = 'player1_absent' in request.form
        player2_absent = 'player2_absent' in request.form
        
        if player1_id == player2_id:
            flash('Cannot record match between same player', 'error')
        else:
            try:
                # Get player names for messages
                player1 = TournamentDB.get_player_by_id(player1_id)
                player2 = TournamentDB.get_player_by_id(player2_id)
                player1_name = player1['name'] if player1 else 'Player 1'
                player2_name = player2['name'] if player2 else 'Player 2'
                
                match_id = TournamentDB.record_match(
                    tournament_id, player1_id, player2_id, player1_goals, player2_goals,
                    player1_absent, player2_absent
                )
                
                # Generate appropriate success message
                if player1_absent and player2_absent:
                    result_msg = "Match nullified - both players absent"
                elif player1_absent:
                    result_msg = f"Walkover win for {player2_name} - {player1_name} absent"
                elif player2_absent:
                    result_msg = f"Walkover win for {player1_name} - {player2_name} absent"
                else:
                    if player1_goals > player2_goals:
                        result_msg = f"{player1_name} wins {player1_goals}-{player2_goals}!"
                    elif player2_goals > player1_goals:
                        result_msg = f"{player2_name} wins {player2_goals}-{player1_goals}!"
                    else:
                        result_msg = f"Draw {player1_goals}-{player2_goals}!"
                
                rating_update_msg = "" if (player1_absent and player2_absent) else " Ratings updated."
                flash(f'Match recorded successfully! {result_msg}{rating_update_msg}', 'success')
                return redirect(url_for('record_match'))
            except Exception as e:
                flash(f'Error recording match: {str(e)}', 'error')
    
    tournaments = TournamentDB.get_all_tournaments()
    # Get tournament_id from URL parameter if provided
    selected_tournament_id = request.args.get('tournament_id')
    return render_template('record_match.html', tournaments=tournaments, selected_tournament_id=selected_tournament_id)

@app.route('/admin/players/<int:player_id>')
@admin_required
@no_cache
def player_details(player_id):
    """View detailed player information"""
    player = TournamentDB.get_player_details(player_id)
    if not player:
        flash('Player not found', 'error')
        return redirect(url_for('view_all_players'))
    
    # Get comprehensive player data
    match_history = TournamentDB.get_player_match_history(player_id)
    tournament_participation = TournamentDB.get_player_tournament_participation(player_id)
    rating_history = TournamentDB.get_player_rating_history(player_id)
    vs_opponents = TournamentDB.get_player_vs_opponents(player_id)
    
    # Calculate additional statistics
    total_goals_for = sum([match['player_goals'] for match in match_history])
    total_goals_against = sum([match['opponent_goals'] for match in match_history])
    
    # Calculate recent form (last 5 matches)
    recent_matches = match_history[:5] if match_history else []
    recent_form = [match['result'] for match in recent_matches]
    
    # Calculate rating trend (last 10 matches)
    rating_trend = []
    if len(rating_history) > 1:
        recent_ratings = rating_history[-11:] if len(rating_history) >= 11 else rating_history
        for i in range(1, len(recent_ratings)):
            rating_change = recent_ratings[i]['rating'] - recent_ratings[i-1]['rating']
            rating_trend.append({
                'match': recent_ratings[i]['event'],
                'change': rating_change,
                'rating': recent_ratings[i]['rating']
            })
    
    return render_template('player_details.html',
                         player=player,
                         match_history=match_history,
                         tournament_participation=tournament_participation,
                         rating_history=rating_history,
                         vs_opponents=vs_opponents,
                         total_goals_for=total_goals_for,
                         total_goals_against=total_goals_against,
                         recent_form=recent_form,
                         rating_trend=rating_trend)

@app.route('/admin/stats')
@admin_required
@no_cache
def view_player_stats():
    """View player statistics"""
    overall_stats = TournamentDB.get_overall_player_stats()
    tournaments = TournamentDB.get_all_tournaments()
    
    # Get tournament-specific stats if requested
    tournament_stats = []
    selected_tournament = None
    tournament_id = request.args.get('tournament_id')
    if tournament_id:
        try:
            tournament_id = int(tournament_id)
            selected_tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
            if selected_tournament:
                tournament_stats = TournamentDB.get_player_tournament_stats(tournament_id)
        except ValueError:
            pass
    
    return render_template('player_stats.html', 
                         overall_stats=overall_stats,
                         tournaments=tournaments,
                         tournament_stats=tournament_stats,
                         selected_tournament=selected_tournament)

@app.route('/admin/matches/bulk', methods=['GET', 'POST'])
@admin_required
@no_cache
def bulk_record_matches():
    """Bulk record multiple matches at once"""
    if request.method == 'POST':
        try:
            matches_data = []
            tournament_id = int(request.form['tournament_id'])
            
            # Get all match data from form
            match_count = int(request.form.get('match_count', 0))
            
            for i in range(match_count):
                player1_id = request.form.get(f'match_{i}_player1_id')
                player2_id = request.form.get(f'match_{i}_player2_id')
                player1_goals = request.form.get(f'match_{i}_player1_goals')
                player2_goals = request.form.get(f'match_{i}_player2_goals')
                
                # Skip incomplete matches
                if not all([player1_id, player2_id, player1_goals is not None, player2_goals is not None]):
                    continue
                
                matches_data.append({
                    'tournament_id': tournament_id,
                    'player1_id': int(player1_id),
                    'player2_id': int(player2_id),
                    'player1_goals': int(player1_goals),
                    'player2_goals': int(player2_goals)
                })
            
            if matches_data:
                match_ids = TournamentDB.record_bulk_matches(matches_data)
                flash(f'Successfully recorded {len(match_ids)} matches! Ratings updated.', 'success')
            else:
                flash('No valid matches to record', 'error')
                
        except Exception as e:
            flash(f'Error recording matches: {str(e)}', 'error')
        
        return redirect(url_for('bulk_record_matches'))
    
    tournaments = TournamentDB.get_all_tournaments()
    return render_template('bulk_record_matches.html', tournaments=tournaments)

@app.route('/admin/matches')
@admin_required
@no_cache
def manage_matches():
    """View and manage all matches"""
    tournament_id = request.args.get('tournament_id')
    matches = TournamentDB.get_all_matches(tournament_id=tournament_id, limit=50)
    tournaments = TournamentDB.get_all_tournaments()
    
    selected_tournament = None
    if tournament_id:
        try:
            tournament_id = int(tournament_id)
            selected_tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
        except ValueError:
            pass
    
    return render_template('manage_matches.html', 
                         matches=matches, 
                         tournaments=tournaments,
                         selected_tournament=selected_tournament)

@app.route('/admin/matches/<int:match_id>/edit', methods=['GET', 'POST'])
@admin_required
@no_cache
def edit_match(match_id):
    """Edit a match"""
    match = TournamentDB.get_match_by_id(match_id)
    if not match:
        flash('Match not found', 'error')
        return redirect(url_for('manage_matches'))
    
    if request.method == 'POST':
        try:
            new_player1_goals = int(request.form.get('player1_goals', 0))
            new_player2_goals = int(request.form.get('player2_goals', 0))
            player1_absent = 'player1_absent' in request.form
            player2_absent = 'player2_absent' in request.form
            
            TournamentDB.edit_match(match_id, new_player1_goals, new_player2_goals, player1_absent, player2_absent)
            
            # Generate appropriate success message
            if player1_absent and player2_absent:
                result_msg = "Match updated - both players marked absent (nullified)"
            elif player1_absent:
                result_msg = "Match updated - walkover win assigned"
            elif player2_absent:
                result_msg = "Match updated - walkover win assigned"
            else:
                result_msg = "Match updated successfully!"
            
            flash(f'{result_msg} Player ratings have been recalculated.', 'success')
            return redirect(url_for('manage_matches'))
        except Exception as e:
            flash(f'Error updating match: {str(e)}', 'error')
    
    return render_template('edit_match.html', match=match)

@app.route('/admin/matches/<int:match_id>/delete', methods=['POST'])
@admin_required
@no_cache
def delete_match(match_id):
    """Delete a match"""
    try:
        TournamentDB.delete_match(match_id)
        flash('Match deleted successfully! Player ratings have been recalculated.', 'success')
    except Exception as e:
        flash(f'Error deleting match: {str(e)}', 'error')
    
    return redirect(url_for('manage_matches'))

# API Routes for dynamic loading
@app.route('/api/tournament/<int:tournament_id>/players')
@admin_required
def get_tournament_players_api(tournament_id):
    """Get players in tournament (for dropdowns)"""
    players = TournamentDB.get_tournament_players(tournament_id)
    return jsonify([{'id': p['id'], 'name': p['name'], 'rating': p['rating']} for p in players])

# Test route to verify app is working
@app.route('/test')
@no_cache
def test():
    """Test route to verify app functionality"""
    return "<h1>App is working! Routes are functional.</h1>"

# Redirect root to admin login if not authenticated
@app.route('/home')
@no_cache
def home():
    """Legacy home page - redirects to admin"""
    return redirect(url_for('admin_dashboard'))

def create_app():
    """Application factory pattern for production deployment"""
    # Initialize database on app creation
    try:
        init_db()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        print("Please ensure your database connection is properly configured.")
    return app

if __name__ == '__main__':
    # For local development only
    import os
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    create_app()
    app.run(debug=debug_mode, port=port, host='0.0.0.0')
