"""
Check if rating recalculation happens consistently in all match operations
"""

import re

def check_function_for_rating_calc(file_path, function_name, start_line, end_line):
    """Check if a function contains rating recalculation"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    function_code = ''.join(lines[start_line-1:end_line])
    
    has_calc = 'calculate_overall_rating_from_last_matches' in function_code
    has_update = re.search(r'UPDATE players SET rating', function_code, re.IGNORECASE)
    
    return {
        'function': function_name,
        'has_calculation': has_calc,
        'has_rating_update': has_update is not None,
        'start_line': start_line,
        'end_line': end_line
    }

def analyze_all_match_operations():
    """Analyze all match recording/editing operations"""
    
    file_path = 'database.py'
    
    # Define all match-related functions to check
    functions_to_check = [
        ('record_match', 1077, 1107),
        ('_record_null_match', 1110, 1153),
        ('_record_walkover_match', 1156, 1308),
        ('_record_normal_match', 1311, 1484),
        ('_record_bulk_null_match', 2443, 2485),
        ('_record_bulk_walkover_match', 2486, 2578),
        ('_record_bulk_normal_match', 2581, 2679),
        ('edit_match', 2891, 3100),
        ('delete_match', 3398, 3450),
    ]
    
    print("=" * 100)
    print("RATING RECALCULATION CONSISTENCY CHECK")
    print("=" * 100)
    print()
    print("Checking if rating recalculation happens in ALL match operations...")
    print()
    
    results = []
    for func_name, start, end in functions_to_check:
        try:
            result = check_function_for_rating_calc(file_path, func_name, start, end)
            results.append(result)
        except Exception as e:
            print(f"Error checking {func_name}: {e}")
    
    print(f"{'Function':<35} {'Has Recalc?':<15} {'Updates Rating?':<20} {'Lines'}")
    print("-" * 100)
    
    all_consistent = True
    for r in results:
        status_calc = "✅ YES" if r['has_calculation'] else "❌ NO"
        status_update = "✅ YES" if r['has_rating_update'] else "❌ NO"
        
        print(f"{r['function']:<35} {status_calc:<15} {status_update:<20} {r['start_line']}-{r['end_line']}")
        
        if not r['has_calculation'] or not r['has_rating_update']:
            all_consistent = False
    
    print("\n" + "=" * 100)
    print("CONCLUSION:")
    print("=" * 100)
    
    if all_consistent:
        print("✅ CONSISTENT: All match operations recalculate and update ratings")
    else:
        print("❌ INCONSISTENT: Some operations do NOT recalculate ratings!")
        print("\n⚠️  This means ratings might be outdated or incorrect after:")
        for r in results:
            if not r['has_calculation']:
                print(f"   - {r['function']}")
    
    print("\n" + "=" * 100)
    print("BULK OPERATIONS CHECK:")
    print("=" * 100)
    
    bulk_functions = [r for r in results if 'bulk' in r['function'].lower()]
    if bulk_functions:
        print("\nBulk operations found:")
        bulk_consistent = all(r['has_calculation'] for r in bulk_functions)
        for r in bulk_functions:
            status = "✅" if r['has_calculation'] else "❌"
            print(f"  {status} {r['function']}")
        
        if not bulk_consistent:
            print("\n⚠️  WARNING: Bulk operations might not recalculate ratings!")
    else:
        print("\nNo bulk operations found in database.py")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    analyze_all_match_operations()
