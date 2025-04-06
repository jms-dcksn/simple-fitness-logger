from flask import jsonify, render_template, redirect, url_for, request
from . import views
from models import Exercise, Workout, Set, WorkoutExercise, db
from datetime import datetime


# Add this function after the other route definitions
def get_last_set_for_exercise(exercise_id, current_workout_id):
    """Get the set with the heaviest weight for an exercise, excluding sets from the current workout."""
    return Set.query.filter(
        Set.exercise_id == exercise_id,
        Set.workout_id != current_workout_id,
        Set.weight.isnot(None)  # Exclude sets with no weight recorded
    ).order_by(Set.weight.desc()).first()


@views.route('/')
def index():
    exercises = Exercise.query.all()
    exercises_data = [{'id': e.id, 'name': e.name} for e in exercises]
    return render_template('index.html', exercises=exercises_data)

# Move other view routes here...

@views.route('/workout', methods=['GET', 'POST'])
def workout():
    # Get the active workout (most recent unfinished workout)
    active_workout = Workout.query.filter_by(finished=False).order_by(Workout.date_created.desc()).first()
    exercises = Exercise.query.all()
    exercises_data = [{'id': e.id, 'name': e.name} for e in exercises]

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
                         exercises=exercises_data, 
                         active_workout=active_workout,
                         past_workouts=past_workouts)

@views.route('/history')
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

@views.route('/admin', methods=['GET', 'POST'])
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

@views.route('/finish_workout', methods=['POST'])
def finish_workout():
    workout_id = request.form['workout_id']
    workout = Workout.query.get_or_404(workout_id)
    workout.finished = True
    db.session.commit()
    return redirect(url_for('index'))