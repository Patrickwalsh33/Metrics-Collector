from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from models import db, Device, Metric, MetricData
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///metrics.db'
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
    
    # Get or create device
    device = Device.query.filter_by(name=data['device_name']).first()
    if not device:
        device = Device(name=data['device_name'])
        db.session.add(device)
        db.session.flush()  # This will assign an ID to the device
    
    # Get or create metric type
    metric = Metric.query.filter_by(name=data['metric_name']).first()
    if not metric:
        # Determine unit based on metric name
        unit = {
            'CPU_Usage': '%',
            'Memory_Usage': '%',
            'BTC_Price': 'USD'
        }.get(data['metric_name'], 'unknown')
        metric = Metric(name=data['metric_name'], unit=unit)
        db.session.add(metric)
        db.session.flush()  # This will assign an ID to the metric
    
    # Create new metric data
    new_metric_data = MetricData(
        metricID=metric.id,
        deviceId=device.id,
        value=data['value']
    )
    db.session.add(new_metric_data)
    db.session.commit()
    return jsonify({'status': 'success'})

# Reporting API endpoints
@app.route('/api/metrics/<device_name>/<metric_name>')
def get_metrics(device_name, metric_name):
    # Get query parameters for time range
    time_range = request.args.get('time_range', '10min')  # Default to 10 minutes
    limit = int(request.args.get('limit', 100))  # Default to 100 points
    
    query = MetricData.query.join(Device).join(Metric).filter(
        Device.name == device_name,
        Metric.name == metric_name
    )
    
    # Calculate the time threshold based on the selected window
    now = datetime.utcnow()
    if time_range == '10min':
        threshold = now - timedelta(minutes=10)
    elif time_range == '30min':
        threshold = now - timedelta(minutes=30)
    elif time_range == '1hour':
        threshold = now - timedelta(hours=1)
    elif time_range == '1day':
        threshold = now - timedelta(days=1)
    else:
        # Default to 10 minutes if invalid time range
        threshold = now - timedelta(minutes=10)
    
    # Filter by time threshold and order by timestamp in ascending order (oldest to newest)
    metrics = query.filter(
        MetricData.timestamp >= threshold
    ).order_by(MetricData.timestamp.asc()).limit(limit).all()
    
    return jsonify([metric.to_dict() for metric in metrics])

@app.route('/api/devices')
def get_devices():
    devices = Device.query.all()
    return jsonify([device.name for device in devices])

@app.route('/api/metrics/device/<device_name>')
def get_device_metrics(device_name):
    metrics = Metric.query.join(MetricData).join(Device).filter(
        Device.name == device_name
    ).distinct().all()
    return jsonify([metric.name for metric in metrics])

# Frontend routes
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True) 