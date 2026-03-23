from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
import os
from urllib.parse import urljoin
from datetime import datetime
from sqlalchemy import func
from config import Config
from models import db, Campaign, Tracking, User
from datetime import datetime, timezone  

#  Flask Application Setup
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'         
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#  Database Session Management
@app.before_request
def before_request():
    db.session.rollback()  

@app.teardown_request
def teardown_request(exception=None):
    if exception:
        db.session.rollback()
    else:
        try:
            db.session.commit()
        except:
            db.session.rollback()

# Create DB Tables
with app.app_context():
    db.create_all()


BASE_URL = "http://127.0.0.1:5000"    

def send_email(to_email, subject, html_content):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = Config.FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# Routes
@app.route('/')
def index():
    return redirect(url_for('admin_dashboard'))

# Admin route to create campaign and send emails
@app.route('/admin/create-campaign', methods=['GET', 'POST'])
@login_required
def create_campaign():
    
    sent_count = 0
        
    if request.method == 'POST':
        title = request.form.get('title')
        emails_raw = request.form.get('emails')
        template = request.form.get('template', 'outlook')

        if not title or not emails_raw:
            flash('Title and emails are required', 'danger')
            return redirect(request.url)

        emails = [e.strip() for e in emails_raw.replace(',', '\n').splitlines() if e.strip()]

        campaign = Campaign(
            title=title,
            target_emails='\n'.join(emails),
            template=template
        )
        db.session.add(campaign)
        db.session.flush() 

        
        for email in emails:
          
            tracking = Tracking(
                campaign_id=campaign.id,
                email=email,
                tracking_uuid=str(uuid.uuid4()),
                act='sent',
                action='sent',
                ip_address='server',
                user_agent='server'
            )
            db.session.add(tracking)
            db.session.flush()  

            tracking_link = urljoin(BASE_URL, f"/track/click/{tracking.tracking_uuid}")

            subject = "Test message from security training"

            html = f"""
            <html>
            <body>
            <p>Hi,</p>
            <p>This is just a test email for the awareness platform.</p>
            <p><strong>Please click the link below to continue the test:</strong></p>
            <p><a href="{tracking_link}">Click here for the test</a></p>
            <p>If you were not expecting this email, you can safely ignore it.</p>
            <p>Security Awareness Team</p>
            </body>
            </html>
            """
            
            print(f"TESTTEST: Email={email},Tracking_link={tracking_link}")

            if send_email(email, subject, html):
                sent_count += 1
                print(f"Successfully queued email to {email}") 
            else:
                print(f"Failed to queue email to {email}") 

        
        db.session.commit()
        print(f"DB commit executed. Sent count: {sent_count}") 

        flash(f'Campaign created. {sent_count} email(s) sent successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/create_campaign.html')

 
# Login route   
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')
#logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        elif len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')




# Tracking route for email clicks  
@app.route('/track/click/<tracking_uuid>')
def track_click(tracking_uuid):
    tracking = Tracking.query.filter_by(tracking_uuid=tracking_uuid).first()
    if not tracking:
        return "Invalid link", 404

    try:
        # Update click
        tracking.action = 'clicked'
        tracking.ip_address = request.remote_addr
        tracking.user_agent = request.user_agent.string
        tracking.created_at = datetime.now(timezone.utc)  # fixed version

        # Log open separately
        open_track = Tracking(
            campaign_id=tracking.campaign_id,
            email=tracking.email,
            tracking_uuid=str(uuid.uuid4()),
            action='opened',
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(open_track)

        db.session.commit()
        print("track_click committed successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error in track_click: {e}")
       
    
    return redirect(url_for('phishing_login', tracking_uuid=tracking.tracking_uuid))


# Phishing login page and submission handling
@app.route('/phishing/login/<tracking_uuid>', methods=['GET', 'POST'])
def phishing_login(tracking_uuid):
    tracking = Tracking.query.filter_by(tracking_uuid=tracking_uuid).first()
    if not tracking:
        return "Invalid session", 404

    if request.method == 'POST':
        username = request.form.get('username')

        try:
            submit_track = Tracking(
                campaign_id=tracking.campaign_id,
                email=tracking.email,
                tracking_uuid=str(uuid.uuid4()),
                action='submitted',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                username_submitted=username,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(submit_track)
            db.session.commit()
           
        except Exception as e:
            db.session.rollback()
            print(f"Error in submission: {e}")

        return render_template('phishing/success.html')
    
    return render_template('phishing/outlook_login.html', tracking_uuid=tracking_uuid)
    
    
# dashboard 
@app.route('/admin/dashboard')
@login_required 
def admin_dashboard():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    
    stats = {}
    for c in campaigns:
        
        sent = db.session.query(func.count(Tracking.id)).filter_by(
            campaign_id=c.id, act='sent'
        ).scalar() or 0
        
        opened = db.session.query(func.count(Tracking.id)).filter_by(
            campaign_id=c.id, action='opened'
        ).scalar() or 0
        
        clicked = db.session.query(func.count(Tracking.id)).filter_by(
            campaign_id=c.id, action='clicked'
        ).scalar() or 0
        
        submitted = db.session.query(func.count(Tracking.id)).filter_by(
            campaign_id=c.id, action='submitted'
        ).scalar() or 0
        
        stats[c.id] = {
            'sent': sent,
            #'opened': opened,
            'clicked': clicked,
            'submitted': submitted
        }
        
        
        print(f"Campaign {c.id} ({c.title}): sent={sent}, opened={opened}, clicked={clicked}, submitted={submitted}")
    
    return render_template('admin/dashboard.html', campaigns=campaigns, stats=stats)

# temporary 
@app.route('/debug-commit')
def debug_commit():
    from datetime import datetime
    import uuid

    # Dummy campaign and tracking
    campaign = Campaign(title="Debug Test", target_emails="test@example.com", template="outlook")
    db.session.add(campaign)
    db.session.flush()

    tracking = Tracking(
        campaign_id=campaign.id,
        email="test@example.com",
        tracking_uuid=str(uuid.uuid4()),
        action='sent',
        ip_address='debug',
        user_agent='debug'
    )
    db.session.add(tracking)

    db.session.commit()

    return f"Debug commit done. Check DB for campaign id {campaign.id} and tracking 'sent'"
    
if __name__ == '__main__':
    app.run(debug=True)
    
