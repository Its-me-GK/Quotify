from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from flask_mail import Mail
import os
import math
import ssl
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

with open('config.json','r') as c:
    params = json.load(c)["params"]

app = Flask(__name__)

secret_key = os.environ.get('SECRET_KEY')
if not secret_key and params['local_server'] == "True":
    secret_key = "local-development-secret-change-me"
if not secret_key:
    raise RuntimeError("SECRET_KEY must be configured in the production environment")
app.secret_key = secret_key

app.config.update(
    UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER'),
    SESSION_COOKIE_SECURE=params['local_server'] != "True",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME=os.environ.get('GMAIL_USER'),
    MAIL_PASSWORD=os.environ.get('GMAIL_PASSWORD'),
)

if params['local_server'] == "True":
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('LOCAL_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('PRODUCTION_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Aiven MySQL TLS: verify the server certificate using the project CA.
ca_path = os.path.join(app.root_path, 'certs', 'aiven-ca.pem')
ssl_context = ssl.create_default_context(cafile=ca_path)
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 280,
    'pool_timeout': 10,
    'connect_args': {
        'ssl': ssl_context
    }
}

mail = Mail(app)
db = SQLAlchemy(app)

class Contacts(db.Model):
    __tablename__ = 'Contacts'
    srno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phoneno = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(254), nullable=False)

class Posts(db.Model):
    __tablename__ = 'Posts'
    srno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(30), nullable=False)
    slug = db.Column(db.String(20), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    tagline = db.Column(db.String(30), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(15), nullable=True)

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

@app.route("/")
def home():
    posts = Posts.query.order_by(Posts.srno.desc()).all()
    last = math.ceil(len(posts) / int(params['no_of_posts']))
    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1
    page = int(page)
    if last and page > last:
        page = last
    posts = posts[(page-1)*int(params['no_of_posts']):page*int(params['no_of_posts'])]
    if page == 1:
        prev = "#"
        next = "/?page=2" if last > 1 else "#"
    elif page == last:
        prev = "/?page=" + str(page-1)
        next = "#"
    else:
        prev = "/?page=" + str(page-1)
        next = "/?page=" + str(page+1)
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        msg = request.form.get('msg', '').strip()
        entries = Contacts(name=name, phoneno=phone, message=msg, date=datetime.now(), email=email)
        db.session.add(entries)
        db.session.commit()
        mail.send_message(
            'New message from ' + name,
            sender=os.environ.get('GMAIL_USER'),
            recipients=[os.environ.get('GMAIL_USER')],
            reply_to=email,
            body=msg + '\n' + phone,
        )
    return render_template('contact.html', params=params)

@app.route("/about")
def about():
    return render_template('about.html', params=params)

@app.route("/uploader", methods=['GET', 'POST'])
def upload():
    if not ('user' in session and session['user'] == os.environ.get('ADMIN_USERNAME')):
        return "Forbidden", 403
    if request.method == 'POST':
        file = request.files.get('file1')
        if not file or not file.filename:
            return "No file selected", 400
        filename = secure_filename(file.filename)
        if not filename:
            return "Invalid filename", 400
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return "File uploaded successfully"
    return render_template('uploader.html', params=params)

@app.route("/edit/<string:srno>", methods=['GET', 'POST'])
def edit_post(srno):
    if not ('user' in session and session['user'] == os.environ.get('ADMIN_USERNAME')):
        return "Forbidden", 403
    if request.method == 'POST':
        title = request.form.get("title")
        tline = request.form.get("tline")
        slug = request.form.get("slug")
        content = request.form.get("content")
        img_file = request.form.get("img_file")
        date = datetime.now()
        if srno == '0':
            post = Posts(title=title, tagline=tline, slug=slug, content=content, img_file=img_file, date=date)
            db.session.add(post)
            db.session.commit()
            return redirect("/dashboard")
        post = Posts.query.filter_by(srno=srno).first()
        if not post:
            return "Post not found", 404
        post.title = title
        post.tagline = tline
        post.slug = slug
        post.content = content
        post.img_file = img_file
        post.date = date
        db.session.commit()
        return redirect("/edit/" + srno)
    post = Posts.query.filter_by(srno=srno).first()
    return render_template('edit.html', params=params, post=post, srno=srno)

@app.route("/dashboard", methods=['GET', 'POST'])
def login():
    if 'user' in session and session['user'] == os.environ.get('ADMIN_USERNAME'):
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts=posts)
    if request.method == 'POST':
        uname = request.form.get('uname')
        upass = request.form.get('pass')
        if uname == os.environ.get('ADMIN_USERNAME') and upass == os.environ.get('ADMIN_PASSWORD'):
            session['user'] = uname
            return redirect('/dashboard')
    return render_template('login.html', params=params)

@app.route("/post/<string:post_slug>")
def fetch_post(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    if not post:
        return "Post not found", 404
    return render_template('post.html', params=params, post=post)

@app.route("/delete/<string:srno>", methods=['GET'])
def delete_post(srno):
    if not ('user' in session and session['user'] == os.environ.get('ADMIN_USERNAME')):
        return "Forbidden", 403
    post = Posts.query.filter_by(srno=srno).first()
    if not post:
        return redirect("/dashboard")
    db.session.delete(post)
    db.session.commit()
    return redirect("/dashboard")

@app.route("/logout")
def remove_session():
    session.pop('user', None)
    return redirect("/dashboard")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
