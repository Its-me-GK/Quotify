from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from flask_mail import Mail
import os
import math
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

with open('config.json','r') as c: #Quotify/config.json
    params = json.load(c)["params"] #loading the params in the variable 

app = Flask(__name__)
app.secret_key = "secret-key-here"
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'ssl': {
            # For mysqlclient, an empty 'ssl' dictionary often works to initiate TLS.
            # If you want to explicitly ensure verification (like VERIFY_CA),
            # you'd need the CA certificate file from Aiven and use `ca` and `verify_mode`.
            # Example for full verification (if you downloaded aiven_ca.pem):
            # 'ca': os.path.join(app.root_path, 'certs', 'aiven_ca.pem'),
            # 'verify_mode': ssl.CERT_REQUIRED # Requires `import ssl` at the top
            #
            # For most Aiven deployments, where the connection string might have previously
            # included `?sslmode=REQUIRED`, simply providing an empty `ssl` dict here
            # or relying on the server's requirement for SSL often suffices once the URL param is gone.
        }
        # You can also set other mysqlclient options here, e.g., 'read_timeout': 10
    }
}

app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = os.environ.get('GMAIL_USER'),
    MAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
)
mail = Mail(app)

if(params['local_server']== "True" ):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('LOCAL_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('PRODUCTION_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    


db = SQLAlchemy(app)

class Contacts(db.Model):
    __tablename__ = 'Contacts'
    srno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phoneno = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)


class Posts(db.Model):
    __tablename__ = 'Posts'
    srno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(30), nullable=False)
    slug = db.Column(db.String(20), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    tagline = db.Column(db.String(30), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(15), nullable=True)
    
@app.route("/")
def home():
        posts = Posts.query.filter_by().all()
        last = math.ceil(len(posts)/int(params['no_of_posts']))
        page = request.args.get('page')
        if (not str(page).isnumeric()):
            page = 1
        page = int(page)
        posts = posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+ int(params['no_of_posts'])]
        if page==1:
            prev = "#"
            next = "/?page="+ str(page+1)
        elif page==last:
            prev = "/?page="+ str(page-1)
            next = "#"
        else:
            prev = "/?page="+ str(page-1)
            next = "/?page="+ str(page+1)
        # posts = Posts.query.filter_by().all()[0:params['no_of_posts']]
        return render_template('index.html',params=params, posts= posts, prev=prev, next = next)


@app.route("/contact", methods = ['GET', 'POST'])
def contact():
    if(request.method=='POST'):
        '''Add entry to the database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        msg = request.form.get('msg')
        entries = Contacts(name=name, phoneno = phone, message = msg, date= datetime.now(),email = email )
        db.session.add(entries)
        db.session.commit()
        mail.send_message(
            'New message from ' + name,
            sender = email,
            recipients =[os.environ.get('GMAIL_USER')], 
            body = msg + '\n' +phone,
    )
    return render_template('contact.html',params=params)


@app.route("/about")
def about():
    return render_template('about.html',params=params)

@app.route("/uploader", methods=['GET','POST'])
def upload():
    if('user' in session and session['user'] == os.environ.get('ADMIN_USERNAME')):
        if request.method == 'POST':
            file = request.files['file1']
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
            return "File uploaded successfully"

@app.route("/edit/<string:srno>", methods = ['GET', 'POST'])
def edit_post(srno):
    if('user' in session and session['user'] == os.environ.get('ADMIN_USERNAME')):
        if request.method == 'POST':
            title = request.form.get("title")
            tline = request.form.get("tline")
            slug = request.form.get("slug")
            content = request.form.get("content")
            img_file = request.form.get("img_file")
            date = datetime.now()

            if srno == '0':
                post = Posts(title=title,tagline=tline,slug= slug, content=content, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(srno=srno).first()
                post.title = title
                post.tagline = tline
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect("/edit/"+srno)
        post = Posts.query.filter_by(srno=srno).first()
        return render_template('edit.html',params=params, post=post, srno=srno)


@app.route("/dashboard", methods = ['GET', 'POST'])
def login():
    if ('user' in session and session['user'] == os.environ.get('ADMIN_USERNAME')) :
        posts = Posts.query.all()
        return render_template('dashboard.html', params= params, posts=posts)

    if (request.method =='POST'):
        uname = request.form.get('uname')
        upass = request.form.get('pass')
        if (uname == os.environ.get('ADMIN_USERNAME') and upass == os.environ.get('ADMIN_PASSWORD')):
            session['user'] = uname
            posts = Posts.query.all()
            return render_template('dashboard.html', params= params, posts=posts)
    
    return render_template('login.html',params=params)


@app.route("/post/<string:post_slug>", methods=['GET'])
def fetch_post(post_slug):
    post = Posts.query.filter_by(slug= post_slug).first()
    return render_template('post.html',params=params, post = post)


@app.route("/delete/<string:srno>", methods=['GET'])
def delete_post(srno):
    if ('user' in session and session['user'] == os.environ.get('ADMIN_USERNAME')) :
        post = Posts.query.filter_by(srno=srno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")


@app.route("/logout")
def remove_session():
    session.pop('user')
    return redirect("/dashboard")

app.run(debug=True)