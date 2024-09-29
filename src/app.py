import logging
from typing import Any

from flask import Flask, jsonify, request
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_mixins import AllFeaturesMixin

# Initialize the app, database, and encryption handler
app = Flask(__name__)

logger = logging.getLogger()

db: SQLAlchemy = SQLAlchemy()
bcrypt: Bcrypt = Bcrypt(app)


def app_setup(app_config: dict[str, Any] | None = None):
    if app_config is not None:
        logger.info('found %s additional app_config parameters', len(app_config))
        app.config.update(app_config)
    else:
        logger.info('found no additional app_config parameters, using sqlite')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)


# Define the User model
class User(db.Model, AllFeaturesMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


# POST endpoint for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Validate input
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400

    user = User.query.filter_by(username=data['username']).first()

    # Check if user exists and verify password
    if user and bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401


@app.post('/user')
def user_post():
    data = request.get_json()
    u = User(
        username=data['username'],
        password=bcrypt.generate_password_hash(data['password'], 12).decode(),
    )
    db.session.add(u)
    to_dict = u.to_dict()
    return jsonify(to_dict), 201


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
