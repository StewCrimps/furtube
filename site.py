from flask import Flask, render_template, request, abort, session, redirect,url_for
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from datetime import datetime
import humanize
import uuid
import os


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'haha guess the key buh')
os.makedirs(app.instance_path, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'users.db')}"
app.url_map.strict_slashes = False #Makes /example(/) not mandatory

db = SQLAlchemy(app)
app.app_context().push() 
videoUpload=os.path.join(app.root_path, "static","videos")
allowedFormats=["mp4","mkv","mov","m4p","m4v"]
# Mail config #####################################################
from flask_mail import Mail, Message
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
# app.cofing['MAIL_USE_SSL'] = 
app.config['MAIL_USERNAME'] = 'furtu.be.official'
app.config['MAIL_PASSWORD'] = 'wkqz wxho joac jzhl' 
mail=Mail(app)


##################################################################

# Definitions ##################################################################
def time_formater(time):
    past = datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S.%f")
    formatted_time = humanize.naturaltime(datetime.now() - past)
    return formatted_time

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowedFormats


def get_uploaded_videos():
    videos = []
    for filename in sorted(os.listdir(videoUpload), reverse=True):
        if allowed_file(filename):
            extension = filename.rsplit(".", 1)[1].lower()
            videos.append({
                "filename": filename,
                "title": os.path.splitext(filename)[0],
                "ext": extension,
            })
    return videos

# Create Model
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80),nullable=False) 
    handle = db.Column(db.String(80),nullable=False,unique=True) 
    email = db.Column(db.String(120), nullable=False,unique=True) 
    password = db.Column(db.String(255), nullable=False) 
    profile_image = db.Column(db.String(200)) 
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    verified = db.Column(db.Boolean,default=False,nullable=False)
    verification_token = db.Column(db.String(200),unique=True,nullable=True)

class Videos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    thumpnail = db.Column(db.String)
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String,unique=True,nullable=False)

class UserHistory(db.Model):
    __tablename__ = 'user_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'video_id', name='uq_user_video_history'),
    )

# class UserVideo(db.Model):
#     publisher = db.Column(db.Integer, db.ForeignKey('users.id'),primary_key=True)
#     vidvideo = db.Column(db.Integer, db.ForeignKey('videos.id'), primary_key=True)
#     date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)
#     intrested = db.Column(db.Integer)
#     unintrested = db.Column(db.Integer)

with app.app_context():
    db.create_all()

def get_current_user():
    email = session.get("user_email")
    print(email)
    q = Users.query.filter_by(email=email).first()
    # q = "1@1.com"
    if q:
        return email
    else:
        return None

def get_current_user_record():
    email = session.get("user_email")                         
    if not email:
        return None
    return Users.query.filter_by(email=email).first()


def record_user_history(user_id, video_id):
    history_entry = UserHistory.query.filter_by(user_id=user_id, video_id=video_id).first()
    if history_entry:
        history_entry.viewed_at = datetime.utcnow()
    else:
        db.session.add(UserHistory(user_id=user_id, video_id=video_id))
    db.session.commit()

##################################################################

# Site Routes ##################################################################
# Route for the index page
@app.route('/')
def home(): 
    db_videos = Videos.query.order_by(Videos.id.desc()).all()
    videos = []
    for v in db_videos:
        if not os.path.exists(os.path.join(videoUpload, v.filename)):
            continue
        uploader = Users.query.get(v.uploaded_by)
        videos.append({
            "id": v.id,
            "filename": v.filename,
            "title": v.title,
            "description": v.description,
            "uploaded_by": uploader.handle if uploader else "unknown",
            "date_added": time_formater(v.date_uploaded),
        })
    current_user = get_current_user()
    return render_template('index.html',current_user=current_user,videos=videos)

# Route for the login page
@app.route('/login/', methods=['GET', 'POST'])
def login():
    current_user = get_current_user()
    if current_user is not None:
        return redirect (url_for("home"))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Users.query.filter_by(email=email).first()
        if user and user.password == password:
            if user.verified:
                session["user_email"] = email
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Verify your account via email.",current_user=current_user)
        else:
            return render_template('login.html', error="Please check your credentials.",current_user=current_user)
    return render_template('login.html',current_user=current_user)

@app.route('/logout/')
def logout(): 
    session.clear()
    return redirect (url_for("home"))

# Route for the signup page
@app.route('/signup/', methods=['GET', 'POST'])
def signup():
    current_user = get_current_user()
    if current_user is not None:
        return redirect (url_for("home"))
    if request.method == 'POST':
        username = request.form['username'].strip() # ===> strip για να αφαιρούνται κενά 
        handle = request.form['handle'].strip().lower().lstrip('@') # ===> trim + lowercase + αφαίρεση προαιρετικού @, αν δοθεί παράδειγμα με @ το route δεν πρέπει να το απορρίπτει.
        for i in handle:
            if i>='a' and i<='z' or i in ['_','.','-'] or i.isdigit():   
                print("Handle is fine")
            else:
                error = "Handle cannot contain special characters, accepted a-z , 0-9 and '.''-''_'"
                return render_template('signup.html', error=error)
        email = request.form['email'].strip().lower() # ===>  trim/lowercase 
        password1 = request.form['password1']
        password2 = request.form['password2']
         
        existing_user = Users.query.filter_by(email=email).first()
        existing_user1 = Users.query.filter_by(handle=handle).first()
        if existing_user:
            error = "Email already exists. Please choose a different one."
            return render_template('signup.html', error=error)
        elif existing_user1:
            error = "Handle already exists. Please choose a different one."
            return render_template('signup.html', error=error)
        elif password1 != password2:
            error = "Passwords do not match. Please try again."
            return render_template('signup.html', error=error,current_user=current_user)
        else: # all ok save record to our database
            new_user = Users(email=email, 
                            password=password1,
                            username = username,
                            handle = handle,
                            profile_image = "profile.png",
                            verified = False,
                            verification_token = str(uuid.uuid4())
                            )
            db.session.add(new_user)  
            db.session.commit()  
            session["user_email"] = email
            send_welcome_email(new_user)
            
            return redirect(url_for('home'))
    return render_template('signup.html',current_user=current_user,error="")

@app.route('/channel/')
@app.route('/channel/@<string:handle>', methods=['GET'])
def channel(handle=None):
    current_user = get_current_user_record()
    if current_user is None:
        return redirect(url_for('login'))
    if handle == None:
        variable = current_user
        handle=current_user
        user_videos = Videos.query.filter_by(uploaded_by=current_user.id).order_by(Videos.id.desc()).all()
        print("jm,hjh",current_user.handle)
    else:
        print(handle)
        user = Users.query.filter_by(handle=handle).first()
        if user is None:
            return redirect(url_for('home'))
        variable = user
        user_videos = Videos.query.filter_by(uploaded_by=user.id).order_by(Videos.id.desc()).all()
        print("OOOP",user)
        print("jm,hjh",current_user.handle)
    channel_videos = []
    for video in user_videos:
        if os.path.exists(os.path.join(videoUpload, video.filename)):
            channel_videos.append({
                "id": video.id,
                "filename": video.filename,
                "title": video.title,
                "ext": video.filename.rsplit(".", 1)[1].lower() if "." in video.filename else "",
                "uploaded_by": variable.handle,
                "date_added": time_formater(video.date_uploaded),
            })
    return render_template('channel.html', current_user=current_user, videos=channel_videos, channel_user=variable)
    # return render_template('channel.html',handle=handle)

@app.route('/search/')
def search(): 
    current_user = get_current_user()

    return render_template('search.html',videos=get_uploaded_videos(),current_user=current_user)

# Route for the dashboard page
@app.route('/watch/<string:id>', methods=['GET'])
def watch(id=None):
    current_user = get_current_user_record()
    videoid = id

    video = None
    if videoid:
        if videoid.isdigit():
            video = Videos.query.get(int(videoid))
        else:
            video = Videos.query.filter_by(filename=videoid).first()

    if video and current_user:
        record_user_history(current_user.id, video.id)

    return render_template('watch.html', tag=videoid, current_user=current_user)

@app.route('/terms-of-service/')
def tos():
    current_user = get_current_user()
    return render_template('tos.html',current_user=current_user)

@app.route('/privacy-policy/')
def privacypolicy():
    current_user = get_current_user()
    return render_template('privacy-policy.html',current_user=current_user)

@app.route('/cookies-usage/')
def cookie_usage():
    current_user = get_current_user()
    return render_template('tos.html',current_user=current_user)

@app.route('/history/')
def history(): 
    current_user = get_current_user_record()
    if current_user is None:
        return redirect(url_for('login'))

    history_rows = UserHistory.query.filter_by(user_id=current_user.id).order_by(UserHistory.viewed_at.desc()).all()
    videos = []
    for row in history_rows:
        video = Videos.query.get(row.video_id)
        if not video:
            continue
        if not os.path.exists(os.path.join(videoUpload, video.filename)):
            continue
        uploader = Users.query.get(video.uploaded_by)
        videos.append({
            "id": video.id,
            "filename": video.filename,
            "title": video.title,
            "description": video.description,
            "uploaded_by": uploader.handle if uploader else "unknown",
            "date_added": time_formater(video.date_uploaded),
        })
    return render_template('history.html', videos=videos, current_user=current_user)
@app.route('/channel/upload', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
def upload(): 
    current_user = get_current_user_record()  
    if current_user is None:
        return redirect(url_for("login"))  
    if request.method == "POST":
        title = request.form.get("title").strip()
        description = request.form.get("description", "").strip()
        thumbnail = request.files.get("image")
        file = request.files.get("video")
        if title == "":
            return render_template('editor.html', error="Video title is required.", current_user=current_user.email)
        if description == "":
            return render_template('editor.html', error="Video description is required.", current_user=current_user.email)
        if thumbnail is None or thumbnail.filename == "":
            return render_template('editor.html', error="Thumbnail file is required.", current_user=current_user.email)
        if file is None or file.filename == "":
            return render_template('editor.html', error="Video file is required.", current_user=current_user.email)
        if "." not in thumbnail.filename:
            return render_template('editor.html', error="Invalid thumbnail file format.", current_user=current_user.email)
        thumbnail_extension = thumbnail.filename.rsplit(".", 1)[1].lower()
        if thumbnail_extension not in ["png", "jpg", "webp", "jpeg"]:
            return render_template('editor.html', error="Thumbnail must be a PNG, JPG, JPEG, or WEBP file.", current_user=current_user.email)
        if file.filename == "":
            return render_template('editor.html', error="Import a file.", current_user=current_user.email)  
        if "." not in file.filename:
            return render_template('editor.html', error="Invalid video file format.", current_user=current_user.email)  
        extension = file.filename.rsplit(".", 1)[1].lower()
        print(file, extension)
        if extension not in allowedFormats:
            return render_template('editor.html', error="Video must be an MP4, MKV, MOV, M4P, or M4V file.", current_user=current_user.email) 

        safe_name = secure_filename(file.filename)  
        new_video = Videos(
            title=safe_name,  
            description=f"Uploaded by {current_user.handle}",  
            filename="pending",  
            uploaded_by=current_user.id  
        )
        db.session.add(new_video)
        db.session.commit()  

        final_filename = f"{new_video.id}.{extension}"  
        new_video.title = safe_name
        new_video.filename = final_filename
        db.session.commit() 
        file.save(os.path.join(videoUpload, final_filename))  
        return render_template('editor.html', success="Video uploaded successfully.", current_user=current_user.email)  
    return render_template('editor.html', current_user=current_user.email)  

@app.errorhandler(404)
def page_not_found(e):
    current_user = get_current_user()
    return render_template('error.html', errQuote="This content is not availible.", error="404",current_user=current_user), 404

@app.errorhandler(403)
def restricted_page(e):
    current_user = get_current_user()
    return render_template('error.html', errQuote="This content is not availible.", error="404",current_user=current_user), 403
##################################################################

# None insite coding related ##################################################################

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_welcome_email(user):

    msg = Message(
        'Welcome to FurTube',
        recipients=[user.email],
        sender=app.config['MAIL_USERNAME']
    )
    msg.html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 5px; background-color: #101010;">
    <div style="background-color: #333333; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h1 style="color: #965209; margin-bottom: 20px;">Welcome to FurTube</h1>
        <img src="https://www.furtu.be/static/images/orange_main_full_logo.png" alt="Furtube Logo" style="width: 300px; margin:auto; display:block;">
        <h4 style="color: #666; line-height: 1.6;">
            Hello {user.username},<br><br>
            You are now a member of the <b>furtu.be</b> community.<br><br>
            In furtube you can upload all sorts of fur-y activity, your cat doing silly things, maybe a fantastic drawing of your pet, your dog chasing its tail or even your hampster running on the wheel while reaching speeds of a race car!
            Thank you for signing up to our site!
            <br><br> 
            Have fun!
            And incase you haven't read the terms of service, which you definately didn't please read the <a href="furtu.be/terms-of-service/">Terms Of Service</a>
        </h4>
        <p style="color: #999; font-size: 15px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
            If you did not sign-up to furtube using this e-mail contact our <a href="furtu.be/support">support</a>. Thank you.
        </p>
    </div>
</div>

    '''
    Thread(target=send_async_email, args=(app, msg)).start()
####################################################################################################################################



# zrok reservd key = r4ymbmvtbj2c










if __name__ == '__main__':
    app.run(debug=True, host='192.168.1.2', port=5000)
