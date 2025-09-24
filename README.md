# Player Tournament System

A comprehensive player-centric tournament management system built with Flask, PostgreSQL, and modern UI components. This system allows administrators to manage players, create tournaments, record 1v1 matches, and track detailed statistics with an ELO-style rating system.

## Features

### 🎯 Core Functionality
- **Player Management**: Add single players or bulk import multiple players
- **Tournament System**: Create and manage tournaments without complex team structures
- **1v1 Match Recording**: Record matches between individual players with goal tracking
- **ELO Rating System**: Automatic rating calculations (300-1000 range) based on match results
- **Comprehensive Statistics**: Track player performance across tournaments and overall

### 🔐 Security
- Admin-only access with session-based authentication
- Protected routes requiring login
- Secure database connection with environment variables

### 🎨 Modern UI
- Glassmorphism design with Tailwind CSS
- Responsive layout for desktop and mobile
- Interactive dashboards with real-time statistics
- Font Awesome icons and custom animations

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd "C:\Drive d\html\task16"
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser and go to:**
   ```
   http://localhost:5000
   ```

## Usage Guide

### Home Page
- Central dashboard with navigation cards
- Tournament overview statistics
- Links to all major features

### Enter Match
1. Select Team 1 from dropdown
2. Select Team 2 from dropdown (different from Team 1)
3. Players are automatically displayed based on team selection
4. Enter goals scored for each player (Captain and Member)
5. View real-time match summary
6. Submit to save results

### View Leaderboards
- **Golden Boot**: Click to see top goal scorers
- **Golden Glove**: Click to see best defensive records
- **Clean Sheets**: Click to see players with most clean sheets
- **Team Standings**: Click to see teams ranked by points
- Switch between leaderboards using navigation tabs

## Data Storage

### matches.csv Structure
```csv
MatchID,Date,Club,Player,Role,Goals,GoalsConceded,CleanSheet,Points
1,2024-01-15 14:30:00,CHELSEA,Sanju,Captain,2,1,0,3
1,2024-01-15 14:30:00,CHELSEA,Mufaris,Member,1,0,1,3
1,2024-01-15 14:30:00,INTER MILAN,Fajas,Captain,1,2,0,0
1,2024-01-15 14:30:00,INTER MILAN,Melwin,Member,0,1,0,0
```

### Calculations
- **Goals**: Directly entered by user
- **Goals Conceded**: Goals scored by direct opponent (Captain vs Captain, Member vs Member)
- **Clean Sheet**: 1 if direct opponent scored 0 goals, otherwise 0
- **Points**: 3 for win, 1 for draw, 0 for loss (individual matchup basis)

## Example Workflow

### 1. Enter a Match: Chelsea vs Inter Milan
- **Captain vs Captain**: Sanju (2 goals) vs Fajas (1 goal)
- **Member vs Member**: Mufaris (1 goal) vs Melwin (0 goals)

### 2. Automatic Processing
- **Captain matchup**: Sanju wins (3 points), Fajas loses (0 points)
- **Member matchup**: Mufaris wins (3 points), Melwin loses (0 points)
- **Clean sheets**: Mufaris gets clean sheet (Melwin scored 0), others don't
- **Team totals**: Chelsea 6 points, Inter Milan 0 points
- Data saved with Match ID 1

### 3. View Results
- **Golden Boot**: Sanju (2 goals), Mufaris (1 goal), Fajas (1 goal)
- **Golden Glove**: Melwin (1.0 avg conceded), Fajas (2.0 avg), Sanju/Mufaris (varies)
- **Clean Sheets**: Mufaris (1 clean sheet)
- **Team Standings**: Chelsea (6 points), Inter Milan (0 points)

## Teams List

The application includes 35 teams:

**Premier League**: Chelsea, Liverpool, Manchester City, Manchester United, Arsenal, Tottenham, Aston Villa, Newcastle United, Crystal Palace

**La Liga**: Real Madrid, Barcelona, Atletico Madrid, Real Betis, Sevilla, Athletic Bilbao

**Serie A**: Juventus, Inter Milan, AC Milan, AS Roma, Lazio, Atalanta, Napoli, Fiorentina

**Bundesliga**: Bayern Munich, Borussia Dortmund, Bayer Leverkusen

**Ligue 1**: PSG, Lyon, Marseille, Monaco

**Other European**: Porto, Sporting CP, Benfica, Ajax, Galatasaray

## File Structure
```
task16/
│
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── matches.csv           # Data storage (created automatically)
│
└── templates/
    ├── home.html         # Home page template
    ├── enter_match.html  # Match entry form
    └── leaderboard.html  # Leaderboard display
```

## Technical Details

- **Backend**: Flask (Python web framework)
- **Data Processing**: Pandas for CSV handling and statistics
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Icons**: Font Awesome
- **Responsive**: Mobile-first design
- **Storage**: CSV file (easily viewable in Excel/Google Sheets)

## Troubleshooting

### Common Issues

1. **Port already in use:**
   - Change port in `app.py`: `app.run(debug=True, port=5001)`

2. **Module not found:**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`

3. **CSV file locked:**
   - Close Excel if you have `matches.csv` open

### Development Mode
The app runs in debug mode by default, which means:
- Automatic restart on code changes
- Detailed error messages
- Hot reloading

## Future Enhancements

Potential features to add:
- Match history view
- Team statistics
- Player profile pages
- Export functionality
- Database integration
- User authentication
- Tournament brackets
- Advanced statistics

---

**Built with ❤️ using Flask, Pandas, and Tailwind CSS**