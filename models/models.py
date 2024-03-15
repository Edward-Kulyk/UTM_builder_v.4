from app import db
from sqlalchemy.orm import relationship


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
    campaign_name = db.Column(db.String(50), db.ForeignKey('campaign.name'), nullable=False)
    domain = db.Column(db.String(20), nullable=False)
    slug = db.Column(db.String(50), nullable=False)
    short_id = db.Column(db.String(20), nullable=True)
    short_secure_url = db.Column(db.String(20), nullable=True)
    clicks_count = db.Column(db.Integer, default=0)
    clicks_count24h = db.Column(db.Integer, default=0)
    clicks_count1w = db.Column(db.Integer, default=0)
    clicks_count2w = db.Column(db.Integer, default=0)
    clicks_count3w = db.Column(db.Integer, default=0)

    campaign = relationship("Campaign", back_populates="links")


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    url_by_default = db.Column(db.String(255), nullable=True)
    domain_by_default = db.Column(db.String(20), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    hide = db.Column(db.Boolean, default=False)

    links = relationship("UTMLink", back_populates="campaign")

