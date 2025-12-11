from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# ==================== MODELE BAZY DANYCH ====================

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    manager_email = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<Department {self.name}>'

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_type = db.Column(db.String(50), nullable=False)  # 'Leave' or 'Purchase'
    employee_name = db.Column(db.String(100), nullable=False)
    employee_email = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50))
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Oczekujący')  # Oczekujący, Zatwierdzony, Odrzucony
    priority = db.Column(db.String(20), default='Średnia')
    
    # Pola dla wniosków urlopowych
    leave_start_date = db.Column(db.Date)
    leave_end_date = db.Column(db.Date)
    leave_days = db.Column(db.Integer)
    leave_reason = db.Column(db.Text)
    
    # Pola dla wniosków zakupowych
    item_description = db.Column(db.Text)
    quantity = db.Column(db.Integer)
    estimated_cost = db.Column(db.Float)
    justification = db.Column(db.Text)
    
    # Pola zatwierdzania
    approver_name = db.Column(db.String(100))
    approver_email = db.Column(db.String(100))
    approval_date = db.Column(db.DateTime)
    approver_comments = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Request {self.id} - {self.request_type}>'

# ==================== INICJALIZACJA BAZY ====================

def init_db():
    with app.app_context():
        db.create_all()
        
        # Dodaj przykładowe działy jeśli baza jest pusta
        if Department.query.count() == 0:
            departments = [
                Department(name='IT', manager_email='manager.it@firma.pl'),
                Department(name='HR', manager_email='manager.hr@firma.pl'),
                Department(name='Finanse', manager_email='manager.finance@firma.pl'),
                Department(name='Operacje', manager_email='manager.ops@firma.pl')
            ]
            db.session.add_all(departments)
            db.session.commit()
            print("✅ Baza danych zainicjalizowana z przykładowymi działami")
        
        # Dodaj przykładowe wnioski dla testowania
        if Request.query.count() == 0:
            sample_requests = [
                Request(
                    request_type='Urlop',
                    employee_name='Jan Kowalski',
                    employee_email='jan.kowalski@firma.pl',
                    department='IT',
                    leave_start_date=datetime.now().date() + timedelta(days=7),
                    leave_end_date=datetime.now().date() + timedelta(days=14),
                    leave_days=5,
                    leave_reason='Urlop wypoczynkowy',
                    status='Oczekujący',
                    priority='Średnia'
                ),
                Request(
                    request_type='Zakup',
                    employee_name='Anna Nowak',
                    employee_email='anna.nowak@firma.pl',
                    department='HR',
                    item_description='Laptop Dell XPS 15',
                    quantity=1,
                    estimated_cost=5999.00,
                    justification='Wymiana starego sprzętu',
                    status='Oczekujący',
                    priority='Wysoka'
                )
            ]
            db.session.add_all(sample_requests)
            db.session.commit()
            print("✅ Dodano przykładowe wnioski testowe")

# ==================== ROUTING - STRONY ====================

@app.route('/')
def index():
    """Strona główna z statystykami"""
    total_requests = Request.query.count()
    pending_requests = Request.query.filter_by(status='Oczekujący').count()
    approved_requests = Request.query.filter_by(status='Zatwierdzony').count()
    rejected_requests = Request.query.filter_by(status='Odrzucony').count()
    
    recent_requests = Request.query.order_by(Request.submission_date.desc()).limit(5).all()
    
    return render_template('index.html',
                         total_requests=total_requests,
                         pending_requests=pending_requests,
                         approved_requests=approved_requests,
                         rejected_requests=rejected_requests,
                         recent_requests=recent_requests)

@app.route('/new-request', methods=['GET', 'POST'])
def new_request():
    """Formularz nowego wniosku"""
    if request.method == 'POST':
        request_type = request.form.get('request_type')
        
        new_req = Request(
            request_type=request_type,
            employee_name=request.form.get('employee_name'),
            employee_email=request.form.get('employee_email'),
            department=request.form.get('department'),
            priority=request.form.get('priority', 'Średnia')
        )
        
        # Pola specyficzne dla typu wniosku
        if request_type == 'Urlop':
            start_date = datetime.strptime(request.form.get('leave_start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('leave_end_date'), '%Y-%m-%d').date()
            leave_days = (end_date - start_date).days + 1
            
            new_req.leave_start_date = start_date
            new_req.leave_end_date = end_date
            new_req.leave_days = leave_days
            new_req.leave_reason = request.form.get('leave_reason')
            
        elif request_type == 'Zakup':
            new_req.item_description = request.form.get('item_description')
            new_req.quantity = int(request.form.get('quantity', 1))
            new_req.estimated_cost = float(request.form.get('estimated_cost', 0))
            new_req.justification = request.form.get('justification')
        
        try:
            db.session.add(new_req)
            db.session.commit()
            
            # Tutaj można dodać wysyłanie emaila do managera
            send_notification_to_manager(new_req)
            
            flash('Wniosek został pomyślnie wysłany!', 'success')
            return redirect(url_for('my_requests'))
        except Exception as e:
            db.session.rollback()
            flash(f'Błąd przy zapisywaniu wniosku: {str(e)}', 'error')
    
    departments = Department.query.all()
    return render_template('new_request.html', departments=departments)

@app.route('/my-requests')
def my_requests():
    """Lista wszystkich wniosków"""
    status_filter = request.args.get('status', 'all')
    type_filter = request.args.get('type', 'all')
    
    query = Request.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if type_filter != 'all':
        query = query.filter_by(request_type=type_filter)
    
    requests_list = query.order_by(Request.submission_date.desc()).all()
    
    return render_template('my_requests.html', 
                         requests=requests_list,
                         status_filter=status_filter,
                         type_filter=type_filter)

@app.route('/approve-requests')
def approve_requests():
    """Lista wniosków do zatwierdzenia (dla managerów)"""
    pending_requests = Request.query.filter_by(status='Oczekujący').order_by(Request.submission_date.desc()).all()
    return render_template('approve_requests.html', requests=pending_requests)

@app.route('/approve/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    """Zatwierdzenie wniosku"""
    req = Request.query.get_or_404(request_id)
    
    req.status = 'Zatwierdzony'
    req.approver_name = request.form.get('approver_name', 'Manager')
    req.approver_email = request.form.get('approver_email', 'manager@firma.pl')
    req.approver_comments = request.form.get('comments', '')
    req.approval_date = datetime.utcnow()
    
    try:
        db.session.commit()
        
        # Tutaj można dodać wysyłanie emaila do pracownika
        send_notification_to_employee(req, 'approved')
        
        flash('Wniosek został zatwierdzony!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Błąd przy zatwierdzaniu: {str(e)}', 'error')
    
    return redirect(url_for('approve_requests'))

@app.route('/reject/<int:request_id>', methods=['POST'])
def reject_request(request_id):
    """Odrzucenie wniosku"""
    req = Request.query.get_or_404(request_id)
    
    req.status = 'Odrzucony'
    req.approver_name = request.form.get('approver_name', 'Manager')
    req.approver_email = request.form.get('approver_email', 'manager@firma.pl')
    req.approver_comments = request.form.get('comments', '')
    req.approval_date = datetime.utcnow()
    
    try:
        db.session.commit()
        
        # Tutaj można dodać wysyłanie emaila do pracownika
        send_notification_to_employee(req, 'rejected')
        
        flash('Wniosek został odrzucony.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Błąd przy odrzucaniu: {str(e)}', 'error')
    
    return redirect(url_for('approve_requests'))

@app.route('/dashboard')
def dashboard():
    """Dashboard ze statystykami i wykresami"""
    # Statystyki według statusu
    stats_by_status_raw = db.session.query(
        Request.status, 
        db.func.count(Request.id)
    ).group_by(Request.status).all()
    
    # Konwersja do listy słowników (JSON-serializable)
    stats_by_status = [{'status': row[0], 'count': row[1]} for row in stats_by_status_raw]
    
    # Statystyki według typu
    stats_by_type_raw = db.session.query(
        Request.request_type, 
        db.func.count(Request.id)
    ).group_by(Request.request_type).all()
    
    stats_by_type = [{'type': row[0], 'count': row[1]} for row in stats_by_type_raw]
    
    # Statystyki według działu
    stats_by_dept_raw = db.session.query(
        Request.department, 
        db.func.count(Request.id)
    ).group_by(Request.department).all()
    
    stats_by_dept = [{'department': row[0] or 'Brak', 'count': row[1]} for row in stats_by_dept_raw]
    
    return render_template('dashboard.html',
                         stats_by_status=stats_by_status,
                         stats_by_type=stats_by_type,
                         stats_by_dept=stats_by_dept)

# ==================== API ENDPOINTS (opcjonalne) ====================

@app.route('/api/requests')
def api_requests():
    """API endpoint zwracający wnioski w JSON"""
    requests_list = Request.query.all()
    return jsonify([{
        'id': r.id,
        'type': r.request_type,
        'employee': r.employee_name,
        'status': r.status,
        'date': r.submission_date.strftime('%Y-%m-%d')
    } for r in requests_list])

@app.route('/api/stats')
def api_stats():
    """API endpoint ze statystykami"""
    return jsonify({
        'total': Request.query.count(),
        'pending': Request.query.filter_by(status='Oczekujący').count(),
        'approved': Request.query.filter_by(status='Zatwierdzony').count(),
        'rejected': Request.query.filter_by(status='Odrzucony').count()
    })

# ==================== FUNKCJE POMOCNICZE ====================

def send_notification_to_manager(req):
    """Symulacja wysyłania emaila do managera"""
    dept = Department.query.filter_by(name=req.department).first()
    if dept:
        print(f"\n📧 EMAIL DO MANAGERA:")
        print(f"Do: {dept.manager_email}")
        print(f"Temat: Nowy wniosek: {req.request_type} - {req.employee_name}")
        print(f"Treść: Pracownik {req.employee_name} złożył wniosek typu {req.request_type}")
        print(f"Status: {req.status}\n")

def send_notification_to_employee(req, action):
    """Symulacja wysyłania emaila do pracownika"""
    print(f"\n📧 EMAIL DO PRACOWNIKA:")
    print(f"Do: {req.employee_email}")
    print(f"Temat: Twój wniosek został {'zatwierdzony' if action == 'approved' else 'odrzucony'}")
    print(f"Treść: Wniosek #{req.id} - Status: {req.status}")
    print(f"Komentarz: {req.approver_comments}\n")

# ==================== URUCHOMIENIE APLIKACJI ====================

if __name__ == '__main__':
    init_db()
    print("\n🚀 Aplikacja uruchomiona!")
    print("📍 Otwórz przeglądarkę: http://localhost:5000")
    print("⏹️  Zatrzymaj: Ctrl+C\n")
    app.run(debug=True)