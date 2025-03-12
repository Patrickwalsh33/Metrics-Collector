from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from models import db, Device, Metric, MetricData
import os
from datetime import datetime, timedelta
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
        
        # Create new metric data
        new_metric_data = MetricData(
            metricID=metric.id,
            deviceId=device.id,
            value=data['value']
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
        query = MetricData.query.join(Device).join(Metric).filter(
            Device.name == device_name,
            Metric.name == metric_name
        )
        
        now = datetime.utcnow()
        if time_range == '10min':
            threshold = now - timedelta(minutes=10)
        elif time_range == '1hour':
            threshold = now - timedelta(hours=1)
        elif time_range == '1day':
            threshold = now - timedelta(days=1)
        else:
            threshold = now - timedelta(minutes=10)
        
        metrics = query.filter(
            MetricData.timestamp >= threshold
        ).order_by(MetricData.timestamp.asc()).limit(limit).all()
        
        return jsonify([metric.to_dict() for metric in metrics])
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run() 