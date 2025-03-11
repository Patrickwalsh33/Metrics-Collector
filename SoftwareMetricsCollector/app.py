from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from models import db, Device, Metric, MetricData
import os
from datetime import datetime, timedelta
import subprocess
import signal
import psutil
import queue
import threading
import time
import json

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

# Global variables for collector management
collector_process = None
collector_status = queue.Queue()
collector_start_time = None

def find_python_executable():
    if os.name == 'nt':  # Windows
        return 'python'
    return 'python3'  # Unix-like systems

@app.route('/api/collector/start', methods=['POST'])
def start_collector():
    global collector_process, collector_start_time
    
    if collector_process is not None:
        return jsonify({'status': 'error', 'message': 'Collector is already running'})
    
    try:
        python_exe = find_python_executable()
        collector_process = subprocess.Popen([python_exe, 'collector_agent.py'])
        collector_start_time = datetime.utcnow()
        collector_status.put(('running', collector_start_time))
        return jsonify({'status': 'success', 'message': 'Collector started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/collector/stop', methods=['POST'])
def stop_collector():
    global collector_process, collector_start_time
    
    if collector_process is None:
        return jsonify({'status': 'error', 'message': 'Collector is not running'})
    
    try:
        if os.name == 'nt':  # Windows
            collector_process.terminate()
        else:  # Unix-like systems
            collector_process.send_signal(signal.SIGTERM)
        
        collector_process.wait(timeout=5)  # Wait for process to terminate
        collector_process = None
        collector_start_time = None
        collector_status.put(('stopped', datetime.utcnow()))
        return jsonify({'status': 'success', 'message': 'Collector stopped'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/events')
def events():
    def generate():
        global collector_process
        while True:
            try:
                # Check collector status
                if collector_process is not None:
                    if collector_process.poll() is not None:  # Process has terminated
                        collector_process = None
                        collector_status.put(('stopped', datetime.utcnow()))
                
                # Send current status
                status = 'running' if collector_process is not None else 'stopped'
                data = {'type': 'collector_status', 'status': status}
                yield f"data: {json.dumps(data)}\n\n"
                
                # Check for status updates
                try:
                    new_status, timestamp = collector_status.get_nowait()
                    data = {'type': 'collector_status', 'status': new_status}
                    yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    pass

                # Add a small delay to prevent excessive CPU usage
                time.sleep(1)
            except GeneratorExit:
                break
            except Exception as e:
                print(f"Error in SSE: {str(e)}")
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')

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
    if time_range == 'live' and collector_start_time is not None:
        # For live mode, only get data since collector started
        threshold = collector_start_time
    elif time_range == '10min':
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
    app.run(host='0.0.0.0', port=8080, debug=True) 