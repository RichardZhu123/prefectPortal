import os, sqlite3, re

from flask import Flask, flash, redirect, render_template, request, session, url_for, send_from_directory
# from flask_socketio import SocketIO, emit
# from flask_session import Session
from functions import *
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from tempfile import mkdtemp

# File directory
FILE_DIRECTORY = '/files'

# Configure application
app = Flask(__name__)

app.secret_key = 'ilikedogs'

# Templates auto-reload
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Clear cache after
@app.after_request
def after_request(response):
    response.headers['Cache-Control'] = "no-cache, no-store, must-revalidate"
    response.headers['Expires'] = 0
    response.headers['Pragma'] = 'no-cache'
    return response

# Use filesystem instead of signed cookies
app.config['SESSION_FILE_DIR'] = mkdtemp()
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'


conn = sqlite3.connect('prefects.db', check_same_thread=False)
db = conn.cursor()


@app.route('/')
@login_required
def index():
    ''' Display user dashboard '''

    db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    creds = db.fetchall()

    if creds[0][14] == 'Executive':
        return redirect(url_for('indexe'))

    db.execute("SELECT * FROM completed WHERE id = ?", (session['user_id'],))
    events = db.fetchall()

    db.execute("SELECT * FROM signup WHERE id = ?", (session['user_id'],))
    future = db.fetchall()

    prefect = dict([
        ('name', creds[0][2]),
        ('credits', float(creds[0][4])),
        ('events', [(event[0], event[2], event[3]) for event in events]),
        ('leader', creds[0][8]),
        ('registered', [(event[0], event[2], lookup(event[1], event[2])['value']) for event in future]),
        ('position', creds[0][14])
        ])

    userId = session['user_id']
    return render_template('index.html', prefect=prefect, id = userId)

@app.route('/indexe')
@login_required
def indexe():
    ''' Display user dashboard '''

    db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    creds = db.fetchall()

    if creds[0][14] == 'Prefect':
        return redirect(url_for('index'))

    userGroup = creds[0][8]

    db.execute('SELECT * FROM users WHERE leader = ? AND id != ?', (userGroup, session['user_id']))
    members = db.fetchall()

    prefect = dict([
        ('name', creds[0][2]),
        ('position', creds[0][14])
        ])

    prefects = []

    for member in members:
        info = dict([
        ('name', member[2]),
        ('credits', member[4]),
        ('gender', member[6]),
        ('grade', member[5]),
        ('size', member[9]),
        ('email', member[13]),
        ('home', member[11]),
        ('cell', member[12]),
        ('dietary', member[7]),
        ('status', member[10])
        ])

        db.execute("SELECT * FROM completed WHERE id = ?", (member[0],))
        completed = db.fetchall()

        db.execute("SELECT * FROM signup WHERE id = ?", (member[0],))
        upcoming = db.fetchall()

        info['completed'] = [(event[0], event[2], event[3]) for event in completed]
        info['upcoming'] = [(event[0], event[2], event[3]) for event in upcoming]

        prefects.append(info)

    total = {
        'male': 0,
        'female': 0,
        'eleven': 0,
        'twelve': 0,
        'xs': 0,
        's': 0,
        'm': 0,
        'l': 0,
        'xl': 0,
        'new': 0,
        'returning': 0
        }

    for member in members:
        if member[6] == 'Male':
            total['male'] += 1
        else:
            total['female'] += 1

        if member[9] == 'XS':
            total['xs'] += 1
        elif member[9] == 'S':
            total['s'] += 1
        elif member[9] == 'M':
            total['m'] += 1
        elif member[9] == 'L':
            total['l'] += 1
        else:
            total['xl'] += 1

        if member[5] == '11':
            total['eleven'] += 1
        else:
            total['twelve'] += 1

        if member[10] == 'New':
            total['new'] += 1
        else:
            total['returning'] += 1

    userId = session['user_id']
    return render_template('indexe.html', prefect = prefect, prefects = prefects, total = total, id = userId)

@app.route('/adde', methods = ['GET', 'POST'])
@login_required
def adde():
    if request.method == 'GET':
        db.execute('SELECT leader FROM users WHERE position = "Executive"')
        leaderData = db.fetchall()

        leaders = [leader[0] for leader in leaderData]

        return render_template('adde.html', leaders = leaders)

    else:
        db.execute('SELECT username FROM users')
        registered = db.fetchall()
        registeredUsers = []

        for username in registered:
            registeredUsers.append(username[0])

        # Check that name is not blank
        if not request.form.get('name'):
            flash('Name cannot be blank')
            return redirect(url_for('adde'))

        # Check that username is not blank
        elif not request.form.get('username'):
            flash('Username cannot be blank')
            return redirect(url_for('adde'))

        # Check that password is not blank
        elif not request.form.get('password'):
            flash('Password cannot be blank')
            return redirect(url_for('adde'))

        # Check that username is not already in system
        elif request.form.get('username') in registeredUsers:
            flash('Username already exists! Try a different username.')
            return redirect(url_for('adde'))

        # Check that password and confirmation match
        elif request.form.get('password') != request.form.get('confirm'):
            flash('Password and confirmation do not match')
            return redirect(url_for('adde'))

        db.execute('INSERT INTO users (username, name, hash, grade, leader) VALUES (?, ?, ?, ?, ?)', (
                request.form.get('username'),
                request.form.get('name'),
                generate_password_hash(request.form.get('password')),
                request.form.get('grade'),
                request.form.get('leader')))
        conn.commit()

        flash('Registered!')
        return redirect(url_for('adde'))

@app.route('/change', methods = ['GET', 'POST'])
@login_required
def change():
    '''Change password'''

    # check if information is sent
    if request.method == 'POST':
        db.execute("SELECT hash FROM users WHERE id = ?",
            (session['user_id'],))
        password = db.fetchall()

        # check if password is not empty and matches current password
        if not request.form.get('current') or not check_password_hash(password[0][0], request.form.get("current")):
            flash('Current password is incorrect')
            return render_template('change.html')
            # return apology('Current password is incorrect')

        # check if new password is not empty
        elif not request.form.get('new'):
            flash('Please enter a new password')
            return render_template('change.html')
            # return apology('Please enter a new password')

        # check that new password and confirmation match
        elif request.form.get('new') != request.form.get('confirmation'):
            flash('Password and confirmation do not match')
            return render_template('change.html')
            # return apology('Password and confirmation do not match')

        # update user's password in users database
        db.execute("UPDATE users SET hash = ? WHERE id = ?",
                   (generate_password_hash(request.form.get("new")),
                   session['user_id']))
        conn.commit()

        flash('Password changed!')  # notify of successful registration
        return redirect(url_for("index"))

    # if no information sent return change password page
    else:
        return render_template("change.html")

@app.route('/changee', methods = ['GET', 'POST'])
@login_required
def changee():
    '''Change password'''

    # check if information is sent
    if request.method == 'POST':
        db.execute("SELECT hash FROM users WHERE id = ?",
            (session['user_id'],))
        password = db.fetchall()

        # check if password is not empty and matches current password
        if not request.form.get('current') or not check_password_hash(password[0][0], request.form.get("current")):
            flash('Current password is incorrect')
            return render_template('changee.html')
            # return apology('Current password is incorrect')

        # check if new password is not empty
        elif not request.form.get('new'):
            flash('Please enter a new password')
            return render_template('changee.html')
            # return apology('Please enter a new password')

        # check that new password and confirmation match
        elif request.form.get('new') != request.form.get('confirmation'):
            flash('Password and confirmation do not match')
            return render_template('changee.html')
            # return apology('Password and confirmation do not match')

        # update user's password in users database
        db.execute("UPDATE users SET hash = ? WHERE id = ?",
                   (generate_password_hash(request.form.get("new")),
                   session['user_id']))
        conn.commit()

        flash('Password changed!')  # notify of successful registration
        return redirect(url_for("indexe"))

    # if no information sent return change password page
    else:
        return render_template("changee.html")

@app.route('/edit', methods = ['GET', 'POST'])
@login_required
def edit():

    if request.method == 'GET':
        # return user information from database
        db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        creds = db.fetchall()

        prefect = dict([
            ('name', creds[0][2]),
            ('grade', creds[0][5]),
            ('gender', creds[0][6]),
            ('dietary', creds[0][7]),
            ('group', creds[0][8]),
            ('size', creds[0][9]),
            ('status', creds[0][10]),
            ('home', creds[0][11]),
            ('cell', creds[0][12]),
            ('email', creds[0][13])
            ])

        return render_template('edit.html', prefect = prefect)

    else:
        # return user information from database
        db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        creds = db.fetchall()

        prefect = dict([
            ('name', creds[0][2]),
            ('grade', creds[0][5]),
            ('gender', creds[0][6]),
            ('dietary', creds[0][7]),
            ('group', creds[0][8]),
            ('size', creds[0][9]),
            ('status', creds[0][10]),
            ('home', creds[0][11]),
            ('cell', creds[0][12]),
            ('email', creds[0][13])
            ])

        inputted = {
            'grade': request.form.get('grade'),
            'gender': request.form.get('gender'),
            'dietary': request.form.get('dietary'),
            'size': request.form.get('size'),
            'status': request.form.get('status'),
            'home': request.form.get('home'),
            'cell': request.form.get('cell'),
            'email': request.form.get('email')
        }

        if not request.form.get('home') or not request.form.get('cell') or not request.form.get('email'):
            flash('Fields were left empty. Please try again.')
            return render_template('edit.html', prefect = prefect)
            # return redirect(url_for('edit'))

        elif re.search(r'[^@]+@[^@]+\.[^@]+', request.form.get('email')) == None:
            flash('Email is invalid. Please try again.')
            return render_template('edit.html', prefect = prefect)

        db.execute('UPDATE users SET grade = ?, gender = ?, dietary = ?, size = ?, status = ?, home = ?, cell = ?, email = ? WHERE id = ?', (inputted['grade'], inputted['gender'], inputted['dietary'], inputted['size'], inputted['status'], inputted['home'], inputted['cell'], inputted['email'], session['user_id']))
        conn.commit()

        flash('Updated!')
        return redirect(url_for('profile'))

@app.route('/edite', methods = ['GET', 'POST'])
@login_required
def edite():

    if request.method == 'GET':
        # return user information from database
        db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        creds = db.fetchall()

        prefect = dict([
            ('name', creds[0][2]),
            ('grade', creds[0][5]),
            ('gender', creds[0][6]),
            ('dietary', creds[0][7]),
            ('group', creds[0][8]),
            ('size', creds[0][9]),
            ('status', creds[0][10]),
            ('home', creds[0][11]),
            ('cell', creds[0][12]),
            ('email', creds[0][13])
            ])

        return render_template('edite.html', prefect = prefect)

    else:
        # return user information from database
        db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
        creds = db.fetchall()

        prefect = dict([
            ('name', creds[0][2]),
            ('grade', creds[0][5]),
            ('gender', creds[0][6]),
            ('dietary', creds[0][7]),
            ('group', creds[0][8]),
            ('size', creds[0][9]),
            ('status', creds[0][10]),
            ('home', creds[0][11]),
            ('cell', creds[0][12]),
            ('email', creds[0][13])
            ])

        inputted = {
            'grade': request.form.get('grade'),
            'gender': request.form.get('gender'),
            'dietary': request.form.get('dietary'),
            'size': request.form.get('size'),
            'status': request.form.get('status'),
            'home': request.form.get('home'),
            'cell': request.form.get('cell'),
            'email': request.form.get('email')
        }

        if not request.form.get('home') or not request.form.get('cell') or not request.form.get('email'):
            flash('Fields were left empty. Please try again.')
            return render_template('edite.html', prefect = prefect)
            # return redirect(url_for('edit'))

        elif re.search(r'[^@]+@[^@]+\.[^@]+', request.form.get('email')) == None:
            flash('Email is invalid. Please try again.')
            return render_template('edite.html', prefect = prefect)

        db.execute('UPDATE users SET grade = ?, gender = ?, dietary = ?, size = ?, status = ?, home = ?, cell = ?, email = ? WHERE id = ?', (inputted['grade'], inputted['gender'], inputted['dietary'], inputted['size'], inputted['status'], inputted['home'], inputted['cell'], inputted['email'], session['user_id']))
        conn.commit()

        flash('Updated!')
        return redirect(url_for('profilee'))

@app.route('/editprefecte')
@login_required
def editprefecte():
    db.execute('SELECT leader FROM users WHERE id = ?', (session['user_id'],))
    groupName = db.fetchall()[0][0]

    db.execute('SELECT * FROM users WHERE leader = ? AND position != "Executive"', (groupName,))
    groupPrefects = db.fetchall()

    prefects = [{
        'name': prefect[2],
        'id': prefect[0]
    } for prefect in groupPrefects]

    prefect = {
        'name': None,
        'grade': None,
        'gender': None,
        'dietary': None,
        'leader': None,
        'size': None,
        'status': None,
        'home': None,
        'cell': None,
        'email': None
    }

    db.execute('SELECT leader FROM users WHERE position = "Executive"')
    leaderData = db.fetchall()

    leaders = [leader[0] for leader in leaderData]

    return render_template('editprefecte.html', prefects = prefects, leaders = leaders, prefect = prefect, visibility = 'hidden')

@app.route('/editprefecte/<prefectId>', methods = ['GET', 'POST'])
@login_required
def editPrefectInfo(prefectId):
    if request.method == 'GET':
        db.execute('SELECT leader FROM users WHERE id = ?', (session['user_id'],))
        groupName = db.fetchall()[0][0]

        db.execute('SELECT * FROM users WHERE leader = ? AND position != "Executive"', (groupName,))
        groupPrefects = db.fetchall()

        prefects = [{
            'name': prefect[2],
            'id': prefect[0]
        } for prefect in groupPrefects]

        db.execute('SELECT * FROM users WHERE id = ?', (prefectId,))
        prefectInfo = db.fetchall()

        prefect = {
            'id': prefectInfo[0][0],
            'name': prefectInfo[0][2],
            'username': prefectInfo[0][1],
            'grade': prefectInfo[0][5],
            'gender': prefectInfo[0][6],
            'dietary': prefectInfo[0][7],
            'leader': prefectInfo[0][8],
            'size': prefectInfo[0][9],
            'status': prefectInfo[0][10],
            'home': prefectInfo[0][11],
            'cell': prefectInfo[0][12],
            'email': prefectInfo[0][13]
        }

        db.execute('SELECT leader FROM users WHERE position = "Executive"')
        leaderData = db.fetchall()

        leaders = [leader[0] for leader in leaderData]

        return render_template('editprefecte.html', prefects = prefects, leaders = leaders, prefect = prefect, visibility = 'visible')
    else:
        db.execute('UPDATE users SET name = ?, username = ?, grade = ?, gender = ?, dietary = ?, leader = ?, size = ?, status = ?, home = ?, cell = ?, email = ? WHERE id = ?', (request.form.get('name'), request.form.get('username'), request.form.get('grade'), request.form.get('gender'), request.form.get('dietary'), request.form.get('leader'), request.form.get('size'), request.form.get('status'), request.form.get('home'), request.form.get('cell'), request.form.get('email'), prefectId))
        conn.commit()

        flash('Updated!')
        return redirect(url_for('/editprefecte' + prefectId))

@app.route('/events')
@login_required
def events():
    # Get user's registered events
    db.execute('SELECT * FROM signup WHERE id = ?', (session['user_id'],))
    registeredEvents = db.fetchall()

    registered = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3],
        'code': event[1]
    } for event in registeredEvents]

    # Get available events
    db.execute('SELECT * FROM events WHERE visible = "yes"')
    availableEvents = db.fetchall()

    available = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3],
        'code': event[1]
    } for event in availableEvents if event[1] not in [event[1] for event in registeredEvents]]

    # Get completed events
    db.execute('SELECT * FROM completed WHERE id = ?', (session['user_id'],))
    completedEvents = db.fetchall()

    completed = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3]
    } for event in completedEvents]

    total = 0

    for event in completedEvents:
        total += float(event[3])

    return render_template('events.html', registered = registered, available = available, completed = completed, total = total)

@app.route('/eventse', methods = ['GET', 'POST'])
@login_required
def eventse():

    if request.method == 'GET':
        db.execute('SELECT * FROM events')
        eventData = db.fetchall()

        visible = [{
            'eventName': event[0],
            'eventCode': event[1],
            'shift': event[2],
            'value': event[3],
            } for event in eventData if event[4] == 'yes' and event[5] != 'yes']

        invisible = [{
            'eventName': event[0],
            'eventCode': event[1],
            'shift': event[2],
            'value': event[3],
            } for event in eventData if event[4] == 'no' and event[5] != 'yes']

        finished = [{
            'eventName': event[0],
            'eventCode': event[1],
            'shift': event[2],
            'value': event[3],
            } for event in eventData if event[5] == 'yes']

        totalVisible = len(visible)
        totalInvisible = len(invisible)
        totalFinished = len(finished)

        return render_template('eventse.html', visibleEvents = visible, invisibleEvents = invisible, finishedEvents = finished, totalvis = totalVisible, totalinvis = totalInvisible, totalfinished = totalFinished)

    else:
        if not request.form.get('name'):
            flash('Event name cannot be blank')
            return redirect(url_for('eventse'))

        elif not request.form.get('shift1'):
            flash('Shift 1 value cannot be blank')
            return redirect(url_for('eventse'))

        if request.form.get('visible'):
            db.execute('INSERT INTO files (eventName, eventCode, shift, value) VALUES (?, ?, ?, ?)', (request.form.get('name'), request.form.get('link'), 'yes'))
            fileData = db.fetchall()
        else:
            db.execute('INSERT INTO files (name, link, visible) VALUES (?, ?, ?)', (request.form.get('name'), request.form.get('link'), 'no'))
            fileData = db.fetchall()

        visible = [{
            'name': file[0],
            'link': file[1],
            'id': file[2]
            } for file in fileData if file[3] == 'yes']

        invisible = [{
            'name': file[0],
            'link': file[1],
            'id': file[2]
            } for file in fileData if file[3] == 'no']

        return redirect(url_for('filese'))

        # render_template('filese.html', visibleFiles = visible, invisibleFiles = invisible)

@app.route('/withdraw/<eventCode>')
@login_required
def withdraw(eventCode):
    # Remove from user's registered events
    db.execute('DELETE FROM signup WHERE id = ? AND eventCode = ?', (session['user_id'], eventCode))
    conn.commit()

    # Get user's registered events
    db.execute('SELECT * FROM signup WHERE id = ?', (session['user_id'],))
    registeredEvents = db.fetchall()

    registered = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3],
        'code': event[1]
    } for event in registeredEvents]

    # Get available events
    db.execute('SELECT * FROM events WHERE visible = "yes"')
    availableEvents = db.fetchall()

    available = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3],
        'code': event[1]
    } for event in availableEvents if event[1] not in [event[1] for event in registeredEvents]]

    # Get completed events
    db.execute('SELECT * FROM completed WHERE id = ?', (session['user_id'],))
    completedEvents = db.fetchall()

    completed = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3]
    } for event in completedEvents]

    total = 0

    for event in completedEvents:
        total += float(event[3])

    return render_template('events.html', registered = registered, available = available, completed = completed, total = total)

@app.route('/signup/<eventCode>/<shift>')
@login_required
def signup(eventCode, shift):
    # Add to user's registered events
    db.execute('INSERT INTO signup (eventName, eventCode, shift, value, id) VALUES (?, ?, ?, ?, ?)', (lookup(eventCode, shift)['name'], eventCode, shift, lookup(eventCode, shift)['value'], session['user_id']))
    conn.commit()

    # Get user's registered events
    db.execute('SELECT * FROM signup WHERE id = ?', (session['user_id'],))
    registeredEvents = db.fetchall()

    registered = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3],
        'code': event[1]
    } for event in registeredEvents]

    # Get available events
    db.execute('SELECT * FROM events WHERE visible = "yes"')
    availableEvents = db.fetchall()

    available = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3],
        'code': event[1]
    } for event in availableEvents if event[1] not in [event[1] for event in registeredEvents]]

    # Get completed events
    db.execute('SELECT * FROM completed WHERE id = ?', (session['user_id'],))
    completedEvents = db.fetchall()

    completed = [{
        'name': event[0],
        'shift': event[2],
        'value': event[3]
    } for event in completedEvents]

    total = 0

    for event in completedEvents:
        total += float(event[3])

    return render_template('events.html', registered = registered, available = available, completed = completed, total = total)

@app.route('/files')
@login_required
def files():
    db.execute('SELECT * FROM files')
    fileData = db.fetchall()

    fileDict = [{
        'name': file[0],
        'link': file[1]
        } for file in fileData if file[3] == 'yes']

    return render_template('files.html', files = fileDict)

@app.route('/filese', methods = ['GET', 'POST'])
@login_required
def filese():

    if request.method == 'GET':
        db.execute('SELECT * FROM files')
        fileData = db.fetchall()

        visible = [{
            'name': file[0],
            'link': file[1],
            'id': file[2]
            } for file in fileData if file[3] == 'yes']

        invisible = [{
            'name': file[0],
            'link': file[1],
            'id': file[2]
            } for file in fileData if file[3] == 'no']

        totalVisible = len(visible)
        totalInvisible = len(invisible)

        return render_template('filese.html', visibleFiles = visible, invisibleFiles = invisible, totalvis = totalVisible, totalinvis = totalInvisible)

    else:
        if re.search(r'(?:.+\.)+.+', request.form.get('link')) == None:
            flash('Link is invalid. Please try again.')
            return redirect(url_for('filese'))

        elif not request.form.get('name'):
            flash('File name cannot be blank')
            return redirect(url_for('filese'))

        elif not request.form.get('link'):
            flash('File link cannot be blank')
            return redirect(url_for('filese'))

        if request.form.get('visible'):
            db.execute('INSERT INTO files (name, link, visible) VALUES (?, ?, ?)', (request.form.get('name'), request.form.get('link'), 'yes'))
            fileData = db.fetchall()
        else:
            db.execute('INSERT INTO files (name, link, visible) VALUES (?, ?, ?)', (request.form.get('name'), request.form.get('link'), 'no'))
            fileData = db.fetchall()

        visible = [{
            'name': file[0],
            'link': file[1],
            'id': file[2]
            } for file in fileData if file[3] == 'yes']

        invisible = [{
            'name': file[0],
            'link': file[1],
            'id': file[2]
            } for file in fileData if file[3] == 'no']

        return redirect(url_for('filese'))

@app.route('/hide/<fileId>')
@login_required
def hide(fileId):
    db.execute('UPDATE files SET visible = "no" WHERE id = ?', (fileId,))
    conn.commit()

    return redirect(url_for('filese'))

@app.route('/show/<fileId>')
@login_required
def show(fileId):
    db.execute('UPDATE files SET visible = "yes" WHERE id = ?', (fileId,))
    conn.commit()

    return redirect(url_for('filese'))

@app.route('/remove/<fileId>')
@login_required
def remove(fileId):
    db.execute('DELETE FROM files WHERE id = ?', (fileId,))
    conn.commit()

    return redirect(url_for('filese'))

@app.route('/login', methods = ['GET', 'POST'])
def login():
    '''Log user in'''

    # Forget current user id
    session.clear()

    # Request via POST
    if request.method == "POST":

        # Make sure username is not empty
        if not request.form.get('username'):
            flash('Username cannot be blank')
            return render_template('login.html')
            # return apology('Username cannot be blank', 403)

        # Make sure password is not empty
        elif not request.form.get('password'):
            flash('Password cannot be blank')
            return render_template('login.html')
            # return apology('Password cannot be blank', 403)

        # Query database for username
        db.execute('SELECT * FROM users WHERE username = ?', (request.form.get('username'),))
        rows = db.fetchall()

        # Check that username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][3], request.form.get('password')):
            flash('Invalid username and/or password')
            return render_template('login.html')
            # return apology('Invalid username and/or password', 403)

        session['user_id'] = rows[0][0]

        if rows[0][14] == 'Prefect':
            return redirect('/')

        if rows[0][14] == 'Executive':
            return redirect('/indexe')

    else:
        return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    '''Log user out'''

    # Forget user_id
    session.clear()

    return redirect('/')

@app.route('/profile')
@login_required
def profile():
    '''Display user information'''

    # retrieve user information from database
    db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    creds = db.fetchall()

    prefect = dict([
        ('name', creds[0][2]),
        ('grade', creds[0][5]),
        ('gender', creds[0][6]),
        ('dietary', creds[0][7]),
        ('group', creds[0][8]),
        ('size', creds[0][9]),
        ('status', creds[0][10]),
        ('home', creds[0][11]),
        ('cell', creds[0][12]),
        ('email', creds[0][13])
        ])

    return render_template('profile.html', prefect = prefect)

@app.route('/profilee')
@login_required
def profilee():
    '''Display user information'''

    # retrieve user information from database
    db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    creds = db.fetchall()

    prefect = dict([
        ('name', creds[0][2]),
        ('grade', creds[0][5]),
        ('gender', creds[0][6]),
        ('dietary', creds[0][7]),
        ('group', creds[0][8]),
        ('size', creds[0][9]),
        ('status', creds[0][10]),
        ('home', creds[0][11]),
        ('cell', creds[0][12]),
        ('email', creds[0][13])
        ])

    return render_template('profilee.html', prefect = prefect)

@app.route('/register', methods = ['GET', 'POST'])
def register():
    '''Register user'''

    # Check that information is sent
    if request.method == 'POST':
        registered = db.execute('SELECT username FROM users')

        # Check that username is not blank
        if not request.form.get('username'):
            flash('Username cannot be blank')
            return render_template('register.html')
            # return apology('Username cannot be blank')

        # Check that password is not blank
        elif not request.form.get('password'):
            flash('Password cannot be blank')
            return render_template('register.html')
            # return apology('Password cannot be blank')

        # Check that password and confirmation match
        elif request.form.get('password') != request.form.get('confirm'):
            flash('Password and confirmation do not match')
            return render_template('register.html')
            # return apology('Password and confirmation do not match')

        # Add new user to database
        result = db.execute('INSERT INTO users (name, username, hash) VALUES (?, ?, ?)', (
            request.form.get('name'),
            request.form.get('username'),
            generate_password_hash(request.form.get('password'))))
        conn.commit()

        # If user cannot be added (id must be unique) then refuse
        if not result:
            flash('Account already exists')
            return render_template('register.html')
            # return apology('Account already exists')

        # Get user's information based on username
        db.execute('SELECT * from users WHERE username = ?',
            (request.form.get('username'),))
        info = db.fetchall()

        # Get user's id
        session['user_id'] = info[0][0]

        flash('Registered!')  # Notify of successful registration
        return redirect(url_for('index'))

    # If not POST method then return to registration page
    else:
        return render_template('register.html')

def errorhandler(e):
    '''Handle error'''
    return apology(e.name, e.code)

if __name__ == '__main__':
    app.run(debug=True)

for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
