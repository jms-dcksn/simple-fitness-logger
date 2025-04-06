from datetime import datetime
from database import db

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sets = db.relationship('Set', backref='exercise', lazy=True)
    workouts = db.relationship('WorkoutExercise', back_populates='exercise')
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'sets_count': len(self.sets)
        }

class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'))
    def to_dict(self):
        return {
            'id': self.id,
            'exercise_id': self.exercise_id,
            'reps': self.reps,
            'weight': self.weight,
            'timestamp': self.timestamp.isoformat(),
            'workout_id': self.workout_id
        }

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    finished = db.Column(db.Boolean, default=False)
    workout_exercises = db.relationship('WorkoutExercise', back_populates='workout')
    sets = db.relationship('Set', backref='workout', lazy=True)
    def to_dict(self, include_sets=False):
        data = {
            'id': self.id,
            'name': self.name,
            'date_created': self.date_created.isoformat(),
            'finished': self.finished,
            'exercises': [{
                'id': we.exercise.id,
                'name': we.exercise.name,
                'order': we.order
            } for we in self.workout_exercises]
        }
        if include_sets:
            data['sets'] = [s.to_dict() for s in self.sets]
        return data

class WorkoutExercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    workout = db.relationship('Workout', back_populates='workout_exercises')
    exercise = db.relationship('Exercise', back_populates='workouts')