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
    
    const response = await fetch(`/api/v1/${endpoint}`, options);
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
    console.log('Logging set with data:', { exerciseId, reps, weight, workoutId });
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

// Handle finishing a workout
async function finishWorkout(workoutId) {
    try {
        await fetchAPI(`workouts/${workoutId}`, 'PUT', { // Use fetchAPI
            finished: true
        });
        window.location.href = '/';
    } catch (error) {
        alert('Failed to finish workout: ' + error.message);
    }
}

            // Handle adding exercise to workout
            async function addExerciseToWorkout(form) {
                const searchInput = form.querySelector('input[name="searchExercise"]');
                const typedName = searchInput.value;
                
                const match = allExercises.find(ex => ex.name.toLowerCase() === typedName.toLowerCase());
                if (!match) {
                    alert(`Exercise "${typedName}" not found`);
                    return;
                }
            
                try {
                    const workoutId = form.querySelector('input[name="workout_id"]').value;
                    await fetchAPI(`workouts/${workoutId}/exercises`, 'POST', { // Use fetchAPI
                        exercise_id: match.id
                    });
                    window.location.reload();
                } catch (error) {
                    alert('Failed to add exercise: ' + error.message);
                }
            }

            async function swapExercise(form) {
                try {
                    // Ensure the form elements are correctly accessed
                        const workoutExerciseId = form.querySelector('input[name="workout_exercise_id"]').value;
                        const newExerciseId = form.querySelector('select[name="new_exercise_id"]').value;
                        const workoutId = form.querySelector('input[name="workout_id"]').value;
                        console.log(newExerciseId)
                        console.log(workoutExerciseId)
                        console.log(workoutId)

                        // Check if the values are correctly retrieved
                        if (!workoutExerciseId || !newExerciseId || !workoutId) {
                            alert('Please ensure all fields are filled out correctly.');
                            return;
                        }
            
                    // Remove the old exercise
                    await fetchAPI(`workouts/${workoutId}/exercises?workout_exercise_id=${workoutExerciseId}`, 'DELETE');
            
                    // Add the new exercise
                    await fetchAPI(`workouts/${workoutId}/exercises`, 'POST', {
                        exercise_id: parseInt(newExerciseId)
                    });
            
                    // Close modal and reload page
                    const modal = bootstrap.Modal.getInstance(document.getElementById('swapExerciseModal'));
                    modal.hide();
                    window.location.reload();
                } catch (error) {
                    alert('Failed to swap exercise: ' + error.message);
                }
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