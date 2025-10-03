# Tournament-Wise Ranking System Implementation

## Overview
The system now tracks player rankings on a **per-tournament basis**, allowing each player to have:
- **Separate ratings for each tournament** they participate in
- **Overall cumulative statistics** across all tournaments

## Key Features

### 1. Tournament-Specific Ratings
- Each player starts with a **NULL rating** when added to the system
- When playing their **first match in a tournament**, they start at **300 rating**
- Rating changes are calculated based on match results using the enhanced ELO system
- **Tournament ratings are independent** - a player can have different ratings in different tournaments

### 2. Overall Statistics
- The `players` table maintains **cumulative stats** across all tournaments:
  - Overall rating
  - Total matches played
  - Wins, draws, losses
  - Goals scored/conceded
  - Clean sheets
  - Golden glove points

### 3. Database Structure

#### `players` table
- `rating` - Overall rating across all tournaments
- `matches_played` - Total matches across all tournaments
- `matches_won/drawn/lost` - Cumulative W-D-L record
- Other cumulative statistics

#### `player_stats` table (Tournament-Specific)
- `tournament_rating` - **NEW!** Player's rating in this specific tournament
- `tournament_id` - Which tournament these stats are for
- `matches_played` - Matches in this tournament
- `wins/draws/losses` - W-D-L in this tournament
- Other tournament-specific stats

## How It Works

### First Match in a Tournament
1. Player has **NULL** tournament_rating in `player_stats`
2. System uses **300** as starting rating
3. Match result determines rating change from 300
4. New tournament_rating is saved

### Subsequent Matches
1. System retrieves player's **current tournament_rating**
2. Calculates rating change based on:
   - Match result (win/draw/loss)
   - Goals scored/conceded
   - Clean sheet bonuses
   - Opponent's rating
3. Updates **tournament_rating** in `player_stats`
4. Updates **overall rating** in `players` table

### Example Flow
```
Player A joins "Division Tour" tournament:
- Tournament rating: NULL (not played yet)
- Overall rating: NULL (new player)

Match 1 in Division Tour (vs Player B with 350 rating):
- Starts at: 300 (default)
- Result: Win 3-1
- Rating change: +25
- New tournament rating: 325
- New overall rating: 325

Match 2 in Division Tour (vs Player C with 400 rating):
- Starts at: 325 (previous tournament rating)
- Result: Loss 1-2
- Rating change: -15
- New tournament rating: 310
- New overall rating: 310

Player A joins "ESK Derby" tournament:
- Tournament rating: NULL (first time in this tournament)
- Overall rating: 310 (from previous tournament)

Match 1 in ESK Derby:
- Starts at: 300 (new tournament, starts fresh)
- ... rating calculated independently
```

## Viewing Rankings

### Overall Rankings
- Shows cumulative performance across **all tournaments**
- Uses `rating` from `players` table
- URL: `/public/rankings?scope=overall`

### Tournament-Specific Rankings
- Shows performance in a **specific tournament only**
- Uses `tournament_rating` from `player_stats` table
- URL: `/public/rankings?scope=<tournament_id>`
- Rankings are **independent** of other tournaments

## Files Modified

1. **database.py**
   - Added `tournament_rating` column to `player_stats` table
   - Updated `_record_normal_match()` to track tournament ratings
   - Updated `_record_walkover_match()` to track tournament ratings
   - Updated `get_player_tournament_stats()` to use tournament_rating

2. **app.py**
   - Updated `public_rankings()` to sort by tournament_rating for tournament views
   - Updated sorting logic to handle NULL ratings

3. **templates/public_rankings.html**
   - Updated to display tournament_rating for tournament-specific views
   - Shows "N/A" for players without tournament ratings

## Migration Scripts

### migrate_tournament_rating.py
- Adds `tournament_rating` column to existing database

### recalculate_tournament_ratings.py
- **Recalculates all existing matches** with tournament-wise system
- Resets all ratings and replays matches in chronological order
- Updates both tournament and overall ratings

### test_tournament_wise_ranking.py
- Verifies tournament-wise rankings are working correctly
- Shows side-by-side comparison of tournament vs overall rankings

## Rating Calculation

### Normal Match
```python
# Start with 300 if NULL, else use existing tournament rating
tournament_rating = 300 if current_tournament_rating is None else current_tournament_rating

# Calculate rating change using enhanced ELO system
# Includes: base ELO + goal bonuses + clean sheet bonuses
rating_change = calculate_enhanced_rating_change(...)

# Apply bounds (0-1000)
new_tournament_rating = max(0, min(1000, tournament_rating + rating_change))

# Update both tournament and overall ratings
```

### Walkover Match
- Same logic but with 75% of normal rating change
- Applies to both tournament and overall ratings

### Null Match (Both Absent)
- -15 penalty to both tournament and overall ratings
- No match statistics recorded

## Benefits

1. **Fair Competition**: Players start fresh in each tournament
2. **Historical Accuracy**: Can see how a player performed in specific tournaments
3. **Overall Progress**: Still tracks cumulative performance
4. **Flexibility**: Players can join new tournaments without being disadvantaged by low overall rating
5. **Comparison**: Can compare tournament performance vs overall performance

## Usage Examples

### Check Tournament Rankings
```bash
python test_tournament_wise_ranking.py
```

### Recalculate All Ratings
```bash
python recalculate_tournament_ratings.py
```

### View in Web Interface
1. Go to `/public/rankings`
2. Click on a tournament tab to see tournament-specific rankings
3. Click "Overall" to see cumulative rankings across all tournaments

## Technical Notes

- Tournament ratings are stored separately from overall ratings
- Both are updated simultaneously during match recording
- NULL tournament_rating indicates player hasn't played in that tournament yet
- Rating calculation uses the same enhanced ELO formula for consistency
- Database uses `ON CONFLICT DO UPDATE` for efficient upserts

## Future Enhancements

- Tournament leaderboards with reset options
- Season-based ratings
- Export tournament-specific statistics
- Compare player performance across tournaments
- Tournament difficulty ratings based on average participant rating
