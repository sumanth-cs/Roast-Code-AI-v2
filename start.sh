#!/bin/bash

# Start Redis in background
redis-server --daemonize yes

# Wait for Redis to start
sleep 3

# Start backend
cd backend && gunicorn --bind 0.0.0.0:5001 --workers 2 app:app &

# Start frontend
cd /app/frontend && streamlit run app.py --server.port 8501 --server.address 0.0.0.0