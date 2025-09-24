#!/bin/bash

# Exit on any error
set -e

echo "Starting Player Tournament System..."

# Run database initialization/migration if needed
echo "Initializing database..."
python -c "
from database import DatabaseManager
import os

db = DatabaseManager()
print('Database connection successful')
print('Application ready to start!')
"

# Start the application with gunicorn
echo "Starting Gunicorn server..."
exec gunicorn --config gunicorn.conf.py app:app