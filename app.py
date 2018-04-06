from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
# from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


app = Flask(__name__)

#Config for MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'YOURPASSWORD'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
#init MySQL DB
mysql = MySQL(app)

# used data file to test displaying articles
# Articles = Articles()


# home route
@app.route('/')
def index():
    return render_template('home.html')

# about route
@app.route('/about')
def about():
    return render_template('about.html')

# show all articles route
@app.route('/articles')
def articles():
    # create cursor
    cur = mysql.connection.cursor()

    #Get articles
    result = cur.execute("SELECT * FROM articles")

    #fetchall() is sql syntax - returns everything in dictionary form 
    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles = articles)
    else:
        msg = 'No Article Found'
        return render_template('articles.html', msg=msg)

    # Close db connection
    cur.close()

# can add variables for the route if it is dynamic
@app.route('/article/<string:id>/')
def article(id):
    # create cursor
    cur = mysql.connection.cursor()

    #Get articles
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    #fetchall() is sql syntax - returns everything in dictionary form 
    article = cur.fetchone()

    return render_template('article.html', article=article)


# register form class using wtforms
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# user register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    # get form fields and encrypt password
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        #create db cursor and execute query
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        #commit to DB
        mysql.connection.commit()

        #close DB connection
        cur.close()

        #send success flash message and redirect
        flash('You are now registered and can now login', 'success')
        return redirect(url_for('login'))


    return render_template('register.html', form=form)

#User login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # get form fields from the request object not wtforms
        username = request.form['username']
        password_candidate = request.form['password']

        # create db cursor
        cur = mysql.connection.cursor()

        # get user by username from mysql database
        result = cur.execute('SELECT * FROM users WHERE username = %s', [username])

        if result > 0:
            # get stored hash password if the cursor finds something
            # fetchone is sql syntax - returns the first match from the cursor query
            # cursor default changed to dict so dict syntax can be used to get record fields
            data = cur.fetchone()
            password = data['password']

            # compare password candidate to actual password
            if sha256_crypt.verify(password_candidate, password):
                # if passwords match send user to dashboard with success message
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error) 

            # close db cursor once username queried and passwords compared
            cur.close()

        # return error if input username not found  
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')



#Check if user logged
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unathorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout route
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard route
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # create cursor
    cur = mysql.connection.cursor()

    #Get articles
    result = cur.execute("SELECT * FROM articles")

    #fetchall() is sql syntax - returns everything in dictionary form 
    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles = articles)
    else:
        msg = 'No Article Found'
        return render_template('dashboard.html', msg=msg)

    # Close db connection
    cur.close()

# Article form class using wtforms
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = StringField('Body', [validators.Length(min=30)])

# Add Article route
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # create cursor
        cur = mysql.connection.cursor()

        # add record into articles table with form fields
        # could also get the user's actual name
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))

        # commit to db
        mysql.connection.commit()

        # close db connection, create message and send user back to dashboard
        cur.close()
        flash('Article Created', 'success')
        return redirect(url_for('dashboard'))

    # just return the add article form if the request method is GET
    return render_template('add_article.html', form=form)

# Edit Article route
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # create cursor to get current values
    cur = mysql.connection.cursor()

    # get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", (id))
    article = cur.fetchone()

    # get form and populate fields
    form = ArticleForm(request.form)
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        # set new values using what the user changed
        title = request.form['title']
        body = request.form['body']

        # create cursor
        cur = mysql.connection.cursor()

        # add record into articles table with form fields
        # could also get the user's actual name
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id = %s", (title, body, id))

        # commit to db
        mysql.connection.commit()

        # close db connection, create message and send user back to dashboard
        cur.close()
        flash('Article Updated', 'success')
        return redirect(url_for('dashboard'))

    # just return the add article form if the request method is GET
    return render_template('edit_article.html', form=form)

#delete article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    #create cursor
    cur = mysql.connection.cursor()

    #execute query
    cur.execute('DELETE FROM articles WHERE id = %s', (id))

    # commit to db
    mysql.connection.commit()

    # close db connection, create message and send user back to dashboard
    cur.close()
    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))

# debug mode hot reloads the web page
if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)