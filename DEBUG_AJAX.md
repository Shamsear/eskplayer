# Debugging AJAX Division Management

## Steps to Debug:

### 1. Start Flask with Debug Output
```bash
python app.py
```

### 2. Open Browser DevTools
- Press F12
- Go to "Console" tab
- Go to "Network" tab

### 3. Try Adding a Division

#### In the Console tab, you should see:
```
Form submit prevented
Division Name: [your division name]
Division Rating: [your rating]
Sending AJAX request...
Response status: 200
Response headers: application/json
Response data: {success: true, message: "...", division: {...}}
```

#### In the Network tab, you should see:
- A POST request to `/admin/tournaments/[id]/edit`
- Type: `fetch` or `xhr` (NOT `document`)
- Status: 200
- Response Type: `json` (NOT `html`)

#### In the Flask Console, you should see:
```
=== ADD DIVISION DEBUG ===
Division name: [your division name]
Starting rating: [your rating]
Is AJAX: True
X-Requested-With: XMLHttpRequest
Accept: application/json
========================

Division created with ID: [new id]
Returning JSON response: {'success': True, ...}
```

## Common Issues and Solutions:

### Issue 1: Page Refreshes
**Symptom**: Page reloads after clicking "Add Division"

**Causes**:
- Form submit not being prevented
- JavaScript error before `e.preventDefault()`
- Form has default action attribute

**Check**:
1. Console should show "Form submit prevented"
2. If not, there's a JavaScript error - check console for red errors

### Issue 2: HTML Response Instead of JSON
**Symptom**: Console shows HTML in response, or error parsing JSON

**Causes**:
- Backend not detecting AJAX request
- Headers not being sent correctly

**Check Flask Console for**:
```
Is AJAX: False  ← Should be True!
```

**If False, check**:
1. Headers in Network tab - should have:
   - `X-Requested-With: XMLHttpRequest`
   - `Accept: application/json`

### Issue 3: Division Not Appearing
**Symptom**: No error, but division doesn't show up

**Causes**:
- DOM manipulation function error
- Division ID not returned
- JavaScript error in `addDivisionToList()`

**Check**:
1. Console for: `Response data: {success: true, ...}`
2. Console for JavaScript errors after response
3. Inspect DOM - check if division was actually added

### Issue 4: 400/500 Error Response
**Symptom**: Network shows red status code

**Check Flask Console for**:
- Error messages
- Stack trace
- Database errors

## Manual Testing Commands:

### Test if division was actually created:
```python
python -c "from database import TournamentDB; divs = TournamentDB.get_divisions_by_tournament(1); print(f'Divisions: {divs}')"
```

### Delete test divisions:
```python
python -c "from database import TournamentDB; TournamentDB.delete_division(2)"
```

## What Should Happen (No Refresh):

1. ✅ Click "Add Division" button
2. ✅ Button changes to "Adding..." with spinner
3. ✅ Console logs appear
4. ✅ Flask console shows debug output
5. ✅ JSON response received
6. ✅ Form clears (name and rating inputs empty)
7. ✅ New division card appears with animation
8. ✅ Green toast notification appears
9. ✅ Division count updates
10. ✅ Button returns to "Add Division"
11. ✅ **NO PAGE REFRESH**

## If Still Not Working:

1. Check browser console for ANY red errors
2. Check Flask console for errors
3. Verify you're on the edit tournament page (not create)
4. Try clearing browser cache (Ctrl+Shift+Delete)
5. Try a different browser
6. Check if JavaScript is enabled
7. Share the console output and Flask logs for further debugging
