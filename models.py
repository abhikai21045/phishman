from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()
# Campaign model to store email campaign details
class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    target_emails = db.Column(db.Text, nullable=False)  
    template = db.Column(db.String(50), default='outlook')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Tracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    tracking_uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    act = db.Column(db.String(50)) # sent constant
    action = db.Column(db.String(50))  # sent / clicked / submitted
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    username_submitted = db.Column(db.String(255))  #  for submitted action
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    campaign = db.relationship('Campaign', backref='trackings')

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)