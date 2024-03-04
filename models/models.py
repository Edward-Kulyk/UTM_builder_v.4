from app import db

class ExcludedOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option_type = db.Column(db.String(50), nullable=False)
    option_value = db.Column(db.String(255), nullable=False)

class UTMLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    campaign_content = db.Column(db.String(50), nullable=True)
    campaign_source = db.Column(db.String(50), nullable=False)
    campaign_medium = db.Column(db.String(50), nullable=False)
    campaign_name = db.Column(db.String(50), nullable=False)
    domain = db.Column(db.String(20), nullable=False)
    slug = db.Column(db.String(50), nullable=False)
    short_id = db.Column(db.String(20), nullable=True)
    short_secure_url = db.Column(db.String(20), nullable=True)
    clicks_count = db.Column(db.Integer, default=0)