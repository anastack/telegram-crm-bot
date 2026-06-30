let tg = window.Telegram.WebApp;
tg.expand();

// Настройка темы Telegram
document.documentElement.style.setProperty('--bg-color', tg.themeParams.bg_color || '#0f172a');
document.documentElement.style.setProperty('--text-color', tg.themeParams.text_color || '#f8fafc');

// Показ пользователя
const userInfo = document.getElementById('user-info');
if (tg.initDataUnsafe.user) {
    userInfo.innerText = `@${tg.initDataUnsafe.user.username || tg.initDataUnsafe.user.first_name}`;
}

// Навигация (Tabs)
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Убираем active у всех
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // Ставим active текущему
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
        
        // Если открыли вкладку, обновляем данные
        if (btn.dataset.tab === 'appointments') loadAppointments();
        if (btn.dataset.tab === 'clients') loadClients();
        if (btn.dataset.tab === 'dashboard') loadStats();
    });
});

// API вызовы
const API_BASE = '/api';

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        const data = await res.json();
        document.getElementById('stat-appointments').innerText = data.total_appointments;
        document.getElementById('stat-active').innerText = data.active_appointments;
        document.getElementById('stat-clients').innerText = data.total_clients;
    } catch (e) {
        console.error('Ошибка загрузки статистики:', e);
    }
}

async function loadAppointments() {
    const list = document.getElementById('appointments-list');
    list.innerHTML = 'Загрузка...';
    try {
        const res = await fetch(`${API_BASE}/appointments`);
        const data = await res.json();
        list.innerHTML = '';
        
        if (data.length === 0) {
            list.innerHTML = '<p>Записей нет.</p>';
            return;
        }

        data.forEach(app => {
            const el = document.createElement('div');
            el.className = 'card-item glass';
            const statusClass = app.status === 'active' ? 'status-active' : 'status-cancelled';
            const statusText = app.status === 'active' ? 'Активна' : 'Отменена';
            
            el.innerHTML = `
                <div class="status-badge ${statusClass}">${statusText}</div>
                <h4>${app.service}</h4>
                <p>👤 Клиент: ${app.client_name}</p>
                <p>👨‍💼 Мастер: ${app.provider}</p>
                <p>📅 ${app.date} в ${app.time}</p>
                ${app.status === 'active' ? `<button class="btn-danger" onclick="cancelApp(${app.id})">Отменить запись</button>` : ''}
            `;
            list.appendChild(el);
        });
    } catch (e) {
        console.error(e);
        list.innerHTML = 'Ошибка загрузки';
    }
}

async function loadClients() {
    const list = document.getElementById('clients-list');
    list.innerHTML = 'Загрузка...';
    try {
        const res = await fetch(`${API_BASE}/clients`);
        const data = await res.json();
        renderClients(data);
        
        // Поиск
        document.getElementById('client-search').addEventListener('input', (e) => {
            const q = e.target.value.toLowerCase();
            const filtered = data.filter(c => c.name.toLowerCase().includes(q));
            renderClients(filtered);
        });

    } catch (e) {
        console.error(e);
        list.innerHTML = 'Ошибка загрузки';
    }
}

function renderClients(data) {
    const list = document.getElementById('clients-list');
    list.innerHTML = '';
    if (data.length === 0) {
        list.innerHTML = '<p>Клиенты не найдены.</p>';
        return;
    }
    data.forEach(c => {
        const el = document.createElement('div');
        el.className = 'card-item glass';
        el.innerHTML = `
            <h4>${c.name}</h4>
            <p>ID: ${c.telegram_id}</p>
        `;
        list.appendChild(el);
    });
}

window.cancelApp = async function(id) {
    if(!confirm('Отменить эту запись?')) return;
    
    try {
        const res = await fetch(`${API_BASE}/appointments/${id}/cancel`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            tg.showAlert('Запись отменена');
            loadAppointments(); // Перезагружаем
            loadStats();
        }
    } catch (e) {
        tg.showAlert('Ошибка при отмене');
    }
}

// Загружаем статистику при старте
loadStats();
