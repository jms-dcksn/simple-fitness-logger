// Utility functions
async function fetchAPI(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(`/api/${endpoint}`, options);
    return response.json();
}

// Exercise handling
async function addExercise(name) {
    return await fetchAPI('exercises', 'POST', { name });
}

async function getExercises() {
    return await fetchAPI('exercises');
}

// Set logging
async function logSet(exerciseId, reps, weight, workoutId = null) {
    return await fetchAPI('sets', 'POST', {
        exercise_id: exerciseId,
        reps,
        weight,
        workout_id: workoutId
    });
}

// Workout handling
async function createWorkout(name, exerciseIds) {
    return await fetchAPI('workouts', 'POST', {
        name,
        exercises: exerciseIds
    });
}

async function getWorkouts() {
    return await fetchAPI('workouts');
}

// Initialize page-specific functionality
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    
    if (path === '/workout') {
        initializeWorkoutPage();
    } else if (path === '/history') {
        initializeHistoryPage();
    }
});

function initializeWorkoutPage() {
    // Add workout page specific initialization
}

function initializeHistoryPage() {
    // Add history page specific initialization
}

// Add this to your existing main.js

async function initializeIndexPage() {
    const exerciseSelect = document.getElementById('exercise');
    const addExerciseBtn = document.getElementById('addExerciseBtn');
    const quickLogForm = document.getElementById('quickLogForm');

    // // Load existing exercises
    // const exercises = await getExercises();
    // exercises.forEach(exercise => {
    //     const option = document.createElement('option');
    //     option.value = exercise.id;
    //     option.textContent = exercise.name;
    //     exerciseSelect.appendChild(option);
    // });

     // Check if we're on the correct page with the required elements
     if (!exerciseSelect || !addExerciseBtn || !quickLogForm) {
        console.log('Required elements not found for index page');
        return;
    }

        // Handle new exercise button
        addExerciseBtn.addEventListener('click', async () => {
            const exerciseName = prompt('Enter exercise name:');
            if (exerciseName) {
                const newExercise = await addExercise(exerciseName);
                const option = document.createElement('option');
                option.value = newExercise.id;
                option.textContent = newExercise.name;
                exerciseSelect.appendChild(option);
                exerciseSelect.value = newExercise.id;
            }
        });
    
        // Handle form submission
        quickLogForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const exerciseId = exerciseSelect.value;
            const reps = document.getElementById('reps').value;
            const weight = document.getElementById('weight').value || null;
    
            try {
                await logSet(exerciseId, parseInt(reps), weight ? parseFloat(weight) : null);
                alert('Set logged successfully!');
                quickLogForm.reset();
            } catch (error) {
                alert('Error logging set');
                console.error(error);
            }
        });
}

// Update your DOMContentLoaded listener
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    
    if (path === '/') {
        initializeIndexPage();
    } else if (path === '/workout') {
        initializeWorkoutPage();
    } else if (path === '/history') {
        initializeHistoryPage();
    }
});