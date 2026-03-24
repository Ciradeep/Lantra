/**
 * app.js — LANTRA Frontend Logic
 * Calls the FastAPI backend at localhost:8001/api/v1
 */

const API_BASE = "http://127.0.0.1:8001/api/v1";

// ── Language definitions (mirror config/languages.json) ───────────────────────
const LANGUAGES = [
  { code: "hi", name: "Hindi",     native: "हिन्दी",    script: "Devanagari" },
  { code: "ta", name: "Tamil",     native: "தமிழ்",     script: "Tamil"      },
  { code: "te", name: "Telugu",    native: "తెలుగు",    script: "Telugu"     },
  { code: "bn", name: "Bengali",   native: "বাংলা",     script: "Bengali"    },
  { code: "mr", name: "Marathi",   native: "मराठी",     script: "Devanagari" },
  { code: "gu", name: "Gujarati",  native: "ગુજરાતી",  script: "Gujarati"   },
  { code: "kn", name: "Kannada",   native: "ಕನ್ನಡ",    script: "Kannada"    },
  { code: "ml", name: "Malayalam", native: "മലയാളം",    script: "Malayalam"  },
  { code: "pa", name: "Punjabi",   native: "ਪੰਜਾਬੀ",   script: "Gurmukhi"   },
  { code: "or", name: "Odia",      native: "ଓଡ଼ିଆ",    script: "Odia"       },
];

// ── Quick examples ─────────────────────────────────────────────────────────────
const EXAMPLES = {
  thriller: {
    text: "A gripping detective thriller set in the rain-soaked streets of Mumbai, where a brilliant but troubled investigator chases a ghost from his past.",
    lang: "hi", genre: "thriller"
  },
  drama: {
    text: "A heartwarming family drama about three generations of a Tamil household navigating love, tradition, and modernity in present-day Chennai.",
    lang: "ta", genre: "drama"
  },
  hinglish: {
    text: "yeh series bahut amazing hai — ek action-packed thriller jo aapko seeti bajane par majboor kar dagi!",
    lang: "hi", genre: "action"
  },
  bengali: {
    text: "A young woman from rural Bengal discovers her extraordinary musical talent and fights against all odds to make it to the national stage.",
    lang: "bn", genre: "drama"
  },
};

// ── State ──────────────────────────────────────────────────────────────────────
let selectedLang = "hi";

// ── Init ───────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  buildLangGrid();
  buildLanguagesSection();
  wireExampleChips();
  wireCharCounter();
  checkAPIStatus();
  wireHapticsPlayer();
  wireSpeechToText();
});

// ── Language selector grid ─────────────────────────────────────────────────────
function buildLangGrid() {
  const grid = document.getElementById("lang-grid");
  grid.innerHTML = LANGUAGES.map(lang => `
    <button
      class="lang-btn ${lang.code === selectedLang ? "selected" : ""}"
      id="lang-${lang.code}"
      onclick="selectLang('${lang.code}')"
      title="${lang.name} (${lang.script})"
    >
      <span class="lang-native">${lang.native}</span>
      <span class="lang-name">${lang.name}</span>
    </button>
  `).join("");
}

function selectLang(code) {
  document.querySelectorAll(".lang-btn").forEach(btn => btn.classList.remove("selected"));
  document.getElementById(`lang-${code}`)?.classList.add("selected");
  selectedLang = code;
}

// ── Languages info section ─────────────────────────────────────────────────────
function buildLanguagesSection() {
  const grid = document.getElementById("languages-grid");
  grid.innerHTML = LANGUAGES.map(lang => `
    <div class="language-card" onclick="selectLang('${lang.code}'); scrollToLocalizer()">
      <span class="lang-card-native">${lang.native}</span>
      <div class="lang-card-name">${lang.name}</div>
      <div class="lang-card-script">${lang.script}</div>
    </div>
  `).join("");
}

function scrollToLocalizer() {
  document.getElementById("localizer")?.scrollIntoView({ behavior: "smooth" });
}

// ── Example chips ──────────────────────────────────────────────────────────────
function wireExampleChips() {
  document.querySelectorAll(".example-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const ex = EXAMPLES[chip.dataset.example];
      if (!ex) return;
      document.getElementById("input-text").value = ex.text;
      document.getElementById("genre-select").value = ex.genre;
      selectLang(ex.lang);
      updateCharCounter(ex.text.length);
    });
  });
}

// ── Char counter ───────────────────────────────────────────────────────────────
function wireCharCounter() {
  const ta = document.getElementById("input-text");
  ta.addEventListener("input", () => updateCharCounter(ta.value.length));
}
function updateCharCounter(count) {
  const el = document.getElementById("char-counter");
  if (el) {
    el.textContent = count;
    el.style.color = count > 1800 ? "var(--saffron)" : "";
  }
}

// ── API status check ───────────────────────────────────────────────────────────
async function checkAPIStatus() {
  const badge = document.getElementById("status-badge");
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const data = await res.json();
      badge.textContent = `⚡ API Online (${data.languages || 10} langs)`;
      badge.style.background = "rgba(0,201,167,0.15)";
      badge.style.borderColor = "";
      badge.style.color = "";
    } else {
      setOffline(badge);
    }
  } catch {
    setOffline(badge);
  }
}
function setOffline(badge) {
  badge.textContent = "⚠️ API Offline";
  badge.style.background = "rgba(255,111,47,0.15)";
  badge.style.borderColor = "rgba(255,111,47,0.35)";
  badge.style.color = "var(--saffron)";
}

// ── Input Mode ──────────────────────────────────────────────────────────────
let inputMode = "text";

function switchTab(mode) {
  inputMode = mode;
  if(mode === "text") {
    el("text-input-section").style.display = "block";
    el("video-input-section").style.display = "none";
    el("tab-text").style.background = "";
    el("tab-text").style.color = "";
    el("tab-video").style.background = "var(--card-bg)";
    el("tab-video").style.color = "var(--text-1)";
    document.querySelector(".examples-row").style.display = "flex";
  } else {
    el("text-input-section").style.display = "none";
    el("video-input-section").style.display = "block";
    el("tab-video").style.background = "";
    el("tab-video").style.color = "";
    el("tab-text").style.background = "var(--card-bg)";
    el("tab-text").style.color = "var(--text-1)";
    document.querySelector(".examples-row").style.display = "none";
  }
}

// ── MAIN: Localize ─────────────────────────────────────────────────────────────
async function doLocalize() {
  const genre = document.getElementById("genre-select").value;
  const audio = document.getElementById("audio-toggle").checked;

  if (inputMode === "text") {
    const text  = document.getElementById("input-text").value.trim();
    if (!text) { shakeInput(); return; }

    setLoadingState(true);
    animateLoadingSteps();

    try {
      const res = await fetch(`${API_BASE}/localize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text, target_lang: selectedLang, genre, generate_audio: audio,
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
      renderOutput(await res.json());
    } catch (err) {
      setLoadingState(false);
      showError(err.message || "Connection failed.");
    }

  } else {
    const file = document.getElementById("video-file-input").files[0];
    if (!file) { showError("Please attach a video file."); return; }
    
    setLoadingState(true);
    animateLoadingSteps();

    const fd = new FormData();
    fd.append("file", file);
    fd.append("source_lang", document.getElementById("video-source-lang").value);
    fd.append("target_lang", selectedLang);
    fd.append("genre", genre);
    fd.append("generate_audio", audio);

    try {
      const res = await fetch(`${API_BASE}/localize/video`, { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
      renderOutput(await res.json());
    } catch (err) {
      setLoadingState(false);
      showError(err.message || "Connection failed.");
    }
  }
}

// ── Render output ──────────────────────────────────────────────────────────────
function renderOutput(data) {
  hide("output-placeholder");
  hide("error-state");
  show("output-result");
  show("copy-btn");

  // Language tag
  const langInfo = LANGUAGES.find(l => l.code === data.target_lang) || {};
  el("output-lang-tag").innerHTML = `
    ${langInfo.native || ""} &nbsp;·&nbsp; ${data.target_lang_name}
    <span style="font-size:0.75rem; color: var(--text-3)">(${data.target_script || ""})</span>
  `;

  // Detection metadata
  const det = data.detection || {};
  if (data.transcribed_text) {
     el("meta-detection").innerHTML = `<span class="meta-tag" style="background:var(--saffron); color:#000; display:block; white-space:normal; line-height:1.4;"><strong>Transcribed Audio:</strong> ${data.transcribed_text}</span>`;
  } else {
     el("meta-detection").innerHTML = [
       `<span class="meta-tag">Detected: ${det.lang || "?"}</span>`,
       `<span class="meta-tag">Script: ${det.script || "?"}</span>`,
       data.is_hinglish_input ? `<span class="meta-tag" style="color:var(--saffron)">🔀 Hinglish Handled</span>` : "",
       det.confidence ? `<span class="meta-tag">Conf: ${(det.confidence * 100).toFixed(0)}%</span>` : "",
     ].filter(Boolean).join("");
  }

  // Translated text
  el("translated-text").textContent = data.localized_text || "";

  // Romanized
  if (data.romanized && data.romanized.trim()) {
    el("romanized-content").textContent = data.romanized;
    show("romanized-text");
  } else {
    hide("romanized-text");
  }

  // Engine badges
  el("engine-badge").innerHTML = [
    `<span class="engine-tag good">Translation: ${data.translation_engine || "?"}</span>`,
    data.audio_engine ? `<span class="engine-tag good">Audio: ${data.audio_engine}</span>` : "",
  ].join("");

  // Store haptic data globally to play it
  window.currentHaptics = data.haptics || null;
  
  // Haptics player
  if (data.haptics && data.haptics.length > 0) {
    show("haptics-player");
    const vis = el("haptics-visualizer");
    vis.innerHTML = "";
    data.haptics.forEach((h, i) => {
      const span = document.createElement("span");
      span.id = `haptic-word-${i}`;
      span.style.padding = "2px 6px";
      span.style.borderRadius = "4px";
      span.style.background = "rgba(255,255,255,0.05)";
      span.style.transition = "background 0.1s, transform 0.1s, color 0.1s";
      span.textContent = h.word;
      vis.appendChild(span);
    });
  } else {
    hide("haptics-player");
  }

  // Audio player
  if (data.audio_path) {
    const filename = data.audio_path.split(/[\\/]/).pop();
    // Audio served at /api/v1/audio/{filename}
    const audioURL = `${API_BASE}/audio/${filename}`;
    el("audio-element").src = audioURL;
    el("audio-download").href = audioURL;
    el("audio-download").download = filename;
    show("audio-player");
  } else {
    hide("audio-player");
  }

  // Cultural note
  if (data.cultural_note && data.cultural_note.trim()) {
    el("cultural-note-text").textContent = data.cultural_note;
    show("cultural-details");
  } else {
    hide("cultural-details");
  }
}

// ── Copy output ────────────────────────────────────────────────────────────────
async function copyOutput() {
  const text = el("translated-text").textContent;
  try {
    await navigator.clipboard.writeText(text);
    const btn = document.getElementById("copy-btn");
    btn.textContent = "✅ Copied!";
    setTimeout(() => btn.textContent = "📋 Copy", 2000);
  } catch { /* ignore */ }
}

// ── Haptics Player ─────────────────────────────────────────────────────────────
function wireHapticsPlayer() {
  const btn = document.getElementById("play-haptics-btn");
  if (!btn) return;
  btn.addEventListener("click", () => {
    if (!window.currentHaptics || window.currentHaptics.length === 0) return;
    playHapticsSequence(window.currentHaptics);
  });
}

function playHapticsSequence(hapticsData) {
  // 1. Build the full vibration pattern array to play immediately
  // (Calling vibrate inside setTimeout loses the user-interaction permission)
  let fullPattern = [];
  hapticsData.forEach(h => {
    fullPattern.push(...h.pattern);
    fullPattern.push(h.delay_after);
  });
  
  // Remove the trailing pause
  if (fullPattern.length > 0) {
    fullPattern.pop();
  }
  
  // Needs to be called immediately on click
  if (navigator.vibrate) {
    navigator.vibrate(0); // Cancel any running vibrations
    navigator.vibrate(fullPattern);
  }

  // Fallback / PC Simulation: Play a low frequency buzzing sound (Web Audio API)
  simulateVibrationWithAudio(hapticsData);

  // 2. Play the visual highlights synchronized with the pattern delays
  let currentTime = 0;
  
  hapticsData.forEach((h, i) => {
    setTimeout(() => {
      // Visual feedback
      const span = el(`haptic-word-${i}`);
      if (span) {
        span.style.background = "var(--saffron)";
        span.style.color = "#000";
        span.style.transform = "scale(1.15)";
        
        // Duration of current vibration pattern
        const duration = h.pattern.reduce((a, b) => a + b, 0);
        setTimeout(() => {
            span.style.background = "rgba(255,255,255,0.05)";
            span.style.color = "";
            span.style.transform = "scale(1)";
        }, duration || 100);
      }
    }, currentTime);
    
    const duration = h.pattern.reduce((a, b) => a + b, 0);
    currentTime += duration + h.delay_after;
  });
}

let audioCtx;
function simulateVibrationWithAudio(hapticsData) {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
    
    const now = audioCtx.currentTime;
    let timeOffset = 0;
    
    hapticsData.forEach(h => {
      for (let i = 0; i < h.pattern.length; i++) {
        const dur = h.pattern[i] / 1000;
        if (i % 2 === 0) { // Vibrate phase
          const oscillator = audioCtx.createOscillator();
          const gainNode = audioCtx.createGain();
          
          oscillator.type = 'sawtooth'; 
          oscillator.frequency.value = 60; // 60Hz rumble
          gainNode.gain.value = 0.5; // Half volume buzz
          
          // Gentle fade out to avoid audio clicks
          gainNode.gain.setTargetAtTime(0, now + timeOffset + dur - 0.01, 0.015);
          
          oscillator.connect(gainNode);
          gainNode.connect(audioCtx.destination);
          
          oscillator.start(now + timeOffset);
          oscillator.stop(now + timeOffset + dur);
        }
        timeOffset += dur;
      }
      timeOffset += (h.delay_after / 1000);
    });
  } catch (e) {
    console.log("Audio Simulator skipped.");
  }
}

// ── UI helpers ─────────────────────────────────────────────────────────────────
function setLoadingState(loading) {
  const btn = document.getElementById("localize-btn");
  btn.disabled = loading;
  if (loading) {
    if (_stepTimer) { clearTimeout(_stepTimer); _stepTimer = null; }
    hide("output-placeholder");
    hide("output-result");
    hide("error-state");
    hide("copy-btn");
    show("loading-state");
  } else {
    if (_stepTimer) { clearTimeout(_stepTimer); _stepTimer = null; }
    hide("loading-state");
  }
}

const STEPS = ["step-detect", "step-translate", "step-culture", "step-audio"];
let _stepTimer = null;
function animateLoadingSteps() {
  STEPS.forEach(id => el(id)?.classList.remove("active", "done"));
  let i = 0;
  function next() {
    if (i > 0) el(STEPS[i - 1])?.classList.replace("active", "done");
    if (i < STEPS.length) {
      el(STEPS[i])?.classList.add("active");
      i++;
      _stepTimer = setTimeout(next, 1200);
    }
  }
  next();
}

function showError(message) {
  hide("output-placeholder");
  hide("output-result");
  show("error-state");
  hide("copy-btn");
  el("error-message").textContent = message;
}

function shakeInput() {
  const ta = document.getElementById("input-text");
  ta.style.borderColor = "var(--saffron)";
  ta.style.animation = "none";
  requestAnimationFrame(() => {
    ta.style.animation = "shake 0.45s ease";
  });
  setTimeout(() => { ta.style.borderColor = ""; ta.style.animation = ""; }, 600);
}

// Inject shake animation dynamically
const shakeStyle = document.createElement("style");
shakeStyle.textContent = `
  @keyframes shake {
    0%,100%{transform:translateX(0)}
    20%{transform:translateX(-8px)}
    40%{transform:translateX(8px)}
    60%{transform:translateX(-5px)}
    80%{transform:translateX(5px)}
  }
`;
document.head.appendChild(shakeStyle);

function el(id) { return document.getElementById(id); }

// show() aware of flex containers — avoids collapsing flex layouts
function show(id) {
  const e = el(id);
  if (!e) return;
  // Restore display based on element role
  const flexIds = new Set(["audio-player", "engine-badge", "meta-detection",
                            "output-result", "loading-state", "error-state"]);
  const inlineFlex = new Set(["copy-btn", "output-lang-tag"]);
  if (flexIds.has(id))       { e.style.display = "flex"; }
  else if (inlineFlex.has(id)) { e.style.display = "inline-flex"; }
  else                        { e.style.display = ""; }
}
function hide(id) { const e = el(id); if (e) e.style.display = "none"; }

// ── Text-to-Speech (Dictation) ────────────────────────────────────────────────
function wireSpeechToText() {
  const micBtn = document.getElementById("stt-mic-btn");
  const textArea = document.getElementById("input-text");
  if (!micBtn || !textArea) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micBtn.style.display = "none"; // Hide if browser doesn't support STT
    return;
  }

  const micStyle = document.createElement("style");
  micStyle.textContent = `
    @keyframes micPulse {
      0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 111, 47, 0.7); }
      70% { transform: scale(1.1); box-shadow: 0 0 0 10px rgba(255, 111, 47, 0); }
      100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 111, 47, 0); }
    }
  `;
  document.head.appendChild(micStyle);

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-IN"; // Default to English India

  let isRecording = false;

  recognition.onstart = () => {
    isRecording = true;
    micBtn.style.background = "var(--saffron)";
    micBtn.style.animation = "micPulse 1.5s infinite";
    textArea.placeholder = "Listening...";
  };

  recognition.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    const currentVal = textArea.value.trim();
    textArea.value = currentVal ? currentVal + " " + transcript : transcript;
    updateCharCounter(textArea.value.length);
  };

  recognition.onerror = (event) => {
    console.warn("Speech Recognition Error:", event.error);
    stopRecording();
  };

  recognition.onend = () => {
    stopRecording();
  };

  function stopRecording() {
    isRecording = false;
    micBtn.style.background = "var(--surface-color, rgba(0, 0, 0, 0.4))";
    micBtn.style.animation = "none";
    textArea.placeholder = "Enter English (or Hinglish) series description here...\\n\\nExample: A gripping detective thriller set in the rain-soaked streets of Mumbai, where a brilliant investigator chases a ghost from his past.";
  }

  micBtn.addEventListener("click", () => {
    if (isRecording) {
      recognition.stop();
    } else {
      recognition.start();
    }
  });
}
