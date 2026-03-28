 // ==========================================
        // 1. API SERVICE (Mock Backend pre Python)
        // ==========================================
        const ApiService = {
            async login(name, role) {
                return new Promise(resolve => setTimeout(() => resolve({ success: true, user: { name, role } }), 500));
            },

            // GET /api/investor/requests
            async getInvestorRequests() {
                return new Promise(resolve => setTimeout(() => {
                    resolve([
                        { id: "REQ-104", summary: "European B2B Fintech (Seed)", contact: "Slack", status: "Under Review" }
                    ]);
                }, 300));
            },

            // POST /api/ai/analyze-thesis
            // Toto je ten Python AI model, ktorý vyhodnocuje text
            async analyzeThesis(text) {
                return new Promise(resolve => {
                    setTimeout(() => {
                        // Veľmi jednoduchá mock logika
                        let cat = "General Tech"; let stage = "Early Stage";
                        if(text.toLowerCase().includes("saas")) cat = "B2B SaaS";
                        if(text.toLowerCase().includes("bio")) cat = "Biotech";
                        if(text.toLowerCase().includes("seed")) stage = "Seed Round";
                        if(text.toLowerCase().includes("series a")) stage = "Series A";

                        resolve({
                            success: true,
                            category: cat,
                            stage: stage,
                            summary: `Seeking ${stage} startup in ${cat} sector.`
                        });
                    }, 1200); // Simulácia dlhšieho "AI myslenia"
                });
            },

            // POST /api/investor/requests/new
            async createRequest(payload) {
                return new Promise(resolve => setTimeout(() => resolve({ success: true, id: "REQ-" + Math.floor(Math.random()*1000) }), 800));
            }
        };

        // ==========================================
        // 2. STATE MANAGEMENT
        // ==========================================
        let AppState = { user: null, activeDraft: {} };

        // ==========================================
        // 3. UI CONTROLLERS
        // ==========================================

        // --- AUTH & NAVIGÁCIA ---
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('login-name').value;
            const role = document.getElementById('login-role').value;
            const btn = document.getElementById('login-btn');

            btn.innerText = "Authenticating..."; btn.disabled = true;

            const res = await ApiService.login(name, role);
            AppState.user = res.user;
            
            document.getElementById('auth-view').style.display = 'none';
            document.getElementById('app-view').classList.add('active');
            
            // Nastavenie UI
            document.getElementById('sidebar-user-role').innerText = role.toUpperCase();
            document.getElementById('set-name').value = name;
            document.getElementById('set-role').value = role.toUpperCase();

            // Zapnutie Ethical Mode ak je zaškrtnutý
            if(document.getElementById('set-calm').checked) {
                document.getElementById('main-content-area').classList.add('calm-mode');
            }
            
            navigate('dashboard');
            showToast(`Welcome, ${name}`, "success");
            btn.innerText = "Sign In"; btn.disabled = false;
        });

        function handleLogout() {
            AppState.user = null;
            document.getElementById('app-view').classList.remove('active');
            document.getElementById('auth-view').style.display = 'flex';
            showToast("Logged out", "info");
        }

        function navigate(target) {
            // Prepínanie Sidebar aktívnych tried
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById(`nav-${target}`).classList.add('active');

            // Prepínanie View
            document.querySelectorAll('.dashboard-view').forEach(v => v.classList.remove('active'));
            
            if (target === 'settings') {
                document.getElementById('settings-view').classList.add('active');
            } else if (target === 'dashboard') {
                if (AppState.user.role === 'employee') {
                    document.getElementById('employee-dashboard').classList.add('active');
                } else {
                    document.getElementById('investor-dashboard').classList.add('active');
                    loadInvestorList();
                }
            }
        }

        // --- NASTAVENIA (SETTINGS) ---
        function saveSettings() {
            const btn = event.target;
            btn.innerText = "Saving...";
            
            setTimeout(() => {
                AppState.user.name = document.getElementById('set-name').value;
                const calmMode = document.getElementById('set-calm').checked;
                
                if(calmMode) {
                    document.getElementById('main-content-area').classList.add('calm-mode');
                } else {
                    document.getElementById('main-content-area').classList.remove('calm-mode');
                }
                
                btn.innerText = "Save Preferences";
                showToast("Preferences updated", "success");
            }, 500);
        }

        // --- INVESTOR WIZARD LOGIKA ---
        function invWizard(step) {
            document.querySelectorAll('.wizard-step').forEach(el => el.classList.remove('active'));
            document.getElementById(`inv-view-${step}`).classList.add('active');
        }

        async function loadInvestorList() {
            invWizard('list');
            const list = document.getElementById('investor-requests-list');
            const data = await ApiService.getInvestorRequests();
            
            list.innerHTML = data.map(req => `
                <div class="request-card">
                    <div>
                        <div style="font-weight: 600; margin-bottom: 4px;">${req.summary}</div>
                        <div style="font-size: 0.8rem; color: var(--text-dim);">ID: ${req.id} • Prefers: ${req.contact}</div>
                    </div>
                    <div><span class="status-badge orange">${req.status}</span></div>
                </div>
            `).join('');
        }

        // Krok 1 -> Krok 2 (Dotaz na AI)
        document.getElementById('inv-compose-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btn-analyze');
            const thesis = document.getElementById('inv-desc').value;
            const contact = document.getElementById('inv-contact').value;

            btn.innerHTML = "Processing via AI Model... <span style='animation: pulse 1s infinite'>⏳</span>"; 
            btn.disabled = true;

            // Uložíme dočasne
            AppState.activeDraft = { thesis, contact };

            // Voláme Python AI
            const analysis = await ApiService.analyzeThesis(thesis);

            if(analysis.success) {
                AppState.activeDraft.analysis = analysis;
                
                // Naplníme Kontrolnú obrazovku
                document.getElementById('ai-category').innerText = analysis.category;
                document.getElementById('ai-stage').innerText = analysis.stage;
                document.getElementById('ai-summary').innerText = analysis.summary;
                document.getElementById('ai-original-text').innerText = `"${thesis}"`;

                invWizard('confirm'); // Prepneme obrazovku
            }
            btn.innerText = "Analyze Request with AI →"; btn.disabled = false;
        });

        // Krok 2 -> Odoslanie do DB
        async function submitFinalRequest() {
            const btn = document.getElementById('btn-submit-final');
            btn.innerText = "Submitting..."; btn.disabled = true;

            const response = await ApiService.createRequest(AppState.activeDraft);

            if(response.success) {
                showToast("Request successfully sent to Ecosystem team.", "success");
                document.getElementById('inv-desc').value = ''; // Vyčistenie
                
                // Pridáme to vizuálne do listu pre ukážku
                const list = document.getElementById('investor-requests-list');
                list.innerHTML = `
                    <div class="request-card" style="border-left: 3px solid var(--green);">
                        <div>
                            <div style="font-weight: 600; margin-bottom: 4px;">${AppState.activeDraft.analysis.summary}</div>
                            <div style="font-size: 0.8rem; color: var(--text-dim);">ID: ${response.id} • Prefers: ${AppState.activeDraft.contact}</div>
                        </div>
                        <div><span class="status-badge green">New / Queued</span></div>
                    </div>
                ` + list.innerHTML;

                invWizard('list'); // Návrat na dashboard
            }
            btn.innerText = "Yes, Confirm & Submit"; btn.disabled = false;
        }

        // --- POMOCNÉ FUNKCIE ---
        function showToast(msg, type) {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.innerHTML = `<span style="font-size:1.2rem">${type==='success'?'🟢':'🔵'}</span> <span>${msg}</span>`;
            container.appendChild(toast);
            setTimeout(() => { toast.style.animation = 'slideIn 0.3s reverse forwards'; setTimeout(()=>toast.remove(),300); }, 3000);
        }