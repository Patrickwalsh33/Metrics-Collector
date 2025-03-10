from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    metrics = db.relationship('MetricData', backref='device', lazy=True)

class Metric(db.Model):
    __tablename__ = 'metrics'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    data = db.relationship('MetricData', backref='metric', lazy=True)

class MetricData(db.Model):
    __tablename__ = 'metricData'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    metricID = db.Column(db.Integer, db.ForeignKey('metrics.id'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    deviceId = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'device_name': self.device.name,
            'metric_name': self.metric.name,
            'value': self.value,
            'unit': self.metric.unit,
            'timestamp': self.timestamp.isoformat()
        } 