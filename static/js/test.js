let questions = [];
let currentQuestion = 0;
let timeLeft = 20 * 60; // 20 minutes in seconds
let timerInterval;
let testId = null;

// Initialize the test
async function initializeTest() {
    try {
        const response = await fetch('/api/generate-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                subject: window.subject,
                topic: window.topic
            })
        });
        
        const data = await response.json();
        console.log('API response:', data);
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        if (!data.questions || data.questions.length === 0) {
            alert('No questions generated. Please try again.');
            return;
        }
        questions = data.questions;
        testId = data.test_id;
        questions.forEach((q, i) => console.log('Rendering question:', i + 1, q));
        try {
            renderQuestions();
        } catch (e) {
            console.error('Error rendering questions:', e);
            alert('Error rendering questions. Please check the console for details.');
        }
        startTimer();
    } catch (error) {
        console.error('Error loading questions:', error);
        alert('Error loading questions. Please try again.');
    }
}

// Normalize options for robust rendering
function normalizeOptions(options) {
    if (!Array.isArray(options)) return [];
    let norm = [];
    for (let opt of options) {
        if (typeof opt === 'string') {
            norm.push(opt);
        } else if (typeof opt === 'object' && opt !== null) {
            if ('id' in opt && 'text' in opt) {
                norm.push(`${opt.id}) ${opt.text}`);
            } else if ('key' in opt && 'value' in opt) {
                norm.push(`${opt.key}) ${opt.value}`);
            } else if ('label' in opt && 'text' in opt) {
                norm.push(`${opt.label}) ${opt.text}`);
            } else if ('label' in opt && 'value' in opt) {
                norm.push(`${opt.label}) ${opt.value}`);
            } else {
                norm.push(Object.values(opt).join(' '));
            }
        } else {
            norm.push(String(opt));
        }
    }
    return norm;
}

// Render questions
function renderQuestions() {
    const container = document.getElementById('question-container');
    const nav = document.getElementById('question-nav');
    container.innerHTML = '';
    nav.innerHTML = '';
    questions.forEach((q, index) => {
        // Normalize options for robust rendering
        q.options = normalizeOptions(q.options);
        // Question container
        const questionDiv = document.createElement('div');
        questionDiv.className = `question-container ${index === 0 ? 'active' : ''}`;
        let html = `
            <h4 class="mb-4">Question ${index + 1}</h4>
            <p class="mb-4">${q.question_text}</p>
            <div class="options">
                ${q.options.map((opt, i) => `
                    <button class="option-btn" data-index="${i}" onclick="selectOption(${index}, ${i})">
                        ${opt}
                    </button>
                `).join('')}
            </div>
            <div class="mt-4 d-flex gap-2">
                <button class="btn btn-outline-primary me-2" onclick="getHint(${index})">
                    <i class="fas fa-lightbulb"></i> Hint
                </button>
                <button class="btn btn-outline-primary" onclick="getConceptClarity(${index})">
                    <i class="fas fa-graduation-cap"></i> Concept Clarity
                </button>
            </div>
        `;
        questionDiv.innerHTML = html;
        container.appendChild(questionDiv);
        // Navigation button
        const navBtn = document.createElement('button');
        navBtn.className = 'btn btn-outline-primary';
        navBtn.textContent = index + 1;
        navBtn.onclick = () => showQuestion(index);
        nav.appendChild(navBtn);
    });
    updateNavigationButtons();
}

// Show specific question
function showQuestion(index) {
    document.querySelectorAll('.question-container').forEach((q, i) => {
        q.classList.toggle('active', i === index);
    });
    
    document.querySelectorAll('#question-nav button').forEach((btn, i) => {
        btn.classList.toggle('btn-primary', i === index);
        btn.classList.toggle('btn-outline-primary', i !== index);
    });
    
    currentQuestion = index;
    updateNavigationButtons();
}

// Update navigation buttons
function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const submitBtn = document.getElementById('submit-btn');
    
    prevBtn.disabled = currentQuestion === 0;
    nextBtn.style.display = currentQuestion === questions.length - 1 ? 'none' : 'inline-block';
    submitBtn.style.display = currentQuestion === questions.length - 1 ? 'inline-block' : 'none';
}

// Select an option
function selectOption(questionIndex, optionIndex) {
    const question = questions[questionIndex];
    const optionBtns = document.querySelectorAll(`.question-container:nth-child(${questionIndex + 1}) .option-btn`);
    
    optionBtns.forEach(btn => btn.classList.remove('selected'));
    optionBtns[optionIndex].classList.add('selected');
    
    question.user_answer = String.fromCharCode(65 + optionIndex);
}

// Get hint
async function getHint(questionIndex) {
    const question = questions[questionIndex];
    const modal = new bootstrap.Modal(document.getElementById('hintModal'));
    const content = document.getElementById('hint-content');
    
    content.textContent = 'Loading hint...';
    modal.show();
    
    try {
        const response = await fetch('/api/get-hint', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question_id: question.id
            })
        });
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        content.innerHTML = data.hint;
    } catch (error) {
        console.error('Error getting hint:', error);
        content.textContent = 'Error loading hint. Please try again.';
    }
}

// Get solution
async function getSolution(questionIndex) {
    const question = questions[questionIndex];
    const modal = new bootstrap.Modal(document.getElementById('solutionModal'));
    const content = document.getElementById('solution-content');
    
    content.textContent = 'Loading solution...';
    modal.show();
    
    try {
        const response = await fetch('/api/get-solution', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question_id: question.id
            })
        });
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        content.innerHTML = data.solution;
    } catch (error) {
        console.error('Error getting solution:', error);
        content.textContent = 'Error loading solution. Please try again.';
    }
}

// Get concept clarity
async function getConceptClarity(questionIndex) {
    const question = questions[questionIndex];
    const modal = new bootstrap.Modal(document.getElementById('conceptModal'));
    const content = document.getElementById('concept-content');
    
    content.textContent = 'Loading concept explanation...';
    modal.show();
    
    try {
        const response = await fetch('/api/get-concept-clarity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question_id: question.id
            })
        });
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        // Render as bulleted list if array, else as plain text
        if (Array.isArray(data.concept)) {
            content.innerHTML = '<ul>' + data.concept.map(item => `<li>${item}</li>`).join('') + '</ul>';
        } else {
            content.innerHTML = data.concept;
        }
    } catch (error) {
        console.error('Error getting concept clarity:', error);
        content.textContent = 'Error loading concept explanation. Please try again.';
    }
}

// Start timer
function startTimer() {
    timerInterval = setInterval(() => {
        timeLeft--;
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        document.getElementById('timer').textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            submitTest();
        }
    }, 1000);
}

// Submit test
async function submitTest() {
    clearInterval(timerInterval);
    
    try {
        const response = await fetch('/api/submit-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                test_id: testId,
                time_taken: 20 * 60 - timeLeft, // Calculate and send time_taken
                answers: questions.map(q => ({
                    question_id: q.id,
                    answer: q.user_answer !== undefined ? q.user_answer : null
                }))
            })
        });
        
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        
        window.location.href = `/test-results/${testId}`;
    } catch (error) {
        console.error('Error submitting test:', error);
        alert('Error submitting test. Please try again.');
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    initializeTest();
    
    // Navigation buttons
    document.getElementById('prev-btn').addEventListener('click', () => {
        if (currentQuestion > 0) {
            showQuestion(currentQuestion - 1);
        }
    });
    
    document.getElementById('next-btn').addEventListener('click', () => {
        if (currentQuestion < questions.length - 1) {
            showQuestion(currentQuestion + 1);
        }
    });
    
    document.getElementById('submit-btn').addEventListener('click', () => {
        if (confirm('Are you sure you want to submit the test?')) {
            submitTest();
        }
    });
}); 