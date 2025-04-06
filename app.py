from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_migrate import Migrate
from database import db
from models import Exercise, Set, Workout, WorkoutExercise
from datetime import datetime
from config import APP_METADATA
from blueprints.api.views import views

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness_logger.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

from blueprints.api.v1 import api_v1
app.register_blueprint(api_v1)
app.register_blueprint(views)


# # Add this after creating the Flask app
@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt=None):
    return date.strftime(fmt)

@app.context_processor
def inject_metadata():
    return dict(metadata=APP_METADATA)

if __name__ == '__main__':
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Start the Flask server')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port number to run the server on (default: 5000)')
    
    args = parser.parse_args()
    
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=args.port)