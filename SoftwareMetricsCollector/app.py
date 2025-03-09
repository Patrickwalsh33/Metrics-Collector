from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from models import db, Metric
import os

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
    new_metric = Metric(
        device_name=data['device_name'],
        metric_name=data['metric_name'],
        value=data['value']
    )
    db.session.add(new_metric)
    db.session.commit()
    return jsonify({'status': 'success'})

# Reporting API endpoints
@app.route('/api/metrics/<device_name>/<metric_name>')
def get_metrics(device_name, metric_name):
    metrics = Metric.query.filter_by(
        device_name=device_name,
        metric_name=metric_name
    ).order_by(Metric.timestamp.desc()).limit(100).all()
    return jsonify([metric.to_dict() for metric in metrics])

@app.route('/api/devices')
def get_devices():
    devices = db.session.query(Metric.device_name).distinct().all()
    return jsonify([device[0] for device in devices])

@app.route('/api/metrics/device/<device_name>')
def get_device_metrics(device_name):
    metrics = db.session.query(Metric.metric_name).filter_by(
        device_name=device_name
    ).distinct().all()
    return jsonify([metric[0] for metric in metrics])

# Frontend routes
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True) 