import Timer from './timer.js';

const tempoDisplay = document.querySelector('.tempo');
const tempoText = document.querySelector('.tempo-text');
const decreaseTempoBtn = document.querySelector('.decrease-tempo');
const increaseTempoBtn = document.querySelector('.increase-tempo');
const tempoSlider = document.querySelector('.slider');
const tapTempoBtn = document.querySelector('.tap-tempo');
const startStopBtn = document.querySelector('.start-stop');
const subtractBeats = document.querySelector('.subtract-beats');
const addBeats = document.querySelector('.add-beats');
const measureCount = document.querySelector('.measure-count');

const click1 = new Audio('static/audio/Perc_MetronomeQuartz_hi2.mp3');
const click2 = new Audio('static/audio/Perc_MetronomeQuartz_lo2.mp3');

let bpm = 140;
let beatsPerMeasure = 4;
let count = 0;
let isRunning = false;
let tempoTextString = 'Medium';
let tapTimestamps = [];

decreaseTempoBtn.addEventListener('click', () => {
    if (bpm <= 20) { return };
    bpm--;
    validateTempo();
    updateMetronome();
});
increaseTempoBtn.addEventListener('click', () => {
    if (bpm >= 280) { return };
    bpm++;
    validateTempo();
    updateMetronome();
});
tempoSlider.addEventListener('input', () => {
    bpm = tempoSlider.value;
    validateTempo();
    updateMetronome();
});

subtractBeats.addEventListener('click', () => {
    if (beatsPerMeasure <= 2) { return };
    beatsPerMeasure--;
    measureCount.textContent = beatsPerMeasure;
    count = 0;
});
addBeats.addEventListener('click', () => {
    if (beatsPerMeasure >= 12) { return };
    beatsPerMeasure++;
    measureCount.textContent = beatsPerMeasure;
    count = 0;
});

tapTempoBtn.addEventListener('click', () => {
    const now = Date.now();

    // Clear taps if more than 2 seconds have passed since the last tap
    if (tapTimestamps.length && (now - tapTimestamps[tapTimestamps.length - 1]) > 2000) {
        tapTimestamps = [];
    }

    // Add current tap timestamp
    tapTimestamps.push(now);

    // Calculate BPM if there are at least 2 taps
    if (tapTimestamps.length >= 2) {
        const intervals = [];
        for (let i = 1; i < tapTimestamps.length; i++) {
            intervals.push(tapTimestamps[i] - tapTimestamps[i - 1]);
        }

        // Calculate average interval in milliseconds
        const averageInterval = intervals.reduce((a, b) => a + b) / intervals.length;
        // Convert interval to BPM (60,000 ms per min)
        bpm = Math.round(60000 / averageInterval);
        // Limit BPM to the slider's min and max range
        bpm = Math.max(20, Math.min(280, bpm));
        // Update metronome with new BPM
        updateMetronome();
    }
});

startStopBtn.addEventListener('click', () => {
    count = 0;
    if (!isRunning) {
        metronome.start();
        isRunning = true;
        startStopBtn.textContent = 'STOP';
    } else {
        metronome.stop();
        isRunning = false;
        startStopBtn.textContent = 'START';
    }
});

function updateMetronome() {
    tempoDisplay.textContent = bpm;
    tempoSlider.value = bpm;
    metronome.timeInterval = 60000 / bpm;
    
    if (bpm <= 40) { tempoTextString = "Grave (Very Slow)" };
    if (bpm > 40 && bpm <= 60) { tempoTextString = "Largo (Broad and Slow)" };
    if (bpm > 60 && bpm <= 76) { tempoTextString = "Adagio (Slow and Expressive)" };
    if (bpm > 76 && bpm <= 108) { tempoTextString = "Andante (Walking Speed)" };
    if (bpm > 108 && bpm <= 120) { tempoTextString = "Moderato (Moderate Tempo)" };
    if (bpm > 120 && bpm <= 168) { tempoTextString = "Allegro (Fast and Lively)" };
    if (bpm > 168 && bpm <= 200) { tempoTextString = "Presto (Very Fast)" };
    if (bpm > 200 && bpm <= 280) { tempoTextString = "Prestissimo (Extremely Fast)" };

    tempoText.textContent = tempoTextString;
}

function validateTempo() {
    if (bpm <= 20) { return };
    if (bpm >= 280) { return };
}

function playClick() {
    console.log(count);
    if (count === beatsPerMeasure) {
        count = 0;
    }

    // Play sound
    if (count === 0) {
        click1.play();
        click1.currentTime = 0;
    } else {
        click2.play();
        click2.currentTime = 0;
    }

    // Flash effect on .container
    const container = document.querySelector('.container');
    container.classList.add('flash');
    setTimeout(() => {
        container.classList.remove('flash');
    }, 100); // Remove after 100ms

    count++;
}

const metronome = new Timer(playClick, 60000 / bpm, { immediate: true });

/* Volume slider */
const volumeSlider = document.getElementById('volume-slider');

// Set initial volume to 50%
volumeSlider.value = 0.5;
click1.volume = 0.5;
click2.volume = 0.5;

// Adjust volume based on slider
volumeSlider.addEventListener('input', () => {
    const volume = volumeSlider.value;
    click1.volume = volume;
    click2.volume = volume;
});
