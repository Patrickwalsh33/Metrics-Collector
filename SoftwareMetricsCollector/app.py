from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from models import db, Device, Metric, MetricData
import os
from datetime import datetime, timedelta, timezone
import json

app = Flask(__name__)
CORS(app)

# Get absolute path for database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'metrics.db')

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()


# Aggregator API endpoint
@app.route('/api/metrics', methods=['POST'])
def add_metric():
    data = request.json
    
    try:
        # Get or create device
        device = Device.query.filter_by(name=data['device_name']).first()
        if not device:
            device = Device(name=data['device_name'])
            db.session.add(device)
            db.session.flush()
        
        # Get or create metric type
        metric = Metric.query.filter_by(name=data['metric_name']).first()
        if not metric:
            unit = {
                'CPU_Usage': '%',
                'Memory_Usage': '%',
                'BTC_Price': 'USD'
            }.get(data['metric_name'], 'unknown')
            metric = Metric(name=data['metric_name'], unit=unit)
            db.session.add(metric)
            db.session.flush()
        
        # Create new metric data with proper UTC timestamp
        timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        new_metric_data = MetricData(
            metricID=metric.id,
            deviceId=device.id,
            value=data['value'],
            timestamp=timestamp
        )
        db.session.add(new_metric_data)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Reporting API endpoints
@app.route('/api/metrics/<device_name>/<metric_name>')
def get_metrics(device_name, metric_name):
    time_range = request.args.get('time_range', '10min')
    limit = int(request.args.get('limit', 100))
    
    try:
        # Calculate the time threshold using UTC
        now = datetime.now(timezone.utc)
        if time_range == '10min':
            threshold = now - timedelta(minutes=10)
        elif time_range == '1hour':
            threshold = now - timedelta(hours=1)
        elif time_range == '1day':
            threshold = now - timedelta(days=1)
        else:
            threshold = now - timedelta(minutes=10)
        
        print(f"Time range: {time_range}")
        print(f"Current time (UTC): {now}")
        print(f"Threshold time (UTC): {threshold}")
        
        # Build the query with explicit timestamp conversion
        query = MetricData.query.join(Device).join(Metric).filter(
            Device.name == device_name,
            Metric.name == metric_name,
            MetricData.timestamp >= threshold
        ).order_by(MetricData.timestamp.asc())
        
        # Get the metrics
        metrics = query.limit(limit).all()
        
        # Convert to dict with proper UTC timestamp formatting
        result = []
        for metric in metrics:
            # Ensure the timestamp is UTC aware
            if metric.timestamp.tzinfo is None:
                timestamp = metric.timestamp.replace(tzinfo=timezone.utc)
            else:
                timestamp = metric.timestamp
                
            metric_dict = {
                'timestamp': timestamp.isoformat(),
                'value': metric.value
            }
            result.append(metric_dict)
        
        print(f"Number of records found: {len(result)}")
        if result:
            print(f"First record time: {result[0]['timestamp']}")
            print(f"Last record time: {result[-1]['timestamp']}")
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_metrics: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

# Add this new endpoint after your existing endpoints
@app.route('/api/debug/metrics/<device_name>/<metric_name>')
def debug_metrics(device_name, metric_name):
    try:
        # Get all metrics for this device and metric type
        query = MetricData.query.join(Device).join(Metric).filter(
            Device.name == device_name,
            Metric.name == metric_name
        ).order_by(MetricData.timestamp.desc())
        
        metrics = query.limit(10).all()  # Get last 10 records
        
        # Get count of all records
        total_count = query.count()
        
        # Get time range of data
        oldest = MetricData.query.join(Device).join(Metric).filter(
            Device.name == device_name,
            Metric.name == metric_name
        ).order_by(MetricData.timestamp.asc()).first()
        
        newest = MetricData.query.join(Device).join(Metric).filter(
            Device.name == device_name,
            Metric.name == metric_name
        ).order_by(MetricData.timestamp.desc()).first()
        
        return jsonify({
            'total_records': total_count,
            'oldest_record_time': oldest.timestamp.isoformat() if oldest else None,
            'newest_record_time': newest.timestamp.isoformat() if newest else None,
            'last_10_records': [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'value': m.value
                } for m in metrics
            ]
        })
    except Exception as e:
        print(f"Error in debug_metrics: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run() 