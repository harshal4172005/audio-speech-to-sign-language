// Speech recognition variables
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const transcription = document.getElementById('transcription');
const signVideo = document.getElementById('sign-video');
const languageSelect = document.getElementById('language-select');

let recognition;
let isListening = false;

// Initialize speech recognition if available
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
        
        // If we have a final result, send to backend
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
    // Fallback for browsers that don't support speech recognition
    startBtn.disabled = true;
    stopBtn.disabled = true;
    transcription.textContent = "Speech recognition not supported in this browser. Please upload an audio file instead.";
}

// Handle Start Listening Button
startBtn.addEventListener('click', () => {
    if (!isListening && recognition) {
        startListening();
    } else if (!recognition) {
        alert("Speech recognition is not supported in your browser. Please use the file upload option.");
    }
});

// Handle Stop Listening Button
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

// Handle File Upload
document.getElementById('audio-upload').addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        transcription.textContent = `Processing file: ${file.name}...`;
        
        // Create form data to send the file
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

// Process transcript and display sign language
async function processTranscript(text) {
    // Clear previous content
    signVideo.innerHTML = "";
    
    if (!text.trim()) {
        signVideo.innerHTML = "<p>No speech detected</p>";
        return;
    }
    
    const selectedLanguage = languageSelect.value;
    const words = text.trim().split(/\s+/);
    
    // Process each word or check for phrases
    const wordElements = [];
    
    // First check for full sentence matches
    const fullText = text.toUpperCase();
    const response = await fetch(`/get-sign-data?text=${encodeURIComponent(fullText)}&language=${selectedLanguage}`);
    const data = await response.json();
    
    if (data.found && data.isFullMatch) {
        // Found a full sentence match
        displaySignMedia(data.path, signVideo);
    } else {
        // Process word by word
        for (const word of words) {
            try {
                const response = await fetch(`/get-sign-data?text=${encodeURIComponent(word)}&language=${selectedLanguage}`);
                const data = await response.json();
                
                if (data.found) {
                    wordElements.push(createSignElement(data.path, word));
                } else {
                    // If word not found, display letter by letter
                    const letterElements = await displayWordByLetters(word, selectedLanguage);
                    wordElements.push(...letterElements);
                }
            } catch (error) {
                console.error(`Error fetching sign for "${word}":`, error);
                const errorElement = document.createElement('div');
                errorElement.textContent = `[Error displaying "${word}"]`;
                wordElements.push(errorElement);
            }
        }
        
        // Append all elements to the sign video container
        wordElements.forEach(element => signVideo.appendChild(element));
    }
}

// Display sign language media (image or gif)
function displaySignMedia(path, container) {
    container.innerHTML = '';
    
    const isGif = path.toLowerCase().endsWith('.gif');
    
    if (isGif) {
        const video = document.createElement('img');
        video.src = path;
        video.className = 'img-fluid rounded sign-image';
        video.alt = 'Sign language animation';
        container.appendChild(video);
    } else {
        const img = document.createElement('img');
        img.src = path;
        img.className = 'img-fluid rounded sign-image';
        img.alt = 'Sign language gesture';
        container.appendChild(img);
    }
}

// Create an element for a sign
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

// Display a word letter by letter when no sign exists
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
                    const fallbackElement = document.createElement('div');
                    fallbackElement.className = 'sign-letter-fallback d-inline-block m-1';
                    fallbackElement.textContent = letter;
                    letterElements.push(fallbackElement);
                }
            } catch (error) {
                console.error(`Error fetching sign for letter "${letter}":`, error);
                const errorElement = document.createElement('div');
                errorElement.className = 'sign-letter-error d-inline-block m-1';
                errorElement.textContent = letter;
                letterElements.push(errorElement);
            }
        } else {
            // For non-alphabet characters, just display them directly
            const charElement = document.createElement('div');
            charElement.className = 'sign-char d-inline-block m-1 px-2';
            charElement.textContent = letter;
            letterElements.push(charElement);
        }
    }
    
    return letterElements;
}

// Feedback Submission
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
            body: JSON.stringify({
                feedback: feedbackText
            })
        });
        
        const data = await response.json();
        if (data.success) {
            alert('Feedback submitted successfully!');
            document.getElementById('feedback').value = ''; // Clear feedback field
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
    // Initially hide stop button
    stopBtn.classList.add('d-none');
});
