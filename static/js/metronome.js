const tempoDisplay = document.querySelector('.tempo');
const tempoText = document.querySelector('.tempo-text');
const decreaseTempoBtn = document.querySelector('.decrease-tempo');
const increaseTempoBtn = document.querySelector('.increase-tempo');
const tempoSlider = document.querySelector('.slider');
const startStopBtn = document.querySelector('.start-stop');
const subtractBeats = document.querySelector('.subtract-beats');
const addBeats = document.querySelector('.add-beats');
const measureCount = document.querySelector('.measure-count');

let bpm = 140;
let beatsPerMeasure = 4;

decreaseTempoBtn.addEventListener('click', () => {
    if (bpm < 20) return;
    bpm --;
    tempoDisplay.textContent = bpm;
    tempoSlider.value = bpm;
});
increaseTempoBtn.addEventListener('click', () => {
    if (bpm > 280) return;
    bpm ++;
    tempoDisplay.textContent = bpm;
    tempoSlider.value = bpm;
});
tempoSlider.addEventListener('input', () => {
    bpm = tempoSlider.value;
    tempoDisplay.textContent = bpm;
    tempoSlider.value = bpm;

});

subtractBeats.addEventListener('click', () => {
    beatsPerMeasure--;
    measureCount.textContent = beatsPerMeasure;
});
addBeats.addEventListener('click', () => {
    beatsPerMeasure++;
    measureCount.textContent = beatsPerMeasure;
});