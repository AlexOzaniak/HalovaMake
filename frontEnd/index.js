// ==========================================
// 1. API SERVICE (Mock Backend pre Python)
// ==========================================
const ApiService = {
    async login(email, password) {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                if (email && password) {
                    resolve({ 
                        success: true, 
                        user: { name: email.split('@')[0], email: email, role: 'finder' } 
                    });
                } else {
                    reject("Zadajte email a heslo");
                }
            }, 600);
        });
    },

    async register(name, email, password, role) {
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({ success: true, message: "Účet bol úspešne vytvorený!" });
            }, 800);
        });
    }
};

// ==========================================
// 2. UI KONTROLÓRY A LOGIKA (Poslucháče udalostí)
// ==========================================

// --- PREPÍNANIE MEDZI LOGIN A REGISTER ---
document.getElementById('go-to-register').addEventListener('click', () => {
    document.getElementById('login-section').style.display = 'none';
    document.getElementById('register-section').style.display = 'block';
});

document.getElementById('go-to-login').addEventListener('click', () => {
    document.getElementById('register-section').style.display = 'none';
    document.getElementById('login-section').style.display = 'block';
});

// --- OBSLUHA LOGINU ---
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('login-btn');

    btn.innerText = "Overujem..."; 
    btn.disabled = true;

    try {
        const res = await ApiService.login(email, password);
        
        document.getElementById('auth-view').classList.remove('active');
        document.getElementById('app-view').classList.add('active');
        
        document.getElementById('welcome-name').innerText = res.user.name;
        document.getElementById('sidebar-user-role').innerText = res.user.role.toUpperCase();
        document.getElementById('dashboard-role-display').innerText = res.user.role.toUpperCase();
        
        showToast("Úspešne prihlásený!", "success");
    } catch (error) {
        showToast(error, "error");
    } finally {
        btn.innerText = "Prihlásiť sa"; 
        btn.disabled = false;
    }
});

// --- OBSLUHA REGISTRÁCIE ---
document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const role = document.getElementById('reg-role').value;
    const btn = document.getElementById('reg-btn');

    btn.innerText = "Vytváram účet..."; 
    btn.disabled = true;

    try {
        const res = await ApiService.register(name, email, password, role);
        
        showToast("Účet vytvorený! Môžeš sa prihlásiť.", "success");
        
        document.getElementById('login-email').value = email;
        
        // Prepneme späť na prihlásenie
        document.getElementById('register-section').style.display = 'none';
        document.getElementById('login-section').style.display = 'block';
    } catch (error) {
        showToast("Chyba pri registrácii", "error");
    } finally {
        btn.innerText = "Vytvoriť účet"; 
        btn.disabled = false;
    }
});

// --- OBSLUHA ODHLÁSENIA ---
document.getElementById('logout-btn').addEventListener('click', () => {
    document.getElementById('app-view').classList.remove('active');
    document.getElementById('auth-view').classList.add('active');
    
    document.getElementById('login-password').value = '';
    document.getElementById('reg-password').value = '';
    
    showToast("Odhlásenie prebehlo úspešne", "info");
});

// --- POMOCNÁ FUNKCIA (Toasty) ---
function showToast(msg, type) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span style="font-size:1.2rem">${type==='success'?'🟢':'🔵'}</span> <span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => { 
        toast.style.animation = 'slideIn 0.3s reverse forwards'; 
        setTimeout(()=>toast.remove(), 300); 
    }, 3000);
}

let ws;

function addItemToFeed(request, prepend = false) {
    const feed = document.getElementById('request-feed');
    if (!feed) return;

    const existing = document.querySelector(`[data-id="${request.id}"]`);
    const item = document.createElement('li');
    item.dataset.id = request.id;
    item.style.padding = '8px';
    item.style.borderBottom = '1px solid rgba(255,255,255,0.12)';
    item.innerHTML = `<strong>${request.nadpis || 'Bez názvu'}</strong> (${request.typ_pouzivatela || 'unknown'}) - <em>${request.kategoria || 'ine'}</em><br>${(request.popis || '').substring(0, 90)}...<br><small>${request.status || 'nova'}</small>`;

    if (existing) {
        existing.replaceWith(item);
        return;
    }

    if (prepend) {
        feed.prepend(item);
    } else {
        feed.appendChild(item);
    }
}

function setupRealtimeWS() {
    const statusEl = document.getElementById('realtime-status');
    if (!statusEl) return;

    // Automaticky detekuj URL
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let host = window.location.hostname;
    let port = window.location.port || (window.location.protocol === 'https:' ? 443 : 80);
    
    // Ak sme na localhost alebo 127.0.0.1, skús port 8000
    if (host === 'localhost' || host === '127.0.0.1') {
        port = 8000;
    }
    
    const wsUrl = `${protocol}://${host}:${port}/ws/ziadosti`;
    console.log('Connecting to WebSocket:', wsUrl);

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        statusEl.textContent = `WebSocket pripojený (${wsUrl})`;
        statusEl.style.color = '#8ef';
        showToast('WebSocket live backend pripravený', 'success');
    };

    ws.onmessage = (e) => {
        const payload = JSON.parse(e.data);

        if (payload.event === 'snapshot') {
            const feed = document.getElementById('request-feed');
            if (feed) feed.innerHTML = '';
            payload.requests.forEach((item) => addItemToFeed(item));
            return;
        }

        if (payload.event === 'new_request') {
            addItemToFeed(payload.request, true);
            showToast('Pridaná nová žiadosť (real-time)', 'success');
            return;
        }

        if (payload.event === 'status_updated') {
            addItemToFeed(payload.request);
            showToast('Aktualizovaný status dodaný real-time', 'info');
            return;
        }

        if (payload.event === 'deleted') {
            const item = document.querySelector(`[data-id="${payload.request_id}"]`);
            if (item) item.remove();
            showToast('Žiadosť bola zmazaná real-time', 'info');
            return;
        }
    };

    ws.onclose = () => {
        statusEl.textContent = 'WebSocket odpojený (pokúsim sa znova za 3s)';
        statusEl.style.color = '#f88';
        showToast('WebSocket spojenie prerušené', 'error');
        // Pokúsim sa znova za 3 sekundy
        setTimeout(setupRealtimeWS, 3000);
    };

    ws.onerror = (err) => {
        statusEl.textContent = 'WebSocket chyba - skontroluj backend URL';
        statusEl.style.color = '#f88';
        console.error('WebSocket error:', err);
    };
}

async function submitAIRequest(text) {
    try {
        // Dynamicky vzorci API URL
        let apiUrl = `${window.location.protocol}//${window.location.hostname}`;
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            apiUrl += ':8000';
        } else if (window.location.port) {
            apiUrl += `:${window.location.port}`;
        }
        apiUrl += '/ziadosti';

        console.log('Sending to API:', apiUrl);

        const res = await fetch(apiUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text})
        });
        if (!res.ok) throw new Error('Chyba pri odosielaní');

        const data = await res.json();
        const statusEl = document.getElementById('ai-request-status');
        const jsonEl = document.getElementById('ai-response-json');
        statusEl.textContent = `AI žiadosť vytvorená (ID: ${data.id}). Stav: ${data.status}.`; 
        if (jsonEl) {
            jsonEl.textContent = JSON.stringify(data, null, 2);
        }
        showToast('Žiadosť odoslaná na AI spracovanie', 'success');
        return data;
    } catch (e) {
        const statusEl = document.getElementById('ai-request-status');
        statusEl.textContent = 'Chyba pri odosielaní AI požiadavky: ' + e.message;
        showToast(e.message || 'Chyba', 'error');
        console.error('API Error:', e);
        return null;
    }
}

// spusti WS po prihlásení
const loginForm = document.getElementById('login-form');
if (loginForm) {
    loginForm.addEventListener('submit', setupRealtimeWS);
}

const aiRequestForm = document.getElementById('ai-request-form');
if (aiRequestForm) {
    aiRequestForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = document.getElementById('ai-request-input').value.trim();
        if (!text) {
            showToast('Napíš text žiadosti', 'error');
            return;
        }
        await submitAIRequest(text);
        document.getElementById('ai-request-input').value = '';
    });
}
