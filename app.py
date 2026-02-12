from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Branch, ClassRoom, Transaction, StoreItem, Receipt
import secrets
import qrcode
from io import BytesIO
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'college-project-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scholarcash_v2.db' 

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AUTH & HOME ROUTES ---

@app.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    if current_user.role == 'principal':
        return redirect(url_for('dashboard_principal'))
    elif current_user.role in ['teacher', 'tutor', 'hod']:
        return redirect(url_for('dashboard_teacher'))
    elif current_user.role == 'student':
        return redirect(url_for('dashboard_student'))
    return "Unknown Role", 403

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            
            # Check if mobile device
            user_agent = request.headers.get('User-Agent', '').lower()
            is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad'])
            
            if user.role in ['teacher', 'tutor', 'hod'] and is_mobile:
                return redirect(url_for('mobile_dashboard'))
            
            return redirect(url_for('home'))
        flash("Invalid Credentials", "error")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- PRINCIPAL: DASHBOARD & CREATION ---

@app.route('/principal')
@login_required
def dashboard_principal():
    if current_user.role != 'principal': return "Denied", 403
    
    branches = Branch.query.all()
    classes = ClassRoom.query.all()
    all_users = User.query.filter(User.role.in_(['teacher', 'tutor', 'hod'])).all()
    store_items = StoreItem.query.all()
    
    total_circulation = db.session.query(db.func.sum(User.balance)).scalar() or 0
    
    return render_template('dashboards/principal.html', 
                           branches=branches, 
                           staff=all_users, 
                           classes=classes,
                           store_items=store_items,
                           circulation=total_circulation)

@app.route('/principal/add_branch', methods=['POST'])
@login_required
def add_branch():
    if current_user.role != 'principal': return "Denied", 403
    name = request.form.get('name')
    if Branch.query.filter_by(name=name).first():
        flash('Branch already exists', 'error')
    else:
        db.session.add(Branch(name=name))
        db.session.commit()
        flash(f'Branch "{name}" created!', 'success')
    return redirect(url_for('dashboard_principal'))

@app.route('/principal/add_class', methods=['POST'])
@login_required
def add_class():
    if current_user.role != 'principal': return "Denied", 403
    name = request.form.get('name')
    branch_id = request.form.get('branch_id')
    db.session.add(ClassRoom(name=name, branch_id=branch_id))
    db.session.commit()
    flash(f'Class "{name}" added!', 'success')
    return redirect(url_for('dashboard_principal'))

# --- UPDATE: The 'add_staff' function (HOD Fix) ---
@app.route('/principal/add_staff', methods=['POST'])
@login_required
def add_staff():
    if current_user.role != 'principal': return "Denied", 403
    
    email = request.form.get('email')
    name = request.form.get('name')
    role = request.form.get('role')
    branch_id = request.form.get('branch_id')
    class_id = request.form.get('class_id')
    password = request.form.get('password')  # FIX: Get password from form

    # FIX: Validate password exists
    if not password:
        flash("Password is required", "error")
        return redirect(url_for('dashboard_principal'))

    new_user = User(email=email, name=name, role=role, 
                    password=generate_password_hash(password, method='pbkdf2:sha256'))

    # 1. Branch Logic (Required for Teacher/HOD)
    if role in ['teacher', 'hod'] and branch_id:
        new_user.branch_id = int(branch_id)

    db.session.add(new_user)
    db.session.commit()

    # 2. Class Tutor Logic (Optional for HOD, Required for Tutor)
    if (role == 'tutor' or role == 'hod') and class_id:
        classroom = ClassRoom.query.get(int(class_id))
        if classroom:  # FIX: Check if classroom exists
            classroom.tutor_id = new_user.id
            
            if not new_user.branch_id:
                new_user.branch_id = classroom.branch_id
                
            db.session.commit()

    flash(f'User {name} created as {role}', 'success')
    return redirect(url_for('dashboard_principal'))


@app.route('/principal/add_item', methods=['POST'])
@login_required
def add_store_item():
    if current_user.role != 'principal': return "Denied", 403
    name = request.form.get('name')
    cost = int(request.form.get('cost'))
    stock = int(request.form.get('stock'))
    new_item = StoreItem(name=name, cost=cost, stock=stock, creator_id=current_user.id)
    db.session.add(new_item)
    db.session.commit()
    flash(f'Added "{name}" to store!', 'success')
    return redirect(url_for('dashboard_principal'))

@app.route('/principal/mint', methods=['POST'])
@login_required
def mint_coins():
    if current_user.role != 'principal': return "Denied", 403
    target_user = User.query.get(request.form.get('user_id'))
    amount = int(request.form.get('amount'))
    reason = request.form.get('reason')
    
    if target_user:
        target_user.balance += amount
        tx = Transaction(sender_id=current_user.id, receiver_id=target_user.id, 
                         amount=amount, reason=f"Budget: {reason}")
        db.session.add(tx)
        db.session.commit()
        flash(f'Allocated {amount} coins to {target_user.name}', 'success')
    return redirect(url_for('dashboard_principal'))

# --- ALL EDIT ROUTES (User, Branch, Class, Store) ---

@app.route('/edit/user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    # Allow principal OR tutor (for their own students) to edit
    user = User.query.get(id)
    
    if not user:
        flash("User not found", "error")
        return redirect(url_for('home'))
    
    # Check permissions
    can_edit = False
    
    if current_user.role == 'principal':
        can_edit = True
    elif current_user.role == 'tutor' and user.role == 'student':
        # Tutor can edit students in their class
        if current_user.tutor_of_class:
            tutor_class_ids = [c.id for c in current_user.tutor_of_class]
            if user.class_id in tutor_class_ids:
                can_edit = True
    
    if not can_edit:
        return "Denied", 403
    
    branches = Branch.query.all()
    classes = ClassRoom.query.all()

    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        new_role = request.form.get('role')
        
        # Handle password update
        new_password = request.form.get('password')
        if new_password and new_password.strip():
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        # Only principal can change roles
        if current_user.role == 'principal':
            user.role = new_role
            
            # Handle Branch (For Teachers & HODs)
            if new_role in ['teacher', 'hod']:
                branch_id = request.form.get('branch_id')
                user.branch_id = int(branch_id) if branch_id else None

            # Handle Class Tutoring (For Tutors & HODs)
            if new_role in ['tutor', 'hod']:
                class_id = request.form.get('class_id')
                
                # Remove from old class
                old_class = ClassRoom.query.filter_by(tutor_id=user.id).first()
                if old_class:
                    old_class.tutor_id = None
                
                # Assign to new class
                if class_id:
                    new_class = ClassRoom.query.get(int(class_id))
                    new_class.tutor_id = user.id
                    if not user.branch_id:
                        user.branch_id = new_class.branch_id

            # Handle Students
            elif new_role == 'student':
                class_id = request.form.get('class_id')
                if class_id:
                    user.class_id = int(class_id)
                    # Update branch based on class
                    cls = ClassRoom.query.get(int(class_id))
                    if cls:
                        user.branch_id = cls.branch_id
        
        # Tutor can only update student's class, not role
        elif current_user.role == 'tutor' and user.role == 'student':
            class_id = request.form.get('class_id')
            if class_id:
                user.class_id = int(class_id)
                cls = ClassRoom.query.get(int(class_id))
                if cls:
                    user.branch_id = cls.branch_id

        db.session.commit()
        flash('User updated!', 'success')
        
        # Redirect based on who edited
        if current_user.role == 'principal':
            return redirect(url_for('dashboard_principal'))
        else:
            return redirect(url_for('dashboard_teacher'))
        
    return render_template('edit_item.html', item=user, type='user', branches=branches, classes=classes)

@app.route('/edit/branch/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_branch(id):
    if current_user.role != 'principal': return "Denied", 403
    branch = Branch.query.get(id)
    if request.method == 'POST':
        branch.name = request.form.get('name')
        db.session.commit()
        flash('Branch updated!', 'success')
        return redirect(url_for('dashboard_principal'))
    return render_template('edit_item.html', item=branch, type='branch')

@app.route('/edit/class/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_class(id):
    if current_user.role != 'principal': return "Denied", 403
    classroom = ClassRoom.query.get(id)
    if request.method == 'POST':
        classroom.name = request.form.get('name')
        db.session.commit()
        flash('Class updated!', 'success')
        return redirect(url_for('dashboard_principal'))
    return render_template('edit_item.html', item=classroom, type='class')

@app.route('/edit/store/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_store_item(id):
    if current_user.role != 'principal': return "Denied", 403
    item = StoreItem.query.get(id)
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.cost = int(request.form.get('cost'))
        item.stock = int(request.form.get('stock'))
        db.session.commit()
        flash(f'Updated {item.name}!', 'success')
        return redirect(url_for('dashboard_principal'))
    return render_template('edit_item.html', item=item, type='store')


# --- DELETE ROUTE (Universal) ---

@app.route('/delete/<type>/<int:id>')
@login_required
def delete_item(type, id):
    if current_user.role != 'principal': return "Denied", 403
    item = None
    if type == 'user': item = User.query.get(id)
    elif type == 'branch': item = Branch.query.get(id)
    elif type == 'class': item = ClassRoom.query.get(id)
    elif type == 'store': item = StoreItem.query.get(id)
    
    if item:
        db.session.delete(item)
        db.session.commit()
        flash(f'Deleted {type} item successfully', 'success')
    else:
        flash('Item not found', 'error')
    return redirect(url_for('dashboard_principal'))

# --- TEACHER ROUTES ---

@app.route('/teacher')
@login_required
def dashboard_teacher():
    if current_user.role not in ['teacher', 'tutor', 'hod']: 
        return "Denied", 403
    
    # Get transactions
    my_txs = Transaction.query.filter_by(sender_id=current_user.id)\
                              .order_by(Transaction.timestamp.desc())\
                              .limit(20).all()
    
    # Determine all capabilities based on actual assignments, not just role field
    is_tutor = bool(current_user.tutor_of_class and len(current_user.tutor_of_class) > 0)
    is_hod = bool(current_user.branch_id and current_user.role == 'hod')
    is_subject_teacher = bool(current_user.branch_id)
    
    # Get branch info
    my_branch = None
    if current_user.branch_id:
        my_branch = Branch.query.get(current_user.branch_id)
    
    # Get students based on capabilities
    branch_students = []  # For subject teachers/HODs - all students in branch
    class_students = []   # For tutors - students in specific classes
    
    if is_tutor:
        # Get students from tutor's classes
        for cls in current_user.tutor_of_class:
            students = User.query.filter_by(role='student', class_id=cls.id).all()
            class_students.extend(students)
    
    if is_subject_teacher or is_hod:
        # Get all students in the branch
        if my_branch:
            branch_classes = ClassRoom.query.filter_by(branch_id=my_branch.id).all()
            class_ids = [c.id for c in branch_classes]
            if class_ids:
                branch_students = User.query.filter(
                    User.role == 'student',
                    User.class_id.in_(class_ids)
                ).all()
    
    # Remove duplicates
    seen = set()
    unique_branch = []
    for s in branch_students:
        if s.id not in seen:
            seen.add(s.id)
            unique_branch.append(s)
    branch_students = unique_branch
    
    seen = set()
    unique_class = []
    for s in class_students:
        if s.id not in seen:
            seen.add(s.id)
            unique_class.append(s)
    class_students = unique_class
    
    # For HOD: Get branch staff (teachers and tutors)
    branch_staff = []
    if is_hod and my_branch:
        branch_staff = User.query.filter(
            User.branch_id == my_branch.id,
            User.id != current_user.id,
            User.role.in_(['teacher', 'tutor'])
        ).all()
    
    # For HOD: Get branch stats
    branch_stats = {}
    if is_hod and my_branch:
        total_students = len(branch_students)
        total_teachers = len(branch_staff)
        total_classes = ClassRoom.query.filter_by(branch_id=my_branch.id).count()
        branch_balance = sum(s.balance for s in branch_students)
        branch_stats = {
            'students': total_students,
            'teachers': total_teachers,
            'classes': total_classes,
            'balance': branch_balance
        }
    
    return render_template('dashboards/teacher.html', 
                         transactions=my_txs,
                         branch_students=branch_students,
                         class_students=class_students,
                         branch_staff=branch_staff,
                         branch_stats=branch_stats,
                         my_branch=my_branch,
                         is_tutor=is_tutor,
                         is_hod=is_hod,
                         is_subject_teacher=is_subject_teacher)


@app.route('/teacher/transfer', methods=['POST'])
@login_required
def transfer_coins():
    if current_user.role not in ['teacher', 'tutor', 'hod']:
        return "Denied", 403
        
    receiver_id = request.form.get('receiver_id') 
    amount = int(request.form.get('amount'))
    reason = request.form.get('reason')
    
    if current_user.balance < amount:
        flash("Insufficient Budget!", "error")
        return redirect(url_for('dashboard_teacher'))
        
    receiver = User.query.filter_by(id=receiver_id, role='student').first()
    if not receiver:
        flash("Student not found", "error")
        return redirect(url_for('dashboard_teacher'))
    
    # Verify teacher can send to this student
    can_send = False
    
    # Check if tutor of student's class
    if current_user.tutor_of_class:
        for cls in current_user.tutor_of_class:
            if receiver.class_id == cls.id:
                can_send = True
                break
    
    # Check if same branch (teacher/HOD)
    if not can_send and current_user.branch_id:
        if receiver.branch_id == current_user.branch_id:
            can_send = True
    
    if not can_send:
        flash("You cannot send coins to this student", "error")
        return redirect(url_for('dashboard_teacher'))

    current_user.balance -= amount
    receiver.balance += amount
    
    tx = Transaction(
        sender_id=current_user.id, 
        receiver_id=receiver.id, 
        amount=amount, 
        reason=reason
    )
    
    db.session.add(tx)
    db.session.commit()
    
    flash(f"Sent {amount} coins to {receiver.name}", "success")
    return redirect(url_for('dashboard_teacher'))


@app.route('/hod/allocate', methods=['POST'])
@login_required
def hod_allocate():
    """HOD can allocate coins to teachers in their branch"""
    if current_user.role != 'hod':
        return "Denied", 403
    
    teacher_id = request.form.get('teacher_id')
    amount = int(request.form.get('amount'))
    reason = request.form.get('reason')
    
    # Verify teacher is in HOD's branch
    teacher = User.query.filter_by(id=teacher_id, branch_id=current_user.branch_id).first()
    if not teacher:
        flash("Teacher not found in your branch", "error")
        return redirect(url_for('dashboard_teacher'))
    
    if current_user.balance < amount:
        flash("Insufficient balance", "error")
        return redirect(url_for('dashboard_teacher'))
    
    current_user.balance -= amount
    teacher.balance += amount
    
    tx = Transaction(
        sender_id=current_user.id,
        receiver_id=teacher.id,
        amount=amount,
        reason=f"HOD Allocation: {reason}"
    )
    
    db.session.add(tx)
    db.session.commit()
    
    flash(f"Allocated {amount} coins to {teacher.name}", "success")
    return redirect(url_for('dashboard_teacher'))



# --- STUDENT ROUTES ---

@app.route('/student')
@login_required
def dashboard_student():
    if current_user.role != 'student': return "Denied", 403
    my_txs = Transaction.query.filter(
        (Transaction.sender_id == current_user.id) | 
        (Transaction.receiver_id == current_user.id)
    ).order_by(Transaction.timestamp.desc()).limit(10).all()
    store_items = StoreItem.query.filter(StoreItem.stock > 0).all()
    my_receipts = Receipt.query.filter_by(student_id=current_user.id).order_by(Receipt.timestamp.desc()).all()
    return render_template('dashboards/student.html', transactions=my_txs, store_items=store_items, receipts=my_receipts)

@app.route('/student/qr_image')
@login_required
def qr_image():
    data = f"USER-{current_user.id}"
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/student/buy/<int:item_id>')
@login_required
def buy_item(item_id):
    if current_user.role != 'student': return "Denied", 403
    item = StoreItem.query.get(item_id)
    if not item or item.stock < 1:
        flash("Out of stock!", "error")
        return redirect(url_for('dashboard_student'))
    if current_user.balance < item.cost:
        flash("Insufficient funds!", "error")
        return redirect(url_for('dashboard_student'))
    
    current_user.balance -= item.cost
    item.stock -= 1
    code = secrets.token_hex(3).upper()
    receipt = Receipt(student_id=current_user.id, item_id=item.id, unique_code=code, status='PENDING')
    tx = Transaction(sender_id=current_user.id, receiver_id=1, amount=item.cost, reason=f"Store: {item.name}")
    
    db.session.add(receipt)
    db.session.add(tx)
    db.session.commit()
    flash(f"Purchased {item.name}! Code: {code}", "success")
    return redirect(url_for('dashboard_student'))

# --- UPDATE: Add this Register Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        class_id = request.form.get('class_id')
        
        if User.query.filter_by(email=email).first():
            flash("Email already exists", "error")
        else:
            # Create Student
            new_student = User(name=name, email=email, role='student', 
                               password=generate_password_hash(password, method='pbkdf2:sha256'),
                               class_id=int(class_id))
            
            # Auto-link to Branch
            cls = ClassRoom.query.get(int(class_id))
            new_student.branch_id = cls.branch_id
            
            db.session.add(new_student)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
            
    # Load classes for dropdown
    classes = ClassRoom.query.all()
    return render_template('register.html', classes=classes)

@app.route('/tutor/add_student', methods=['POST'])
@login_required
def tutor_add_student():
    # Check if user manages ANY class
    if not current_user.tutor_of_class:
        flash("You are not a Class Tutor!", "error")
        return redirect(url_for('dashboard_teacher'))
    
    # Get the first class they manage (assuming 1 class per tutor)
    my_class = current_user.tutor_of_class[0]
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')  # ADD THIS LINE
    
    # Validate password exists
    if not password:
        flash("Password is required!", "error")
        return redirect(url_for('dashboard_teacher'))
    
    if User.query.filter_by(email=email).first():
        flash("Email already exists!", "error")
    else:
        # Create Student linked to Tutor's Class & Branch
        new_student = User(name=name, email=email, role='student',
                           password=generate_password_hash(password, method='pbkdf2:sha256'),  # USE FORM PASSWORD
                           class_id=my_class.id,
                           branch_id=my_class.branch_id)
        
        db.session.add(new_student)
        db.session.commit()
        flash(f"Added {name} to Class {my_class.name}. Password set successfully.", "success")
        
    return redirect(url_for('dashboard_teacher'))

@app.route('/mobile')
@login_required
def mobile_dashboard():
    """Mobile-optimized money transfer interface"""
    if current_user.role not in ['teacher', 'tutor', 'hod']:
        return "Denied", 403
    
    # Get students based on role
    students = []
    if current_user.role == 'tutor' and current_user.tutor_of_class:
        for cls in current_user.tutor_of_class:
            students.extend(User.query.filter_by(role='student', class_id=cls.id).all())
    elif current_user.branch_id:
        branch_classes = ClassRoom.query.filter_by(branch_id=current_user.branch_id).all()
        class_ids = [c.id for c in branch_classes]
        if class_ids:
            students = User.query.filter(User.role == 'student', User.class_id.in_(class_ids)).all()
    
    # Remove duplicates
    seen = set()
    unique_students = []
    for s in students:
        if s.id not in seen:
            seen.add(s.id)
            unique_students.append(s)
    students = unique_students
    
    # Get recent transactions
    transactions = Transaction.query.filter(
        (Transaction.sender_id == current_user.id) | (Transaction.receiver_id == current_user.id)
    ).order_by(Transaction.timestamp.desc()).limit(10).all()
    
    return render_template('mobile_transfer.html', 
                         students=students, 
                         transactions=transactions)


@app.route('/mobile/transfer', methods=['POST'])
@login_required
def mobile_transfer():
    """Quick transfer from mobile interface"""
    if current_user.role not in ['teacher', 'tutor', 'hod']:
        return "Denied", 403
    
    receiver_id = request.form.get('receiver_id')
    amount = int(request.form.get('amount'))
    reason = request.form.get('reason', 'Mobile transfer')
    
    if current_user.balance < amount:
        flash("Insufficient balance!", "error")
        return redirect(url_for('mobile_dashboard'))
    
    receiver = User.query.filter_by(id=receiver_id, role='student').first()
    if not receiver:
        flash("Student not found", "error")
        return redirect(url_for('mobile_dashboard'))
    
    # Verify permission
    can_send = False
    if current_user.tutor_of_class:
        for cls in current_user.tutor_of_class:
            if receiver.class_id == cls.id:
                can_send = True
                break
    elif current_user.branch_id and receiver.branch_id == current_user.branch_id:
        can_send = True
    
    if not can_send:
        flash("Cannot send to this student", "error")
        return redirect(url_for('mobile_dashboard'))
    
    # Perform transfer
    current_user.balance -= amount
    receiver.balance += amount
    
    tx = Transaction(
        sender_id=current_user.id,
        receiver_id=receiver.id,
        amount=amount,
        reason=reason
    )
    
    db.session.add(tx)
    db.session.commit()
    
    flash(f"Sent {amount} coins to {receiver.name}!", "success")
    return redirect(url_for('mobile_dashboard'))



# --- MAIN ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email="principal@school.com").first():
            p = User(email="principal@school.com", password=generate_password_hash("admin", method='pbkdf2:sha256'), 
                     name="Principal Skinner", role="principal", balance=1000000)
            db.session.add(p)
            db.session.commit()
            
    app.run(debug=True, port=5000)
