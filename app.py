from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response, Response
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
            return render_template('admin/admin_login.html', error='Invalid username or password')
    
    return render_template('admin/admin_login.html')

@app.route('/admin/logout')
@no_cache
def admin_logout():
    """Admin logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public_home'))

@app.route('/admin')
@admin_required
@no_cache
def admin_dashboard():
    """Admin dashboard - now the main entry point"""
    # Get statistics for dashboard
    players = TournamentDB.get_all_players(limit=10)
    tournaments = TournamentDB.get_all_tournaments()
    
    # Get awards data
    golden_boot_overall = TournamentDB.get_golden_boot_overall()
    golden_glove_overall = TournamentDB.get_golden_glove_points_overall()
    
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
    
    return render_template('admin/admin_dashboard.html', 
                         players=players,
                         tournaments=tournaments,
                         stats=stats,
                         recent_matches=recent_matches,
                         golden_boot_overall=golden_boot_overall,
                         golden_glove_overall=golden_glove_overall)

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
                    try:
                        # Use dedicated base64 upload function
                        from imagekit_config import upload_player_photo_base64
                        upload_result = upload_player_photo_base64(cropped_image_data, player_name, 0)  # Temp ID, will update
                        if upload_result['success']:
                            photo_url = upload_result['url']
                            photo_file_id = upload_result['file_id']
                        else:
                            flash(f'Cropped photo upload failed: {upload_result["error"]}', 'error')
                            return render_template('admin/add_player.html')
                    except Exception as e:
                        flash(f'Photo processing failed: {str(e)}', 'error')
                        return render_template('admin/add_player.html')
                # Handle regular photo upload if provided (fallback)
                elif photo_file and photo_file.filename:
                    upload_result = upload_player_photo(photo_file, player_name, 0)  # Temp ID, will update
                    if upload_result['success']:
                        photo_url = upload_result['url']
                        photo_file_id = upload_result['file_id']
                    else:
                        flash(f'Photo upload failed: {upload_result["error"]}', 'error')
                        return render_template('admin/add_player.html')
                
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
    
    return render_template('admin/add_player.html')

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
    
    return render_template('admin/bulk_add_players.html')

@app.route('/admin/players')
@admin_required
@no_cache
def view_all_players():
    """View all players with search"""
    search = request.args.get('search', '')
    players = TournamentDB.get_all_players(search=search if search else None)
    return render_template('admin/view_players.html', players=players, search=search)

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
            rating_str = request.form.get('rating', '').strip()
            is_rated = request.form.get('is_rated') == 'on'
            
            # Handle rating based on checkbox state
            if is_rated:
                # Player should have a rating
                if not rating_str:
                    flash('Rating is required when "Player has a rating" is checked', 'error')
                    return render_template('admin/edit_player.html', player=player)
                try:
                    rating = int(rating_str)
                    if rating < 0 or rating > 1000:
                        flash('Rating must be between 0 and 1000', 'error')
                        return render_template('admin/edit_player.html', player=player)
                except ValueError:
                    flash('Rating must be a valid number', 'error')
                    return render_template('admin/edit_player.html', player=player)
            else:
                # Player is unrated
                rating = None
            
            photo_file = request.files.get('photo')
            cropped_image_data = request.form.get('cropped_image_data')
            remove_photo = request.form.get('remove_photo') == 'true'
            
            if not name:
                flash('Player name cannot be empty', 'error')
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
                    # Handle cropped image data (base64) - use dedicated base64 upload function
                    try:
                        # Use dedicated base64 upload function
                        from imagekit_config import upload_player_photo_base64
                        upload_result = upload_player_photo_base64(cropped_image_data, name, player_id)
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
    
    return render_template('admin/edit_player.html', player=player)

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
        tournament_type = request.form.get('tournament_type', 'normal')
        
        if tournament_name:
            try:
                # Create tournament with type
                tournament_id = TournamentDB.create_tournament(tournament_name, tournament_type=tournament_type)
                
                # If division tournament, create divisions
                if tournament_type == 'division':
                    division_names = request.form.getlist('division_name[]')
                    division_ratings = request.form.getlist('division_rating[]')
                    
                    if not division_names or not division_ratings:
                        raise ValueError('Division tournament must have at least one division')
                    
                    # Create each division
                    for div_name, div_rating in zip(division_names, division_ratings):
                        if div_name.strip() and div_rating:
                            TournamentDB.create_division(
                                tournament_id,
                                div_name.strip(),
                                int(div_rating)
                            )
                
                flash(f'Tournament "{tournament_name}" created successfully!', 'success')
                return redirect(url_for('manage_tournament', tournament_id=tournament_id))
            except Exception as e:
                flash(f'Error creating tournament: {str(e)}', 'error')
        else:
            flash('Tournament name cannot be empty', 'error')
    
    return render_template('admin/create_tournament.html')

@app.route('/admin/tournaments')
@admin_required
@no_cache
def manage_tournaments():
    """Manage all tournaments"""
    tournaments = TournamentDB.get_all_tournaments()
    return render_template('admin/manage_tournaments.html', tournaments=tournaments)

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
    
    # Get divisions if it's a division tournament
    divisions = []
    if tournament.get('tournament_type') == 'division':
        divisions = TournamentDB.get_divisions_by_tournament(tournament_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_players':
            player_ids = request.form.getlist('player_ids')
            division_id = request.form.get('division_id')  # For division tournaments
            
            if player_ids:
                try:
                    # For division tournaments, ensure division is selected
                    if tournament.get('tournament_type') == 'division':
                        if not division_id:
                            flash('Please select a division for the players', 'error')
                            return redirect(url_for('manage_tournament', tournament_id=tournament_id))
                        TournamentDB.add_players_to_tournament(tournament_id, [int(pid) for pid in player_ids], int(division_id))
                    else:
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
        elif action == 'assign_division':
            # Action to reassign player to a different division
            player_id = int(request.form.get('player_id'))
            new_division_id = int(request.form.get('new_division_id'))
            try:
                TournamentDB.assign_player_to_division(tournament_id, player_id, new_division_id)
                flash('Player division updated!', 'success')
            except Exception as e:
                flash(f'Error updating player division: {str(e)}', 'error')
        elif action == 'bulk_assign_division':
            # Action to bulk assign multiple players to a division
            player_ids = request.form.getlist('bulk_player_ids')
            bulk_division_id = request.form.get('bulk_division_id')
            
            if not player_ids:
                flash('No players selected', 'error')
            elif not bulk_division_id:
                flash('No division selected', 'error')
            else:
                try:
                    bulk_division_id = int(bulk_division_id)
                    success_count = 0
                    for player_id in player_ids:
                        try:
                            TournamentDB.assign_player_to_division(tournament_id, int(player_id), bulk_division_id)
                            success_count += 1
                        except Exception as e:
                            print(f'Error assigning player {player_id}: {str(e)}')
                    
                    if success_count > 0:
                        flash(f'Successfully assigned {success_count} player(s) to division!', 'success')
                    else:
                        flash('Failed to assign players to division', 'error')
                except Exception as e:
                    flash(f'Error in bulk assignment: {str(e)}', 'error')
        
        return redirect(url_for('manage_tournament', tournament_id=tournament_id))
    
    tournament_players = TournamentDB.get_tournament_players(tournament_id)
    all_players = TournamentDB.get_all_players()
    
    # Get available players (not in tournament)
    tournament_player_ids = {p['id'] for p in tournament_players}
    available_players = [p for p in all_players if p['id'] not in tournament_player_ids]
    
    return render_template('admin/manage_tournament.html', 
                         tournament=tournament, 
                         tournament_players=tournament_players,
                         available_players=available_players,
                         divisions=divisions)

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

@app.route('/admin/tournaments/<int:tournament_id>/edit', methods=['GET', 'POST'])
@admin_required
@no_cache
def edit_tournament(tournament_id):
    """Edit tournament details including name, photo, type, and divisions"""
    tournament = TournamentDB.get_tournament_by_id(tournament_id)
    if not tournament:
        flash('Tournament not found', 'error')
        return redirect(url_for('manage_tournaments'))
    
    divisions = TournamentDB.get_divisions_by_tournament(tournament_id)
    
    if request.method == 'POST':
        action = request.form.get('action', 'update')
        
        # Handle division-related actions
        if action == 'add_division':
            division_name = request.form.get('division_name', '').strip()
            division_starting_rating = request.form.get('division_starting_rating', '').strip()
            
            # Check if this is an AJAX request
            is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                      'application/json' in request.headers.get('Accept', ''))
            
            print(f"\n=== ADD DIVISION DEBUG ===")
            print(f"Division name: {division_name}")
            print(f"Starting rating: {division_starting_rating}")
            print(f"Is AJAX: {is_ajax}")
            print(f"X-Requested-With: {request.headers.get('X-Requested-With')}")
            print(f"Accept: {request.headers.get('Accept')}")
            print(f"========================\n")
            
            if not division_name or not division_starting_rating:
                if is_ajax:
                    return jsonify({'success': False, 'error': 'Division name and starting rating are required'}), 400
                flash('Division name and starting rating are required', 'error')
            else:
                try:
                    starting_rating = int(division_starting_rating)
                    division_id = TournamentDB.create_division(tournament_id, division_name, starting_rating)
                    print(f"Division created with ID: {division_id}")
                    
                    if is_ajax:
                        response_data = {
                            'success': True, 
                            'message': f'Division "{division_name}" added successfully!',
                            'division': {
                                'id': division_id,
                                'name': division_name,
                                'starting_rating': starting_rating
                            }
                        }
                        print(f"Returning JSON response: {response_data}")
                        return jsonify(response_data)
                    flash(f'Division "{division_name}" added successfully!', 'success')
                    return redirect(url_for('edit_tournament', tournament_id=tournament_id))
                except ValueError:
                    if is_ajax:
                        return jsonify({'success': False, 'error': 'Starting rating must be a valid number'}), 400
                    flash('Starting rating must be a valid number', 'error')
                except Exception as e:
                    if is_ajax:
                        return jsonify({'success': False, 'error': str(e)}), 500
                    flash(f'Error creating division: {str(e)}', 'error')
        elif action == 'update_division':
            division_id = request.form.get('division_id')
            division_name = request.form.get('division_name', '').strip()
            division_starting_rating = request.form.get('division_starting_rating', '').strip()
            is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                      'application/json' in request.headers.get('Accept', ''))
            
            if division_id and division_name and division_starting_rating:
                try:
                    starting_rating = int(division_starting_rating)
                    TournamentDB.update_division(int(division_id), division_name, starting_rating)
                    if is_ajax:
                        return jsonify({
                            'success': True,
                            'message': f'Division "{division_name}" updated successfully!',
                            'division': {
                                'id': int(division_id),
                                'name': division_name,
                                'starting_rating': starting_rating
                            }
                        })
                    flash('Division updated successfully!', 'success')
                    return redirect(url_for('edit_tournament', tournament_id=tournament_id))
                except ValueError:
                    if is_ajax:
                        return jsonify({'success': False, 'error': 'Starting rating must be a valid number'}), 400
                    flash('Starting rating must be a valid number', 'error')
                except Exception as e:
                    if is_ajax:
                        return jsonify({'success': False, 'error': str(e)}), 500
                    flash(f'Error updating division: {str(e)}', 'error')
        elif action == 'delete_division':
            division_id = request.form.get('division_id')
            is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                      'application/json' in request.headers.get('Accept', ''))
            
            if division_id:
                try:
                    TournamentDB.delete_division(int(division_id))
                    if is_ajax:
                        return jsonify({'success': True, 'message': 'Division deleted successfully!'})
                    flash('Division deleted successfully!', 'success')
                    return redirect(url_for('edit_tournament', tournament_id=tournament_id))
                except Exception as e:
                    if is_ajax:
                        return jsonify({'success': False, 'error': str(e)}), 500
                    flash(f'Error deleting division: {str(e)}', 'error')
        elif action == 'update':
            # Handle main tournament update
            try:
                name = request.form['name'].strip()
                tournament_type = request.form.get('tournament_type', 'normal')
                photo_file = request.files.get('photo')
                cropped_image_data = request.form.get('cropped_image_data')
                remove_photo = request.form.get('remove_photo') == 'true'
                
                if not name:
                    flash('Tournament name cannot be empty', 'error')
                else:
                    # Handle photo operations first
                    current_photo_file_id = tournament.get('tournament_photo_file_id')
                    tournament_photo_url = tournament.get('tournament_photo_url')
                    tournament_photo_file_id = current_photo_file_id
                    
                    if remove_photo and current_photo_file_id:
                        # Remove current photo
                        try:
                            from imagekit_config import delete_tournament_photo
                            delete_tournament_photo(current_photo_file_id)
                            tournament_photo_url = None
                            tournament_photo_file_id = None
                        except Exception as e:
                            flash(f'Photo removal failed: {str(e)}', 'error')
                    elif cropped_image_data:
                        # Handle cropped image data (base64)
                        try:
                            from imagekit_config import upload_tournament_photo_base64
                            upload_result = upload_tournament_photo_base64(cropped_image_data, name, tournament_id)
                            if upload_result['success']:
                                # Delete old photo if it exists
                                if current_photo_file_id:
                                    try:
                                        from imagekit_config import delete_tournament_photo
                                        delete_tournament_photo(current_photo_file_id)
                                    except:
                                        pass  # Don't fail if old photo deletion fails
                                
                                tournament_photo_url = upload_result['url']
                                tournament_photo_file_id = upload_result['file_id']
                            else:
                                flash(f'Photo upload failed: {upload_result["error"]}', 'error')
                        except Exception as e:
                            flash(f'Photo processing failed: {str(e)}', 'error')
                    elif photo_file and photo_file.filename:
                        # Upload new photo (fallback for direct file upload)
                        try:
                            from imagekit_config import upload_tournament_photo
                            upload_result = upload_tournament_photo(photo_file, name, tournament_id)
                            if upload_result['success']:
                                # Delete old photo if it exists
                                if current_photo_file_id:
                                    try:
                                        from imagekit_config import delete_tournament_photo
                                        delete_tournament_photo(current_photo_file_id)
                                    except:
                                        pass  # Don't fail if old photo deletion fails
                                
                                tournament_photo_url = upload_result['url']
                                tournament_photo_file_id = upload_result['file_id']
                            else:
                                flash(f'Photo upload failed: {upload_result["error"]}', 'error')
                        except Exception as e:
                            flash(f'Photo processing failed: {str(e)}', 'error')
                    
                    # Handle tournament type change
                    old_type = tournament.get('tournament_type', 'normal')
                    if old_type != tournament_type:
                        if tournament_type == 'normal':
                            # Changing from division to normal - remove all divisions and division assignments
                            for division in divisions:
                                TournamentDB.delete_division(division['id'])
                            flash(f'Tournament "{name}" updated successfully! Changed to normal tournament and removed all divisions.', 'success')
                        else:
                            # Changing from normal to division - divisions need to be added separately
                            flash(f'Tournament "{name}" updated successfully! Changed to division tournament. Add divisions below.', 'success')
                    else:
                        flash(f'Tournament "{name}" updated successfully!', 'success')
                    
                    # Update tournament in database
                    TournamentDB.update_tournament(tournament_id, name, tournament_photo_url, tournament_photo_file_id, tournament_type)
                    return redirect(url_for('edit_tournament', tournament_id=tournament_id))
            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                flash(f'Error updating tournament: {str(e)}', 'error')
    
    return render_template('admin/edit_tournament.html', tournament=tournament, divisions=divisions)

@app.route('/admin/tournaments/<int:tournament_id>/delete', methods=['POST'])
@admin_required
@no_cache
def delete_tournament(tournament_id):
    """Delete a tournament and all associated data"""
    try:
        tournament = TournamentDB.get_tournament_by_id(tournament_id)
        if not tournament:
            flash('Tournament not found', 'error')
        else:
            tournament_name = tournament['name']
            photo_file_id = tournament.get('tournament_photo_file_id')
            
            # Delete tournament from database (this will cascade delete related data)
            TournamentDB.delete_tournament(tournament_id)
            
            # Clean up photo if it exists
            if photo_file_id:
                try:
                    from imagekit_config import delete_tournament_photo
                    delete_tournament_photo(photo_file_id)
                except Exception as e:
                    print(f"Warning: Failed to delete photo for tournament {tournament_name}: {e}")
            
            flash(f'Tournament "{tournament_name}" has been deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting tournament: {str(e)}', 'error')
    
    return redirect(url_for('manage_tournaments'))

@app.route('/admin/tournaments/<int:tournament_id>/recalculate', methods=['POST'])
@admin_required
@no_cache
def recalculate_tournament_stats(tournament_id):
    """Recalculate all stats for a specific tournament"""
    try:
        tournament = TournamentDB.get_tournament_by_id(tournament_id)
        if not tournament:
            return jsonify({'success': False, 'error': 'Tournament not found'}), 404
        
        # Call the recalculation method
        result = TournamentDB.recalculate_tournament_ratings(tournament_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message'],
                'players_updated': result.get('players_updated', 0),
                'matches_processed': result.get('matches_processed', 0)
            })
        else:
            return jsonify({'success': False, 'error': 'Recalculation failed'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/tournaments/<int:tournament_id>/recalculation-details', methods=['GET', 'POST'])
@admin_required
@no_cache
def recalculation_details(tournament_id):
    """Show recalculation page - GET shows confirm, POST shows live processing page"""
    try:
        tournament = TournamentDB.get_tournament_by_id(tournament_id)
        if not tournament:
            flash('Tournament not found', 'error')
            return redirect(url_for('manage_tournaments'))
        
        # If GET request, just show the information page
        if request.method == 'GET':
            # Get match count for display
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) as count 
                        FROM player_matches 
                        WHERE tournament_id = %s
                    """, (tournament_id,))
                    match_count = cursor.fetchone()['count']
                    
                    cursor.execute("""
                        SELECT COUNT(DISTINCT player_id) as count
                        FROM tournament_players
                        WHERE tournament_id = %s
                    """, (tournament_id,))
                    player_count = cursor.fetchone()['count']
            finally:
                conn.close()
            
            return render_template('admin/recalculation_confirm.html', 
                                 tournament=tournament,
                                 match_count=match_count,
                                 player_count=player_count)
        
        # If POST request, show the live processing page
        # Get all matches first to show them while processing
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        pm.*,
                        p1.name as player1_name,
                        p2.name as player2_name,
                        tp1.division_id as player1_division_id,
                        tp2.division_id as player2_division_id,
                        d1.name as player1_division,
                        d2.name as player2_division
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    LEFT JOIN players p2 ON pm.player2_id = p2.id
                    LEFT JOIN tournament_players tp1 ON tp1.player_id = p1.id AND tp1.tournament_id = pm.tournament_id
                    LEFT JOIN tournament_players tp2 ON tp2.player_id = p2.id AND tp2.tournament_id = pm.tournament_id
                    LEFT JOIN divisions d1 ON d1.id = tp1.division_id
                    LEFT JOIN divisions d2 ON d2.id = tp2.division_id
                    WHERE pm.tournament_id = %s
                    ORDER BY pm.played_at ASC NULLS LAST, pm.match_id ASC
                """, (tournament_id,))
                matches = cursor.fetchall()
        finally:
            conn.close()
        
        return render_template('admin/recalculation_live.html', 
                             tournament=tournament,
                             matches=matches)
        
    except Exception as e:
        flash(f'Error during recalculation: {str(e)}', 'error')
        return redirect(url_for('manage_tournament', tournament_id=tournament_id))

@app.route('/admin/tournaments/<int:tournament_id>/do-recalculate', methods=['GET'])
@admin_required
@no_cache
def do_recalculate(tournament_id):
    """Stream recalculation progress match by match"""
    import json
    import time
    
    def generate():
        try:
            tournament = TournamentDB.get_tournament_by_id(tournament_id)
            if not tournament:
                yield f"data: {json.dumps({'error': 'Tournament not found'})}\n\n"
                return
            
            conn = get_db_connection()
            
            # Get all players in tournament and their initial ratings
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT player_id, division_id
                    FROM tournament_players
                    WHERE tournament_id = %s
                """, (tournament_id,))
                tournament_players = cursor.fetchall()
            
            # Clear existing tournament stats
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM player_stats WHERE tournament_id = %s", (tournament_id,))
            conn.commit()
            
            # Initialize ratings based on divisions
            is_division = tournament.get('tournament_type') == 'division'
            current_ratings = {}
            
            for tp in tournament_players:
                player_id = tp['player_id']
                if is_division and tp['division_id']:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT starting_rating FROM divisions WHERE id = %s", (tp['division_id'],))
                        div = cursor.fetchone()
                        current_ratings[player_id] = div['starting_rating'] if div else 300
                else:
                    current_ratings[player_id] = 300
            
            # Get all matches
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT pm.*, p1.name as player1_name, p2.name as player2_name
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    LEFT JOIN players p2 ON pm.player2_id = p2.id
                    WHERE pm.tournament_id = %s
                    ORDER BY pm.played_at ASC NULLS LAST, pm.match_id ASC
                """, (tournament_id,))
                matches = cursor.fetchall()
            
            total = len(matches)
            yield f"data: {json.dumps({'type': 'start', 'total': total, 'initial_ratings': current_ratings})}\n\n"
            
            # Process each match
            for index, match in enumerate(matches):
                p1_id = match['player1_id']
                p2_id = match['player2_id']
                g1 = match['player1_goals']
                g2 = match['player2_goals']
                is_walkover = match.get('is_walkover', False)
                is_null = match.get('is_null_match', False)
                is_draw = match.get('is_draw', False)
                winner_id = match.get('winner_id')
                p1_absent = match.get('player1_absent', False)
                p2_absent = match.get('player2_absent', False)
                
                # Get current ratings
                p1_rating_before = current_ratings.get(p1_id, 300)
                p2_rating_before = current_ratings.get(p2_id, 300) if p2_id else 0
                
                # Calculate rating changes
                if is_null:
                    NULL_PENALTY = 15
                    p1_rating_after = max(0, min(1000, p1_rating_before - NULL_PENALTY))
                    p2_rating_after = max(0, min(1000, p2_rating_before - NULL_PENALTY)) if p2_id else 0
                elif is_walkover:
                    if winner_id == p1_id:
                        change_w, change_l = TournamentDB.calculate_rating_change(p1_rating_before, p2_rating_before, False)
                        change1, change2 = int(change_w * 0.75), int(change_l * 0.75)
                    else:
                        change_w, change_l = TournamentDB.calculate_rating_change(p2_rating_before, p1_rating_before, False)
                        change2, change1 = int(change_w * 0.75), int(change_l * 0.75)
                    p1_rating_after = max(0, min(1000, p1_rating_before + change1))
                    p2_rating_after = max(0, min(1000, p2_rating_before + change2)) if p2_id else 0
                else:
                    change1, change2 = TournamentDB.calculate_enhanced_rating_change(
                        p1_rating_before, p2_rating_before, g1, g2, p1_absent, p2_absent
                    )
                    p1_rating_after = max(0, min(1000, p1_rating_before + change1))
                    p2_rating_after = max(0, min(1000, p2_rating_before + change2)) if p2_id else 0
                
                # Update current ratings
                current_ratings[p1_id] = p1_rating_after
                if p2_id:
                    current_ratings[p2_id] = p2_rating_after
                
                # Update match record
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE player_matches SET
                            player1_rating_before = %s,
                            player2_rating_before = %s,
                            player1_rating_after = %s,
                            player2_rating_after = %s
                        WHERE id = %s
                    """, (p1_rating_before, p2_rating_before, p1_rating_after, p2_rating_after, match['id']))
                conn.commit()
                
                # Update stats if not null
                if not is_null:
                    for pid, rating_after, won, drawn, lost, gf, ga in [
                        (p1_id, p1_rating_after, 1 if winner_id == p1_id else 0, 1 if is_draw else 0, 1 if winner_id == p2_id else 0, g1, g2),
                        (p2_id, p2_rating_after, 1 if winner_id == p2_id else 0, 1 if is_draw else 0, 1 if winner_id == p1_id else 0, g2, g1) if p2_id else None
                    ]:
                        if pid:
                            glove_points = 0 if is_walkover else TournamentDB.calculate_golden_glove_points(gf, ga, winner_id == pid, is_draw)
                            with conn.cursor() as cursor:
                                cursor.execute("""
                                    INSERT INTO player_stats (player_id, tournament_id, tournament_rating, matches_played, wins, draws, losses, goals_scored, goals_conceded, clean_sheets, golden_glove_points)
                                    VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (player_id, tournament_id) DO UPDATE SET
                                        tournament_rating = %s, matches_played = player_stats.matches_played + 1,
                                        wins = player_stats.wins + %s, draws = player_stats.draws + %s, losses = player_stats.losses + %s,
                                        goals_scored = player_stats.goals_scored + %s, goals_conceded = player_stats.goals_conceded + %s,
                                        clean_sheets = player_stats.clean_sheets + %s, golden_glove_points = player_stats.golden_glove_points + %s
                                """, (pid, tournament_id, rating_after, won, drawn, lost, gf, ga, 1 if ga == 0 else 0, glove_points,
                                      rating_after, won, drawn, lost, gf, ga, 1 if ga == 0 else 0, glove_points))
                            conn.commit()
                
                # Send progress update
                match_data = {
                    'index': index,
                    'player1_name': match['player1_name'],
                    'player2_name': match.get('player2_name'),
                    'player1_goals': g1,
                    'player2_goals': g2,
                    'player1_rating_before': float(p1_rating_before),
                    'player1_rating_after': float(p1_rating_after),
                    'player2_rating_before': float(p2_rating_before),
                    'player2_rating_after': float(p2_rating_after),
                    'is_guest_match': match.get('is_guest_match', False),
                    'guest_name': match.get('guest_name')
                }
                
                yield f"data: {json.dumps({'type': 'progress', 'data': match_data})}\n\n"
                time.sleep(0.001)  # Tiny delay for smoother streaming
            
            # Recalculate overall ratings
            for player_id in current_ratings.keys():
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE players SET rating = NULL, matches_played = 0, matches_won = 0, 
                        matches_drawn = 0, matches_lost = 0, goals_scored = 0, goals_conceded = 0,
                        clean_sheets = 0, golden_glove_points = 0 WHERE id = %s
                    """, (player_id,))
                    cursor.execute("""
                        SELECT * FROM player_matches
                        WHERE player1_id = %s OR player2_id = %s
                        ORDER BY played_at ASC NULLS LAST, match_id ASC
                    """, (player_id, player_id))
                    all_matches = cursor.fetchall()
                    
                    overall_rating = 300
                    for pm in all_matches:
                        is_p1 = pm['player1_id'] == player_id
                        rating_change = pm['player1_rating_after'] - pm['player1_rating_before'] if is_p1 else pm['player2_rating_after'] - pm['player2_rating_before']
                        overall_rating += rating_change
                        
                        if not pm.get('is_null_match'):
                            gf = pm['player1_goals'] if is_p1 else pm['player2_goals']
                            ga = pm['player2_goals'] if is_p1 else pm['player1_goals']
                            won = 1 if pm.get('winner_id') == player_id else 0
                            drawn = 1 if pm.get('is_draw') else 0
                            lost = 1 if (not pm.get('is_draw') and pm.get('winner_id') != player_id) else 0
                            glove = 0 if pm.get('is_walkover') else TournamentDB.calculate_golden_glove_points(gf, ga, pm.get('winner_id') == player_id, pm.get('is_draw'))
                            
                            cursor.execute("""
                                UPDATE players SET rating = %s, matches_played = matches_played + 1,
                                matches_won = matches_won + %s, matches_drawn = matches_drawn + %s, matches_lost = matches_lost + %s,
                                goals_scored = goals_scored + %s, goals_conceded = goals_conceded + %s,
                                clean_sheets = clean_sheets + %s, golden_glove_points = golden_glove_points + %s
                                WHERE id = %s
                            """, (overall_rating, won, drawn, lost, gf, ga, 1 if ga == 0 else 0, glove, player_id))
                conn.commit()
            
            conn.close()
            
            # Small delay to ensure all progress updates are received
            time.sleep(0.1)
            
            # Send completion message
            yield f"data: {json.dumps({'type': 'complete', 'message': f'Successfully recalculated {total} matches'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

# Match Recording Routes
@app.route('/admin/matches/record', methods=['GET', 'POST'])
@admin_required
@no_cache
def record_match():
    """Record a 1v1 match or guest match"""
    if request.method == 'POST':
        tournament_id = int(request.form['tournament_id'])
        is_guest_match = 'is_guest_match' in request.form
        
        if is_guest_match:
            # Guest match: clan member vs external player
            clan_player_id = int(request.form['player1_id'])
            guest_name = request.form.get('guest_name', '').strip()
            clan_goals = int(request.form.get('player1_goals', 0))
            guest_goals = int(request.form.get('player2_goals', 0))
            clan_absent = 'player1_absent' in request.form
            guest_absent = 'player2_absent' in request.form
            
            if not guest_name:
                flash('Guest player name is required for guest matches', 'error')
            else:
                try:
                    # Get clan player name for messages
                    clan_player = TournamentDB.get_player_by_id(clan_player_id)
                    clan_player_name = clan_player['name'] if clan_player else 'Clan Player'
                    
                    match_id = TournamentDB.record_guest_match(
                        tournament_id, clan_player_id, guest_name, 
                        clan_goals, guest_goals, clan_absent, guest_absent
                    )
                    
                    # Generate appropriate success message
                    if clan_absent and guest_absent:
                        result_msg = "Match nullified - both players absent"
                    elif clan_absent:
                        result_msg = f"Guest {guest_name} wins by walkover - {clan_player_name} absent"
                    elif guest_absent:
                        result_msg = f"{clan_player_name} wins by walkover - {guest_name} absent"
                    else:
                        if clan_goals > guest_goals:
                            result_msg = f"{clan_player_name} beats {guest_name} {clan_goals}-{guest_goals}!"
                        elif guest_goals > clan_goals:
                            result_msg = f"{guest_name} beats {clan_player_name} {guest_goals}-{clan_goals}!"
                        else:
                            result_msg = f"{clan_player_name} draws with {guest_name} {clan_goals}-{guest_goals}!"
                    
                    rating_update_msg = "" if (clan_absent and guest_absent) else f" {clan_player_name}'s rating updated."
                    flash(f'Guest match recorded successfully! {result_msg}{rating_update_msg}', 'success')
                    return redirect(url_for('record_match'))
                except Exception as e:
                    flash(f'Error recording guest match: {str(e)}', 'error')
        else:
            # Regular match between two clan members
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
    return render_template('admin/record_match.html', tournaments=tournaments, selected_tournament_id=selected_tournament_id)

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
    player_awards = TournamentDB.get_player_awards(player_id)
    
    # Get tournament-wise rating breakdown (NEW!)
    tournament_breakdown = TournamentDB.get_player_tournament_breakdown(player_id)
    
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
    
    return render_template('admin/player_details.html',
                         player=player,
                         match_history=match_history,
                         tournament_participation=tournament_participation,
                         rating_history=rating_history,
                         vs_opponents=vs_opponents,
                         total_goals_for=total_goals_for,
                         total_goals_against=total_goals_against,
                         recent_form=recent_form,
                         rating_trend=rating_trend,
                         player_awards=player_awards,
                         tournament_breakdown=tournament_breakdown)

@app.route('/admin/stats')
@admin_required
@no_cache
def view_player_stats():
    """View player statistics"""
    overall_stats = TournamentDB.get_overall_player_stats()
    tournaments = TournamentDB.get_all_tournaments()
    
    # Check for award filter
    award_filter = request.args.get('award')
    
    # Sort overall stats based on award filter
    if award_filter == 'golden_boot':
        overall_stats = sorted(overall_stats, key=lambda x: (x['goals_scored'], x['goals_scored']/max(x['matches_played'], 1)), reverse=True)
    elif award_filter == 'golden_glove':
        # Filter players with at least 4 matches for overall stats, sort by highest Golden Glove points
        qualified_stats = [s for s in overall_stats if s['matches_played'] >= 4]
        unqualified_stats = [s for s in overall_stats if s['matches_played'] < 4]
        qualified_stats = sorted(qualified_stats, key=lambda x: (x.get('golden_glove_points', 0), x.get('golden_glove_points', 0)/max(x['matches_played'], 1)), reverse=True)
        overall_stats = qualified_stats + sorted(unqualified_stats, key=lambda x: (x.get('golden_glove_points', 0), x.get('golden_glove_points', 0)/max(x['matches_played'], 1)), reverse=True)
    else:
        # Default sort by rating (already sorted by database query)
        pass
    
    # Add calculated fields for overall stats
    for stat in overall_stats:
        stat['goals_per_match'] = round(stat['goals_scored'] / max(stat['matches_played'], 1), 1)
        stat['goals_conceded_per_match'] = round(stat['goals_conceded'] / max(stat['matches_played'], 1), 1)
    
    # Get award data
    golden_ball_overall = TournamentDB.get_golden_ball_overall()
    golden_boot_overall = TournamentDB.get_golden_boot_overall()
    golden_glove_overall = TournamentDB.get_golden_glove_points_overall()
    golden_ball_top = TournamentDB.get_golden_ball_top_players(10)
    golden_boot_top = TournamentDB.get_golden_boot_top_players(10)
    golden_glove_top = TournamentDB.get_golden_glove_points_top_players(10)
    
    # Get tournament-specific stats and awards if requested
    tournament_stats = []
    selected_tournament = None
    golden_ball_tournament = None
    golden_boot_tournament = None
    golden_glove_tournament = None
    golden_ball_tournament_top = []
    golden_boot_tournament_top = []
    golden_glove_tournament_top = []
    
    tournament_id = request.args.get('tournament_id')
    if tournament_id:
        try:
            tournament_id = int(tournament_id)
            selected_tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
            if selected_tournament:
                tournament_stats = TournamentDB.get_player_tournament_stats(tournament_id)
                # Sort based on award filter
                if award_filter == 'golden_boot':
                    tournament_stats = sorted(tournament_stats, key=lambda x: (x['goals_scored'], x['goals_scored']/max(x['matches_played'], 1)), reverse=True)
                elif award_filter == 'golden_glove':
                    # Filter players with at least 3 matches for tournament stats, sort by highest Golden Glove points
                    qualified_stats = [s for s in tournament_stats if s['matches_played'] >= 3]
                    unqualified_stats = [s for s in tournament_stats if s['matches_played'] < 3]
                    qualified_stats = sorted(qualified_stats, key=lambda x: (x.get('golden_glove_points', 0), x.get('golden_glove_points', 0)/max(x['matches_played'], 1)), reverse=True)
                    tournament_stats = qualified_stats + sorted(unqualified_stats, key=lambda x: (x.get('golden_glove_points', 0), x.get('golden_glove_points', 0)/max(x['matches_played'], 1)), reverse=True)
                else:
                    # Default sort by tournament rating (or overall rating if no tournament rating)
                    tournament_stats = sorted(tournament_stats, key=lambda x: (x.get('tournament_rating') or x.get('rating') or 0, x['wins'], x['goals_scored']), reverse=True)
                
                # Add calculated fields
                for stat in tournament_stats:
                    stat['goals_per_match'] = round(stat['goals_scored'] / max(stat['matches_played'], 1), 1)
                    stat['goals_conceded_per_match'] = round(stat['goals_conceded'] / max(stat['matches_played'], 1), 1)
                golden_ball_tournament = TournamentDB.get_golden_ball_tournament(tournament_id)
                golden_boot_tournament = TournamentDB.get_golden_boot_tournament(tournament_id)
                golden_glove_tournament = TournamentDB.get_golden_glove_points_tournament(tournament_id)
                golden_ball_tournament_top = TournamentDB.get_golden_ball_top_players(10, tournament_id)
                golden_boot_tournament_top = TournamentDB.get_golden_boot_top_players(10, tournament_id)
                golden_glove_tournament_top = TournamentDB.get_golden_glove_points_top_players(10, tournament_id)
        except ValueError:
            pass
    
    return render_template('admin/player_stats.html', 
                         overall_stats=overall_stats,
                         tournaments=tournaments,
                         tournament_stats=tournament_stats,
                         selected_tournament=selected_tournament,
                         award_filter=award_filter,
                         golden_ball_overall=golden_ball_overall,
                         golden_boot_overall=golden_boot_overall,
                         golden_glove_overall=golden_glove_overall,
                         golden_ball_top=golden_ball_top,
                         golden_boot_top=golden_boot_top,
                         golden_glove_top=golden_glove_top,
                         golden_ball_tournament=golden_ball_tournament,
                         golden_boot_tournament=golden_boot_tournament,
                         golden_glove_tournament=golden_glove_tournament,
                         golden_ball_tournament_top=golden_ball_tournament_top,
                         golden_boot_tournament_top=golden_boot_tournament_top,
                         golden_glove_tournament_top=golden_glove_tournament_top)


@app.route('/admin/matches/bulk', methods=['GET', 'POST'])
@admin_required
@no_cache
def bulk_record_matches():
    """Bulk record multiple matches at once"""
    if request.method == 'POST':
        try:
            matches_data = []
            validation_errors = []
            
            # Validate tournament selection
            if 'tournament_id' not in request.form or not request.form['tournament_id']:
                flash('Please select a tournament', 'error')
                tournaments = TournamentDB.get_all_tournaments()
                return render_template('admin/bulk_record_matches.html', tournaments=tournaments)
            
            try:
                tournament_id = int(request.form['tournament_id'])
            except (ValueError, TypeError):
                flash('Invalid tournament selection', 'error')
                tournaments = TournamentDB.get_all_tournaments()
                return render_template('admin/bulk_record_matches.html', tournaments=tournaments)
            
            # Get match count
            try:
                match_count = int(request.form.get('match_count', 0))
            except (ValueError, TypeError):
                match_count = 0
            
            if match_count == 0:
                flash('No matches to record', 'error')
                tournaments = TournamentDB.get_all_tournaments()
                return render_template('admin/bulk_record_matches.html', tournaments=tournaments)
            
            # Validate each match
            for i in range(match_count):
                match_errors = []
                match_number = i + 1
                
                # Get form data with validation
                player1_id = request.form.get(f'match_{i}_player1_id')
                player2_id = request.form.get(f'match_{i}_player2_id')
                player1_goals = request.form.get(f'match_{i}_player1_goals')
                player2_goals = request.form.get(f'match_{i}_player2_goals')
                player1_absent = f'match_{i}_player1_absent' in request.form
                player2_absent = f'match_{i}_player2_absent' in request.form
                is_guest_match = f'match_{i}_is_guest_match' in request.form
                guest_name = request.form.get(f'match_{i}_guest_name', '').strip()
                
                # Validate player1_id
                if not player1_id:
                    match_errors.append('Player 1 is required')
                else:
                    try:
                        player1_id = int(player1_id)
                    except (ValueError, TypeError):
                        match_errors.append('Player 1 selection is invalid')
                        player1_id = None
                
                # Validate based on match type
                if is_guest_match:
                    if not guest_name:
                        match_errors.append('Guest player name is required')
                else:
                    if not player2_id:
                        match_errors.append('Player 2 is required')
                    else:
                        try:
                            player2_id = int(player2_id)
                            if player1_id and player1_id == player2_id:
                                match_errors.append('Players must be different')
                        except (ValueError, TypeError):
                            match_errors.append('Player 2 selection is invalid')
                            player2_id = None
                
                # Validate goals - but consider player absence
                # When players are absent, goals are automatically managed by the system
                if not player1_absent and not player2_absent:
                    # Only validate goals strictly when no one is absent
                    if player1_goals is None or player1_goals == '':
                        match_errors.append('Player 1 goals are required')
                    else:
                        try:
                            player1_goals = int(player1_goals)
                            if player1_goals < 0:
                                match_errors.append('Player 1 goals must be 0 or higher')
                        except (ValueError, TypeError):
                            match_errors.append('Player 1 goals must be a valid number')
                            player1_goals = None
                    
                    if player2_goals is None or player2_goals == '':
                        match_errors.append('Player 2 goals are required')
                    else:
                        try:
                            player2_goals = int(player2_goals)
                            if player2_goals < 0:
                                match_errors.append('Player 2 goals must be 0 or higher')
                        except (ValueError, TypeError):
                            match_errors.append('Player 2 goals must be a valid number')
                            player2_goals = None
                else:
                    # When players are absent, accept any valid numeric goals (walkover/nullified scores)
                    try:
                        player1_goals = int(player1_goals) if player1_goals else 0
                    except (ValueError, TypeError):
                        player1_goals = 0  # Default for absent players
                    
                    try:
                        player2_goals = int(player2_goals) if player2_goals else 0  
                    except (ValueError, TypeError):
                        player2_goals = 0  # Default for absent players
                
                # Add match errors to validation errors list
                if match_errors:
                    for error in match_errors:
                        validation_errors.append(f'Match {match_number}: {error}')
                    continue
                
                # If validation passes, add to matches_data
                matches_data.append({
                    'tournament_id': tournament_id,
                    'player1_id': player1_id,
                    'player2_id': player2_id,
                    'player1_goals': player1_goals,
                    'player2_goals': player2_goals,
                    'player1_absent': player1_absent,
                    'player2_absent': player2_absent,
                    'is_guest_match': is_guest_match,
                    'guest_name': guest_name if is_guest_match else None
                })
            
            # If there are validation errors, show them
            if validation_errors:
                error_message = 'Please fix the following errors:\n' + '\n'.join(validation_errors)
                flash(error_message, 'error')
                tournaments = TournamentDB.get_all_tournaments()
                return render_template('admin/bulk_record_matches.html', tournaments=tournaments)
            
            # If no valid matches, show error
            if not matches_data:
                flash('No valid matches found to record', 'error')
                tournaments = TournamentDB.get_all_tournaments()
                return render_template('admin/bulk_record_matches.html', tournaments=tournaments)
            
            # Process validated matches
            match_ids = []
            regular_matches = []
            processing_errors = []
            
            for i, match_data in enumerate(matches_data):
                try:
                    if match_data.get('is_guest_match', False):
                        # Process guest match
                        guest_match_id = TournamentDB.record_guest_match(
                            match_data['tournament_id'],
                            match_data['player1_id'], 
                            match_data['guest_name'],
                            match_data['player1_goals'],
                            match_data['player2_goals'],
                            match_data['player1_absent'],
                            match_data['player2_absent']
                        )
                        match_ids.append(guest_match_id)
                    else:
                        # Collect regular matches for bulk processing
                        regular_matches.append(match_data)
                except Exception as e:
                    processing_errors.append(f'Match {i+1}: {str(e)}')
            
            # Process regular matches in bulk if any
            if regular_matches:
                try:
                    regular_match_ids = TournamentDB.record_bulk_matches(regular_matches)
                    match_ids.extend(regular_match_ids)
                except Exception as e:
                    processing_errors.append(f'Regular matches processing error: {str(e)}')
            
            # Show results
            if processing_errors:
                error_message = 'Some matches could not be recorded:\n' + '\n'.join(processing_errors)
                flash(error_message, 'error')
            
            if match_ids:
                total_matches = len(match_ids)
                guest_count = sum(1 for match in matches_data if match.get('is_guest_match', False))
                regular_count = total_matches - guest_count
                
                success_msg = f'Successfully recorded {total_matches} match{"es" if total_matches > 1 else ""}!'
                if guest_count > 0 and regular_count > 0:
                    success_msg += f' ({regular_count} regular, {guest_count} guest)'
                elif guest_count > 0:
                    success_msg += f' (all guest matches)'
                success_msg += ' Ratings updated.'
                
                flash(success_msg, 'success')
            elif not processing_errors:  # Only show this if we haven't already shown processing errors
                flash('No matches were recorded', 'error')
                
        except Exception as e:
            flash(f'Error recording matches: {str(e)}', 'error')
        
        return redirect(url_for('bulk_record_matches'))
    
    tournaments = TournamentDB.get_all_tournaments()
    return render_template('admin/bulk_record_matches.html', tournaments=tournaments)

@app.route('/admin/matches')
@admin_required
@no_cache
def manage_matches():
    """View and manage all matches with pagination and search"""
    tournament_id = request.args.get('tournament_id')
    search_query = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    
    # Get per_page from request with default of 25, allow up to 10000 matches
    per_page = int(request.args.get('per_page', 25))
    per_page = max(1, min(per_page, 10000))  # Limit between 1 and 10000
    
    # For search functionality, we'll load more matches than requested
    # This allows client-side search to work across more data
    search_limit = max(per_page, 1000)  # Load at least 1000 matches for search
    
    # Calculate offset for pagination
    offset = (page - 1) * per_page
    
    # Convert tournament_id to int if provided
    tournament_id_int = None
    if tournament_id:
        try:
            tournament_id_int = int(tournament_id)
        except ValueError:
            tournament_id = None
    
    # Get matches - load more for better search functionality
    all_matches = TournamentDB.get_all_matches(
        tournament_id=tournament_id_int, 
        limit=search_limit, 
        offset=0,  # Start from beginning for search
        search_query=None  # Don't filter server-side, we'll do client-side
    )
    
    # For display, we'll use client-side pagination and search
    matches = all_matches
    
    # Get total count for pagination (all matches, not just loaded)
    total_matches = TournamentDB.get_matches_count(
        tournament_id=tournament_id_int,
        search_query=None  # Total count without search filter
    )
    
    # For client-side pagination, we work with loaded matches
    loaded_matches_count = len(matches)
    
    # Calculate pagination info based on total matches
    total_pages = (total_matches + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    # Get tournaments for filter
    tournaments = TournamentDB.get_all_tournaments()
    
    selected_tournament = None
    if tournament_id_int:
        selected_tournament = next((t for t in tournaments if t['id'] == tournament_id_int), None)
    
    return render_template('admin/manage_matches.html', 
                         matches=matches, 
                         tournaments=tournaments,
                         selected_tournament=selected_tournament,
                         current_page=page,
                         total_pages=total_pages,
                         has_prev=has_prev,
                         has_next=has_next,
                         total_matches=total_matches,
                         loaded_matches_count=loaded_matches_count,
                         per_page=per_page,
                         search_query=search_query)

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
            new_guest_name = request.form.get('guest_name', '').strip() or None
            
            TournamentDB.edit_match(match_id, new_player1_goals, new_player2_goals, player1_absent, player2_absent, new_guest_name)
            
            # Generate appropriate success message based on match type
            match_type = match.get('match_type', 'regular')
            if player1_absent and player2_absent:
                result_msg = "Match updated - both players marked absent (nullified)"
            elif player1_absent:
                if match_type == 'guest':
                    result_msg = "Guest match updated - clan player absent (guest wins walkover)"
                else:
                    result_msg = "Match updated - walkover win assigned"
            elif player2_absent:
                if match_type == 'guest':
                    result_msg = "Guest match updated - guest absent (clan player wins walkover)"
                else:
                    result_msg = "Match updated - walkover win assigned"
            else:
                if match_type == 'guest':
                    result_msg = "Guest match updated successfully!"
                else:
                    result_msg = "Match updated successfully!"
            
            if match_type == 'guest':
                flash(f'{result_msg} Clan member rating has been recalculated.', 'success')
            else:
                flash(f'{result_msg} Player ratings have been recalculated.', 'success')
            return redirect(url_for('manage_matches'))
        except Exception as e:
            flash(f'Error updating match: {str(e)}', 'error')
    
    return render_template('admin/edit_match.html', match=match)

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

@app.route('/admin/matches/bulk-delete', methods=['POST'])
@admin_required
@no_cache
def bulk_delete_matches():
    """Bulk delete selected matches"""
    try:
        match_ids = request.form.getlist('match_ids')
        if not match_ids:
            flash('No matches selected for deletion.', 'error')
            return redirect(url_for('manage_matches'))
        
        deleted_count = 0
        errors = []
        
        for match_id in match_ids:
            try:
                TournamentDB.delete_match(int(match_id))
                deleted_count += 1
            except Exception as e:
                errors.append(f'Match #{match_id}: {str(e)}')
        
        if deleted_count > 0:
            flash(f'Successfully deleted {deleted_count} match{"es" if deleted_count > 1 else ""}! Player ratings have been recalculated.', 'success')
        
        if errors:
            flash(f'Errors occurred: {"; ".join(errors)}', 'error')
    
    except Exception as e:
        flash(f'Error during bulk delete: {str(e)}', 'error')
    
    return redirect(url_for('manage_matches'))

# API Routes for dynamic loading
@app.route('/api/tournament/<int:tournament_id>/players')
@admin_required
def get_tournament_players_api(tournament_id):
    """Get players in tournament (for dropdowns) with division info and tournament rating"""
    players = TournamentDB.get_tournament_players(tournament_id)
    return jsonify([
        {
            'id': p['id'], 
            'name': p['name'], 
            'rating': p.get('display_rating') or p['rating'] or 'Unrated',
            'tournament_rating': p.get('tournament_rating'),
            'overall_rating': p['rating'],
            'division_id': p.get('division_id'),
            'division_name': p.get('division_name')
        } for p in players
    ])

# Public Routes (No Authentication Required)
@app.route('/')  # Root URL now shows public homepage
@app.route('/public')
@no_cache
def public_home():
    """Public homepage with tournament overview"""
    try:
        # Get basic statistics
        players = TournamentDB.get_all_players(limit=5)
        tournaments = TournamentDB.get_all_tournaments()
        
        # Get awards data
        golden_boot_overall = TournamentDB.get_golden_boot_overall()
        golden_glove_overall = TournamentDB.get_golden_glove_points_overall()
        golden_ball_overall = TournamentDB.get_golden_ball_overall() if hasattr(TournamentDB, 'get_golden_ball_overall') else None
        
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
                active_tournaments = [t for t in tournaments if t['status'] == 'active']
                
                # Total matches
                cursor.execute("SELECT COUNT(*) as count FROM player_matches")
                total_matches = cursor.fetchone()['count']
                
                # Average rating
                cursor.execute("SELECT AVG(rating) as avg_rating FROM players")
                avg_rating_result = cursor.fetchone()
                average_rating = int(avg_rating_result['avg_rating']) if avg_rating_result['avg_rating'] else 300
                
                # Recent matches for activity feed
                cursor.execute("""
                    SELECT pm.*, p1.name as player1_name, p2.name as player2_name, t.name as tournament_name
                    FROM player_matches pm
                    JOIN players p1 ON pm.player1_id = p1.id
                    LEFT JOIN players p2 ON pm.player2_id = p2.id
                    JOIN tournaments t ON pm.tournament_id = t.id
                    ORDER BY pm.played_at DESC
                    LIMIT 10
                """)
                recent_matches = cursor.fetchall()
        except Exception as e:
            total_players = len(players)
            total_tournaments = len(tournaments)
            active_tournaments = [t for t in tournaments if t['status'] == 'active']
            total_matches = 0
            average_rating = 300
            recent_matches = []
        finally:
            conn.close()
        
        # Create stats object
        stats = {
            'total_players': total_players,
            'total_tournaments': total_tournaments,
            'active_tournaments': len(active_tournaments),
            'total_matches': total_matches,
            'average_rating': average_rating
        }
        
        return render_template('public_home.html',
                             top_players=players,
                             tournaments=tournaments,
                             stats=stats,
                             recent_matches=recent_matches,
                             active_tournaments=active_tournaments,
                             golden_boot_overall=golden_boot_overall,
                             golden_glove_overall=golden_glove_overall,
                             golden_ball_overall=golden_ball_overall)
    except Exception as e:
        return f"Error loading public homepage: {str(e)}", 500

@app.route('/public/rankings')
@no_cache
def public_rankings():
    """Public player rankings page"""
    try:
        search = request.args.get('search', '')
        award_filter = request.args.get('award')
        scope = request.args.get('scope', 'overall')  # overall, or tournament_id
        
        # Get tournaments for the filter tabs
        tournaments = TournamentDB.get_all_tournaments()
        
        # Get player statistics based on scope
        if scope == 'overall':
            players_stats = TournamentDB.get_overall_player_stats()
        else:
            # Try to get tournament-specific stats
            try:
                tournament_id = int(scope)
                players_stats = TournamentDB.get_player_tournament_stats(tournament_id)
                # Do NOT fall back to overall stats if tournament has no players
                # Tournament-specific stats will be empty list if no data exists
                # (no fallback needed, keep the empty list)
            except (ValueError, TypeError):
                # Fallback to overall if invalid tournament id
                players_stats = TournamentDB.get_overall_player_stats()
                scope = 'overall'
        
        # Sort based on award filter FIRST (this determines the ranking order)
        if award_filter == 'golden_boot':
            players_stats = sorted(players_stats, key=lambda x: (x['goals_scored'], x['goals_scored']/max(x['matches_played'], 1)), reverse=True)
        elif award_filter == 'golden_glove':
            qualified_stats = [s for s in players_stats if s['matches_played'] >= 4]
            unqualified_stats = [s for s in players_stats if s['matches_played'] < 4]
            qualified_stats = sorted(qualified_stats, key=lambda x: (x.get('golden_glove_points', 0), x.get('golden_glove_points', 0)/max(x['matches_played'], 1)), reverse=True)
            players_stats = qualified_stats + sorted(unqualified_stats, key=lambda x: (x.get('golden_glove_points', 0), x.get('golden_glove_points', 0)/max(x['matches_played'], 1)), reverse=True)
        else:
            # Sort by tournament_rating for tournament-specific view, overall rating for overall view
            if scope != 'overall':
                # Tournament-specific: sort by tournament_rating
                players_stats = sorted(players_stats, key=lambda x: (x.get('tournament_rating') if x.get('tournament_rating') is not None else -1, x['wins'], x['goals_scored']), reverse=True)
            # else: players are already sorted by overall rating (default)
        
        # Assign ranking AFTER sorting is complete (this ranking reflects the current filter combination)
        for i, player in enumerate(players_stats):
            player['original_rank'] = i + 1
        
        # Apply search filter (preserves ranking but filters display)
        if search:
            players_stats = [s for s in players_stats if search.lower() in s['name'].lower()]
        
        # Find selected tournament for display
        selected_tournament = None
        if scope != 'overall':
            try:
                tournament_id = int(scope)
                selected_tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
            except (ValueError, TypeError):
                pass
        
        return render_template('public_rankings.html',
                             players=players_stats,
                             tournaments=tournaments,
                             search=search,
                             award_filter=award_filter,
                             scope=scope,
                             selected_tournament=selected_tournament)
    except Exception as e:
        return f"Error loading rankings: {str(e)}", 500

@app.route('/public/matches')
@no_cache
def public_matches():
    """Public match results page with pagination and search"""
    try:
        tournament_id = request.args.get('tournament_id')
        page = int(request.args.get('page', 1))
        per_page = 25  # Fixed at 25 matches per page for public view
        
        # Convert tournament_id to int if provided
        selected_tournament_id = None
        if tournament_id:
            try:
                selected_tournament_id = int(tournament_id)
            except ValueError:
                tournament_id = None
        
        # For search functionality, we'll load more matches than displayed
        # This allows client-side search to work across more data
        search_limit = max(per_page, 1000)  # Load at least 1000 matches for search
        
        # Calculate offset for pagination
        offset = (page - 1) * per_page
        
        # Get matches - load more for better search functionality
        matches = TournamentDB.get_all_matches(
            tournament_id=selected_tournament_id, 
            limit=search_limit, 
            offset=0,  # Start from beginning for search
            search_query=None  # Don't filter server-side, we'll do client-side
        )
        
        tournaments = TournamentDB.get_all_tournaments()
        
        # Get total count for pagination (all matches, not just loaded)
        total_matches = TournamentDB.get_matches_count(
            tournament_id=selected_tournament_id,
            search_query=None  # Total count without search filter
        )
        
        # For client-side pagination, we work with loaded matches
        loaded_matches_count = len(matches)
        
        # Calculate pagination info based on total matches
        total_pages = (total_matches + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        # Find selected tournament
        selected_tournament = None
        if selected_tournament_id:
            selected_tournament = next((t for t in tournaments if t['id'] == selected_tournament_id), None)
        
        # Calculate match statistics
        total_goals = sum(match.get('player1_goals', 0) + match.get('player2_goals', 0) for match in matches)
        avg_goals_per_match = total_goals / len(matches) if matches else 0
        
        # Today's matches
        from datetime import date
        today = date.today()
        today_matches = len([m for m in matches if m.get('played_at') and m['played_at'].date() == today])
        
        # Match outcome statistics
        decisive_matches = len([m for m in matches if m.get('player1_goals', 0) != m.get('player2_goals', 0)])
        draw_matches = len([m for m in matches if m.get('player1_goals', 0) == m.get('player2_goals', 0)])
        walkover_matches = len([m for m in matches if m.get('player1_absent') or m.get('player2_absent')])
        
        # Top scorers from recent matches
        top_scorers = []
        high_scoring_matches = sorted([m for m in matches], key=lambda x: x.get('player1_goals', 0) + x.get('player2_goals', 0), reverse=True)
        
        return render_template('public_matches.html',
                             matches=matches,
                             tournaments=tournaments,
                             selected_tournament=selected_tournament,
                             selected_tournament_id=selected_tournament_id,
                             current_page=page,
                             total_pages=total_pages,
                             has_prev=has_prev,
                             has_next=has_next,
                             total_matches=total_matches,
                             loaded_matches_count=loaded_matches_count,
                             per_page=per_page,
                             total_goals=total_goals,
                             avg_goals_per_match=avg_goals_per_match,
                             today_matches=today_matches,
                             decisive_matches=decisive_matches,
                             draw_matches=draw_matches,
                             walkover_matches=walkover_matches,
                             top_scorers=top_scorers,
                             high_scoring_matches=high_scoring_matches[:6])
    except Exception as e:
        return f"Error loading matches: {str(e)}", 500

@app.route('/public/player/<int:player_id>')
@no_cache
def public_player_profile(player_id):
    """Public player profile page"""
    try:
        player = TournamentDB.get_player_details(player_id)
        if not player:
            return "Player not found", 404
        
        # Get comprehensive player data
        match_history = TournamentDB.get_player_match_history(player_id)
        tournament_participation = TournamentDB.get_player_tournament_participation(player_id)
        rating_history = TournamentDB.get_player_rating_history(player_id)
        vs_opponents = TournamentDB.get_player_vs_opponents(player_id)
        player_awards = TournamentDB.get_player_awards(player_id)
        
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
        
        # Get player's rank
        all_players = TournamentDB.get_overall_player_stats()
        player_rank = None
        for idx, p in enumerate(all_players):
            if p['id'] == player_id:
                player_rank = idx + 1
                break
        
        return render_template('public_player_profile.html',
                             player=player,
                             match_history=match_history,
                             tournament_participation=tournament_participation,
                             rating_history=rating_history,
                             vs_opponents=vs_opponents,
                             total_goals_for=total_goals_for,
                             total_goals_against=total_goals_against,
                             recent_form=recent_form,
                             rating_trend=rating_trend,
                             player_awards=player_awards,
                             player_rank=player_rank)
    except Exception as e:
        return f"Error loading player profile: {str(e)}", 500

@app.route('/public/tournaments')
@no_cache
def public_tournaments():
    """Public tournaments listing page"""
    try:
        tournaments = TournamentDB.get_all_tournaments()
        
        # Calculate tournament statistics
        active_tournaments = [t for t in tournaments if t['status'] == 'active']
        active_count = len(active_tournaments)
        
        # Get additional tournament data
        conn = get_db_connection()
        total_participants = 0
        total_tournament_matches = 0
        
        try:
            with conn.cursor() as cursor:
                # Get participant and match counts for each tournament
                for tournament in tournaments:
                    # Get player count
                    cursor.execute("SELECT COUNT(*) as count FROM tournament_players WHERE tournament_id = %s", (tournament['id'],))
                    tournament['player_count'] = cursor.fetchone()['count']
                    total_participants += tournament['player_count']
                    
                    # Get match count
                    cursor.execute("SELECT COUNT(*) as count FROM player_matches WHERE tournament_id = %s", (tournament['id'],))
                    tournament['match_count'] = cursor.fetchone()['count']
                    total_tournament_matches += tournament['match_count']
                    
                    # Get top player in tournament
                    cursor.execute("""
                        SELECT p.id, p.name, p.rating, p.photo_url
                        FROM players p
                        JOIN tournament_players tp ON p.id = tp.player_id
                        WHERE tp.tournament_id = %s
                        ORDER BY p.rating DESC
                        LIMIT 1
                    """, (tournament['id'],))
                    top_player = cursor.fetchone()
                    if top_player:
                        tournament['top_player_id'] = top_player['id']
                        tournament['top_player_name'] = top_player['name']
                        tournament['top_player_rating'] = top_player['rating']
                        tournament['top_player_photo_url'] = top_player['photo_url']
        finally:
            conn.close()
        
        return render_template('public_tournaments.html',
                             tournaments=tournaments,
                             active_tournaments=active_tournaments,
                             active_count=active_count,
                             total_participants=total_participants,
                             total_tournament_matches=total_tournament_matches)
    except Exception as e:
        return f"Error loading tournaments: {str(e)}", 500

@app.route('/public/tournament/<int:tournament_id>')
@no_cache
def public_tournament_detail(tournament_id):
    """Public tournament detail page"""
    try:
        tournament = TournamentDB.get_tournament_by_id(tournament_id)
        if not tournament:
            return "Tournament not found", 404
        
        # Get tournament data
        tournament_players = TournamentDB.get_tournament_players(tournament_id)
        tournament_matches = TournamentDB.get_all_matches(tournament_id=tournament_id)
        tournament_stats = TournamentDB.get_player_tournament_stats(tournament_id)
        
        # Sort tournament stats by points (wins * 3 + draws)
        tournament_stats = sorted(tournament_stats, key=lambda x: (x['wins'] or 0) * 3 + (x['draws'] or 0), reverse=True)
        
        # Get tournament awards
        golden_ball_tournament = TournamentDB.get_golden_ball_tournament(tournament_id) if hasattr(TournamentDB, 'get_golden_ball_tournament') else None
        golden_boot_tournament = TournamentDB.get_golden_boot_tournament(tournament_id) if hasattr(TournamentDB, 'get_golden_boot_tournament') else None
        golden_glove_tournament = TournamentDB.get_golden_glove_points_tournament(tournament_id) if hasattr(TournamentDB, 'get_golden_glove_points_tournament') else None
        
        # Calculate tournament statistics
        total_goals = sum(match.get('player1_goals', 0) + match.get('player2_goals', 0) for match in tournament_matches)
        avg_goals_per_match = total_goals / len(tournament_matches) if tournament_matches else 0
        
        # Match outcome statistics
        decisive_matches = len([m for m in tournament_matches if m.get('player1_goals', 0) != m.get('player2_goals', 0)])
        draw_matches = len([m for m in tournament_matches if m.get('player1_goals', 0) == m.get('player2_goals', 0)])
        
        return render_template('public_tournament_detail.html',
                             tournament=tournament,
                             tournament_players=tournament_players,
                             tournament_matches=tournament_matches,
                             tournament_stats=tournament_stats,
                             golden_ball_tournament=golden_ball_tournament,
                             golden_boot_tournament=golden_boot_tournament,
                             golden_glove_tournament=golden_glove_tournament,
                             total_goals=total_goals,
                             avg_goals_per_match=avg_goals_per_match,
                             decisive_matches=decisive_matches,
                             draw_matches=draw_matches)
    except Exception as e:
        return f"Error loading tournament details: {str(e)}", 500

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
