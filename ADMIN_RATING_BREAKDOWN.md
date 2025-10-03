# Admin Tournament-Wise Rating Breakdown

## Overview
Added a comprehensive **Tournament-Wise Rating Breakdown** section to the admin player details page. This allows admins to understand how a player's rating has changed in each tournament.

## What Was Added

### 1. New Database Function
**File**: `database.py`
**Function**: `get_player_tournament_breakdown(player_id)`

This function retrieves:
- Player's overall rating and match count
- Detailed stats for each tournament the player participated in
- Starting rating, current rating, and rating change for each tournament
- Match statistics (wins, draws, losses, goals, clean sheets)
- Tournament dates (first and last match)

### 2. Updated Admin Route
**File**: `app.py`
**Route**: `/admin/players/<player_id>`

Added `tournament_breakdown` data to the player_details view.

### 3. Enhanced Player Details Template
**File**: `templates/admin/player_details.html`

Added a new section showing:

#### Overall Summary
- Total overall rating
- Number of tournaments participated in
- Total matches across all tournaments

#### Per-Tournament Breakdown
For each tournament, displays:

**Header**:
- Tournament name
- Tournament status (Active/Completed/Archived)
- Current tournament rating (large badge)

**Rating Progress Indicator**:
- Starting rating (300 for first match)
- Visual progress bar showing rating change
- Rating change (+/- points)
- Current tournament rating

**Tournament Statistics**:
- Matches played
- Wins
- Goals scored
- Clean sheets

**Additional Info**:
- Win-Draw-Loss record
- Tournament period (dates)

## Visual Features

### Color Coding
- **Green progress bar**: Positive rating change
- **Red progress bar**: Negative rating change
- **Green/Red text**: Shows gain/loss clearly

### Layout
- Card-based design with hover effects
- Gradient backgrounds for visual appeal
- Icon indicators for different stats
- Responsive grid layout

## Example Display

```
Tournament-Wise Rating Breakdown
================================

Overall Summary:
- Overall Rating: 455
- Total Tournaments: 2
- Total Matches: 11

Division Tour (Active)               Tournament Rating: 452
─────────────────────────────────────────────────────────
Starting Rating: 300 ────► +152 points ────► Current: 452

Stats: 10 Matches | 8 Wins | 28 Goals | 5 Clean Sheets
Record: 8W-1D-1L
Period: Sep 15 - Oct 02, 2025

ESK Derby (Completed)                Tournament Rating: 327
─────────────────────────────────────────────────────────
Starting Rating: 300 ────► +27 points ────► Current: 327

Stats: 1 Match | 1 Win | 3 Goals | 1 Clean Sheet
Record: 1W-0D-0L
Period: Oct 01, 2025
```

## Benefits for Admins

1. **Clear Performance Tracking**: See how a player performed in each specific tournament
2. **Rating Progression**: Understand if a player improved or declined during a tournament
3. **Tournament Comparison**: Compare player performance across different tournaments
4. **Starting Point Clarity**: See that each player starts at 300 in each new tournament
5. **Visual Indicators**: Quick color-coded feedback on performance

## Use Cases

### Scenario 1: Player with Multiple Tournaments
**Jomish Joshy**:
- Division Tour: 452 rating (+152 from 300)
- ESK Derby: 327 rating (+27 from 300)
- Overall: 341 rating

**Admin Understanding**: "Jomish performed excellently in Division Tour but needs improvement in future tournaments."

### Scenario 2: Single Tournament Player
**Hami**:
- Division Tour: 455 rating (+155 from 300)
- Overall: 455 rating (same as tournament)

**Admin Understanding**: "Hami only played in Division Tour, so tournament and overall ratings match perfectly."

### Scenario 3: Declining Performance
**Player X**:
- Tournament 1: 450 rating (+150)
- Tournament 2: 280 rating (-20)
- Overall: 350 rating (average performance)

**Admin Understanding**: "Player X declined significantly in Tournament 2. Needs review or training."

## Access

**URL**: `/admin/players/<player_id>`

**Navigation**: 
1. Login to admin panel
2. Go to "View Players"
3. Click on any player's "View Details" button
4. Scroll to "Tournament-Wise Rating Breakdown" section

## Technical Notes

- Ratings are fetched from `player_stats` table (tournament_rating column)
- Starting rating is determined from first match `rating_before` value
- Rating change is calculated as: current_rating - start_rating
- Color coding automatically applied based on positive/negative change
- Responsive design works on mobile and desktop

## Future Enhancements

Possible additions:
- Match-by-match rating progression chart
- Compare multiple players side-by-side
- Export rating history to CSV
- Rating predictions based on trends
- Tournament difficulty indicators
