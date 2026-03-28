// ==========================================
// 1. API SERVICE (Mock Backend pre Python)
// ==========================================
const ApiService = {
    async login(email, password) {
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                if (email && password) {
                    let role = email.includes('seeker') ? 'seeker' : 'finder';
                    resolve({ success: true, user: { name: email.split('@')[0], email: email, role: role } });
                } else {
                    reject("Zadajte email a heslo");
                }
            }, 600);
        });
    },

    async register(name, email, password, role) {
        return new Promise((resolve) => {
            setTimeout(() => { resolve({ success: true }); }, 800);
        });
    },

    // NOVÉ: Finder odosiela správu (zajtra tu bude fetch na Python)
    async sendMessage(content) {
        return new Promise((resolve) => {
            setTimeout(() => { 
                resolve({ success: true, message: "Správa odoslaná na AI analýzu" }); 
            }, 800);
        });
    },

    // NOVÉ: Seeker sťahuje správy už ohodnotené AI agentom z SQL
    async getMessages() {
        return new Promise((resolve) => {
            setTimeout(() => {
                // Toto presne simuluje to, čo ti zajtra vráti Python z SQL databázy
                resolve([
                    { 
                        id: 1, 
                        sender: "Finder_Tech_01", 
                        content: "Máme riešenie pre váš problém s dátami...", 
                        isImportant: true, // Určil AI Agent
                        aiCategory: "B2B Softvér",
                        time: "Dnes 14:30"
                    },
                    { 
                        id: 2, 
                        sender: "Startup_Slovakia", 
                        content: "Zasielame náš pitch deck na ukážku.", 
                        isImportant: false, // Určil AI Agent
                        aiCategory: "Všeobecné",
                        time: "Včera 09:15"
                    }
                ]);
            }, 600);
        });
    }
};



// ==========================================
// 2. STATE (Pamäť aplikácie)
// ==========================================
let AppState = { user: null };

// ==========================================
// 3. UI KONTROLÓRY A LOGIKA
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

    btn.innerText = "Overujem..."; btn.disabled = true;

    try {
        const res = await ApiService.login(email, password);
        AppState.user = res.user; // Uložíme si usera do pamäte
        
        document.getElementById('auth-view').classList.remove('active');
        document.getElementById('app-view').classList.add('active');
        
        setupDashboard(AppState.user);
        showToast("Úspešne prihlásený!", "success");
    } catch (error) {
        showToast(error, "error");
    } finally {
        btn.innerText = "Prihlásiť sa"; btn.disabled = false;
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

    btn.innerText = "Vytváram účet..."; btn.disabled = true;

    try {
        await ApiService.register(name, email, password, role);
        showToast("Účet vytvorený! Môžeš sa prihlásiť.", "success");
        
        // Zadáme email do loginu, aby si nemusel písať znova
        document.getElementById('login-email').value = email;
        
        document.getElementById('register-section').style.display = 'none';
        document.getElementById('login-section').style.display = 'block';
    } catch (error) {
        showToast("Chyba pri registrácii", "error");
    } finally {
        btn.innerText = "Vytvoriť účet"; btn.disabled = false;
    }
});

// --- NASTAVENIE DASHBOARDU PO PRIHLÁSENÍ ---
function setupDashboard(user) {
    // Globálne údaje
    document.getElementById('welcome-name').innerText = user.name;
    document.getElementById('sidebar-user-role').innerText = user.role.toUpperCase();
    
    // Predvyplnenie Nastavení
    document.getElementById('set-name').value = user.name;
    document.getElementById('set-role').value = user.role.toUpperCase();

    // Zobrazenie správneho dashboardu podľa roly
    if (user.role === 'finder') {
        document.getElementById('dashboard-finder').style.display = 'block';
        document.getElementById('dashboard-seeker').style.display = 'none';
    } else {
        document.getElementById('dashboard-finder').style.display = 'none';
        document.getElementById('dashboard-seeker').style.display = 'block';
    }

    navigate('dashboard'); // Defaultne otvoríme dashboard
}

// --- NAVIGÁCIA (Prepínanie v Menu) ---
function navigate(viewName) {
    // 1. Zvýraznenie menu
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.getElementById(`nav-${viewName}`).classList.add('active');

    // 2. Skrytie všetkých sekcií
    document.querySelectorAll('.app-view-section').forEach(el => {
        el.classList.remove('active');
        el.style.display = 'none';
    });

    // 3. Zobrazenie vybranej sekcie
    const activeView = document.getElementById(`view-${viewName}`);
    activeView.style.display = 'block';
    setTimeout(() => activeView.classList.add('active'), 10); // kvôli plynulej CSS animácii

    // 4. Ak sme otvorili Správy, natiahneme fiktívne dáta
    if (viewName === 'messages') {
        loadMessages();
    }
}

// Priradenie eventov na menu
document.getElementById('nav-dashboard').addEventListener('click', () => navigate('dashboard'));
document.getElementById('nav-messages').addEventListener('click', () => navigate('messages'));
document.getElementById('nav-settings').addEventListener('click', () => navigate('settings'));

// --- UKLADANIE NASTAVENÍ ---
document.getElementById('save-settings-btn').addEventListener('click', () => {
    const newName = document.getElementById('set-name').value;
    
    // Aktualizácia v pamäti a na obrazovke
    AppState.user.name = newName;
    document.getElementById('welcome-name').innerText = newName;
    
    showToast("Nastavenia boli úspešne uložené", "success");
});

// --- MOCK SPRÁVY (Generovanie pre ukážku) ---
// --- DYNAMICKÉ NAČÍTANIE SPRÁV (Prepojené na AI Backend) ---
async function loadMessages() {
    const list = document.getElementById('messages-list');
    list.innerHTML = '<div style="color: var(--text-dim); font-size: 0.9rem;">Načítavam a analyzujem správy...</div>';
    
    try {
        // Opýtame sa API na správy
        const messages = await ApiService.getMessages();
        
        // Vyčistíme a vykreslíme
        list.innerHTML = '';
        
        messages.forEach(msg => {
            // Ak AI agent určil, že je správa dôležitá, dáme jej výraznejší štýl
            const isImportantTag = msg.isImportant ? `<span style="color:var(--orange); font-size:0.7rem; border:1px solid var(--orange); padding:2px 6px; border-radius:10px; margin-left:8px;">Dôležité</span>` : '';
            const opacityStyle = msg.isImportant ? 'opacity: 1;' : 'opacity: 0.7;'; // Ethical AI tlmenie
            
            list.innerHTML += `
                <div style="padding: 16px; border: 1px solid var(--border-light); border-radius: 8px; background: rgba(0,0,0,0.2); cursor: pointer; ${opacityStyle} transition: 0.2s;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='${msg.isImportant ? '1' : '0.7'}'">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                        <div style="font-weight: 600; font-size: 0.95rem;">${msg.sender} ${isImportantTag}</div>
                        <div style="font-size: 0.75rem; color: var(--text-dim);">${msg.time}</div>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--accent-blue); margin-bottom: 6px;">Kategória AI: ${msg.aiCategory}</div>
                    <div style="font-size: 0.85rem; color: var(--text-dim);">${msg.content}</div>
                </div>
            `;
        });
        
    } catch (error) {
        list.innerHTML = '<div style="color: var(--red); font-size: 0.9rem;">Chyba pri načítaní správ z databázy.</div>';
    }
}

// --- OBSLUHA ODHLÁSENIA ---
document.getElementById('logout-btn').addEventListener('click', () => {
    AppState.user = null;
    document.getElementById('app-view').classList.remove('active');
    document.getElementById('auth-view').classList.add('active');
    
    document.getElementById('login-password').value = '';
    document.getElementById('reg-password').value = '';
    
    showToast("Odhlásenie prebehlo úspešne", "info");
});

// --- LIVE AI MATCHMAKING ---
async function queryLiveAiMatches() {
    const query = document.getElementById('ai-query').value.trim();
    const results = document.getElementById('ai-results');
    if (!query) {
        showToast('Zadaj dopyt pre AI', 'error');
        return;
    }

    results.textContent = 'Posielam požiadavku na backend...';

    try {
        const backendUrl = 'http://127.0.0.1:8000/ai-matches?query=' + encodeURIComponent(query);
        const res = await fetch(backendUrl, { method: 'POST' });
        if (!res.ok) {
            // 404 / 503 / 500 handling
            const txt = await res.text();
            throw new Error(`HTTP ${res.status} ${txt}`);
        }
        const data = await res.json();
        // For compatibility with /ziadosti fallback
        if (data.ai_analyza) {
            results.textContent = JSON.stringify(data.ai_analyza, null, 2);
        } else {
            results.textContent = JSON.stringify(data, null, 2);
        }
        showToast('AI odpoveď prijatá', 'success');
    } catch (error) {
        results.textContent = 'Chyba: ' + error.message;
        showToast('Chyba pri volaní backendu', 'error');
    }
}

document.getElementById('ai-query-btn').addEventListener('click', queryLiveAiMatches);

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