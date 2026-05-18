/* ============================================================
   MyZenn — Frontend Logic
   ============================================================ */

const API_BASE = '';
const USER_ID = localStorage.getItem('myzenn_user_id') || 'user_' + Math.random().toString(36).substr(2, 9);
localStorage.setItem('myzenn_user_id', USER_ID);

// ---- State ----
let isTyping = false;
let breathingActive = false;
let breathingInterval = null;
let breathCycle = 0;
let breathStep = 0;
let breathSeconds = 0;

// ---- View Management ----
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const view = document.getElementById('view-' + viewName);
    const nav = document.getElementById('nav-' + viewName);
    if (view) view.classList.add('active');
    if (nav) nav.classList.add('active');
    if (viewName === 'mood') loadDashboard();
    if (viewName === 'journal') loadJournals();
    // Close mobile sidebar
    document.getElementById('sidebar').classList.remove('open');
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// ---- Chat ----
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || isTyping) return;

    addMessage('user', message);
    input.value = '';
    input.style.height = 'auto';
    isTyping = true;
    document.getElementById('send-btn').disabled = true;

    // Show typing indicator
    const typingId = addTypingIndicator();

    try {
        const res = await fetch(API_BASE + '/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, user_id: USER_ID })
        });
        const data = await res.json();
        removeTypingIndicator(typingId);

        if (data.response) {
            addMessage('assistant', data.response);
        }
        if (data.crisis && data.crisis.is_crisis) {
            document.getElementById('crisis-banner').classList.remove('hidden');
        }
        if (data.mood) {
            updateMoodRing(data.mood.mood_score);
        }
    } catch (err) {
        removeTypingIndicator(typingId);
        addMessage('assistant', "I'm having trouble connecting right now. Please try again in a moment. If you're in crisis, please call 988. 💙");
    }

    isTyping = false;
    document.getElementById('send-btn').disabled = false;
}

function addMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `message ${role} fade-in`;

    const avatar = role === 'user' ? '👤' : '🧘';
    const formatted = formatMessage(content);

    div.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content glass-card">${formatted}</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function formatMessage(text) {
    // Convert markdown-like formatting
    let html = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/^[-•] (.+)$/gm, '<li>$1</li>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/((<li>.*?<\/li>\s*)+)/g, '<ul>$1</ul>');

    // Convert paragraphs
    html = html.split('\n\n').map(p => {
        p = p.trim();
        if (!p) return '';
        if (p.startsWith('<ul>') || p.startsWith('<li>')) return p;
        return `<p>${p}</p>`;
    }).join('');

    // Single newlines within paragraphs
    html = html.replace(/([^>])\n([^<])/g, '$1<br>$2');

    return html || `<p>${text}</p>`;
}

function addTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    const id = 'typing-' + Date.now();
    div.id = id;
    div.className = 'message assistant fade-in';
    div.innerHTML = `
        <div class="message-avatar">🧘</div>
        <div class="message-content glass-card">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
    // Auto-resize textarea
    const input = e.target;
    setTimeout(() => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }, 0);
}

function clearChat() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
        <div class="message assistant fade-in">
            <div class="message-avatar">🧘</div>
            <div class="message-content glass-card">
                <p>Chat cleared. I'm still here whenever you need to talk. 💙</p>
                <p>How are you feeling right now?</p>
            </div>
        </div>
    `;
}

// ---- Mood Tracker ----
function updateMoodSlider() {
    const value = document.getElementById('mood-slider').value;
    document.getElementById('mood-slider-display').textContent = value;
}

function toggleChip(btn) {
    btn.classList.toggle('active');
}

async function logMood() {
    const score = parseInt(document.getElementById('mood-slider').value);
    const activeChips = document.querySelectorAll('#emotion-chips .chip.active');
    const emotions = Array.from(activeChips).map(c => c.textContent.trim());

    try {
        await fetch(API_BASE + '/api/mood', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID, score, emotions })
        });

        // Reset chips
        activeChips.forEach(c => c.classList.remove('active'));
        updateMoodRing(score);
        loadDashboard();

        // Show success feedback
        const btn = document.getElementById('log-mood-btn');
        btn.textContent = '✓ Logged!';
        btn.disabled = true;
        setTimeout(() => { btn.textContent = 'Log Mood'; btn.disabled = false; }, 2000);
    } catch (err) {
        console.error('Failed to log mood:', err);
    }
}

function updateMoodRing(score) {
    document.getElementById('mood-ring-value').textContent = score;
}

async function loadDashboard() {
    try {
        const res = await fetch(API_BASE + '/api/dashboard/' + USER_ID);
        const data = await res.json();

        // Update stats
        const stats = data.stats || {};
        document.getElementById('stat-avg-mood').textContent = (stats.avg_mood || 5).toFixed(1);
        document.getElementById('stat-streak').textContent = stats.current_streak || 0;
        document.getElementById('stat-entries').textContent = stats.total_moods || 0;
        document.getElementById('stat-sessions').textContent = stats.total_conversations || 0;

        // Update mood chart
        renderMoodChart(data.mood_history || []);

        // Update profile display
        if (data.profile && data.profile.name) {
            document.getElementById('profile-name-display').textContent = data.profile.name;
        }
    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function renderMoodChart(moods) {
    const chart = document.getElementById('mood-chart');
    if (!moods.length) {
        chart.innerHTML = '<div class="chart-placeholder"><span>📈</span><p>Start tracking to see your mood trends</p></div>';
        return;
    }

    const maxBars = 30;
    const recent = moods.slice(-maxBars);
    const colors = ['#FF4757', '#FF6B81', '#FFA502', '#FFEAA7', '#55E6C1', '#4ECDC4', '#6C63FF', '#A29BFE'];

    chart.innerHTML = recent.map(m => {
        const score = m.score || 5;
        const height = (score / 10) * 160 + 10;
        const colorIdx = Math.min(Math.floor(score / 1.3), colors.length - 1);
        return `<div class="mood-bar" style="height:${height}px;background:${colors[colorIdx]}" data-score="${score}/10" title="${score}/10"></div>`;
    }).join('');
}

// ---- Journal ----
async function saveJournal() {
    const input = document.getElementById('journal-input');
    const content = input.value.trim();
    if (!content) return;

    const btn = document.getElementById('save-journal-btn');
    btn.textContent = 'Saving...';
    btn.disabled = true;

    try {
        await fetch(API_BASE + '/api/journal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, user_id: USER_ID })
        });
        input.value = '';
        btn.textContent = '✓ Saved!';
        setTimeout(() => { btn.textContent = 'Save & Analyze'; btn.disabled = false; }, 2000);
        loadJournals();
    } catch (err) {
        btn.textContent = 'Save & Analyze';
        btn.disabled = false;
        console.error('Journal save error:', err);
    }
}

async function loadJournals() {
    try {
        const res = await fetch(API_BASE + '/api/journals/' + USER_ID);
        const data = await res.json();
        const container = document.getElementById('journal-entries');

        if (!data.journals || !data.journals.length) {
            container.innerHTML = '<div class="empty-state"><span>📓</span><p>No journal entries yet.</p></div>';
            return;
        }

        container.innerHTML = data.journals.reverse().map(j => {
            const date = new Date(j.timestamp).toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
            });
            const preview = j.content ? (j.content.length > 150 ? j.content.substring(0, 150) + '...' : j.content) : j.preview || '';
            const sentiment = j.sentiment || 'neutral';
            return `
                <div class="journal-entry-item">
                    <div class="journal-entry-date">${date}</div>
                    <div class="journal-entry-preview">${preview}</div>
                    <span class="journal-entry-mood">${sentiment} • ${j.mood_score || 5}/10</span>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Journals load error:', err);
    }
}

// ---- Breathing Exercise ----
const BREATH_STEPS = [
    { text: 'Breathe In', duration: 4, className: 'inhale' },
    { text: 'Hold', duration: 4, className: 'hold' },
    { text: 'Breathe Out', duration: 4, className: 'exhale' },
    { text: 'Hold', duration: 4, className: 'hold' }
];
const TOTAL_CYCLES = 4;

function toggleBreathing() {
    if (breathingActive) {
        stopBreathing();
    } else {
        startBreathing();
    }
}

function startBreathing() {
    breathingActive = true;
    breathCycle = 0;
    breathStep = 0;
    breathSeconds = BREATH_STEPS[0].duration;

    const btn = document.getElementById('breathe-start-btn');
    btn.textContent = '⏸ Pause';

    runBreathStep();
    breathingInterval = setInterval(() => {
        breathSeconds--;
        updateBreathUI();

        if (breathSeconds <= 0) {
            breathStep++;
            if (breathStep >= BREATH_STEPS.length) {
                breathStep = 0;
                breathCycle++;
                if (breathCycle >= TOTAL_CYCLES) {
                    stopBreathing();
                    document.getElementById('breathe-text').textContent = 'Complete! 🙏';
                    return;
                }
            }
            breathSeconds = BREATH_STEPS[breathStep].duration;
            runBreathStep();
        }
    }, 1000);
}

function runBreathStep() {
    const step = BREATH_STEPS[breathStep];
    const circle = document.getElementById('breathe-circle');
    circle.className = 'breathe-circle ' + step.className;
    document.getElementById('breathe-text').textContent = step.text;
    updateBreathUI();

    // Update progress bar
    const totalSeconds = BREATH_STEPS.reduce((a, s) => a + s.duration, 0) * TOTAL_CYCLES;
    const elapsed = breathCycle * 16 + breathStep * 4 + (4 - breathSeconds);
    const progress = elapsed / totalSeconds;
    const circumference = 2 * Math.PI * 90;
    document.getElementById('breathe-progress-bar').style.strokeDashoffset = circumference * (1 - progress);
}

function updateBreathUI() {
    const totalRemaining = (TOTAL_CYCLES - breathCycle - 1) * 16 + (BREATH_STEPS.length - breathStep - 1) * 4 + breathSeconds;
    const mins = Math.floor(totalRemaining / 60);
    const secs = totalRemaining % 60;
    document.getElementById('breathe-timer').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
}

function stopBreathing() {
    breathingActive = false;
    if (breathingInterval) clearInterval(breathingInterval);
    breathingInterval = null;

    const btn = document.getElementById('breathe-start-btn');
    btn.textContent = '▶ Start';

    const circle = document.getElementById('breathe-circle');
    circle.className = 'breathe-circle';
    document.getElementById('breathe-progress-bar').style.strokeDashoffset = 565;
}

// ---- Profile ----
async function saveProfile() {
    const name = document.getElementById('profile-name').value.trim();
    const activeGoals = document.querySelectorAll('.goal-chip.active');
    const goals = Array.from(activeGoals).map(c => c.textContent.trim());

    const btn = document.getElementById('save-profile-btn');
    btn.textContent = 'Saving...';
    btn.disabled = true;

    try {
        await fetch(API_BASE + '/api/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: USER_ID, name: name || undefined, goals: goals.length ? goals : undefined })
        });

        if (name) document.getElementById('profile-name-display').textContent = name;
        btn.textContent = '✓ Saved!';
        setTimeout(() => { btn.textContent = 'Save Profile'; btn.disabled = false; }, 2000);
    } catch (err) {
        btn.textContent = 'Save Profile';
        btn.disabled = false;
        console.error('Profile save error:', err);
    }
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    // Load saved profile name
    fetch(API_BASE + '/api/profile/' + USER_ID)
        .then(r => r.json())
        .then(d => {
            if (d.name && d.name !== 'Friend') {
                document.getElementById('profile-name-display').textContent = d.name;
                document.getElementById('profile-name').value = d.name;
            }
        })
        .catch(() => {});
});
