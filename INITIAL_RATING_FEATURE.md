# Initial Rating Feature

## Overview
Added an optional `initial_rating` field for players to allow admins to set a custom starting overall rating for players who don't start with a division tournament.

## Purpose
This feature allows admins to set a custom starting overall rating for players who:
- Join late with known skill levels
- Are imported from other systems
- Need a custom initial rating for any reason

## How It Works

### Rating Priority System
When a player plays their first match in a tournament, their starting rating is determined by the following priority:

1. **Division Tournament Starting Rating** (Highest Priority)
   - If the player's first tournament is a division tournament, they use the division's `starting_rating`
   - Example: If assigned to "Division A" with starting_rating=300, they start at 300

2. **Player's Initial Rating** (Medium Priority)
   - If the player's first tournament is NOT a division tournament AND they have an `initial_rating` set, use that
   - Example: If `initial_rating=350` and first tournament is normal, they start at 350

3. **Default Rating** (Lowest Priority)
   - If neither of the above applies, use the default rating of 300
   - Example: No division, no initial_rating → start at 300

### Overall Rating Calculation
- The overall rating is calculated cumulatively from all matches across all tournaments
- It starts from the first tournament's starting rating (following the priority above)
- All subsequent match rating changes are applied cumulatively

## Database Changes

### New Column
- **Table**: `players`
- **Column**: `initial_rating` (INTEGER, nullable)
- **Purpose**: Stores the custom initial overall rating for the player

### Migration
The column was added via database migration in `database.py`:
```python
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
```

## Code Changes

### 1. Database Functions (`database.py`)

#### `add_player()`
```python
def add_player(name, photo_url=None, photo_file_id=None, initial_rating=None):
    """Add a new player with optional photo and initial rating"""
    # ... inserts with initial_rating field
```

#### `edit_player()`
```python
def edit_player(player_id, name, rating, initial_rating=None):
    """Edit player name, rating and initial rating"""
    # ... updates initial_rating field
```

#### `_record_normal_match()` and `_record_walkover_match()`
Updated to check for `initial_rating` when determining default starting ratings:
```python
# Get player's initial_rating if set
cursor.execute("SELECT initial_rating FROM players WHERE id = %s", (player1_id,))
player1_initial = cursor.fetchone()
default_rating1 = player1_initial['initial_rating'] if player1_initial and player1_initial['initial_rating'] is not None else 300
```

### 2. Flask Routes (`app.py`)

#### `add_player()` route
```python
# Get initial rating if provided
initial_rating_str = request.form.get('initial_rating', '').strip()
initial_rating = None
if initial_rating_str:
    try:
        initial_rating = int(initial_rating_str)
        if initial_rating < 0 or initial_rating > 1000:
            flash('Initial rating must be between 0 and 1000', 'error')
            return render_template('admin/add_player.html')
    except ValueError:
        flash('Initial rating must be a valid number', 'error')
        return render_template('admin/add_player.html')

# Add player to database
player_id = TournamentDB.add_player(player_name, photo_url, photo_file_id, initial_rating)
```

#### `edit_player()` route
Similar validation and passing to `TournamentDB.edit_player()`.

### 3. HTML Templates

#### `add_player.html`
Added input field for initial_rating:
```html
<!-- Initial Rating (Optional) -->
<div>
    <label for="initial_rating" class="block text-sm font-medium text-gray-700 mb-2">
        <i class="fas fa-star mr-2"></i>Initial Overall Rating (Optional)
    </label>
    <input type="number" 
           id="initial_rating" 
           name="initial_rating" 
           min="0" 
           max="1000" 
           class="input-focus w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-lg"
           placeholder="300 (default)">
    <p class="text-xs text-gray-500 mt-2">
        <i class="fas fa-info-circle mr-1"></i>Set a custom starting overall rating for this player. Leave empty to use default (300). This only applies if player starts in a non-division tournament.
    </p>
</div>
```

#### `edit_player.html`
Added similar input field with pre-filled value from database.

## Usage Examples

### Example 1: Player Joining Late
A player with known skill joins late. Admin sets `initial_rating=450`.
- First match: Tournament-specific rating starts at 450
- Overall rating starts at 450
- All subsequent matches build on this base

### Example 2: Division Tournament Priority
Player with `initial_rating=400` joins "Division A" (starting_rating=270) first.
- First match: Uses division's 270 (NOT the 400)
- Division tournaments override initial_rating

### Example 3: Normal Tournament with Initial Rating
Player with `initial_rating=350` joins "Normal Tournament 1" first.
- First match: Uses 350 (their initial_rating)
- Overall rating starts at 350

### Example 4: Default Behavior
Player with no initial_rating joins any tournament.
- First match: Uses default 300
- Same as before this feature was added

## Testing

Run the test script to verify functionality:
```bash
python test_initial_rating.py
```

Test results:
- ✓ Player creation with initial_rating
- ✓ Player editing with initial_rating
- ✓ Match recording uses correct initial_rating
- ✓ Default rating (300) used when initial_rating is NULL

## Notes

1. **Validation**: Initial rating must be between 0 and 1000
2. **Optional**: Field is optional and can be left empty
3. **Division Priority**: Division tournament starting ratings always take priority over initial_rating
4. **Overall Rating Only**: This affects only the overall rating calculation, not tournament-specific ratings
5. **Backward Compatible**: Existing players without initial_rating continue to work with default 300

## Future Enhancements

Potential improvements:
1. Bulk set initial_rating for multiple players
2. Import initial ratings from CSV
3. History tracking of initial_rating changes
4. UI to show when initial_rating was used vs division rating
