from datetime import datetime
from flask import Flask, render_template, request, abort, session, redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
import os



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

class Videos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    # publisher = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_uploaded = db.Column(db.DateTime, default=datetime.utcnow)
    

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

##################################################################

# Site Routes ##################################################################
# Route for the index page
@app.route('/')
def home(): 
    current_user = get_current_user()
    return render_template('index.html',videos=get_uploaded_videos(),current_user=current_user)

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
            session["user_email"] = email
            return redirect(url_for('home'))
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
        handle= request.form['handle']
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
                            profile_image = "profile.png"
                            )  
            db.session.add(new_user)  
            db.session.commit()  # add to database
            session["user_email"] = email
            send_welcome_email(new_user)
            
            return redirect(url_for('home'))
    return render_template('signup.html',current_user=current_user,error="agagag")

@app.route('/channel/')
def channel():

    current_user = get_current_user()
    return render_template('channel.html')

@app.route('/search/')
def search(): 

    return render_template('search.html',videos=get_uploaded_videos())

# Route for the dashboard page
@app.route('/watch/')
def watch():
    videoid = request.args.get('watch')
    print(videoid)
    current_user = get_current_user()
    return render_template('watch.html',tag=videoid,current_user=current_user)

@app.route('/terms-of-service/')
def tos():
    current_user = get_current_user()
    return render_template('tos.html',current_user=current_user)

@app.route('/history/')
def history(): 
    current_user = get_current_user()
    return render_template('history.html',videos=get_uploaded_videos(),current_user=current_user)

@app.route('/upload', methods=['GET', 'POST'])
def upload(): 
    if "user_email" not in session:
        return redirect (url_for("login"))
    if request.method == "POST":
        file = request.files["video"]
        if file.filename == "":
            return render_template('editor.html', error="Import a file.")
        extension = file.filename.rsplit(".", 1)[1].lower()
        print (file, extension)
        if extension not in allowedFormats:
            return render_template('editor.html', error="Invalid file format.")
    return render_template('editor.html')

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
        <img src="https://r4ymbmvtbj2c.share.zrok.io/static/images/orange_main_full_logo.png" alt="Furtube Logo" style="width: 300px; margin:auto; display:block;">
        <h4 style="color: #666; line-height: 1.6;">
            Hello {user.username},<br><br>
            You are now a member of the <b>furtu.be</b> community.<br><br>
            In furtube you can upload all sorts of fur-y activity, your cat doing silly things, maybe a fantastic drawing of your pet, your dog chasing its tail or even your hampster running on the wheel while reaching speeds of a race car!
            Thank you for signing up to our site!
            <br><br> 
            Have fun!
            And incase you haven't read the terms of service, which you definately didn't please read the <a href="localhost:5000/terms-of-service/">Terms Of Service</a>
        </h4>
        <p style="color: #999; font-size: 15px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
            If you did not sign-up to furtube using this e-mail contact our <a href="localhost:5000/login">support</a>. Thank you.
        </p>
    </div>
</div>

    '''
    Thread(target=send_async_email, args=(app, msg)).start()
####################################################################################################################################



# zrok reservd key = r4ymbmvtbj2c










if __name__ == '__main__':
    app.run(debug=True)
