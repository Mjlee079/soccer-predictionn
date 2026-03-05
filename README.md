# Soccer Prediction Engine

This repository contains a small **soccer match prediction engine** that uses the free tier of the `football.api-sports.io` API.

## Features
- Search for teams by name
- Fetch recent fixtures and head-to-head data
- Multi-factor prediction model (form, attack, defence, venue, goal difference, H2H)
- CLI agent with interactive menu (`agent.py`)
- Example script predicting AmaZulu vs Mamelodi Sundowns (`run_predict.py`)

## Setup
1. Get a free API key from `https://www.api-football.com`.
2. Set the environment variable in PowerShell:
   ```powershell
   $env:FOOTBALL_API_KEY = 'your_key_here'
   ```
3. Install Python 3.9+.

## Usage
Run the interactive agent:
```bash
python agent.py
```

Or run the example AmaZulu vs Mamelodi Sundowns prediction:
```bash
python run_predict.py
```

The client automatically caches API responses under the `.cache` folder to save requests.
