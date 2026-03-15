from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mission-critical-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habit_tracker.db'
db = SQLAlchemy(app)

#1. DEFINE MODELS FIRST
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    # This links the user to their habits
    habits = db.relationship('Habit', backref='owner', lazy=True)



# USER MODEL
class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Incomplete")
    # NEW COLUMNS
    streak = db.Column(db.Integer, default=0)
    last_completed = db.Column(db.Date, nullable=True) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# AUTHENTICATION SYSTEM
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirects here if unauthorized


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

# Add these routes to your existing app.py

@app.route("/")
@login_required
def dashboard():
    # Fetch only the habits belonging to the CURRENT logged-in user
    user_habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Calculate Stats
    total = len(user_habits)
    completed = len([h for h in user_habits if h.status == 'Complete'])
    progress = (completed / total * 100) if total > 0 else 0
    
    return render_template("dashboard.html", 
                           habits=user_habits, 
                           total=total, 
                           completed=completed, 
                           progress=int(progress))

@app.route("/add_habit", methods=['POST'])
@login_required
def add_habit():
    habit_name = request.form.get('habit_name')
    if habit_name:
        # Link the habit to the current_user.id
        new_habit = Habit(name=habit_name, user_id=current_user.id)
        db.session.add(new_habit)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route("/delete/<int:id>")
@login_required
def delete_habit(id):
    habit_to_delete = Habit.query.get_or_404(id)
    
    # Security check: Ensure the current user owns this habit
    if habit_to_delete.user_id == current_user.id:
        db.session.delete(habit_to_delete)
        db.session.commit()
        flash("Mission scrubbed from records.")
    
    return redirect(url_for('dashboard'))


@app.route("/edit/<int:id>", methods=['GET', 'POST'])
@login_required
def edit_habit(id):
    habit = Habit.query.get_or_404(id)
    
    # Security: Ensure user owns this habit
    if habit.user_id != current_user.id:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        new_name = request.form.get('habit_name')
        if new_name:
            habit.name = new_name
            db.session.commit()
            flash("Mission updated!")
            return redirect(url_for('dashboard'))

    return render_template("edit.html", habit=habit)

@app.route("/complete/<int:id>")
@login_required
def complete_habit(id):
    habit = Habit.query.get(id)
    if habit and habit.user_id == current_user.id:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Logic: If last completed was yesterday, increase streak.
        # If it was long ago, reset to 1.
        if habit.last_completed == yesterday:
            habit.streak += 1
        elif habit.last_completed == today:
            pass # Already done today
        else:
            habit.streak = 1 
        
        habit.status = "Complete"
        habit.last_completed = today
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route("/analytics")
@login_required
def analytics():
    # Fetch all habits for this user
    user_habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Logic to find the highest streak number from the list
    if user_habits:
        top_streak = max([h.streak for h in user_habits])
    else:
        top_streak = 0
        
    return render_template("analytics.html", habits=user_habits, top_streak=top_streak)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        
        if User.query.filter_by(username=user).first():
            flash('Username already exists!')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(pw, method='pbkdf2:sha256')
        new_user = User(username=user, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
        
    return render_template("register.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        found_user = User.query.filter_by(username=user).first()

        if found_user and check_password_hash(found_user.password, pw):
            login_user(found_user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid Credentials.')
    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

# INITIALIZE DATABASE
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)