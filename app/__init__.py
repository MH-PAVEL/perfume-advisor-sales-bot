from flask import Flask
from pymongo import MongoClient
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()


def create_app():
    app = Flask(__name__)

    # CORS handle
    CORS(app, resources={
         r"/flask/api/*": {"origins": [os.getenv("CORS_ORIGIN")]}})
    # CORS(app, origins=[os.getenv("CORS_ORIGIN")])

    # @app.before_request
    # def before_request():
    #     # Handle OPTIONS preflight request
    #     if request.method == 'options':
    #         response = make_response()
    #         response.headers['Access-Control-Allow-Origin'] = os.getenv(
    #             "CORS_ORIGIN")
    #         response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    #         response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    #         response.status_code = 200
    #         return response

    # MongoDB connection
    client = MongoClient(os.getenv("MONGO_URI"))
    app.db = client.get_default_database()

    with app.app_context():
        from app import routes

    return app
