from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

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
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        # Ensure timestamp is UTC aware
        if self.timestamp.tzinfo is None:
            timestamp = self.timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = self.timestamp

        return {
            'id': self.id,
            'device_name': self.device.name,
            'metric_name': self.metric.name,
            'value': self.value,
            'unit': self.metric.unit,
            'timestamp': timestamp.isoformat()
        } 