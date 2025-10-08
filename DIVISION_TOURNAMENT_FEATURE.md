# Division Tournament Feature

## Overview
The Division Tournament feature allows you to categorize players into different divisions, each with its own starting rating. This provides more flexibility in managing tournaments with players of varying skill levels.

## Tournament Types

### 1. Normal Tournament
- **Default behavior** - All players start with a rating of 300
- Traditional rating system where everyone begins on equal footing
- Ratings adjust based on match results

### 2. Division Tournament (NEW!)
- Players are assigned to divisions (e.g., Division 1, Division 2, Division 3)
- Each division has a custom starting rating
- Players' ratings are calculated based on their division's starting rating
- Perfect for organizing tournaments with multiple skill tiers

## Features

### Creating a Division Tournament
1. Go to **Admin** → **Create Tournament**
2. Select **"Division Tournament"** as the tournament type
3. Click **"Add Division"** to create divisions
4. For each division, enter:
   - Division name (e.g., "Division 1", "Premier Division", etc.)
   - Starting rating (e.g., 300, 270, 240)
5. Create the tournament

### Editing an Existing Tournament
✅ **YES! You can convert existing tournaments to division tournaments**

1. Go to **Admin** → **Manage Tournaments**
2. Click **"Edit Tournament"** on any tournament
3. Change the tournament type from "Normal" to "Division"
4. Add divisions with their starting ratings
5. Save changes

**Important Notes:**
- When converting to a division tournament, existing players won't automatically be assigned to divisions
- You'll need to manually assign players to divisions in the "Manage Tournament" page
- Existing match data and ratings are preserved

### Managing Division Tournaments
1. Go to **Admin** → **Manage Tournament** → Select your division tournament
2. You'll see a **"Tournament Type"** badge showing it's a Division Tournament
3. When adding players:
   - Select a division from the dropdown
   - Players will be assigned to that division
4. Each player's card shows their division and its starting rating

### Match Recording
- When recording matches in a division tournament:
  - **First match**: Player ratings start at their division's starting rating
  - **Subsequent matches**: Ratings continue from their current tournament rating
- Normal tournaments continue to work as before (all start at 300)

## Example Use Case

### Spring Championship - Division Tournament

**Divisions:**
- **Division 1** (Starting Rating: 300) - For experienced players
- **Division 2** (Starting Rating: 270) - For intermediate players  
- **Division 3** (Starting Rating: 240) - For beginners

**Benefits:**
- Fair matchmaking across skill levels
- Separate starting points for different player groups
- Players compete within appropriate skill ranges
- Ratings reflect performance relative to their division

## Technical Details

### Database Changes
- Added `tournament_type` column to tournaments table
- Created `divisions` table to store division information
- Added `division_id` to `tournament_players` table for player-division mapping

### Rating Calculation
- For normal tournaments: Uses default rating of 300
- For division tournaments: Uses division's `starting_rating` for initial matches
- All subsequent matches use the player's current tournament rating
- Overall rating system (ELO + goals/clean sheets) remains unchanged

## UI Indicators
- **Tournament Type Badge**: Shows "Normal Tournament" or "Division Tournament"
- **Division Badge**: Displayed on player cards in division tournaments
- **Division Dropdown**: Appears when adding players to division tournaments
- **Color Coding**: Purple theme for division-related UI elements

## Migration Path
All existing tournaments are automatically treated as "Normal" tournaments. No data is lost or changed. You can:
1. Keep existing tournaments as normal tournaments
2. Convert any tournament to a division tournament
3. Add divisions to new tournaments from the start

## Future Enhancements (Potential)
- Auto-promotion/relegation between divisions based on performance
- Division-specific leaderboards
- Tournament-wide cross-division matches
- Division champions and awards

---

**Created:** 2025-10-08  
**Status:** ✅ Fully Implemented and Ready to Use
