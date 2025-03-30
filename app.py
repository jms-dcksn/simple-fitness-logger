from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_migrate import Migrate
from database import db
from models import Exercise, Set, Workout, WorkoutExercise
from datetime import datetime
from config import APP_METADATA

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness_logger.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)


# Add this function after the other route definitions
def get_last_set_for_exercise(exercise_id, current_workout_id):
    """Get the set with the heaviest weight for an exercise, excluding sets from the current workout."""
    return Set.query.filter(
        Set.exercise_id == exercise_id,
        Set.workout_id != current_workout_id,
        Set.weight.isnot(None)  # Exclude sets with no weight recorded
    ).order_by(Set.weight.desc()).first()

@app.route('/')
def index():
    exercises = Exercise.query.all()
    return render_template('index.html', exercises=exercises)

@app.route('/workout', methods=['GET', 'POST'])
def workout():
    # Get the active workout (most recent unfinished workout)
    active_workout = Workout.query.filter_by(finished=False).order_by(Workout.date_created.desc()).first()
    exercises = Exercise.query.all()

    # Get past workouts for the list
    past_workouts = Workout.query.filter_by(finished=True).order_by(Workout.date_created.desc()).limit(5).all()
    
    if request.method == 'POST':
        # Create new workout
        workout = Workout(
            name=request.form['workout_name'],
            finished=False
        )
        db.session.add(workout)
        db.session.commit()
        
        # Add exercises to workout
        exercises = request.form.getlist('exercises[]')
        for i, exercise_id in enumerate(exercises):
            workout_exercise = WorkoutExercise(
                workout_id=workout.id,
                exercise_id=int(exercise_id),
                order=i
            )
            db.session.add(workout_exercise)
        
        db.session.commit()
        return redirect(url_for('workout'))
    
    if request.method == 'GET' and active_workout:
        # Add last set information for each exercise
        for workout_exercise in active_workout.workout_exercises:
            workout_exercise.last_set = get_last_set_for_exercise(
                workout_exercise.exercise.id,
                active_workout.id
            )
    
    return render_template('workout.html', 
                         exercises=exercises, 
                         active_workout=active_workout,
                         past_workouts=past_workouts)

@app.route('/history')
def history():
    # Get all workouts ordered by date
    workouts = Workout.query.order_by(Workout.date_created.desc()).all()
    
    # Get all exercises for the filter dropdown
    exercises = Exercise.query.all()
    
    # Calculate statistics
    total_workouts = len(workouts)
    
    # Calculate average weight and reps per workout
    sets = Set.query.all()
    total_workouts = max(1, total_workouts)  # Prevent division by zero
    avg_weight = sum(s.weight or 0 for s in sets) / total_workouts
    avg_reps = sum(s.reps for s in sets) / total_workouts
    
    # Calculate workout frequency (workouts per week)
    if workouts:
        first_workout = min(w.date_created for w in workouts)
        weeks = (datetime.now() - first_workout).days / 7
        workout_frequency = round(total_workouts / max(1, weeks), 1)
    else:
        workout_frequency = 0
    
    # Get most frequent exercises
    frequent_exercises = db.session.query(
        Exercise.name,
        db.func.count(Set.id).label('count')
    ).join(Set).group_by(Exercise.id)\
    .order_by(db.func.count(Set.id).desc())\
    .limit(10).all()
    
    # Format workout data for template
    formatted_workouts = []
    for workout in workouts:
        sets_by_exercise = {}
        for s in workout.sets:
            if s.exercise_id not in sets_by_exercise:
                sets_by_exercise[s.exercise_id] = {
                    'name': s.exercise.name,
                    'sets': [],
                }
            sets_by_exercise[s.exercise_id]['sets'].append({
                'set_number': len(sets_by_exercise[s.exercise_id]['sets']) + 1,
                'exercise_name': s.exercise.name,
                'reps': s.reps,
                'weight': s.weight
            })
        
        formatted_workouts.append({
            'date': workout.date_created,
            'sets': [item for sublist in [e['sets'] for e in sets_by_exercise.values()] for item in sublist]
        })

    return render_template('history.html',
        workouts=formatted_workouts,
        exercises=exercises,
        total_workouts=total_workouts,
        total_weight=round(avg_weight, 1),  # Rounded to 1 decimal place
        total_reps=round(avg_reps, 1),
        workout_frequency=workout_frequency,
        frequent_exercises=frequent_exercises
    )

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'delete_set':
            set_id = request.form.get('set_id')
            set_to_delete = Set.query.get_or_404(set_id)
            db.session.delete(set_to_delete)
            db.session.commit()
            return jsonify({'success': True})
            
        elif action == 'delete_workout':
            workout_id = request.form.get('workout_id')
            workout_to_delete = Workout.query.get_or_404(workout_id)
            
            # Delete workout_exercise associations first
            WorkoutExercise.query.filter_by(workout_id=workout_id).delete()
            
            # Delete associated sets
            Set.query.filter_by(workout_id=workout_id).delete()
            
            # Finally delete the workout
            db.session.delete(workout_to_delete)
            db.session.commit()
            return jsonify({'success': True})
    
    # Get all workouts with their sets
    workouts = Workout.query.order_by(Workout.date_created.desc()).all()
    # Get orphaned sets (sets without workouts)
    orphaned_sets = Set.query.filter_by(workout_id=None).order_by(Set.timestamp.desc()).all()
    
    return render_template('admin.html', 
                         workouts=workouts,
                         orphaned_sets=orphaned_sets)


# API endpoints
@app.route('/api/clone_workout', methods=['POST'])
def clone_workout():
    try:
        data = request.get_json()
        original_workout_id = data.get('workout_id')
        
        # First, check for any existing active workouts and delete them
        active_workouts = Workout.query.filter_by(finished=False).all()
        for workout in active_workouts:
            # Delete associated workout exercises first
            WorkoutExercise.query.filter_by(workout_id=workout.id).delete()
            # Delete any sets associated with this workout
            Set.query.filter_by(workout_id=workout.id).delete()
            # Delete the workout itself
            db.session.delete(workout)
        
        # Get the original workout
        original_workout = Workout.query.get_or_404(original_workout_id)
        
        # Create new workout
        new_workout = Workout(
            name=f"{original_workout.name}",
            finished=False
        )
        db.session.add(new_workout)
        db.session.flush()  # This assigns an ID to new_workout
        
        # Clone all workout exercises
        for we in original_workout.workout_exercises:
            new_we = WorkoutExercise(
                workout_id=new_workout.id,
                exercise_id=we.exercise_id,
                order=we.order
            )
            db.session.add(new_we)
        
        db.session.commit()
        return jsonify({'success': True, 'workout_id': new_workout.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/create_exercise', methods=['POST'])
def create_exercise():
    try:
        name = request.form.get('exercise_name')
        
        if not name:
            return jsonify({'error': 'Exercise name is required'}), 400
        
        # Check if exercise already exists
        existing_exercise = Exercise.query.filter_by(name=name).first()
        if existing_exercise:
            return jsonify({'error': 'Exercise already exists'}), 400
            
        exercise = Exercise(name=name)
        db.session.add(exercise)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'id': exercise.id,
            'name': exercise.name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Failed to create exercise',
            'details': str(e)
        }), 500

@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    exercises = Exercise.query.all()
    return jsonify([{'id': e.id, 'name': e.name} for e in exercises])

@app.route('/log_set', methods=['POST'])
def log_set():
    try:
        if request.is_json:
            # Handle JSON data from fetch API
            data = request.get_json()
            exercise_id = data['exercise_id']
            workout_id = None  # Quick log doesn't belong to a workout
            reps = int(data['reps'])
            weight = float(data['weight']) if data['weight'] is not None else None
        else:
            # Handle form data from regular form submission
            exercise_id = request.form['exercise_id']
            workout_id = request.form['workout_id']
            reps = int(request.form['reps'])
            weight = float(request.form['weight'])

        new_set = Set(
            exercise_id=exercise_id,
            workout_id=workout_id,
            reps=reps,
            weight=weight
        )
        db.session.add(new_set)
        db.session.commit()

        # Return JSON response for API calls, redirect for form submissions
        if request.is_json:
            return jsonify({'message': 'Set logged successfully'}), 200
        return redirect(url_for('workout'))

    except Exception as e:
        print(f"Error logging set: {str(e)}")
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        return "Error logging set", 400

@app.route('/swap_exercise', methods=['POST'])
def swap_exercise():
    print("Received swap exercise request")
    print("Form data:", request.form)
    workout_exercise_id = request.form.get('workout_exercise_id')
    new_exercise_id = request.form.get('new_exercise_id')
    
    workout_exercise = WorkoutExercise.query.get_or_404(workout_exercise_id)
    workout_exercise.exercise_id = new_exercise_id
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/delete_workout_exercise', methods=['POST'])
def delete_workout_exercise():
    try:
        data = request.get_json()
        workout_exercise_id = data.get('workout_exercise_id')
        
        # Delete the workout exercise
        workout_exercise = WorkoutExercise.query.get_or_404(workout_exercise_id)
        
        # Delete any associated sets
        Set.query.filter_by(
            workout_id=workout_exercise.workout_id,
            exercise_id=workout_exercise.exercise_id
        ).delete()
        
        # Delete the workout exercise
        db.session.delete(workout_exercise)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/add_workout_exercise', methods=['POST'])
def add_workout_exercise():
    try:
        workout_id = request.form.get('workout_id')
        exercise_id = request.form.get('exercise_id')
        
        # Get the highest order number for the current workout
        max_order = db.session.query(db.func.max(WorkoutExercise.order))\
            .filter_by(workout_id=workout_id).scalar() or -1
        
        # Create new workout exercise with next order number
        workout_exercise = WorkoutExercise(
            workout_id=workout_id,
            exercise_id=exercise_id,
            order=max_order + 1
        )
        
        db.session.add(workout_exercise)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/workouts', methods=['GET', 'POST'])
def handle_workouts():
    if request.method == 'POST':
        # Handle form data instead of JSON
        workout = Workout(name=request.form['workout_name'])
        db.session.add(workout)
        db.session.commit()
        
        # Handle multiple exercises from form
        exercises = request.form.getlist('exercises[]')
        for i, exercise_id in enumerate(exercises):
            workout_exercise = WorkoutExercise(
                workout_id=workout.id,
                exercise_id=int(exercise_id),
                order=i
            )
            db.session.add(workout_exercise)
        
        db.session.commit()
        return redirect(url_for('workout'))
    else:
        workouts = Workout.query.all()
        return jsonify([{
            'id': w.id,
            'name': w.name,
            'date': w.date_created.isoformat()
        } for w in workouts])


@app.route('/api/history/filter', methods=['GET'])
def filter_history():
    try:
        # Get filter parameters
        search_query = request.args.get('search', '').lower()
        exercise_id = request.args.get('exercise', '')
        date_filter = request.args.get('date', '')

        # Start with base query for sets
        query = Set.query.join(Exercise).order_by(Set.timestamp.desc())

        # Apply filters
        if exercise_id and exercise_id != 'Filter by exercise...':
            query = query.filter(Set.exercise_id == int(exercise_id))
        
        if search_query:
            query = query.filter(Exercise.name.ilike(f'%{search_query}%'))

        if date_filter:
            try:
                date_obj = datetime.strptime(date_filter, '%Y-%m-%d')
                query = query.filter(db.func.date(Set.timestamp) == date_obj.date())
            except ValueError:
                pass

        # Get all sets
        sets = query.all()

        # Format the sets for response
        formatted_sets = []
        for set_item in sets:
            formatted_sets.append({
                'exercise_name': set_item.exercise.name,
                'reps': set_item.reps,
                'weight': set_item.weight,
                'timestamp': set_item.timestamp.isoformat()
            })

        # Group sets by date
        grouped_sets = {}
        for set_item in formatted_sets:
            date = set_item['timestamp'].split('T')[0]
            if date not in grouped_sets:
                grouped_sets[date] = []
            grouped_sets[date].extend([set_item])

        # Format final response
        response = []
        for date in sorted(grouped_sets.keys(), reverse=True):
            response.append({
                'date': f"{date}T00:00:00",
                'sets': grouped_sets[date]
            })

        return jsonify(response)

    except Exception as e:
        print(f"Error in filter_history: {str(e)}")
        return jsonify({'error': 'An error occurred while filtering history'}), 500

# Add this after creating the Flask app
@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt=None):
    return date.strftime(fmt)

@app.route('/finish_workout', methods=['POST'])
def finish_workout():
    workout_id = request.form['workout_id']
    workout = Workout.query.get_or_404(workout_id)
    workout.finished = True
    db.session.commit()
    return redirect(url_for('index'))

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