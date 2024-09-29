import io
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

import pytest
from src.app import app, db, User
from testcontainers.postgres import PostgresContainer
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

# Create a fixture for the Postgres container
@pytest.fixture(scope='module')
def postgres_container():
    with PostgresContainer("postgres:16.3-bookworm") as postgres:
        # Set up volume mapping for init scripts
        initdb_script_dir = Path(__file__).parent / 'sql'
        postgres.with_volume_mapping(str(initdb_script_dir), "/docker-entrypoint-initdb.d/")
        yield postgres


# Create a fixture for the Flask test client
@pytest.fixture(scope="module")
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


# Fixture for initializing the database
@pytest.fixture(scope='function')
def init_db(postgres_container):
    # Update the app's SQLAlchemy URI with the test container connection URL
    # app.config['SQLALCHEMY_DATABASE_URI'] = postgres_container.get_connection_url()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://inventorydbuser:password@db:5432/inventorydb'
    
    # Ensure the app context is pushed for database operations
    with app.app_context():
        # db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

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
        assert row[0].lower().startswith("postgresql 16.3")


# This is a feature in the generic DbContainer class
# but it can't be tested on its own
# so is tested in various database modules
def test_quoted_password():
    user = "inventorydbuser"
    password = "password"
    quoted_password = "password"
    driver = "psycopg2"
    port = "5432"

    kwargs = {
        "driver": driver,
        "username": user,
        "password": password,
        "port":port
    }
    with PostgresContainer("postgres:16.3", **kwargs) as container:
        port = container.get_exposed_port(5432)
        host = container.get_container_host_ip()
        expected_url = f"postgresql+{driver}://{user}:{quoted_password}@{host}:{port}/test"

        url = container.get_connection_url()
        assert url == expected_url

        with sqlalchemy.create_engine(expected_url).begin() as connection:
            result = connection.execute(sqlalchemy.text("select version()"))
            for row in result:
                assert row[0].lower().startswith("postgresql 16.3")


# Test the user creation via the SQLAlchemy model
def test_user_creation(init_db):
    # Create a test user
    hashed_password = bcrypt.generate_password_hash("sells seashells").decode('utf-8')
    user = User(username="sally", password=hashed_password)
    db.session.add(user)
    db.session.commit()

    # Query the database for the user
    user_in_db = User.query.filter_by(username="sally").first()

    # Assertions to validate that the user exists and the password is hashed
    assert user_in_db is not None
    assert user_in_db.username == "sally"
    assert bcrypt.check_password_hash(user_in_db.password, "sells seashells")


# def test_initialize_db_via_initdb_dir(postgres_container):
#     insert_query = "INSERT INTO users_tb(username, password) VALUES ('sally', 'sells seashells');"
#     select_query = "SELECT id, username FROM users_tb;"

#     # Connect to the database using SQLAlchemy
#     engine = sqlalchemy.create_engine(postgres_container.get_connection_url())

#     with engine.begin() as connection:
#         # Insert data
#         connection.execute(sqlalchemy.text(insert_query))
        
#         # Query to check data
#         result = connection.execute(sqlalchemy.text(select_query))
#         fetched_result = result.fetchall()
    
#     # Test the results
#     assert fetched_result[0] == (1, "sally")  # Assuming you're only selecting id and username


def test_login_post(client):
    '''Testing login post - this will probably require Testcontainers with username and password in the database to test correctly...'''
    response = client.post('/login', data=dict(username='testuser', password='testpass'))
    assert b'Login successful' in response.data  # Adjust according to your actual response content


def test_upload_get(client):
    response = client.get('/upload')
    assert response.status_code == 302
    assert b'Upload Excel File' in response.data  # Adjust according to your actual response content


def test_upload_post(client):
    data = {
        'file': (io.BytesIO(b"some initial text data"), 'test.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert b'File uploaded successfully' in response.data  # Adjust according to your actual response content
