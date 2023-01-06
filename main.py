from datetime import datetime

from flask import Flask, render_template, redirect, url_for, flash, request, abort
from functools import wraps
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_migrate import Migrate
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LogInForm, CommentForm
from flask_gravatar import Gravatar

# # GET YEAR FOR COPYRIGHT PURPOSES
year = datetime.today().strftime("%Y")

# # INITIALIZE FLASK APP
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##DATABASE CONNECTION AND CONFIGURATION.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# # CREATE LoginManager OBJECT.
login_manager = LoginManager()
login_manager.init_app(app)


# # INITIALIZE GRAVATAR
gravatar = Gravatar(app,
                    size=150,
                    rating='g',
                    default='robohash',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts_written = relationship("BlogPost", back_populates="author")
    comments_written = relationship("Comments", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create ForeignKey, "users.id". The "users" refers to the tablename in User class.
    author_id = Column(db.Integer, ForeignKey("users.id"))
    # Create reference to the User object. The "posts_written" refers to the posts_written property in User class.
    author = relationship("User", back_populates="posts_written")
    post_comments = relationship("Comments", back_populates="post_commented")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class Comments(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    comment_author_id = Column(db.Integer, ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments_written")

    post_ref = Column(db.Integer, ForeignKey("blog_posts.id"))
    post_commented = relationship("BlogPost", back_populates="post_comments")
# db.create_all()


# # ADMIN-ONLY decorator.
def admin_only(function):
    @wraps(function)
    def wrapper_admin_only(*args, **kwargs):
        if current_user.id != 1:
            return abort(403, "Access Denied, Sucka!")
        return function(*args, **kwargs)
    return wrapper_admin_only


# # DEFINE user_loader.
@login_manager.user_loader
def user_loader(user_id):
    """Given *user_id*, return the associated user object."""
    return User.query.get(user_id)


# # ROUTING
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user, year=year)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if request.method == "POST":
        if User.query.filter_by(email=request.form.get("email")).first():
            # User already exists.
            flash("You've already signed up with that email. Log in, instead.")
            return redirect(url_for('login'))
        hashed_and_salted_pswd = generate_password_hash(
            request.form.get("password"),
            method="pbkdf2:sha256",
            salt_length=8
        )
        new_user = User(
            name=request.form.get("name"),
            email=request.form.get("email"),
            password=hashed_and_salted_pswd
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('get_all_posts'))

    return render_template("register.html", form=form, current_user=current_user, year=year)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LogInForm()
    error = None
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Find user by email.
        user = User.query.filter_by(email=email).first()
        # If email doesn't exist:
        if not user:
            flash("That email doesn't exist! Stop wasting my time! 😠")
            return redirect(url_for('login'))
        # If password doesn't match:
        elif not check_password_hash(user.password, password):
            flash("Wrong password, Genius... 🙄")
            return redirect(url_for('login'))
        # If email & password match:
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))

    return render_template("login.html", form=form, error=error, current_user=current_user, year=year)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts', current_user=current_user))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()

    if not current_user.is_authenticated:
        flash("Please login to view posts.")
        return redirect(url_for('login'))
    elif comment_form.validate_on_submit():
        new_comment = Comments(
            text=comment_form.text.data,
            comment_author=current_user,
            post_ref=post_id,
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))

    post_comments = Comments.query.all()
    return render_template("post.html", post=requested_post, form=comment_form, comments=post_comments,
                           gravatar=gravatar, current_user=current_user, year=year)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user,  year=year)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user, year=year)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user, year=year)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user, year=year)


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
