"""
Test fixtures and sample data for categorization tests.
"""

# Sample notes for testing categorization
SAMPLE_NOTES = [
    {
        'id': 'test001',
        'title': 'Grocery Shopping',
        'content': 'Need to buy milk, eggs, bread, and apples for the week. Also get some cheese and yogurt.'
    },
    {
        'id': 'test002',
        'title': 'Team Meeting Notes',
        'content': 'Discussed Q4 goals and project timeline with Sarah and Mike. Need to finalize budget by Friday.'
    },
    {
        'id': 'test003',
        'title': 'Workout Plan',
        'content': 'Monday - chest and triceps, Tuesday - back and biceps, Wednesday - legs and shoulders'
    },
    {
        'id': 'test004',
        'title': 'Recipe Ideas',
        'content': 'Try making pasta carbonara with pancetta and fresh parmesan. Also want to try homemade pizza.'
    },
    {
        'id': 'test005',
        'title': 'Travel Itinerary',
        'content': 'Flight to NYC on Friday 3pm, hotel reservation at Marriott downtown. Meeting with client Monday.'
    },
    {
        'id': 'test006',
        'title': 'Investment Research',
        'content': 'Look into index funds and ETFs for retirement portfolio diversification. Research Vanguard options.'
    },
    {
        'id': 'test007',
        'title': 'Birthday Party Planning',
        'content': 'Mom\'s 60th birthday next month. Need to book restaurant and invite family members.'
    },
    {
        'id': 'test008',
        'title': 'Code Snippet',
        'content': 'Python function to parse JSON data and extract specific fields for API integration.'
    },
    {
        'id': 'test009',
        'title': 'Book Recommendations',
        'content': 'Read Atomic Habits and The Psychology of Money for personal development and financial literacy.'
    },
    {
        'id': 'test010',
        'title': 'Doctor Appointment',
        'content': 'Annual checkup scheduled for next Tuesday at 2pm with Dr. Johnson. Bring insurance card.'
    }
]

# Expected categorization results for validation
EXPECTED_CATEGORIES = {
    'test001': ['Shopping'],
    'test002': ['Work'],
    'test003': ['Health'],
    'test004': ['Recipes'],
    'test005': ['Travel', 'Work'],  # Could be both
    'test006': ['Finance'],
    'test007': ['Personal'],
    'test008': ['Technical'],
    'test009': ['Education'],
    'test010': ['Health']
}

# Test categorization rules
TEST_CATEGORIZATION_RULES = """
Categorize notes based on the following rules:

1. Personal notes (family, friends, personal thoughts, diary entries) should be labeled "Personal"
2. Work-related notes (meetings, projects, tasks, deadlines) should be labeled "Work"
3. Shopping lists and purchase-related notes should be labeled "Shopping"
4. Health and fitness notes (workouts, medical appointments, diet) should be labeled "Health"
5. Travel notes (trips, itineraries, bookings) should be labeled "Travel"
6. Learning and educational content (courses, tutorials, research) should be labeled "Education"
7. Financial notes (budgets, expenses, investments) should be labeled "Finance"
8. Recipe and cooking notes should be labeled "Recipes"
9. Technical notes (code snippets, configurations, troubleshooting) should be labeled "Technical"
10. Ideas and creative content should be labeled "Ideas"

If a note fits multiple categories, include all relevant labels separated by commas.
If a note doesn't clearly fit any category, label it as "Miscellaneous".
"""
