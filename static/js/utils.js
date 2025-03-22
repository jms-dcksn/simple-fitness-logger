// Exercise form handling
async function handleExerciseFormSubmit(e) {
    e.preventDefault();
    const formData = new FormData(this);
    
    try {
        const response = await fetch(this.action, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Error creating exercise');
        }
        
        const data = await response.json();
        
        // Fetch all exercises to refresh dropdowns
        const exercisesResponse = await fetch('/api/exercises');
        const exercises = await exercisesResponse.json();
        
        // Update all exercise select dropdowns on the page
        const selects = document.querySelectorAll('.exercise-select');
        selects.forEach(select => {
            select.innerHTML = '<option value="">Select Exercise</option>';
            exercises.forEach(exercise => {
                const option = new Option(exercise.name, exercise.id);
                select.add(option);
            });
        });
        
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('newExerciseModal'));
        modal.hide();
        
        // Reset the form
        this.reset();
    } catch (error) {
        console.error('Error:', error);
        alert(error.message || 'Error creating exercise');
    }
}

// Export utilities
window.fitnessUtils = {
    handleExerciseFormSubmit
};