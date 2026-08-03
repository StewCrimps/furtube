from datetime import datetime
from flask import Flask, render_template, request, abort, session, redirect,url_for
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
import os
import uuid



app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'haha guess the key buh')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
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
    username = db.Column(db.String(20),nullable=False) # The decored version of handle Example "TheUSERNAme21"
    handle = db.Column(db.String(25),nullable=False,unique=True) #The stripped version of username used to find the user through the url "theusername21"
    email = db.Column(db.String(20), nullable=False,unique=True)
    password = db.Column(db.String(15), nullable=False)  
    profile_image = db.Column(db.String(30))
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

##################################################################

# Site Routes ##################################################################
# Route for the index page
@app.route('/')
def home(): 
    db_videos = Videos.query.order_by(Videos.id.desc()).all()
    fs_videos = get_uploaded_videos()
    comb = []
    for v in db_videos:
        comb.append({
            "source": "db",
            "id": v.id,
            "title": v.title,
            "description": v.description,
        })
    for v in fs_videos:
        comb.append({
            "source": "fs",
            "filename": v.get("filename"),
            "title": v.get("title"),
            "ext": v.get("ext"),
        })
    current_user = get_current_user()
    return render_template('index.html',current_user=current_user,videos=comb)

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
        username = request.form['username']
        handle = request.form['handle'].lower()
        for i in handle:
            if i>='a' and i<='z' or i in ['_','.','-'] or i.isdigit():   
                print("Handle is fine")
            else:
                error = "Handle cannot contain special characters, accepted a-z , 0-9 and '.''-''_'"
                return render_template('signup.html', error=error)
        email = request.form['email']
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
                            username = request.form['username'],
                            handle = request.form['handle'],
                            profile_image = "profile.png",
                            verified = False,
                            verification_token = str(uuid.uuid4())
                            )  
            db.session.add(new_user)  
            db.session.commit()  # add to database
            session["user_email"] = email
            send_welcome_email(new_user)
            
            return redirect(url_for('home'))
    return render_template('signup.html',current_user=current_user,error="agagag")

@app.route('/channel/')
# @app.route('/channel/@<string:id>')
def channel():
    # handle=id
    current_user = get_current_user_record()
    if current_user is None:
        return redirect(url_for('login'))
    user_videos = Videos.query.filter_by(uploaded_by=current_user.id).order_by(Videos.id.desc()).all()
    channel_videos = []
    for video in user_videos:
        if os.path.exists(os.path.join(videoUpload, video.filename)):
            channel_videos.append({
                "filename": video.filename,
                "title": video.title,
                "ext": video.filename.rsplit(".", 1)[1].lower() if "." in video.filename else "",
                "uploaded_by": current_user.handle,
            })
    return render_template('channel.html', current_user=current_user, videos=channel_videos, channel_user=current_user)
    # return render_template('channel.html',handle=handle)

@app.route('/search/')
def search(): 
    current_user = get_current_user()

    return render_template('search.html',videos=get_uploaded_videos(),current_user=current_user)

# Route for the dashboard page
@app.route('/watch/<string:id>')
def watch():
    videoid=id
    print(videoid)
    current_user = get_current_user()
    return render_template('watch.html',tag=videoid,current_user=current_user)

@app.route('/terms-of-service/')
def tos():
    current_user = get_current_user()
    return render_template('tos.html',current_user=current_user)

@app.route('/privacy-policy/')
def privacypolicy():
    current_user = get_current_user()
    return render_template('privacy-policy.html',current_user=current_user)

@app.route('/history/')
def history(): 
    current_user = get_current_user()
    return render_template('history.html',videos=get_uploaded_videos(),current_user=current_user)

@app.route('/upload', methods=['GET', 'POST'])
def upload(): 
    current_user = get_current_user_record()  # ===> Προστέθηκε η φόρτωση του συνδεδεμένου user από τη βάση. Γιατί: μόνο ένας συνδεδεμένος χρήστης επιτρέπεται να ανεβάζει και πρέπει να γνωρίζουμε τον uploader για να τον αποθηκεύσουμε στο record.
    if current_user is None:
        return redirect(url_for("login"))  # ===> Άλλαξε το redirect να χρησιμοποιεί τον logged-in έλεγχο μέσω του current_user_record. Γιατί: αυτό κάνει το upload να ανοίγει μόνο για authenticated χρήστες, άρα και admin/όλοι οι συνδεδεμένοι χρήστες μπορούν να έχουν πρόσβαση.
    if request.method == "POST":
        file = request.files["video"]  # ===> Έμεινε η ανάκτηση του αρχείου από το form. Γιατί: αυτό είναι το ίδιο upload payload που θα αποθηκεύσουμε.
        if file.filename == "":
            return render_template('editor.html', error="Import a file.", current_user=current_user.email)  # ===> Προστέθηκε current_user στο render_template. Γιατί: η σελίδα editor χρειάζεται να γνωρίζει ποιος χρήστης είναι συνδεδεμένος ώστε να παραμείνει σωστά το UI state.
        if "." not in file.filename:
            return render_template('editor.html', error="Invalid file format.", current_user=current_user.email)  # ===> Προστέθηκε έλεγχος για files χωρίς extension. Γιατί: αποτρέπεται να διασπάσει το αρχείο σε λάθος extension.
        extension = file.filename.rsplit(".", 1)[1].lower()
        print(file, extension)
        if extension not in allowedFormats:
            return render_template('editor.html', error="Invalid file format.", current_user=current_user.email)  # ===> Προστέθηκε το current_user στα error responses. Γιατί: η σελίδα να μην χάσει το user context σε λάθος διαδρομή.

        safe_name = secure_filename(file.filename)  # ===> Προστέθηκε ασφαλής επεξεργασία ονόματος αρχείου. Γιατί: αποφεύγονται ασφαλιστικά/evasion θέματα και κρατιέται το αρχικό όνομα μόνο ως metadata.
        new_video = Videos(
            title=safe_name,  # ===> Τοποθέτησε το αρχικό όνομα ως title του video στο DB. Γιατί: κρατάμε το όνομα που ανέβασε ο χρήστης για να το δείχνουμε στην εφαρμογή.
            description=f"Uploaded by {current_user.handle}",  # ===> Προστέθηκε description με τον uploader handle. Γιατί: για να κρατάμε ποιος ανέβασε το βίντεο.
            filename="pending",  # ===> Προστέθηκε placeholder filename που θα ενημερωθεί μετά το commit. Γιατί: το id του DB δεν υπάρχει μέχρι να δημιουργηθεί το record, άρα το final filename αποτελείται από το ID.
            uploaded_by=current_user.id  # ===> Προστέθηκε αναφορά στον χρήστη που ανέβασε το βίντεο. Γιατί: το DB αποθηκεύει τον uploader και η σχέση παραμένει ξεκάθαρη.
        )
        db.session.add(new_video)
        db.session.commit()  # ===> Δημιουργήθηκε το DB record πρώτα ώστε να πάρουμε το final id. Γιατί: το τελικό όνομα του αρχείου θα είναι το id του video.

        final_filename = f"{new_video.id}.{extension}"  # ===> Δημιουργήθηκε το τελικό όνομα βάσει του id του video και της αρχικής επέκτασης. Γιατί: αυτό είναι το ζητούμενο naming policy: κάθε video θα παίρνει όνομα το id του και την επέκταση που ανέβασε ο χρήστης.
        new_video.title = safe_name
        new_video.filename = final_filename
        db.session.commit()  # ===> Ενημερώθηκε το record με το τελικό filename. Γιατί: το αρχείο και το DB θα μοιράζονται το ίδιο αναγνωριστικό.

        file.save(os.path.join(videoUpload, final_filename))  # ===> Αποθηκεύεται το αρχείο στο static/videos με το τελικό id-based όνομα. Γιατί: έτσι το front-end θα βλέπει το βίντεο και το system θα αποθηκεύει ακριβώς αυτό το όνομα.
        return render_template('editor.html', success="Video uploaded successfully.", current_user=current_user.email)  # ===> Προστέθηκε επιτυχές μήνυμα. Γιατί: ο χρήστης να δει ότι το upload ολοκληρώθηκε.
    return render_template('editor.html', current_user=current_user.email)  # ===> Προστέθηκε current_user στο GET request. Για γιατί: να υπάρχει σωστό user context και να μην καταρρεύσει το template.

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