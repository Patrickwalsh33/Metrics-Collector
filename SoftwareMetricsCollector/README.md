# System Monitoring Tool

A real-time system monitoring dashboard that displays CPU usage, memory usage, and stock prices using Flask and SQLite.

## Features

- Real-time monitoring of system metrics (CPU and Memory usage)
- Integration with third-party data (Stock prices via Yahoo Finance)
- Beautiful web dashboard with live charts
- Historical data storage using SQLite
- RESTful API endpoints for data access

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask web application:
```bash
python app.py
```

2. In a separate terminal, start the collector agent:
```bash
python collector_agent.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

The dashboard will automatically update every 5 seconds with new data.

## Project Structure

- `app.py` - Flask web application with API endpoints
- `collector_agent.py` - System metrics collector and uploader
- `models.py` - SQLite database models
- `templates/index.html` - Dashboard frontend
- `requirements.txt` - Python dependencies

## API Endpoints

- `POST /api/metrics` - Submit new metrics
- `GET /api/metrics/<device_name>/<metric_name>` - Get historical metrics
- `GET /api/devices` - List all devices
- `GET /api/metrics/device/<device_name>` - List metrics for a device

## Technologies Used

- Flask - Web framework
- SQLite - Database
- Chart.js - Frontend charts
- TailwindCSS - Styling
- psutil - System metrics collection
- yfinance - Stock data API 