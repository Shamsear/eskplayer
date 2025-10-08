# New Rating System - Documentation

## Overview
The overall rating system has been updated to use a **base rating of 300** with the **average of rating changes from the last 40 matches** added to it.

## How It Works

### Formula
```
Overall Rating = 300 + (Average of rating changes from last 40 matches)
```

### Example
**Player: Ahmed**

Last 40 matches:
- Match 1: 300 → 305 (change: +5)
- Match 2: 305 → 310 (change: +5)
- Match 3: 310 → 308 (change: -2)
- Match 4: 308 → 315 (change: +7)
- ...
- Match 40: 350 → 352 (change: +2)

**Calculation:**
```
Average change = (5 + 5 - 2 + 7 + ... + 2) / 40 = +12
Overall Rating = 300 + 12 = 312
```

## Key Features

### 1. Base Rating Always 300
- All players start from a common baseline of 300
- Makes comparisons fair across divisions

### 2. Rolling Window (Last 40 Matches)
- Only the most recent 40 matches are considered
- When match 41 is played, match 1 is removed from calculation
- Reflects current form, not lifetime performance

### 3. Division Impact
Players in different divisions will have different rating trajectories:

**Division 1 (Starting: 400)**
- Higher starting point → Bigger positive changes
- Average change: +10 to +20
- Overall Rating: **310 - 320**

**Division 3 (Starting: 300)**
- Balanced starting point
- Average change: ±5
- Overall Rating: **295 - 305**

**Division 6 (Starting: 150)**
- Lower starting point → Smaller or negative changes
- Average change: -10 to -5
- Overall Rating: **290 - 295**

### 4. Stats Remain Cumulative
- Goals scored: Total across ALL matches
- Wins/Losses: Total across ALL matches
- Matches played: Total count
- **Only rating uses the rolling window**

## Benefits

✅ **Fair Rankings**: Division 6 players with many goals won't outrank Division 1 players
✅ **Current Form**: Reflects recent performance (last 40 matches)
✅ **Consistent Base**: Everyone measured from 300
✅ **Division Balanced**: Different divisions have appropriate rating ranges

## Implementation

### Files Modified
1. `database.py`:
   - Updated `calculate_overall_rating_from_last_matches()` function
   - Modified `_record_normal_match()` to use new system
   - Modified `_record_walkover_match()` to use new system
   - Modified `_record_null_match()` to use new system
   - Updated `recalculate_all_ratings()` function

### Database Impact
- **No schema changes required**
- Uses existing `player_matches` table with `rating_before` and `rating_after` columns
- Updates `players.rating` field with new calculation

## Testing

### Verification Script
Run `test_new_rating_system.py` to verify:
```bash
python test_new_rating_system.py
```

Expected output:
```
✅ SUCCESS: Overall rating matches average of last matches!
```

### Recalculation Script
To apply the new system to existing data:
```bash
python apply_new_rating_system.py
```

## Migration

All existing player ratings have been recalculated using the new system. The changes are:

- Players with positive average changes: Rating increased
- Players with negative average changes: Rating decreased
- Most ratings now cluster around **295-310** (near the base of 300)

## Future Matches

All new matches recorded will automatically use the new rating system:
1. Match is played
2. Tournament rating is updated (division-specific)
3. Match rating change is stored
4. Overall rating is recalculated as: 300 + (avg of last 40 changes)

## Example Player Progression

**Player starts in Division 3:**
- Initial: 300 (no matches)
- After 10 matches: 305 (avg change: +0.5)
- After 20 matches: 308 (avg change: +0.4)
- After 40 matches: 312 (avg change: +0.3)

**Same player moves to Division 1:**
- Match 41 in Div 1: Bigger changes (+15, +20, etc.)
- After 50 matches: 315 (recent Div 1 matches increase average)
- After 80 matches: 318 (fully in Div 1 rating range)

## Summary

The new system ensures:
- **Fair competition** across divisions
- **Recent form** is most important
- **Consistent baseline** at 300
- **Proper ranking** where Division 1 > Division 6

---

*Last Updated: 2025-10-08*
*System Version: 2.0 - Rolling Average Rating System*
