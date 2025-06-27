// Speech recognition variables
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const transcription = document.getElementById('transcription');
const signVideo = document.getElementById('sign-video');
const languageSelect = document.getElementById('language-select');

let recognition;
let isListening = false;

// Initialize speech recognition
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
            .map(result => result[0])
            .map(result => result.transcript)
            .join('');

        transcription.textContent = transcript;

        if (event.results[0].isFinal) {
            processTranscript(transcript);
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        transcription.textContent = `Error: ${event.error}`;
        stopListening();
    };
} else {
    startBtn.disabled = true;
    stopBtn.disabled = true;
    transcription.textContent = "Speech recognition not supported in this browser. Please upload an audio file instead.";
}

// Start listening
startBtn.addEventListener('click', () => {
    if (!isListening && recognition) {
        startListening();
    } else if (!recognition) {
        alert("Speech recognition is not supported in your browser. Please use the file upload option.");
    }
});

// Stop listening
stopBtn.addEventListener('click', () => {
    if (isListening) {
        stopListening();
    }
});

function startListening() {
    isListening = true;
    transcription.textContent = "Listening...";
    recognition.start();
    startBtn.classList.add('d-none');
    stopBtn.classList.remove('d-none');
}

function stopListening() {
    isListening = false;
    recognition.stop();
    transcription.textContent = "Listening stopped.";
    startBtn.classList.remove('d-none');
    stopBtn.classList.add('d-none');
}

// Handle file upload
document.getElementById('audio-upload').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        transcription.textContent = `Processing file: ${file.name}...`;

        const formData = new FormData();
        formData.append('audio', file);

        try {
            const response = await fetch('/upload-audio', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (data.text) {
                transcription.textContent = data.text;
                processTranscript(data.text);
            } else {
                transcription.textContent = data.error || "Error processing audio";
            }
        } catch (error) {
            console.error('Error uploading audio:', error);
            transcription.textContent = "Error uploading audio file";
        }
    }
});

// Process transcript
async function processTranscript(text) {
    signVideo.innerHTML = "";

    if (!text.trim()) {
        signVideo.innerHTML = "<p>No speech detected</p>";
        return;
    }

    const selectedLanguage = languageSelect.value;
    const fullText = text.replace(/[.,!?;:]/g, '').trim().toUpperCase();

    try {
        const fullResponse = await fetch(`/get-sign-data?text=${encodeURIComponent(fullText)}&language=${selectedLanguage}`);
        const fullData = await fullResponse.json();

        if (fullData.found) {
            displaySignMedia(fullData.path, signVideo);
            return;
        }
    } catch (error) {
        console.error("Error fetching full sentence sign:", error);
    }

    const words = text.trim().split(/\s+/);
    const wordElements = [];

    for (const word of words) {
        const cleanWord = word.replace(/[.,!?;:]/g, '').toUpperCase();

        try {
            const response = await fetch(`/get-sign-data?text=${encodeURIComponent(cleanWord)}&language=${selectedLanguage}`);
            const data = await response.json();

            if (data.found) {
                wordElements.push(createSignElement(data.path, cleanWord));
            } else {
                const letterElements = await displayWordByLetters(cleanWord, selectedLanguage);
                wordElements.push(...letterElements);
            }
        } catch (error) {
            console.error(`Error fetching sign for "${cleanWord}":`, error);
            const errorElement = document.createElement('div');
            errorElement.textContent = `[Error displaying "${cleanWord}"]`;
            wordElements.push(errorElement);
        }
    }

    wordElements.forEach(element => signVideo.appendChild(element));
}

// Display sign media
function displaySignMedia(path, container) {
    container.innerHTML = '';

    const isGif = path.toLowerCase().endsWith('.gif');
    const media = document.createElement('img');
    media.src = path;
    media.className = 'img-fluid rounded sign-image';
    media.alt = 'Sign language animation';

    container.appendChild(media);
}

// Create sign element
function createSignElement(path, word) {
    const container = document.createElement('div');
    container.className = 'sign-word-container d-inline-block m-2';

    const media = document.createElement('img');
    media.src = path;
    media.className = 'sign-image';
    media.alt = `Sign for "${word}"`;

    const label = document.createElement('div');
    label.className = 'sign-label mt-1';
    label.textContent = word;

    container.appendChild(media);
    container.appendChild(label);

    return container;
}

// Letter-by-letter fallback
async function displayWordByLetters(word, language) {
    const letterElements = [];
    const upperWord = word.toUpperCase();

    for (const letter of upperWord) {
        if (/[A-Z]/.test(letter)) {
            try {
                const response = await fetch(`/get-sign-data?text=${letter}&language=${language}`);
                const data = await response.json();

                if (data.found) {
                    letterElements.push(createSignElement(data.path, letter));
                } else {
                    const fallback = document.createElement('div');
                    fallback.className = 'sign-letter-fallback d-inline-block m-1';
                    fallback.textContent = letter;
                    letterElements.push(fallback);
                }
            } catch (error) {
                console.error(`Error fetching sign for letter "${letter}":`, error);
                const errorElement = document.createElement('div');
                errorElement.className = 'sign-letter-error d-inline-block m-1';
                errorElement.textContent = letter;
                letterElements.push(errorElement);
            }
        } else {
            const charElement = document.createElement('div');
            charElement.className = 'sign-char d-inline-block m-1 px-2';
            charElement.textContent = letter;
            letterElements.push(charElement);
        }
    }

    return letterElements;
}

// Feedback
document.getElementById('submit-feedback').addEventListener('click', async () => {
    const feedbackText = document.getElementById('feedback').value;
    if (!feedbackText.trim()) {
        alert('Please enter feedback before submitting');
        return;
    }

    try {
        const response = await fetch('/submit-feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ feedback: feedbackText })
        });

        const data = await response.json();
        if (data.success) {
            alert('Feedback submitted successfully!');
            document.getElementById('feedback').value = '';
        } else {
            alert(`Error: ${data.error || 'Failed to submit feedback'}`);
        }
    } catch (error) {
        console.error('Error submitting feedback:', error);
        alert('Error submitting feedback. Please try again later.');
    }
});

// Initialize UI
document.addEventListener('DOMContentLoaded', () => {
    stopBtn.classList.add('d-none');
});
