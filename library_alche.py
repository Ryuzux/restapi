from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from functools import wraps
from flask_httpauth import HTTPBasicAuth
from sqlalchemy import func
from datetime import datetime, date


app = Flask(__name__)

app.config['SECRET_KEY']= 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1234@localhost/library'

db = SQLAlchemy(app)
Migrate = Migrate(app, db)
auth = HTTPBasicAuth()

class book(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    title = db.Column(db.String(255))
    year = db.Column(db.Integer())
    total_page = db.Column(db.Integer)
    category_id = db.Column(db.Integer)
    books = db.relationship('book_writer', backref='info_book', lazy='dynamic')
    borrowed = db.relationship('borrow', backref='info_book_borrow', lazy='dynamic')

class writer(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    name = db.Column(db.String(255))
    nation = db.Column(db.String(255))
    birthday = db.Column(db.Date())
    writers = db.relationship('book_writer', backref='info_writer', lazy='dynamic')

class book_writer(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    writer_id = db.Column(db.Integer, db.ForeignKey('writer.id'), nullable=False)
    borrow_id = db.Column(db.Integer, db.ForeignKey('borrow.id'))
    borrowed = db.relationship('borrow', backref='info_book_writer')

class borrow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    start_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, server_default=func.current_timestamp())
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Boolean, default=True)
    confirmation = db.Column(db.Boolean, default=False)
    days_late = db.Column(db.Integer, default=0)

    def count_days_late(self):
        try:
            self.return_date = datetime.strftime(self.return_date, '%Y-%m-%d').date()
        except AttributeError:
            pass
        self.days_late = (self.return_date - self.end_date).days

class user(db.Model):
    id = db.Column(db.Integer, primary_key=True, index=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    users = db.relationship('borrow', backref='info_user', lazy='dynamic')

    @auth.verify_password
    def verify_password(username, password):
        User = user.query.filter_by(username=username).first()
        if User and User.password == password:
            return User
        
    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            username = request.authorization.username
            User = user.query.filter_by(username=username).first()
            if User and User.role == "admin":
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "Unauthorized"}), 401
        return wrapper

    def admin_or_user_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            username = request.authorization.username
            current_user = user.query.filter_by(username=username).first()
            if current_user:
                kwargs['current_user'] = current_user
                if current_user.role == "admin" or current_user.role == "user":
                    return fn(*args, **kwargs)
            return jsonify({"error": "Unauthorized"}), 401
        return wrapper

@app.route('/')
@auth.login_required
def home():
    return "welcome"

@app.route('/logout')
@user.admin_or_user_required
def logout(current_user):
    if current_user.role == 'admin' or current_user.role == 'user':
        current_user.pop('logged_in', None)
        return jsonify({
        'message':'success logout'
    })

@app.route('/book/')
@auth.login_required
@user.admin_or_user_required
def get_book(current_user):
    if current_user.role == 'admin' or current_user.role == 'user':
    
        return jsonify([
        {
            'id': book.id,
            'title': book.title,
            'year': book.year,
            'total_page': book.total_page
        } for book in book.query.all()
    ])

@app.route('/book/', methods=['POST'])
@auth.login_required
@user.admin_required
def add_book():
    data = request.get_json()
    if not 'title' in data:
        return jsonify({
            'error': 'Bad Request',
            'message': 'title must be input'

        }), 400
    b = book(
        title = data['title'],
        year = data['year'],
        total_page = data['total_page']
    )
    db.session.add(b)
    db.session.commit()
    return {
         'title': b.title,
        'year': b.year, 'total_page': b.total_page
    }, 200

@app.route('/book/<int:id>', methods=['PUT'])
@auth.login_required
@user.admin_required
def update_book(id):
    data = request.get_json()
    required_fields = ['title', 'year', 'total_page']
    if not all(field in data for field in required_fields):
        return jsonify({
            'error': 'Bad request',
            'message': 'Required fields are missing'
        }), 400
    up = book.query.filter_by(id=id).first()
    if up is None:
        return jsonify({'error': 'Book not found'}), 404
    up.title = data['title']
    up.year = data['year']
    up.total_page = data['total_page']
    db.session.commit()
    return jsonify({
        'id': up.id, 'title': up.title, 'year': up.year,
        'total_page': up.total_page
    }), 200

@app.route('/writer/')
@auth.login_required
@user.admin_or_user_required
def get_writer(current_user):
    if current_user.role == 'admin' or current_user.role == 'user':

        return jsonify([
        {
            'id': Writer.id, 'name': Writer.name,
            'nation': Writer.nation, 'birthday': Writer.birthday
        }for Writer in writer.query.all()
    ])

@app.route('/writer/', methods=['POST'])
@auth.login_required
@user.admin_required
def add_writer():
    data = request.get_json()
    w = writer(
        name=data['name'],
        nation=data['nation'],
        birthday=data['birthday']
    )
    db.session.add(w)
    db.session.commit()
    return {
         'id': w.id, 'name': w.name, 'nation': w.nation,
        'birthday': w.birthday
    }, 200

@app.route('/bookwriter/')
@auth.login_required
@user.admin_or_user_required
def get_book_writer(current_user):
    if current_user.role == 'admin' or current_user.role == 'user':
        return jsonify([
        {
            'id': bw.id,
            'book_and_writer':{
                'title': bw.info_book.title,
                'year': bw.info_book.year,
                'total_page': bw.info_book.total_page,
                'name_writer': bw.info_writer.name,
                'birthday': bw.info_writer.birthday,
                'nation': bw.info_writer.nation
            }
        }for bw in book_writer.query.all()
    ])

@app.route('/bookwriter/', methods=['POST'])
@auth.login_required
@user.admin_required
def add_id():
    data = request.get_json()
    if not 'book_id' in data or not 'writer_id' in data:
        return jsonify({
            'error': 'bad request',
            'message': 'u need enter available id from both'
        }), 400
    b_id = book.query.filter_by(id=data['book id']).first()
    if not b_id:
        return {
            'error': 'bad request',
            'message': 'invalid book id, or not available id'
        }
    w_id = writer.query.filter_by(id=data['writer_id']).first()
    if not w_id:
        return {
            'error': 'bad request',
            'message': 'invalid writer id, or not available id'
        }
    get_all = book_writer(
        book_id = data['book id'],
        writer_id = data['writer id']
    )
    db.session.add(get_all)
    db.session.commit()
    return {
        'book_id': get_all.book_id, 'writer id': get_all.writer_id,
        'book_and_writer': {
            'title': get_all.info_book.title,
            'name_writer': get_all.info_writer.name,
            'year': get_all.info_book.year,
            'total_page': get_all.info_book.total_page,        
    }
    }, 201

@app.route('/borrow/')
@auth.login_required
@user.admin_or_user_required
def get_borrow(current_user):
    borrowed_books = borrow.query.filter_by(user_id=current_user.id, status=True).all()
    name = current_user.username
    if not borrowed_books:
        return jsonify({'message': 'No currently borrowed books found for {}'.format(name)})
    result = [{
        'id': el.id,
        'book_id': el.book_id,
        'user': el.info_user.username,
        'title': el.info_book_borrow.title,
        'start_date': el.start_date.strftime('%Y-%m-%d'),
        'confirm_by': 'admin' if el.confirmation else 'unconfirmed',
        'end_date': el.end_date.strftime('%Y-%m-%d'),
        'status': 'borrowed' if el.status else 'returned'
    } for el in borrowed_books]
    return jsonify(result)

@app.route('/borrow/', methods=['POST'])
@auth.login_required
@user.admin_or_user_required
def add_borrow(current_user):
    data = request.get_json()
    existing_borrow = borrow.query.filter_by(book_id=data['book_id'], status=True).first()
    if existing_borrow:
        return jsonify({
            'error': 'bad request',
            'message': 'the book was borrowed or in process confirmed'
        })
    new_borrow = borrow(
        book_id=data['book_id'],
        user_id=current_user.id,
        start_date=data['start_date'],
        end_date=data['end_date']
    )
    db.session.add(new_borrow)
    db.session.commit()
    return jsonify(
        {'info_borrow':        
            {'id': new_borrow.id,
            'book_id': new_borrow.book_id,
            'title': new_borrow.info_book_borrow.title,
            'user': new_borrow.info_user.username,
            'confirm_by': 'unconfirmed'
        },
        'info_date':
            {'status': 'ready to borrow',
            'start_date': new_borrow.start_date.strftime('%Y-%m-%d'),
            'end_date': new_borrow.end_date.strftime('%Y-%m-%d'),
            'return_date': new_borrow.return_date,
            'days_late': new_borrow.days_late if new_borrow.days_late else 0
    }})

@app.route('/borrow/update', methods=['PUT'])
@auth.login_required
@user.admin_required
def update_borrow_confirm():
    data = request.get_json()
    borrow_id = data.get('id')
    if not borrow_id:
        return jsonify({
            'error': 'bad request',
            'message': 'id is required in the request body'
        }), 400
    borrow_entry = borrow.query.filter_by(id=borrow_id).first()
    if not borrow_entry:
        return jsonify({
            'error': 'not found',
            'message': 'no borrowing entry found for the specified id'
        }), 404
    if not borrow_entry.status:
        return jsonify({
            'error': 'bad request',
            'message': 'the book has already been returned'
        }), 400
    borrow_entry.confirmation = True
    db.session.commit()
    return jsonify(
        {'info_borrow':
            {'id': borrow_entry.id,
            'book_id': borrow_entry.book_id,
            'title': borrow_entry.info_book_borrow.title,
            'user': borrow_entry.info_user.username,
            'confirm_by': 'admin' if borrow_entry else 'unconfirmed',
            'status': 'borrow' if borrow_entry.status else 'returned'
        },
            'info_date':
            {'start_date': borrow_entry.start_date.strftime('%Y-%m-%d'),
            'end_date': borrow_entry.end_date.strftime('%Y-%m-%d'),
            'return_date': borrow_entry.return_date,
            'days_late': borrow_entry.days_late if borrow_entry else 0
    }}), 200

@app.route('/return/', methods=['PUT'])
@auth.login_required
@user.admin_or_user_required
def update_return_confirm(current_user):
    data = request.get_json()
    borrow_id = data.get('id')
    
    if not borrow_id:
        return jsonify({
            'error': 'bad request',
            'message': 'id is required in the request body'
        }), 400
    
    borrow_entry = borrow.query.filter_by(id=borrow_id, user_id=current_user.id).first()
    
    if not borrow_entry:
        return jsonify({
            'error': 'not found',
            'message': 'no borrowing entry found for the specified id'
        }), 404
    
    if not borrow_entry.status:
        return jsonify({
            'error': 'bad request',
            'message': 'the book has already been returned'
        }), 400
    borrow_entry.return_date = date.today()
    borrow_entry.confirmation = False
    borrow_entry.status = False
    borrow_entry.count_days_late()
    db.session.commit()
    return jsonify(
        {'info_borrow':
            {'id': borrow_entry.id,
            'book_id': borrow_entry.book_id,
            'user': current_user.username,
            'confirm_by': 'admin' if borrow_entry.confirmation else 'unconfirmed',
        },
            'info_date':
            {'status': 'borrow' if borrow_entry.status else 'returned',
            'start_date': borrow_entry.start_date.strftime('%Y-%m-%d'),
            'end_date': borrow_entry.end_date.strftime('%Y-%m-%d'),
            'return_date': borrow_entry.return_date.strftime('%Y-%m-%d'),
            'days_late': borrow_entry.days_late if borrow_entry.days_late else 0,
    }}), 200

@app.route('/return/update', methods=['PUT'])
@auth.login_required
@user.admin_required
def update_borrow_status():
    data = request.get_json()
    borrow_id = data.get('id')
    if not borrow_id:
        return jsonify({
            'error': 'bad request',
            'message': 'id is required in the request body'
        }), 400
    borrow_entry = borrow.query.filter_by(id=borrow_id).first()
    if not borrow_entry:
        return jsonify({
            'error': 'not found',
            'message': 'no borrowing entry found for the specified id'
        }), 404
    if borrow_entry.confirmation == True:
        return jsonify({
            'error': 'bad request',
            'message': 'the book already returned'
        }), 400
    borrow_entry.confirmation = True
    db.session.commit()
    return jsonify(
        {'info_borrow':
            {'id': borrow_entry.id,
            'book_id': borrow_entry.book_id,
            'title': borrow_entry.info_book_borrow.title,
            'user': borrow_entry.info_user.username,
            'confirm_by': 'admin' if borrow_entry else 'unconfirmed',
        },
            'info_date':
            {'status': 'borrow' if borrow_entry.status else 'returned',
            'return_date': borrow_entry.return_date.strftime('%Y-%m-%d') if borrow_entry.return_date else None,
            'start_date': borrow_entry.start_date.strftime('%Y-%m-%d'),
            'end_date': borrow_entry.end_date.strftime('%Y-%m-%d'),
            'days_late': borrow_entry.days_late if borrow_entry else 0
    }}), 200

@app.route('/report/')
@auth.login_required
@user.admin_required
def get_report():
    start = request.form.get('start_date')
    end = request.form.get('end_date')
    late = request.form.get('days_late')
    filtered = borrow.query
    if start:
        filtered = filtered.filter(borrow.start_date >= start)
    if end:
        filtered = filtered.filter(borrow.end_date <= end)
    if late:
        filtered = filtered.filter(borrow.days_late > late)

    result = [
        {'info_borrow':
            {'id': el.id,
            'book_id': el.book_id,
            'user': el.info_user.username,
            'title': el.info_book_borrow.title,
            'confirm_by': 'admin' if el.confirmation else 'unconfirmed'
            },
        'info_date':
            {'start_date': el.start_date.strftime('%Y-%m-%d'),
            'end_date': el.end_date.strftime('%Y-%m-%d'),
            'return_date': el.return_date.strftime('%Y-%m-%d') if el.return_date else None,
            'days_late': el.days_late if el.days_late else 0,
            'status': 'borrowed' if el.status else 'returned'
        }} for el in filtered.all()
    ]
    return jsonify(result)


app.run(host="127.0.0.1", port = 5000, debug=True)