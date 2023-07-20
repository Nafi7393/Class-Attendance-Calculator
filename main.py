from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
import bcrypt, os

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Get the current directory
# current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the raw path relative to the current directory
# db_path = os.path.join(current_dir, "instance", "users.db")
# db_uri = f"sqlite:///{db_path}"

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "SECRET_KEY"
db = SQLAlchemy(app)



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), unique=True, nullable=False)
    email = db.Column(db.String(60), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    courses = db.Column(db.PickleType, nullable=True)

    def set_password(self, password):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.password = hashed_password.decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))


def calculate_overall_stats(courses):
    total_classes_attended = 0
    total_classes_missed = 0

    for course in courses:
        classes_taken = course['classes_taken']
        absent = course['absent']

        total_classes_attended += classes_taken - absent
        total_classes_missed += absent

    total_classes = total_classes_attended + total_classes_missed
    average_percentage = (total_classes_attended / total_classes) * 100 if total_classes > 0 else 0

    overall_stats = {
        'total_classes_attended': total_classes_attended,
        'total_classes_missed': total_classes_missed,
        'average_percentage': round(average_percentage, 2)
    }

    return overall_stats



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if the email or name already exists in the database
        existing_user_email = User.query.filter_by(email=email).first()
        existing_user_name = User.query.filter_by(name=name).first()

        if existing_user_email:
            error = 'Email already exists. Please choose another email.'
            return render_template('register.html', error=error, error_type='email')
        elif existing_user_name:
            error = 'Name already exists. Please choose another name.'
            return render_template('register.html', error=error, error_type='name')

        # Create a new user
        new_user = User(name=name, email=email)
        new_user.set_password(password)  # Hash the password
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    else:
        return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # Set user session
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = user.name
            session['user_courses'] = user.courses

            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid email or password')

    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        # Get the updated courses from the form submission
        courses = request.form.getlist('course')

        # Update the courses for the current user in the database
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                user.courses = courses
                db.session.commit()

    # Retrieve the courses from the database
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        courses = user.courses if user else []
    else:
        courses = []
        return render_template('login.html')

    if courses is None or len(courses) == 0:
        courses = [{'name': '', 'teacher': '', 'classes_taken': 1, 'absent': 0}]

    for i in courses:
        if i["classes_taken"] == 0 or i["classes_taken"] is None:
            i["classes_taken"] = 1

        if i["absent"] <= 0 or i["absent"] is None:
            i["absent"] = 0

    overall_stats = calculate_overall_stats(courses)

    return render_template('dashboard.html', courses=courses, overall_stats=overall_stats)


@app.route('/update_courses', methods=['POST'])
def update_courses():
    courses = request.get_json()['courses']

    # Update the courses for the current user in the database
    user = User.query.get(session['user_id'])
    user.courses = courses
    db.session.commit()

    return jsonify({'message': 'Courses updated successfully'})


@app.route('/remove_course', methods=['POST'])
def remove_course():
    course_index = int(request.form['course_index'])

    # Remove the course from the user's course list in the database
    user = User.query.get(session['user_id'])
    courses = user.courses
    if courses:
        if course_index >= 0 and course_index < len(courses):
            del courses[course_index]
            db.session.commit()

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    # Clear user session
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')


    # to make clean database
    # with app.app_context():
    #     db.create_all()
