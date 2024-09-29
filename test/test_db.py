import io
from json import dumps
from pathlib import Path

import pytest
from flask.testing import FlaskClient
from flask_bcrypt import Bcrypt
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from src.app import User, app, app_setup, db

bcrypt = Bcrypt(app)


# Create a fixture for the Postgres container
@pytest.fixture(scope='session', autouse=True)
def postgres_container():
    postgres = PostgresContainer('postgres:16-alpine')

    # Set up volume mapping for init scripts
    initdb_script_dir = Path(__file__).parent.parent / 'sql'
    postgres.with_volume_mapping(str(initdb_script_dir), '/docker-entrypoint-initdb.d/')

    with postgres:
        yield postgres


# Create a fixture for the Flask test client
@pytest.fixture(scope='module')
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


# Fixture for initializing the database
@pytest.fixture(scope='session', autouse=True)
def init_db(postgres_container: PostgresContainer):
    # Update the app's SQLAlchemy URI with the test container connection URL
    # app.config['SQLALCHEMY_DATABASE_URI'] = postgres_container.get_connection_url()
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://inventorydbuser:password@db:5432/inventorydb'
    app_setup(
        app_config={
            'SQLALCHEMY_DATABASE_URI': postgres_container.get_connection_url()
        }
    )

    with app.app_context():
        # db.create_all()
        yield db


# Test using Flask-SQLAlchemy
def test_docker_run_postgres_with_flask_sqlalchemy(postgres_container):
    # Update the app's SQLAlchemy URI with the test container connection URL
    # app.config['SQLALCHEMY_DATABASE_URI'] = postgres_container.get_connection_url()

    # Ensure the app context is pushed for database operations
    with app.app_context():
        # Reflect the database connection using Flask-SQLAlchemy's db object
        result = db.session.execute(text('SELECT version()'))
        row = result.fetchone()

        # Assertions to validate the PostgreSQL version
        assert row is not None
        assert row[0].lower().startswith('postgresql 16')


# Test the user creation via the SQLAlchemy model
def test_user_creation():
    # Create a test user
    hashed_password = bcrypt.generate_password_hash('sells seashells').decode('utf-8')
    user = User(username='sally', password=hashed_password)
    db.session.add(user)
    db.session.commit()

    # Query the database for the user
    user_in_db = User.query.filter_by(username='sally').first()

    # Assertions to validate that the user exists and the password is hashed
    assert user_in_db is not None
    assert user_in_db.username == 'sally'
    assert bcrypt.check_password_hash(user_in_db.password, 'sells seashells')


def test_login_post(client: FlaskClient):
    """Testing login post

    this will probably require Testcontainers with username and password
    in the database to test correctly...
    """
    response = client.post(
        '/user',
        data=dumps({'username': 'testuser', 'password': 'testpass'}),
        content_type='application/json',
    )
    assert response.status_code == 201

    response = client.post(
        '/login',
        data=dumps({'username': 'testuser', 'password': 'testpass'}),
        content_type='application/json',
    )
    # Adjust according to your actual response content
    assert b'Login successful' in response.data


def test_upload_get(client):
    response = client.get('/upload')
    # assert response.status_code == 302
    # Adjust according to your actual response content
    assert b'404 Not Found' in response.data


def test_upload_post(client):
    data = {'file': (io.BytesIO(b'some initial text data'), 'test.txt')}
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    # Adjust according to your actual response content
    assert b'404 Not Found' in response.data
