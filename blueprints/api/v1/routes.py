from datetime import datetime
from flask import request, jsonify
from . import api_v1
from models import Exercise, Workout, Set, WorkoutExercise, db
from utils.responses import api_response, error_response

@api_v1.route('/exercises', methods=['GET', 'POST'])
def exercises():
    if request.method == 'GET':
        exercises = Exercise.query.all()
        return api_response([e.to_dict() for e in exercises])
    
    try:
        data = request.get_json()
        exercise = Exercise(name=data['name'])
        db.session.add(exercise)
        db.session.commit()
        return api_response(exercise.to_dict(), "Exercise created successfully", 201)
    except Exception as e:
        return error_response(str(e))

@api_v1.route('/workouts', methods=['GET', 'POST'])
def workouts():
    if request.method == 'GET':
        workouts = Workout.query.order_by(Workout.date_created.desc()).all()
        return api_response([w.to_dict() for w in workouts])
    
    try:
        data = request.get_json()
        workout = Workout(
            name=data['name'],
            finished=False
        )
        db.session.add(workout)
        db.session.commit()  # Commit here to get the workout ID
        
        # Add exercises if provided
        if 'exercises' in data:
            for i, exercise_id in enumerate(data['exercises']):
                we = WorkoutExercise(
                    workout_id=workout.id,  # Ensure workout.id is not None
                    exercise_id=exercise_id,
                    order=i
                )
                db.session.add(we)
                
        db.session.commit()
        return api_response(workout.to_dict(), "Workout created successfully", 201)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e))

# ... existing endpoints ...

@api_v1.route('/exercises/<int:exercise_id>', methods=['GET', 'PUT', 'DELETE'])
def exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    
    if request.method == 'GET':
        return api_response(exercise.to_dict())
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            exercise.name = data.get('name', exercise.name)
            db.session.commit()
            return api_response(exercise.to_dict(), "Exercise updated successfully")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(exercise)
            db.session.commit()
            return api_response(message="Exercise deleted successfully")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))

@api_v1.route('/workouts/<int:workout_id>', methods=['GET', 'PUT', 'DELETE'])
def workout(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    
    if request.method == 'GET':
        include_sets = request.args.get('include_sets', 'false').lower() == 'true'
        return api_response(workout.to_dict(include_sets=include_sets))
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            workout.name = data.get('name', workout.name)
            workout.finished = data.get('finished', workout.finished)
            db.session.commit()
            return api_response(workout.to_dict(), "Workout updated successfully")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))
    
    elif request.method == 'DELETE':
        try:
            # Delete associated workout exercises first
            WorkoutExercise.query.filter_by(workout_id=workout_id).delete()
            # Delete associated sets
            Set.query.filter_by(workout_id=workout_id).delete()
            # Delete the workout
            db.session.delete(workout)
            db.session.commit()
            return api_response(message="Workout deleted successfully")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))

@api_v1.route('/workouts/<int:workout_id>/exercises', methods=['POST', 'PUT', 'DELETE'])
def workout_exercises(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            exercise_id = data['exercise_id']
            
            # Get the highest order number
            max_order = db.session.query(db.func.max(WorkoutExercise.order))\
                .filter_by(workout_id=workout_id).scalar() or -1
            
            we = WorkoutExercise(
                workout_id=workout_id,
                exercise_id=exercise_id,
                order=max_order + 1
            )
            db.session.add(we)
            db.session.commit()
            return api_response(workout.to_dict(), "Exercise added to workout")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))
    
    elif request.method == 'PUT':
        try:
            # Reorder exercises
            data = request.get_json()
            exercise_orders = data['exercise_orders']  # [{exercise_id: 1, order: 0}, ...]
            
            for item in exercise_orders:
                we = WorkoutExercise.query.filter_by(
                    workout_id=workout_id,
                    exercise_id=item['exercise_id']
                ).first()
                if we:
                    we.order = item['order']
            
            db.session.commit()
            return api_response(workout.to_dict(), "Exercises reordered successfully")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))

    elif request.method == 'DELETE':
        try:
            workout_exercise_id = request.args.get('workout_exercise_id', type=int)
            if not workout_exercise_id:
                return error_response("Exercise ID is required", 400)
            
            we = WorkoutExercise.query.filter_by(id=workout_exercise_id).first()
            if not we:
                return error_response("Exercise not found in workout", 404)
            
            db.session.delete(we)
            db.session.commit()
            return api_response(message="Exercise removed from workout")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))

@api_v1.route('/sets', methods=['GET', 'POST'])
def sets():
    if request.method == 'GET':
        try:
            # Get filter parameters
            exercise_id = request.args.get('exercise_id')
            workout_id = request.args.get('workout_id')
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            query = Set.query
            
            if exercise_id:
                query = query.filter_by(exercise_id=exercise_id)
            if workout_id:
                query = query.filter_by(workout_id=workout_id)
            if date_from:
                query = query.filter(Set.timestamp >= datetime.fromisoformat(date_from))
            if date_to:
                query = query.filter(Set.timestamp <= datetime.fromisoformat(date_to))
            
            sets = query.order_by(Set.timestamp.desc()).all()
            return api_response([s.to_dict() for s in sets])
        except Exception as e:
            return error_response(str(e))
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            new_set = Set(
                exercise_id=data['exercise_id'],
                workout_id=data.get('workout_id'),  # Optional
                reps=data['reps'],
                weight=data.get('weight')  # Optional
            )
            db.session.add(new_set)
            db.session.commit()
            return api_response(new_set.to_dict(), "Set logged successfully", 201)
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))

@api_v1.route('/sets/<int:set_id>', methods=['GET', 'PUT', 'DELETE'])
def set_operations(set_id):
    set_item = Set.query.get_or_404(set_id)
    
    if request.method == 'GET':
        return api_response(set_item.to_dict())
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            set_item.reps = data.get('reps', set_item.reps)
            set_item.weight = data.get('weight', set_item.weight)
            db.session.commit()
            return api_response(set_item.to_dict(), "Set updated successfully")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(set_item)
            db.session.commit()
            return api_response(message="Set deleted successfully")
        except Exception as e:
            db.session.rollback()
            return error_response(str(e))

@api_v1.route('/stats', methods=['GET'])
def stats():
    try:
        # Get all workouts
        workouts = Workout.query.all()
        total_workouts = len(workouts)
        
        # Calculate average weight and reps per workout
        sets = Set.query.all()
        total_workouts = max(1, total_workouts)  # Prevent division by zero
        avg_weight = sum(s.weight or 0 for s in sets) / total_workouts
        avg_reps = sum(s.reps for s in sets) / total_workouts
        
        # Calculate workout frequency
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
        
        stats_data = {
            'total_workouts': total_workouts,
            'avg_weight': round(avg_weight, 1),
            'avg_reps': round(avg_reps, 1),
            'workout_frequency': workout_frequency,
            'frequent_exercises': [
                {'name': name, 'count': count}
                for name, count in frequent_exercises
            ]
        }
        
        return api_response(stats_data)
    except Exception as e:
        return error_response(str(e))

@api_v1.route('/history/filter', methods=['GET'])
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

@api_v1.route('/workouts/clone', methods=['POST'])
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