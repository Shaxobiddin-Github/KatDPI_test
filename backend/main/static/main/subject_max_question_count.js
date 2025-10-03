// Fanni tanlaganda savollar soni limitini olish uchun AJAX kod namunasi
function updateMaxQuestionCount(subjectId) {
    fetch(`/api/subject-max-question-count/?subject_id=${subjectId}`)
        .then(response => response.json())
        .then(data => {
            if (data.max_question_count !== undefined) {
                // Masalan, input max atributini o‘zgartirish
                document.getElementById('question_count_input').max = data.max_question_count;
                document.getElementById('max_question_info').innerText = `Maksimal savollar soni: ${data.max_question_count}`;
            } else {
                document.getElementById('max_question_info').innerText = 'Fan uchun savollar topilmadi';
            }
        });
}

// HTMLda:
// <select id="subject_select" onchange="updateMaxQuestionCount(this.value)">...</select>
// <input id="question_count_input" type="number" min="1">
// <span id="max_question_info"></span>
