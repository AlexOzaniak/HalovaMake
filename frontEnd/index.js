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