from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database import db
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from models import user
from models.user import User
from models.meal import Meal
import bcrypt

class Config:
  SECRET_KEY = 'base-key'
  SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:admin123@127.0.0.1:3306/daily-diet-crud"
  SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevConfig(Config):
  DEBUG = True

app = Flask(__name__)
app.config.from_object(DevConfig)

login_manager = LoginManager()
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

limiter = Limiter(get_remote_address, app=app, default_limits=["100 per minute"])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'JSON inválido ou ausente.'}), 400
    
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Campos obrigatórios não foram enviados.'}), 400

    if db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none():
        return jsonify({'error': 'Nome de usuário já existe.'}), 400
    
    hashed_password = bcrypt.hashpw(str.encode(password), bcrypt.gensalt())
    new_user = User(username=username, password=hashed_password, role='user')
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Usuário criado com sucessso.'}), 201

@app.route("/user/<int:id_user>/password", methods=["PUT"])
@login_required
def update_password(id_user):
    data = request.get_json()

    if not data:
        return jsonify({'error': 'JSON inválido ou ausente.'}), 400
    
    user = db.session.get(User, id_user)
    password = data.get('password')

    if id_user != current_user.id and current_user.role == "user":
        return jsonify({"message": "Operação não permitida!"}), 403

    if user and password:
        hashed_password = bcrypt.hashpw(str.encode(password), bcrypt.gensalt())
        user.password = hashed_password
        db.session.commit()
        return jsonify({"username": f"Usuário {id_user} atualizado com sucesso!"})

    return jsonify({"message": "Usuário não encontrado"}), 404

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'JSON inválido ou ausente.'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
      return jsonify({'error': 'Campos obrigatórios não foram enviados.'}), 400

    if username and password:
      user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
            
      if user and bcrypt.checkpw(str.encode(password), str.encode(user.password)):
        login_user(user)
        print(current_user.is_authenticated)
        return jsonify({'message': 'Autenticação realizada com sucesso.'})
                
    return jsonify({'error': 'Credenciais inválidas.'}), 401    
        
@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout realizado com sucesso!"})

@app.route('/meals', methods=['POST'])
@login_required
def create_meal():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'JSON inválido ou ausente.'}), 400

    name = data.get('name')
    description = data.get('description')
    datetime = data.get('datetime')
    within_diet = data.get('within_diet')

    if not name or not description or not datetime or within_diet is None:
        return jsonify({'error': 'Os campos obrigatórios não foram enviados.'}), 400

    meal = Meal(
       user_id=current_user.id,
       name=name,
       description=description,
       datetime=datetime,
       within_diet=within_diet
    )
    db.session.add(meal)
    db.session.commit()

    return jsonify({'message': 'Refeição criada com sucesso', 'meal': {
        'id': meal.id,
        'name': meal.name,
        'description': meal.description,
        'datetime': meal.datetime,
        'within_diet': meal.within_diet
    }}), 201

@app.route('/meals', methods=['GET'])
@login_required
def list_meals():
    meals = db.session.execute(
        db.select(Meal).filter_by(user_id=current_user.id)
    ).scalars().all()

    return jsonify({'meals': [{
        'id': m.id,
        'name': m.name,
        'description': m.description,
        'datetime': m.datetime,
        'within_diet': m.within_diet
    } for m in meals]}), 200

@app.route('/meals/<int:meal_id>', methods=['GET'])
@login_required
def get_meal(meal_id):
    meal = db.session.get(Meal, meal_id)

    if not meal:
        return jsonify({'error': 'Refeição não encontrada.'}), 404

    if meal.user_id != current_user.id:
        return jsonify({'error': 'Acesso não autorizado.'}), 403

    return jsonify({'meal': {
        'id': meal.id,
        'name': meal.name,
        'description': meal.description,
        'datetime': meal.datetime,
        'within_diet': meal.within_diet
    }}), 200

@app.route('/meals/<int:meal_id>', methods=['PUT'])
@limiter.limit("10 per minute")
@login_required
def update_meal(meal_id):
    meal = db.session.get(Meal, meal_id)

    if not meal:
        return jsonify({'error': 'Refeição não encontrada.'}), 404

    if meal.user_id != current_user.id:
        return jsonify({'error': 'Acesso não autorizado.'}), 403

    data = request.get_json()

    if not data:
        return jsonify({'error': 'JSON inválido ou ausente.'}), 400
    
    name = data.get('name', meal.name)
    description = data.get('description', meal.description)
    datetime = data.get('datetime', meal.datetime)
    within_diet = data.get('within_diet') if data.get('within_diet') is not None else meal.within_diet

    if (name == meal.name and
        description == meal.description and
        datetime == meal.datetime and
        within_diet == meal.within_diet):
        return jsonify({'message': 'Nenhuma alteração detectada.'}), 200

    meal.name = name
    meal.description = description
    meal.datetime = datetime
    meal.within_diet = within_diet
    db.session.commit()

    return jsonify({'message': 'Refeição atualizada com sucesso', 'meal': {
        'id': meal.id,
        'name': meal.name,
        'description': meal.description,
        'datetime': meal.datetime,
        'within_diet': meal.within_diet
    }}), 200

@app.route('/meals/<int:meal_id>', methods=['DELETE'])
@login_required
def delete_meal(meal_id):
    meal = db.session.get(Meal, meal_id)

    if not meal:
        return jsonify({'error': 'Refeição não encontrada.'}), 404

    if meal.user_id != current_user.id:
        return jsonify({'error': 'Acesso não autorizado.'}), 403

    db.session.delete(meal)
    db.session.commit()

    return jsonify({'message': 'Refeição deletada com sucesso.'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
