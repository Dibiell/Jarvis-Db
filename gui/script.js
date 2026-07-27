// Conexão Socket.IO (Reforçado para Port 5050 - Com Diagnóstico)
if (typeof io === 'undefined') {
    console.error('ERRO CRÍTICO: Biblioteca Socket.IO não foi carregada! Verifique a conexão ou o servidor local.');
    alert('ERRO DE MOTOR: A biblioteca de comunicação (Socket.IO) não carregou. Verifique se o Jarvis está rodando.');
}

// --- Conexão de Segurança (Native Bridge Fallback) ---
function checkNativeBridge() {
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.get_status().then(response => {
            if (response && response.status === 'CONECTADO') {
                if (connectionStatusEl.textContent === 'DESCONECTADO' || connectionStatusEl.textContent === 'TENTANDO CONEXÃO...') {
                    console.log('[BRIDGE] Conectado via API Nativa');
                    connectionStatusEl.textContent = 'CONECTADO (MODO SEGURO)';
                    connectionStatusEl.classList.add('connected');
                    connectionStatusEl.classList.remove('disconnected');
                    // Sincroniza estado inicial se necessário
                    orb.classList.add('connected');
                }
            }
        }).catch(err => console.debug('Bridge ainda não pronta...'));
    }
}

// Inicia monitoramento da ponte nativa (Failsafe)
setInterval(checkNativeBridge, 2000);

const socket = io('http://127.0.0.1:5050', {
    transports: ['websocket', 'polling'],
    reconnectionAttempts: 20,
    reconnectionDelay: 1000,
    timeout: 30000,
    forceNew: true
});

socket.on('connect', () => {
    console.log('[SOCKET] Conectado com sucesso');
    connectionStatusEl.textContent = 'CONECTADO';
    connectionStatusEl.classList.add('connected');
    connectionStatusEl.classList.remove('disconnected', 'unstable');
    orb.classList.add('connected');
});

socket.on('connect_error', (error) => {
    console.warn('Tentativa de conexão socket falhou:', error.message);
    if (connectionStatusEl.textContent !== 'CONECTADO (MODO SEGURO)') {
        connectionStatusEl.textContent = 'TENTANDO CONEXÃO...';
    }
});

const orb = document.getElementById('orb');
const orbContainer = document.getElementById('orb-container');
const transcriptEl = document.getElementById('transcript');
const responseEl = document.getElementById('response');
const systemTimeEl = document.getElementById('system-time');
const connectionStatusEl = document.getElementById('connection-status');
const fullscreenBtn = document.getElementById('fullscreen-toggle');
const restartBtn = document.getElementById('restart-btn');
const recalibrateBtn = document.getElementById('recalibrate-btn');
const minimizeBtn = document.getElementById('minimize-btn');
const closeBtn = document.getElementById('close-btn');

// Chat DOM Elements
const chatSidebarEl = document.getElementById('chat-sidebar');
const chatHeaderEl = document.getElementById('chat-header');
const chatMessagesEl = document.getElementById('chat-messages');
const chatInputEl = document.getElementById('chat-input');
const sendBtnEl = document.getElementById('send-btn');
const agentSelectorEl = document.getElementById('agent-selector');
const agentTabs = document.querySelectorAll('.agent-tab');
const agentDescEl = document.getElementById('agent-description');
const agentRowEl = document.querySelector('.agent-tabs-row'); // Definido globalmente para persistência

// --- Global State ---
let activeAgent = 'jarvis';
let isCollapsed = false;
let currentConnectionUrl = ''; // Armazena a URL para regenerar o QR Code

// --- State Persistence ---
const JARVIS_STATE_KEY = 'jarvis_ui_state';

function saveState() {
    // Sincroniza o chat atual com a memória antes de salvar
    if (activeAgent) {
        agentHistories[activeAgent] = chatMessagesEl.innerHTML;
    }

    const panels = {};
    document.querySelectorAll('.floating-panel').forEach(panel => {
        panels[panel.id] = {
            active: panel.classList.contains('active'),
            left: panel.style.left,
            top: panel.style.top,
            right: panel.style.right,
            bottom: panel.style.bottom,
            width: panel.style.width,
            height: panel.style.height,
            zIndex: panel.style.zIndex
        };
    });

    const state = {
        // activeAgent: activeAgent, // Removido para sempre iniciar com Jarvis
        isCollapsed: isCollapsed,
        terminal: {
            left: chatSidebarEl.style.left,
            top: chatSidebarEl.style.top,
            width: chatSidebarEl.style.width,
            height: chatSidebarEl.style.height,
            position: chatSidebarEl.style.position
        },
        panels: panels,
        agentHistories: agentHistories,
        tabsScrollLeft: agentRowEl ? agentRowEl.scrollLeft : 0 // Salva posição do scroll das abas
    };
    localStorage.setItem(JARVIS_STATE_KEY, JSON.stringify(state));
    console.log('Estado e Memória do J.A.R.V.I.S. salvos localmente.');

    // Sincronização com o Servidor (Persistência Real)
    if (socket && socket.connected) {
        socket.emit('save_ui_state', state);
    }
}

function loadState() {
    const saved = localStorage.getItem(JARVIS_STATE_KEY);
    if (!saved) return;

    try {
        const state = JSON.parse(saved);

        // Restore Agent Histories (MEMÓRIA)
        if (state.agentHistories) {
            Object.assign(agentHistories, state.agentHistories);
            console.log('Memória de conversas restaurada.');
        }

        // Restore Terminal State
        if (state.terminal) {
            if (state.terminal.position === 'absolute') {
                document.body.appendChild(chatSidebarEl);
                chatSidebarEl.style.position = 'absolute';
            }
            if (state.terminal.left) chatSidebarEl.style.left = state.terminal.left;
            if (state.terminal.top) chatSidebarEl.style.top = state.terminal.top;
            if (state.terminal.width) chatSidebarEl.style.width = state.terminal.width;
            if (state.terminal.height) chatSidebarEl.style.height = state.terminal.height;
        }

        if (state.isCollapsed) {
            isCollapsed = true;
            chatSidebarEl.classList.add('collapsed');
            const collapseBtn = document.getElementById('collapse-btn');
            if (collapseBtn) {
                collapseBtn.innerHTML = '▲';
                collapseBtn.title = 'Expandir Terminal';
            }
        }

        // Restore Panels
        if (state.panels) {
            Object.entries(state.panels).forEach(([id, pState]) => {
                const panel = document.getElementById(id);
                if (panel) {
                    // Se for um painel técnico e NÃO estivermos em modo RAIZ, não abre por padrão através da memória
                    const isTechnical = ['voice-monitor-floating', 'intelligence-panel', 'pc-health-floating', 'access-panel-floating'].includes(panel.id);
                    const currentProtocol = document.getElementById('current-protocol')?.textContent;
                    if (pState.active && (!isTechnical || currentProtocol === 'RAIZ')) {
                        panel.classList.add('active');
                    } else {
                        panel.classList.remove('active');
                    }
                    if (pState.left !== undefined) panel.style.left = pState.left;
                    if (pState.top !== undefined) panel.style.top = pState.top;
                    if (pState.right !== undefined) panel.style.right = pState.right;
                    if (pState.bottom !== undefined) panel.style.bottom = pState.bottom;
                    if (pState.width !== undefined) panel.style.width = pState.width;
                    if (pState.height !== undefined) panel.style.height = pState.height;
                    if (pState.zIndex !== undefined) panel.style.zIndex = pState.zIndex;
                }
            });
        }

        // Restore Agent (Removido restauração automática para sempre iniciar como 'jarvis')
        activeAgent = 'jarvis';
        const tab = document.querySelector(`.agent-tab[data-agent="jarvis"]`);
        if (tab) {
            tab.classList.add('active');
            document.body.dataset.theme = 'jarvis';
            agentDescEl.innerText = AGENT_DESCRIPTIONS['jarvis'];

            // Renderiza o histórico específico de Jarvis se existir
            if (agentHistories['jarvis'] && agentHistories['jarvis'].trim().length > 0) {
                chatMessagesEl.innerHTML = agentHistories['jarvis'];
                chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
            }
        }

        // Restaura o scroll das abas se o scrollIntoView não for suficiente ou desejado
        if (state.tabsScrollLeft !== undefined && agentRowEl) {
            agentRowEl.scrollLeft = state.tabsScrollLeft;
        }

        console.log('Ambiente J.A.R.V.I.S. totalmente restaurado.');
    } catch (e) {
        console.error('Erro ao carregar estado:', e);
    }
}

// Inicializados dinamicamente
const agentHistories = {};

const AGENT_DESCRIPTIONS = {
    jarvis: "O seu assistente central e inteligência primária.",
    zeta: "Especialista em Copywriting, persuasão e escrita criativa.",
    nano: "Designer Web focado em interfaces modernas e estética visual.",
    fire: "Arquiteto focado em criar e otimizar novos agentes e prompts.",
    cuzo: "Artista especialista em criar prompts detalhados para geração de imagens.",
    rimex: "Engenheiro de automação focado em n8n e fluxos de trabalho.",
    hugin: "Gerente de modelos: Visão Computacional, Tradução, Áudio e Sentimento.",
    econo: "Especialista em Economia Geral.",
    seneca: "Especialista em Filosofia Estoica para conselhos diários.",
    oscar: "Especialista em Filosofia Estoica, oferecendo conselhos para problemas do dia a dia."
    // INJECT_NEW_DESCRIPTIONS_HERE
};

// --- Draggable & Resizable Chat UI ---
let isDragging = false;
let isResizing = false;
let resizeType = null;
let startX, startY;
let initialLeft, initialTop;
let initialWidth, initialHeight;

function makeAbsolute() {
    if (chatSidebarEl.style.position !== 'absolute') {
        const rect = chatSidebarEl.getBoundingClientRect();
        document.body.appendChild(chatSidebarEl);
        chatSidebarEl.style.position = 'absolute';
        chatSidebarEl.style.left = rect.left + 'px';
        chatSidebarEl.style.top = rect.top + 'px';
        chatSidebarEl.style.width = rect.width + 'px';
        chatSidebarEl.style.height = rect.height + 'px';
        chatSidebarEl.style.bottom = 'auto';
        chatSidebarEl.style.right = 'auto';
        chatSidebarEl.style.margin = '0';
        chatSidebarEl.style.zIndex = '1000';
    }
}

chatHeaderEl.addEventListener('mousedown', (e) => {
    isDragging = true;
    makeAbsolute();
    const currentRect = chatSidebarEl.getBoundingClientRect();
    startX = e.clientX;
    startY = e.clientY;
    initialLeft = parseFloat(chatSidebarEl.style.left) || currentRect.left;
    initialTop = parseFloat(chatSidebarEl.style.top) || currentRect.top;
    chatSidebarEl.classList.add('dragging');
});

// Resize Handle Listeners
const resizeHandles = {
    right: document.getElementById('resize-right'),
    bottom: document.getElementById('resize-bottom'),
    corner: document.getElementById('resize-corner')
};

Object.entries(resizeHandles).forEach(([type, handle]) => {
    handle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        e.stopPropagation();
        isResizing = true;
        resizeType = type;
        makeAbsolute();
        const rect = chatSidebarEl.getBoundingClientRect();
        startX = e.clientX;
        startY = e.clientY;
        initialWidth = rect.width;
        initialHeight = rect.height;
        chatSidebarEl.classList.add('resizing');
    });
});

document.addEventListener('mousemove', (e) => {
    if (isDragging || isResizing) {
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        if (isDragging) {
            let left = initialLeft + dx;
            let top = initialTop + dy;

            // Boundary constraints to keep terminal within screen
            left = Math.max(0, Math.min(left, window.innerWidth - chatSidebarEl.offsetWidth));
            top = Math.max(0, Math.min(top, window.innerHeight - chatSidebarEl.offsetHeight));

            chatSidebarEl.style.left = left + 'px';
            chatSidebarEl.style.top = top + 'px';
        } else if (isResizing) {
            if (resizeType === 'right' || resizeType === 'corner') {
                chatSidebarEl.style.width = Math.max(200, initialWidth + dx) + 'px';
            }
            if (!isCollapsed && (resizeType === 'bottom' || resizeType === 'corner')) {
                chatSidebarEl.style.height = Math.max(100, initialHeight + dy) + 'px';
            }
        }
    }
});

document.addEventListener('mouseup', () => {
    if (isDragging || isResizing) {
        isDragging = false;
        isResizing = false;
        resizeType = null;
        chatSidebarEl.classList.remove('dragging');
        chatSidebarEl.classList.remove('resizing');
        saveState();
    }
});
// --------------------------------------

// Fullscreen Toggle (Native implementation)
if (fullscreenBtn) {
    fullscreenBtn.addEventListener('click', () => {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.toggle_fullscreen();
        }
    });
}

// Restart Button
restartBtn.addEventListener('click', () => {
    const confirmed = confirm('Reiniciar J.A.R.V.I.S.?\nO sistema será encerrado e relancado automaticamente.');
    if (confirmed && window.pywebview && window.pywebview.api) {
        window.pywebview.api.restart_jarvis();
    }
});

// Minimize Button
if (minimizeBtn) {
    minimizeBtn.addEventListener('click', () => {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.minimize_jarvis();
        }
    });
}

// Close Button
if (closeBtn) {
    closeBtn.addEventListener('click', () => {
        const confirmed = confirm('Deseja realmente desligar o sistema J.A.R.V.I.S.?');
        if (confirmed && window.pywebview && window.pywebview.api) {
            window.pywebview.api.close_jarvis();
        }
    });
}

// Modo ORB Toggle (Chamado pelo Python)
window.toggleOrbMode = function (enabled) {
    if (enabled) {
        document.body.classList.add('orb-mode');
        console.log("HUD: Transição para o Modo ORB Flutuante...");
    } else {
        document.body.classList.remove('orb-mode');
        console.log("HUD: Retornando ao Dashboard Full...");
    }
};

// Recalibrate HUD Button (Soft Reset)
recalibrateBtn.addEventListener('click', () => {
    recalibrateHUD();
});

function recalibrateHUD() {
    console.log("Recalibrando motores visuais do HUD...");

    // Efeito de flash visual
    document.body.classList.add('rebooting');

    // Para todas as animações do Anime.js
    if (window.anime) {
        anime.remove('.eq-bar');
        anime.remove('.hud-node');
        anime.remove('.hud-circuits rect');
        anime.remove('.hud-circuits line');
        anime.remove('#orb');
        if (window.activeAnimeTimeline) window.activeAnimeTimeline.pause();
    }

    // Reset de classes
    const currentClass = orb.className;
    orb.className = '';

    // Pequeno delay para forçar o browser a notar a mudança
    setTimeout(() => {
        orb.className = currentClass;
        document.body.classList.remove('rebooting');

        // Re-inicializa componentes dinâmicos
        const eqGroup = document.getElementById('hud-equalizer');
        if (eqGroup) eqGroup.innerHTML = '';
        initEqualizer();

        // Força resize para os gráficos
        window.dispatchEvent(new Event('resize'));

        console.log("HUD Recalibrado com sucesso.");
    }, 500);
}

// F11 Shortcut
window.addEventListener('keydown', (e) => {
    if (e.key === 'F11') {
        e.preventDefault();
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.toggle_fullscreen();
        }
    }
});

// Update Clock
function updateClock() {
    const now = new Date();
    systemTimeEl.textContent = now.toLocaleTimeString('pt-BR');
}
setInterval(updateClock, 1000);
updateClock();

// --- Agent Selection Logic (RE-ENGINEERED & MEMORY FIXED) ---
function initAgentTabs() {
    console.log("HUD: Inicializando sistema de abas...");
    const allTabs = document.querySelectorAll('.agent-tabs-row .agent-tab, .agent-tabs-row [data-agent]');

    allTabs.forEach(tab => {
        // Evita duplicar listeners se a função for chamada múltiplas vezes
        if (tab.getAttribute('data-has-listener')) return;
        tab.setAttribute('data-has-listener', 'true');

        tab.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const agentId = tab.dataset.agent;
            if (!agentId || agentId === activeAgent) return;

            // 1. Salva o histórico do agente que ESTAVA ativo ANTES de trocar
            const previousAgent = activeAgent;

            // 2. Limpa visual das abas e define a nova
            document.querySelectorAll('.agent-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // 3. Troca a variável global
            activeAgent = agentId;
            console.log(`HUD: Trocando de ${previousAgent} para ${activeAgent}`);

            // 4. Executa a troca de memória (agora passando o antigo para salvar)
            switchAgentHistory(activeAgent, previousAgent);

            // 5. Atualiza a descrição e o tema
            agentDescEl.innerText = AGENT_DESCRIPTIONS[activeAgent] || "Assistente especializado.";
            document.body.dataset.theme = activeAgent;

            // Sincroniza cores
            const computedBody = window.getComputedStyle(document.body);
            const accent = computedBody.getPropertyValue('--accent').trim() || '#bf00ff';
            document.documentElement.style.setProperty('--agent-accent', accent);
            document.documentElement.style.setProperty('--agent-accent-alpha', accent + '33');

            // Efeito de transição
            document.body.classList.add('transition-blur', 'theme-shifting');
            orb.style.transition = 'none';
            orb.style.filter = 'brightness(3)';

            setTimeout(() => {
                document.body.classList.remove('transition-blur', 'theme-shifting');
                orb.style.transition = 'all 0.5s ease-out';
                orb.style.filter = '';
            }, 400);

            // Sidebars (se houver)
            document.querySelectorAll('.sidebar').forEach(s => {
                if (s.id !== 'terminal-sidebar' && s.id !== `sidebar-${activeAgent}`) {
                    s.classList.remove('active');
                }
            });
            const agentSidebar = document.getElementById(`sidebar-${activeAgent}`);
            if (agentSidebar) agentSidebar.classList.add('active');

            saveState();

            // Scroll suave para a aba selecionada
            tab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        });
    });
}

// Inicializa no carregamento
initAgentTabs();

// Horizontal Scroll for Agent Selector
if (agentRowEl) {
    agentRowEl.addEventListener('wheel', (e) => {
        if (e.deltaY !== 0) {
            e.preventDefault();
            agentRowEl.scrollLeft += e.deltaY;
            saveState(); // Salva ao rolar
        }
    });

    // Salva o scroll também via arraste ou touch se houver
    agentRowEl.addEventListener('scroll', () => {
        // Usamos um pequeno atraso (debounce) se necessário, mas saveState é leve
        saveState();
    });
}

// --- Collapse / Expand Terminal ---
const collapseBtn = document.getElementById('collapse-btn');
collapseBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // Don't trigger drag
    isCollapsed = !isCollapsed;
    chatSidebarEl.classList.toggle('collapsed', isCollapsed);
    collapseBtn.innerHTML = isCollapsed ? '▲' : '▼';
    collapseBtn.title = isCollapsed ? 'Expandir Terminal' : 'Minimizar Terminal';
    saveState();
});

// Save current agent messages and render another agent's stored history
function switchAgentHistory(newAgent, previousAgent) {
    // 1. Salva o histórico do agente que estava ativo antes (se existir)
    if (previousAgent && previousAgent !== newAgent) {
        // Só salva se houver algo (evita salvar branco se o DOM sumiu por erro)
        if (chatMessagesEl.innerHTML.trim().length > 0) {
            agentHistories[previousAgent] = chatMessagesEl.innerHTML;
            console.log(`Memória do agente ${previousAgent} salva.`);
        }
    }

    // 2. Carrega ou inicia o histórico do novo agente
    if (agentHistories[newAgent] !== undefined && agentHistories[newAgent].trim().length > 0) {
        chatMessagesEl.innerHTML = agentHistories[newAgent];
        console.log(`Memória do agente ${newAgent} restaurada.`);
    } else {
        chatMessagesEl.innerHTML = '';
        const initMsg = (newAgent === 'jarvis')
            ? 'Sistemas Padrão: JARVIS Ativo.'
            : `Agente Especialista: ${newAgent.toUpperCase()} pronto.`;
        const div = document.createElement('div');
        div.classList.add('message', 'system-msg');
        div.textContent = initMsg;
        chatMessagesEl.appendChild(div);

        // Inicializa na memória também
        agentHistories[newAgent] = chatMessagesEl.innerHTML;
    }

    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

function appendMessage(text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', type);
    // Render text with line breaks
    // Safe text formatting for minimal markdown
    let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formattedText = formattedText.replace(/\n/g, '<br>');
    msgDiv.innerHTML = formattedText;

    chatMessagesEl.appendChild(msgDiv);
    // Scroll to bottom
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;

    // Salva o estado imediatamente para não perder mensagens em refresh
    saveState();
}

function sendTextCommand() {
    const text = chatInputEl.value.trim();
    if (!text) return;

    // Se houver um agente especializado ativo (que não seja o Jarvis padrão)
    // adicionamos o prefixo @agent para disparar a skill no backend
    const finalCommand = (activeAgent !== 'jarvis') ? `@${activeAgent} ${text}` : text;

    // UI Update
    appendMessage(text, 'user-msg');
    chatInputEl.value = '';

    // Send to Jarvis
    socket.emit('text_command', { text: finalCommand });

    // Force UI state to "thinking" immediately for feedback
    orb.className = 'orb-thinking';
    transcriptEl.textContent = 'Processando texto...';
}

sendBtnEl.addEventListener('click', sendTextCommand);

chatInputEl.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendTextCommand();
    }
});
// ------------------

// Socket IO Listeners
socket.on('connect', () => {
    console.log('Connected to Jarvis Engine');
    // Quando conecta ao socket, não mudamos o texto de internet imediatamente,
    // esperamos o evento 'connection_status' do Python.
    connectionStatusEl.classList.remove('disconnected');
    connectionStatusEl.classList.add('connected');
});

socket.on('disconnect', () => {
    console.log('Disconnected from Jarvis Engine');
    connectionStatusEl.textContent = 'MOTOR DESLIGADO';
    connectionStatusEl.classList.remove('connected');
    connectionStatusEl.classList.add('disconnected');
});

socket.on('connection_status', (data) => {
    console.log('Internet Status:', data.status);
    const status = data.status.toUpperCase();

    if (status === 'ONLINE') {
        connectionStatusEl.textContent = 'CONECTADO';
        connectionStatusEl.className = 'status-badge connected';
    } else if (status === 'UNSTABLE') {
        connectionStatusEl.textContent = 'INSTÁVEL';
        connectionStatusEl.className = 'status-badge unstable'; // Precisamos definir essa cor no CSS
    } else if (status === 'OFFLINE') {
        connectionStatusEl.textContent = 'OFFLINE';
        connectionStatusEl.className = 'status-badge disconnected';
    }
});

socket.on('state_change', (data) => {
    console.log('State change:', data.state, data.agent);

    // Troca de tema automática se o agente for enviado
    if (data.agent && data.agent !== activeAgent) {
        console.log(`HUD: Mudança de agente via backend para: ${data.agent}`);
        const previousAgent = activeAgent;
        activeAgent = data.agent;

        document.body.dataset.theme = activeAgent;
        agentDescEl.innerText = AGENT_DESCRIPTIONS[activeAgent] || "Assistente especializado.";

        // Atualiza tabs visuais
        document.querySelectorAll('.agent-tab').forEach(t => {
            if (t.dataset.agent === activeAgent) {
                t.classList.add('active');
                t.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            } else {
                t.classList.remove('active');
            }
        });

        // Sincroniza o histórico de chat
        switchAgentHistory(activeAgent, previousAgent);

        // Garante que o estado seja salvo
        saveState();
    }

    // Clear all orb classes first using classList
    orb.classList.remove('orb-listening', 'orb-thinking', 'orb-speaking', 'orb-reasoning', 'orb-idle');
    if (orbContainer) orbContainer.classList.remove('orb-listening', 'orb-thinking', 'orb-speaking', 'orb-reasoning', 'orb-idle');

    // ANIME.JS ANIMATION HANDLING
    // Clean up previous animations if active
    if (window.activeAnimeTimeline) {
        window.activeAnimeTimeline.pause();
    }
    if (window.anime) {
        anime.remove('.eq-bar');
        anime.remove('.hud-node');
        anime.remove('.hud-circuits rect');
        anime.remove('.hud-chromatic-accents circle');

        // Reset properties
        anime({ targets: '.eq-bar', height: 2, duration: 200, easing: 'easeOutQuad' });
        anime({ targets: '.hud-node', scale: 1, filter: 'drop-shadow(0 0 0px var(--accent))', duration: 200 });
    }

    switch (data.state) {
        case 'listening':
            orb.classList.add('orb-listening');
            transcriptEl.textContent = 'Ouvindo...';
            responseEl.textContent = '';

            // ANIME.JS: Equalizer Reactive Effect
            if (window.anime) {
                window.activeAnimeTimeline = anime({
                    targets: '.eq-bar',
                    height: function () { return anime.random(2, 45); }, // Made thicker/taller for visibility
                    easing: 'easeInOutQuad',
                    duration: 150,
                    direction: 'alternate',
                    loop: true,
                    delay: anime.stagger(20)
                });
            }
            break;
        case 'thinking':
            orb.classList.add('orb-thinking');
            transcriptEl.textContent = data.agent ? `Colaboração: ${data.agent.toUpperCase()}...` : 'Processando...';

            // ANIME.JS: Removida a animação frenética e de movimento. 
            // O Orb permanece estático com brilho (CSS) para uma aparência mais estável.
            if (window.anime) {
                anime.remove('#orb');
                anime.remove('.hud-node');
                anime.remove('.hud-circuits line');
                anime.remove('.hud-circuits rect');
            }
            break;
        case 'speaking':
            orb.classList.add('orb-speaking');

            // ANIME.JS: Gentle pulsing while speaking
            if (window.anime) {
                window.activeAnimeTimeline = anime({
                    targets: '.eq-bar',
                    height: function () { return anime.random(5, 20); },
                    easing: 'easeInOutSine',
                    duration: 300,
                    direction: 'alternate',
                    loop: true,
                    delay: anime.stagger(50)
                });
            }
            break;
        case 'reasoning':
            orb.classList.add('orb-reasoning');
            transcriptEl.textContent = 'RACIOCINANDO...';
            responseEl.textContent = '';

            // ANIME.JS: Very subtle constant movement for reasoning (bars only)
            if (window.anime) {
                window.activeAnimeTimeline = anime({
                    targets: '.eq-bar',
                    height: function () { return anime.random(1, 4); }, // Even more subtle
                    easing: 'linear',
                    duration: 1000,
                    direction: 'alternate',
                    loop: true,
                    delay: anime.stagger(100)
                });
            }
            break;
        case 'idle':
        default:
            orb.classList.add('orb-idle');
            transcriptEl.textContent = 'Aguardando comando...';
            break;
    }

    // Sincroniza classes no container para efeitos de iluminação externa (Phase 2)
    if (orbContainer && data.state) {
        orbContainer.classList.add(`orb-${data.state}`);
    }
});

socket.on('server_info', (data) => {
    console.log('[Socket] Server info received:', data);
    if (data.ip) {
        currentConnectionUrl = `http://${data.ip}:5000`;
        updateAccessQRCode(); // Atualiza o QR Code com o IP real da rede
    }
});

socket.on('transcript', (data) => {
    console.log('User transcript received:', data.text);
    transcriptEl.textContent = data.text;
    appendMessage(data.text, 'user-msg');
});

socket.on('restore_ui_state', (remoteState) => {
    console.log('[Socket] Recebendo layout persistente do servidor...');
    if (remoteState) {
        // Mescla o estado local com o do servidor (servidor tem precedência na sincronia)
        const localState = JSON.parse(localStorage.getItem(JARVIS_STATE_KEY)) || {};
        const mergedState = { ...localState, ...remoteState };

        // Salva localmente para manter consistência
        localStorage.setItem(JARVIS_STATE_KEY, JSON.stringify(mergedState));

        // Carrega o estado mesclado usando a função já existente
        loadState();
    }
});

socket.on('response', (data) => {
    console.log('Jarvis response received:', data.text);
    responseEl.textContent = data.text;

    // Routing: Se a resposta foi endereçada a um terminal privado (agente recém criado)
    if (data.target_terminal) {
        const pMsgsEl = document.getElementById(`msgs-${data.target_terminal}`);
        if (pMsgsEl) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', 'jarvis-msg');
            msgDiv.innerHTML = data.text.replace(/\n/g, '<br>');
            pMsgsEl.appendChild(msgDiv);
            pMsgsEl.scrollTop = pMsgsEl.scrollHeight;
            return; // Impede que vá para o terminal principal
        }
    }

    // Caso contrário, vai para o terminal original de comando
    appendMessage(data.text, 'jarvis-msg');
});

// Utility to open external browser
function openExternalUrl(url) {
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.open_external_browser(url);
    } else {
        socket.emit('open_external', { url: url });
    }
}

// PC Health Listener
socket.on('pc_health', (data) => {
    // Update Floating Panel if it exists
    const fCpuBar = document.getElementById('float-cpu-bar');
    const fRamBar = document.getElementById('float-ram-bar');
    const fCpuVal = document.getElementById('float-cpu-val');
    const fRamVal = document.getElementById('float-ram-val');

    if (fCpuBar) {
        fCpuBar.style.width = data.cpu + '%';
        fCpuBar.style.background = data.cpu > 80 ? '#ff3e3e' : 'var(--accent)';
    }
    if (fRamBar) {
        fRamBar.style.width = data.ram + '%';
        fRamBar.style.background = data.ram > 80 ? '#ff3e3e' : 'var(--accent)';
    }
    if (fCpuVal) fCpuVal.textContent = Math.round(data.cpu) + '%';
    if (fRamVal) fRamVal.textContent = Math.round(data.ram) + '%';
});

// Screen Mirror Listener (FDM-3 Perfect Vision)
socket.on('screen_frame', (data) => {
    const mirrorImg = document.getElementById('mirror-canvas');
    const mirrorStats = document.getElementById('mirror-stats');
    if (mirrorImg && data.image) {
        mirrorImg.src = 'data:image/jpeg;base64,' + data.image;
        if (mirrorStats) {
            const latency = Math.floor(Math.random() * 20) + 30;
            mirrorStats.textContent = `FPS: 2 | LATENCY: ${latency}ms`;
        }
    }
});


// Voice Rhythm Listener
socket.on('voice_rhythm', (data) => {
    const fAmpBar = document.getElementById('float-amplitude-bar');
    const fCadBar = document.getElementById('float-cadencia-bar');
    const fAmpVal = document.getElementById('float-amplitude-val');
    const fCadVal = document.getElementById('float-cadencia-val');

    if (fAmpBar) fAmpBar.style.width = data.amplitude + '%';
    if (fCadBar) fCadBar.style.width = data.cadencia + '%';
    if (fAmpVal) fAmpVal.textContent = Math.round(data.amplitude) + '%';
    if (fCadVal) fCadVal.textContent = Math.round(data.cadencia) + '%';

    // Update graph data
    voiceAmplitudeData.shift();
    voiceAmplitudeData.push(data.amplitude);
    voiceCadenceData.shift();
    voiceCadenceData.push(data.cadencia);
});

// --- Draggable Floating Panels ---
document.querySelectorAll('.floating-panel').forEach(panel => {
    const header = panel.querySelector('.panel-header');
    if (header) {
        header.style.cursor = 'grab';
        let floatDragging = false;
        let pStartX, pStartY, pInitialLeft, pInitialTop;

        header.addEventListener('mousedown', (e) => {
            if (e.target.classList.contains('close-panel')) return;

            floatDragging = true;
            header.style.cursor = 'grabbing';
            pStartX = e.clientX;
            pStartY = e.clientY;

            const rect = panel.getBoundingClientRect();
            const parent = panel.offsetParent || document.body;
            const parentRect = parent.getBoundingClientRect();

            pInitialLeft = rect.left - parentRect.left;
            pInitialTop = rect.top - parentRect.top;

            panel.classList.add('dragging');

            if (panel.style.right !== 'auto' || panel.style.bottom !== 'auto') {
                panel.style.bottom = 'auto';
                panel.style.right = 'auto';
                panel.style.left = pInitialLeft + 'px';
                panel.style.top = pInitialTop + 'px';
            }

            document.querySelectorAll('.floating-panel').forEach(p => p.style.zIndex = 200);
            panel.style.zIndex = 201;

            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (floatDragging) {
                const dx = e.clientX - pStartX;
                const dy = e.clientY - pStartY;

                let newLeft = pInitialLeft + dx;
                let newTop = pInitialTop + dy;

                const parent = panel.offsetParent || document.body;
                newLeft = Math.max(0, Math.min(newLeft, parent.clientWidth - panel.offsetWidth));
                // Limite vertical relaxado para permitir descer atÃ© o "PROTOCOLO: RAIZ"
                newTop = Math.max(0, Math.min(newTop, window.innerHeight - 40));

                panel.style.left = newLeft + 'px';
                panel.style.top = newTop + 'px';
            }
        });

        document.addEventListener('mouseup', () => {
            if (floatDragging) {
                floatDragging = false;
                header.style.cursor = 'grab';
                panel.classList.remove('dragging'); // Remove sombra ao soltar
                saveState();
            }
        });
    }
});

// Interactive Orb HUD Logic
document.addEventListener('DOMContentLoaded', () => {
    console.log("HUD: Inicializando gatilhos interativos...");
    const pcTrigger = document.getElementById('node-pc-trigger');
    const pcPanel = document.getElementById('pc-health-floating');
    const pcClose = document.getElementById('close-pc-panel');

    if (pcTrigger && pcPanel) {
        pcTrigger.addEventListener('click', () => {
            pcPanel.classList.toggle('active');
            console.log("HUD: PC Monitoring panel toggled");
            saveState();
        });
    }

    if (pcClose && pcPanel) {
        pcClose.addEventListener('click', () => {
            pcPanel.classList.remove('active');
            saveState();
        });
    }

    voicePanel = document.getElementById('voice-monitor-floating');
    const voiceClose = document.getElementById('close-voice-panel');
    if (voiceClose && voicePanel) {
        voiceClose.addEventListener('click', () => {
            voicePanel.classList.remove('active');
            saveState();
        });
    }

    // Interactive Mobile Remote HUD Logic
    const mobileTrigger = document.getElementById('node-mobile-trigger');
    const mobilePanel = document.getElementById('mobile-remote-floating');
    const mobileClose = document.getElementById('close-mobile-panel');

    if (mobileTrigger && mobilePanel) {
        mobileTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            mobilePanel.classList.toggle('active');
            console.log("HUD: Mobile Remote panel toggled");
            saveState();
        });
    }

    if (mobileClose && mobilePanel) {
        mobileClose.addEventListener('click', (e) => {
            e.stopPropagation();
            mobilePanel.classList.remove('active');
            saveState();
        });
    }

    // Interactive NotebookLM Brain Panel Logic
    const notebookTrigger = document.getElementById('node-notebook-trigger');
    const notebookPanel = document.getElementById('notebook-floating');
    const notebookClose = document.getElementById('close-notebook-panel');

    if (notebookTrigger && notebookPanel) {
        notebookTrigger.addEventListener('click', (e) => {
            e.stopPropagation();
            notebookPanel.classList.toggle('active');
            console.log("HUD: NotebookLM panel toggled");
            saveState();
        });
    }

    if (notebookClose && notebookPanel) {
        notebookClose.addEventListener('click', (e) => {
            e.stopPropagation();
            notebookPanel.classList.remove('active');
            saveState();
        });
    }

    // Interactive Google Web Panel Logic
    const googleTrigger = document.getElementById('node-google-trigger');
    const googlePanel = document.getElementById('google-floating');
    const googleClose = document.getElementById('close-google-panel');
    const googlePopoutBtn = document.getElementById('google-popout-btn');
    const escapeOverlay = document.getElementById('fullscreen-escape-overlay');

    if (googleTrigger && googlePanel) {
        googleTrigger.addEventListener('click', () => {
            googlePanel.classList.toggle('active');
            console.log("HUD: Google panel toggled");
            saveState();
        });
    }

    if (googleClose && googlePanel) {
        googleClose.addEventListener('click', () => {
            googlePanel.classList.remove('active');
            saveState();
        });
    }

    // Botão "Externo" — abre Google no navegador padrão
    if (googlePopoutBtn) {
        googlePopoutBtn.addEventListener('click', () => {
            openExternalUrl('https://www.google.com');
        });
    }

    // ================================================================
    // PROTEÇÃO CONTRA FULLSCREEN DO IFRAME (bug do login Google)
    // ================================================================

    // Função global de escape (usada pelo botão de emergência no HTML)
    window.__jarvisExitFullscreen = function () {
        try {
            if (document.fullscreenElement) document.exitFullscreen();
            if (document.webkitFullscreenElement) document.webkitExitFullscreen();
            if (document.mozFullScreenElement) document.mozCancelFullScreen();
            if (document.msFullscreenElement) document.msExitFullscreen();
        } catch (e) {
            console.warn('[Fullscreen] Erro ao sair:', e);
        }
        // Esconde o overlay de emergência
        if (escapeOverlay) escapeOverlay.style.display = 'none';
        // Garante que o painel do Google seja fechado também
        if (googlePanel) googlePanel.classList.remove('active');
        console.log('[Fullscreen] Saída do modo fullscreen forçada.');
    };

    // Listener que intercepta qualquer pedido de fullscreen
    const handleFullscreenChange = () => {
        const fsElement = document.fullscreenElement
            || document.webkitFullscreenElement
            || document.mozFullScreenElement
            || document.msFullscreenElement;

        if (fsElement) {
            // Verifica se o fullscreen foi pedido pelo iframe do Google
            const googleIframe = document.getElementById('google-webview');
            const isIframeFullscreen = googleIframe && (
                fsElement === googleIframe ||
                googleIframe.contains(fsElement) ||
                // Em alguns casos, o elemento fullscreen é o próprio <html> quando um iframe pede
                fsElement.tagName === 'HTML' || fsElement.tagName === 'BODY'
            );

            if (isIframeFullscreen || fsElement.tagName === 'HTML') {
                console.warn('[Fullscreen] Iframe tentou entrar em fullscreen! Mostrando botão de escape...');
                // Mostra o botão de emergência em vez de forçar saída imediata
                // (forçar saída imediata pode quebrar o login do Google)
                if (escapeOverlay) escapeOverlay.style.display = 'block';
            }
        } else {
            // Saiu do fullscreen — esconde o overlay
            if (escapeOverlay) escapeOverlay.style.display = 'none';
        }
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);
    // ESC como atalho adicional (funciona quando o foco está na página, não no iframe)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && (document.fullscreenElement || document.webkitFullscreenElement)) {
            e.preventDefault();
            window.__jarvisExitFullscreen();
        }
    });

    // Listener para ocultar/mostrar QR Code
    const toggleBtn = document.getElementById('toggle-qr-btn');
    const qrCanvas = document.getElementById('qrcode-canvas');
    if (toggleBtn && qrCanvas) {
        toggleBtn.addEventListener('click', () => {
            const isBlurred = qrCanvas.style.filter && qrCanvas.style.filter.includes('blur');
            qrCanvas.style.filter = isBlurred ? '' : 'blur(15px)';
            qrCanvas.style.opacity = isBlurred ? '1' : '0.4';

            const icon = document.getElementById('toggle-qr-icon');
            if (icon) {
                if (isBlurred) {
                    // Símbolo: Olho Aberto (SVG Path)
                    icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>';
                } else {
                    // Símbolo: Olho Cortado (SVG Path + Line)
                    icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>';
                }
            }
        });
    }

    // Interactive Mirror HUD Logic (FDM-3)
    const mirrorTrigger = document.getElementById('node-mirror-trigger');
    const mirrorPanel = document.getElementById('holographic-mirror-floating');
    const mirrorClose = document.getElementById('close-mirror-panel');

    if (mirrorTrigger && mirrorPanel) {
        mirrorTrigger.addEventListener('click', () => {
            mirrorPanel.classList.toggle('active');
            console.log("HUD: Holographic Mirror panel toggled");
            saveState();
        });
    }

    if (mirrorClose && mirrorPanel) {
        mirrorClose.addEventListener('click', () => {
            mirrorPanel.classList.remove('active');
            saveState();
        });
    }

}); // fim do DOMContentLoaded


// Server Info Listener (for getting Local IP to render QR Code)
socket.on('server_info', (data) => {
    console.log("Server Info recebida:", data);
    if (data.ip) {
        const ipDisplay = document.getElementById('mobile-ip-display');
        const connectionUrl = `http://${data.ip}:5000/mobile`;

        if (ipDisplay) {
            ipDisplay.textContent = connectionUrl;
        }
        currentConnectionUrl = connectionUrl;

        // Pega a cor do agente atual para o QR Code
        const computedBody = window.getComputedStyle(document.body);
        const accent = computedBody.getPropertyValue('--accent').trim() || '#00dcff';
        generateQRCode(connectionUrl, accent);
    }
});


// Função centralizada para gerar o QR Code
function generateQRCode(url, color) {
    const qrCanvas = document.getElementById('qrcode-canvas');
    if (qrCanvas && window.QRious) {
        new QRious({
            element: qrCanvas,
            value: url,
            size: 150,
            background: '#ffffff',
            foreground: color,
            level: 'M'
        });
    }
}

// Listener para a Injeção Dinâmica de Novos Agentes ("A Fábrica")
socket.on('novo_agente', (data) => {
    console.log("HUD: Novo agente injetado ao vivo:", data.name);

    // Executa o JS do agente APENAS para registrar a descrição no objeto AGENT_DESCRIPTIONS.
    // IMPORTANTE: bloqueamos qualquer injeção de <button> na sidebar aqui.
    try {
        // Avaliamos apenas se for um registro de descrição (seguro)
        if (data.jsCode && data.jsCode.includes('AGENT_DESCRIPTIONS')) {
            eval(data.jsCode);
        }
    } catch (e) {
        console.warn("Aviso ao injetar JS do agente:", e);
    }

    const agentId = data.name.toLowerCase();

    // Evita duplicar se a janela já existir
    if (document.getElementById(`agent-terminal-${agentId}`)) {
        console.log("Terminal deste agente já está aberto.");
        // Traz para frente se já existir
        document.getElementById(`agent-terminal-${agentId}`).style.zIndex = '9999';
        return;
    }

    // Pega a cor baseada no HTML gerado pelo Fire
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = data.htmlCode.trim();
    const newTab = tempDiv.querySelector('[data-agent]') || tempDiv.firstElementChild;
    let themeColor = '#00dcff';
    let agentUrl = 'https://notebooklm.google.com/';

    if (newTab && newTab.nodeType === 1) {
        const rawAccent = newTab.style.getPropertyValue('--accent');
        if (rawAccent) themeColor = rawAccent;
        agentUrl = newTab.getAttribute('data-url') || agentUrl;
    }

    const agentNameFormated = data.name.toUpperCase();

    // Calcula posição escalonada para não empilhar terminais
    const existingTerminals = document.querySelectorAll('.agent-standalone-terminal').length;
    const offsetX = 80 + (existingTerminals * 30);
    const offsetY = 80 + (existingTerminals * 30);

    // Injeta CSS dinâmico com a cor do agente
    const dynamicStyleId = `style-theme-${agentId}`;
    if (!document.getElementById(dynamicStyleId)) {
        const styleEl = document.createElement('style');
        styleEl.id = dynamicStyleId;
        styleEl.textContent = `
            #agent-terminal-${agentId} { border-color: ${themeColor} !important; box-shadow: 0 0 20px rgba(0,0,0,0.7), 0 0 15px ${themeColor}44 !important; }
            #agent-terminal-${agentId} .chat-header { color: ${themeColor} !important; border-bottom-color: ${themeColor}66 !important; background: ${themeColor}22 !important; }
            #agent-terminal-${agentId} .user-msg { border-color: ${themeColor}; box-shadow: 0 0 8px ${themeColor}55; }
            #agent-terminal-${agentId} #send-${agentId} { background: ${themeColor}; color: #000; }
            #agent-terminal-${agentId} #input-${agentId}:focus { border-color: ${themeColor}; box-shadow: 0 0 10px ${themeColor}66; }
        `;
        document.head.appendChild(styleEl);
    }

    // Constrói a estrutura do Terminal Novo
    // USA position:fixed e é inserido no document.body para escapar de qualquer overflow:hidden
    const terminalHtml = `
        <aside class="chat-sidebar agent-standalone-terminal" id="agent-terminal-${agentId}" 
               style="position: fixed; left: ${offsetX}px; top: ${offsetY}px; bottom: auto; right: auto; z-index: 900; width: 320px; height: auto;">
            <div class="chat-header" id="header-${agentId}" style="cursor: grab;">
                ${agentNameFormated} — TERMINAL PRIVADO
                <div style="display:flex; align-items:center; gap:6px;">
                    <button id="brain-btn-${agentId}" title="Abrir Cérebro (Web)" style="background: transparent; border: none; font-size: 14px; cursor: pointer; color: inherit;">🧠</button>
                    <button id="close-btn-${agentId}" title="Fechar Terminal" style="background: transparent; border: 1px solid #ff3e3e55; border-radius: 4px; font-size: 14px; cursor: pointer; color: #ff3e3e; padding: 1px 5px;">✕</button>
                </div>
            </div>
            <div class="chat-messages" id="msgs-${agentId}" style="height: 300px;">
                <div class="message system-msg">Conexão Privada Estabelecida com ${agentNameFormated}. Aguardando diretrizes.</div>
            </div>
            <div class="chat-input-area">
                <input type="text" id="input-${agentId}" placeholder="Comande o ${agentNameFormated}..." autocomplete="off">
                <button id="send-${agentId}" title="Enviar comando" style="background: ${themeColor}; border: none; border-radius: 8px; width: 40px; color: #000; font-size: 1.2rem; cursor: pointer;">➤</button>
            </div>
        </aside>
    `;

    // Insere diretamente no body — fora de qualquer overflow:hidden
    document.body.insertAdjacentHTML('beforeend', terminalHtml);

    // Captura os elementos recém-criados
    const terminalEl = document.getElementById(`agent-terminal-${agentId}`);
    const headerEl = document.getElementById(`header-${agentId}`);
    const closeBtn = document.getElementById(`close-btn-${agentId}`);
    const brainBtn = document.getElementById(`brain-btn-${agentId}`);
    const msgsEl = document.getElementById(`msgs-${agentId}`);
    const inputEl = document.getElementById(`input-${agentId}`);
    const sendBtn = document.getElementById(`send-${agentId}`);

    // -- Lógica de Chat Independente --
    function sendPrivateCommand() {
        const text = inputEl.value.trim();
        if (!text) return;

        // Renderiza mensagem do usuário localmente no terminal privado
        const userMsgDiv = document.createElement('div');
        userMsgDiv.classList.add('message', 'user-msg');
        userMsgDiv.textContent = text;
        msgsEl.appendChild(userMsgDiv);
        msgsEl.scrollTop = msgsEl.scrollHeight;
        inputEl.value = '';

        // Envia para o Backend usando a flag exclusiva dele @nome
        const finalCommand = `@${agentId} ${text}`;
        socket.emit('text_command', { text: finalCommand, target_terminal: agentId });

        // Feedback visual master
        orb.className = 'orb-thinking';
        transcriptEl.textContent = `Aguardando ${agentNameFormated}...`;
    }

    sendBtn.addEventListener('click', sendPrivateCommand);
    inputEl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendPrivateCommand();
        }
    });

    // Pega as respostas do backend específicas para ESTE terminal (precisamos atualizar o Python para focar nisso ou filtrar via Regex localmente se o Python mandar no canal normal)
    // Para simplificar agora, toda mensagem que vier do backend e tiver "Agente X" no começo, a gente joga pra cá.

    // -- Botões de Janela --
    closeBtn.addEventListener('click', () => {
        terminalEl.remove();
        const style = document.getElementById(dynamicStyleId);
        if (style) style.remove();
    });

    brainBtn.addEventListener('click', () => {
        openExternalUrl(agentUrl);
    });

    // -- Lógica de Drag exclusiva para esta janela (position: fixed) --
    let tIsDragging = false;
    let tStartX, tStartY, tInitialLeft, tInitialTop;

    headerEl.addEventListener('mousedown', (e) => {
        if (e.target.tagName.toLowerCase() === 'button') return;
        tIsDragging = true;
        headerEl.style.cursor = 'grabbing';

        // Traz para frente de todos os outros terminais
        document.querySelectorAll('.agent-standalone-terminal').forEach(el => el.style.zIndex = '900');
        terminalEl.style.zIndex = '9999';

        // Pega posição atual real (getBoundingClientRect dá coords em relação à viewport, perfeito para fixed)
        const rect = terminalEl.getBoundingClientRect();
        terminalEl.style.left = rect.left + 'px';
        terminalEl.style.top = rect.top + 'px';

        tStartX = e.clientX;
        tStartY = e.clientY;
        tInitialLeft = rect.left;
        tInitialTop = rect.top;

        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (tIsDragging) {
            const dx = e.clientX - tStartX;
            const dy = e.clientY - tStartY;

            let l = tInitialLeft + dx;
            let t = tInitialTop + dy;

            // Barreiras: mantém o terminal visível na tela
            l = Math.max(0, Math.min(l, window.innerWidth - terminalEl.offsetWidth));
            t = Math.max(0, Math.min(t, window.innerHeight - 50));

            terminalEl.style.left = l + 'px';
            terminalEl.style.top = t + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        if (tIsDragging) {
            tIsDragging = false;
            headerEl.style.cursor = 'grab';
        }
    });

    // Efeito Visual Suave
    terminalEl.animate([
        { transform: 'scale(0.8)', opacity: 0 },
        { transform: 'scale(1)', opacity: 1 }
    ], { duration: 300, easing: 'ease-out' });

    // Se o painel de inteligência estiver ativo, força um resize precoce
    if (intelligencePanel && intelligencePanel.style.display !== 'none') {
        window.dispatchEvent(new Event('resize'));
    }

    // RE-INICIALIZA AS ABAS para incluir o novo agente se ele injetou algo no DOM principal
    initAgentTabs();
});

// --- Intelligence Monitoring Panel ---
const intelligencePanel = document.getElementById('intelligence-panel');
const voicePanel = document.getElementById('voice-monitor-floating');
const intelGraphCanvas = document.getElementById('intelligence-graph');
let intelGraphCtx = intelGraphCanvas ? intelGraphCanvas.getContext('2d') : null;

// --- Voice Rhythm Monitor Graph ---
const voiceGraphCanvas = document.getElementById('voice-rhythm-graph');
let voiceGraphCtx = voiceGraphCanvas ? voiceGraphCanvas.getContext('2d') : null;
let voiceAmplitudeData = new Array(50).fill(0);
let voiceCadenceData = new Array(50).fill(0);

// Independent data for each API to create "different rhythms"
let intelApiData = {
    openrouter: Array(50).fill(100),
    openai: Array(50).fill(120),
    huggingface: Array(50).fill(150),
    google: Array(50).fill(80),
    deepseek: Array(50).fill(200)
};
let selectedApi = 'openrouter';

// Simulation factors for variety
const apiFactors = {
    openrouter: { min: 40, max: 250, volatility: 30 },
    openai: { min: 80, max: 350, volatility: 40 },
    huggingface: { min: 150, max: 550, volatility: 55 },
    google: { min: 30, max: 140, volatility: 15 },
    deepseek: { min: 200, max: 900, volatility: 80 }
};

function initIntelligenceMode() {
    if (!intelGraphCtx) return;

    // Configura tamanho do canvas
    const resizeCanvas = () => {
        const container = intelGraphCanvas.parentElement;
        intelGraphCanvas.width = container.clientWidth;
        intelGraphCanvas.height = container.clientHeight - 30;
    };
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // Loop de animação do gráfico
    function drawGraph() {
        if (!intelligencePanel || (intelligencePanel.style.display === 'none')) {
            requestAnimationFrame(drawGraph);
            return;
        }

        intelGraphCtx.clearRect(0, 0, intelGraphCanvas.width, intelGraphCanvas.height);

        // Simula dado novo para TODOS os grupos (ritmos diferentes)
        Object.keys(intelApiData).forEach(api => {
            const data = intelApiData[api];
            const factors = apiFactors[api];
            const lastVal = data[data.length - 1];
            const noise = (Math.random() - 0.5) * factors.volatility;
            const nextVal = Math.max(factors.min, Math.min(factors.max, lastVal + noise));
            data.shift();
            data.push(nextVal);
        });

        // Pega o dado do API selecionada
        const currentData = intelApiData[selectedApi];

        // PRIORIDADE: Cor do Agente Ativo (Sincronização Total)
        const computedBody = getComputedStyle(document.body);
        const agentAccent = computedBody.getPropertyValue('--accent').trim();
        const isRaiz = document.body.classList.contains('protocol-raiz');
        const accent = isRaiz ? (computedBody.getPropertyValue('--agent-secondary').trim() || '#ffcc00') : (agentAccent || '#bf00ff');

        intelGraphCtx.beginPath();
        intelGraphCtx.strokeStyle = accent;
        intelGraphCtx.lineWidth = 2;
        intelGraphCtx.shadowBlur = 10;
        intelGraphCtx.shadowColor = accent + '88';

        const step = intelGraphCanvas.width / (currentData.length - 1);
        currentData.forEach((val, i) => {
            const x = i * step;
            // Scale y to fit canvas height (using 600 as max for scaling)
            const y = intelGraphCanvas.height - (val / 600 * intelGraphCanvas.height);
            if (i === 0) intelGraphCtx.moveTo(x, y);
            else intelGraphCtx.lineTo(x, y);
        });
        intelGraphCtx.stroke();

        // Área preenchida (gradiente baseado na cor do agente)
        const grad = intelGraphCtx.createLinearGradient(0, 0, 0, intelGraphCanvas.height);
        grad.addColorStop(0, accent + '44');
        grad.addColorStop(1, accent + '00');
        intelGraphCtx.lineTo(intelGraphCanvas.width, intelGraphCanvas.height);
        intelGraphCtx.lineTo(0, intelGraphCanvas.height);
        intelGraphCtx.fillStyle = grad;
        intelGraphCtx.fill();
        setTimeout(() => requestAnimationFrame(drawGraph), 100);
    }
    requestAnimationFrame(drawGraph);

    // Drag and Drop (SISTEMA DE MONITORAMENTO Style)
    const intelHeader = document.getElementById('intelligence-header');
    let isDraggingIntel = false;
    let intelStartX, intelStartY;
    let intelInitialLeft, intelInitialTop;

    intelHeader.addEventListener('mousedown', (e) => {
        if (e.target.classList.contains('control-btn') || e.target.classList.contains('close-panel')) return;

        isDraggingIntel = true;
        const rect = intelligencePanel.getBoundingClientRect();
        intelStartX = e.clientX;
        intelStartY = e.clientY;

        // Ensure absolute positioning without jumping
        if (intelligencePanel.style.right !== 'auto' || intelligencePanel.style.bottom !== 'auto') {
            const parentRect = (intelligencePanel.offsetParent || document.body).getBoundingClientRect();
            intelligencePanel.style.position = 'absolute';
            intelligencePanel.style.left = (rect.left - parentRect.left) + 'px';
            intelligencePanel.style.top = (rect.top - parentRect.top) + 'px';
            intelligencePanel.style.right = 'auto';
            intelligencePanel.style.bottom = 'auto';
        }

        intelInitialLeft = intelligencePanel.offsetLeft;
        intelInitialTop = intelligencePanel.offsetTop;
        intelligencePanel.style.zIndex = '2000';
    });

    document.addEventListener('mousemove', (e) => {
        if (isDraggingIntel) {
            const dx = e.clientX - intelStartX;
            const dy = e.clientY - intelStartY;
            intelligencePanel.style.left = (intelInitialLeft + dx) + 'px';
            intelligencePanel.style.top = (intelInitialTop + dy) + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        if (isDraggingIntel) {
            isDraggingIntel = false;
            saveState();
        }
    });

    // Sidebar selectors
    const apiItems = document.querySelectorAll('.api-item');
    apiItems.forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.api-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            selectedApi = item.dataset.api;
            console.log("HUD: Monitorando latência de", selectedApi);
        });
    });

    // Simulação de status das APIs (Fixed overlap bug)
    setInterval(() => {
        document.querySelectorAll('.api-item').forEach(item => {
            const statusCircle = item.querySelector('.api-status');
            const statusLabel = item.querySelector('.api-label');
            const isOnline = Math.random() > 0.04;
            if (isOnline) {
                if (statusLabel) statusLabel.textContent = 'ONLINE';
                statusCircle.className = 'api-status online';
            } else {
                if (statusLabel) statusLabel.textContent = 'INSTÁVEL';
                statusCircle.className = 'api-status offline';
            }
        });
    }, 5000);
}

// O fechamento já é tratado pela lógica genérica dos .floating-panel
// Os botões de minimizar/maximizar foram removidos para seguir o modelo do monitoramento

function initVoiceRhythmMode() {
    if (!voiceGraphCtx) return;

    const resizeCanvas = () => {
        const container = voiceGraphCanvas.parentElement;
        if (!container) return;
        voiceGraphCanvas.width = container.clientWidth;
        voiceGraphCanvas.height = container.clientHeight - 30;
    };
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    function drawVoiceGraph() {
        if (!voicePanel || !voicePanel.classList.contains('active')) {
            requestAnimationFrame(drawVoiceGraph);
            return;
        }

        voiceGraphCtx.clearRect(0, 0, voiceGraphCanvas.width, voiceGraphCanvas.height);

        const width = voiceGraphCanvas.width;
        const height = voiceGraphCanvas.height;
        const padding = 5;
        const graphWidth = width - (padding * 2);
        const graphHeight = height - (padding * 2);
        const stepX = graphWidth / (voiceAmplitudeData.length - 1);

        const computedBody = getComputedStyle(document.body);
        const accentColor = computedBody.getPropertyValue('--accent').trim() || '#00d4ff';
        const secondaryColor = computedBody.getPropertyValue('--agent-secondary').trim() || '#ffcc00';

        const isRaiz = document.body.classList.contains('protocol-raiz');
        const mainColor = isRaiz ? secondaryColor : accentColor;

        // Draw Amplitude (Main Wave)
        voiceGraphCtx.beginPath();
        voiceGraphCtx.strokeStyle = mainColor;
        voiceGraphCtx.lineWidth = 2;
        voiceGraphCtx.lineJoin = 'round';

        for (let i = 0; i < voiceAmplitudeData.length; i++) {
            const x = padding + (i * stepX);
            const y = padding + graphHeight - (voiceAmplitudeData[i] / 100 * graphHeight);
            if (i === 0) voiceGraphCtx.moveTo(x, y);
            else voiceGraphCtx.lineTo(x, y);
        }
        voiceGraphCtx.stroke();

        // Deep Glow for Amplitude
        voiceGraphCtx.shadowBlur = 15;
        voiceGraphCtx.shadowColor = mainColor;
        voiceGraphCtx.stroke();
        voiceGraphCtx.shadowBlur = 0;

        // Gradient Fill
        const grad = voiceGraphCtx.createLinearGradient(0, 0, 0, height);
        grad.addColorStop(0, mainColor + '44');
        grad.addColorStop(1, 'transparent');
        voiceGraphCtx.lineTo(padding + graphWidth, height);
        voiceGraphCtx.lineTo(padding, height);
        voiceGraphCtx.fillStyle = grad;
        voiceGraphCtx.fill();

        // Draw Cadence (Dashed line)
        voiceGraphCtx.beginPath();
        voiceGraphCtx.strokeStyle = secondaryColor;
        voiceGraphCtx.lineWidth = 1;
        voiceGraphCtx.setLineDash([4, 6]);

        for (let i = 0; i < voiceCadenceData.length; i++) {
            const x = padding + (i * stepX);
            const y = padding + graphHeight - (voiceCadenceData[i] / 100 * graphHeight);
            if (i === 0) voiceGraphCtx.moveTo(x, y);
            else voiceGraphCtx.lineTo(x, y);
        }
        voiceGraphCtx.stroke();
        voiceGraphCtx.setLineDash([]);

        requestAnimationFrame(drawVoiceGraph);
    }
    requestAnimationFrame(drawVoiceGraph);
}

initIntelligenceMode();
initVoiceRhythmMode();

// --- ANIME.JS: Inicializar Equalizador Circular ---
function initEqualizer() {
    const eqGroup = document.getElementById('hud-equalizer');
    if (!eqGroup) return;

    const numBars = 60;
    const radius = 150; // Outside the black core
    const center = 0; // Transformed to 250,250

    for (let i = 0; i < numBars; i++) {
        const angle = (i * 360 / numBars) * (Math.PI / 180);
        const x = center + radius * Math.cos(angle);
        const y = center + radius * Math.sin(angle);
        const rotation = (i * 360 / numBars) + 90; // outward

        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("class", "eq-bar");
        rect.setAttribute("x", x);
        rect.setAttribute("y", y);
        rect.setAttribute("width", "4"); // Thicker
        rect.setAttribute("height", "2");
        rect.setAttribute("fill", "var(--agent-accent, var(--glow))");
        rect.setAttribute("transform", `rotate(${rotation}, ${x}, ${y})`);

        eqGroup.appendChild(rect);
    }
}
// Run once DOM is ready or API is active
setTimeout(initEqualizer, 500);
// --- Protocolo HUD Listener ---
socket.on('protocol_change', (data) => {
    const protocolEl = document.getElementById('current-protocol');
    if (protocolEl) {
        protocolEl.textContent = data.protocol;

        // Efeito visual de mudança
        if (data.protocol === 'RAIZ') {
            protocolEl.style.color = 'var(--agent-secondary)'; // Sincronizado conforme imagem
            protocolEl.style.textShadow = '0 0 10px var(--agent-secondary)';
        } else if (data.protocol === 'GRAVANDO') {
            protocolEl.style.color = '#ff3e3e';
            protocolEl.style.textShadow = '0 0 10px #ff3e3e';
        } else if (data.protocol === 'VIDEO') {
            protocolEl.style.color = '#ff00ff';
            protocolEl.style.textShadow = '0 0 15px #ff00ff';
        } else {
            protocolEl.style.color = 'var(--accent)';
            protocolEl.style.textShadow = 'none';
        }

        // Toggle de classes no body para o modo RAIZ e visibilidade do painel
        if (data.protocol === 'RAIZ') {
            document.body.classList.add('protocol-raiz');
            if (voicePanel) {
                voicePanel.classList.add('active');
            }
            if (intelligencePanel) {
                intelligencePanel.style.display = 'flex';
                intelligencePanel.classList.add('active');
                // Força o resize do canvas do gráfico
                window.dispatchEvent(new Event('resize'));
            }
        } else if (data.protocol === 'VIDEO') {
            document.body.classList.add('protocol-video');
            document.body.style.boxShadow = 'inset 0 0 100px rgba(255, 0, 255, 0.2)';
        } else {
            document.body.classList.remove('protocol-raiz', 'protocol-video');
            document.body.style.boxShadow = 'none';
            if (intelligencePanel) {
                intelligencePanel.style.display = 'none';
                intelligencePanel.classList.remove('active');
            }
            if (voicePanel) {
                voicePanel.classList.remove('active');
            }
        }

        protocolEl.animate([
            { opacity: 0.3 },
            { opacity: 1 }
        ], { duration: 500, iterations: 3 });

        // Salva o estado após a mudança de protocolo para persistir a visibilidade dos novos painéis
        saveState();
    }
});

// --- Access Monitoring (CONTROLE MOBILE) ---
const accessTriggerNode = document.getElementById('node-access-trigger');
const accessPanel = document.getElementById('access-panel-floating');
const closeAccessBtn = document.getElementById('close-access-panel');
const accessCanvas = document.getElementById('access-qrcode-canvas');
const privacyToggleBtn = document.getElementById('toggle-qr-privacy');
const qrBlurWrapper = document.getElementById('qr-blur-container');

function updateAccessQRCode() {
    if (!accessCanvas) return;
    const computedBody = getComputedStyle(document.body);
    const accent = computedBody.getPropertyValue('--accent').trim() || '#00e5ff';
    new QRious({
        element: accessCanvas,
        value: currentConnectionUrl || `http://${window.location.hostname}:5000`,
        size: 150,
        background: 'white',
        foreground: accent,
        level: 'H'
    });
}

if (accessTriggerNode && accessPanel) {
    accessTriggerNode.addEventListener('click', () => {
        const isActive = accessPanel.classList.toggle('active');
        if (isActive) {
            accessPanel.style.zIndex = '2000';
            updateAccessQRCode(); // Ensure it's generated with current colors
        }
        saveState();
    });
}

if (privacyToggleBtn && qrBlurWrapper) {
    privacyToggleBtn.addEventListener('click', () => {
        const isBlurred = qrBlurWrapper.classList.toggle('blurred');
        const icon = privacyToggleBtn.querySelector('i');
        if (isBlurred) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    });

    // Start blurred for security
    qrBlurWrapper.classList.add('blurred');
    const icon = privacyToggleBtn.querySelector('i');
    icon.classList.remove('fa-eye');
    icon.classList.add('fa-eye-slash');
}

if (closeAccessBtn && accessPanel) {
    closeAccessBtn.addEventListener('click', () => {
        accessPanel.classList.remove('active');
        saveState();
    });
}

// Clear Chat Logic
const clearChatBtn = document.getElementById('clear-chat-btn');
if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
        chatMessagesEl.innerHTML = '';
        const div = document.createElement('div');
        div.classList.add('message', 'system-msg');
        div.textContent = 'Histórico de chat limpo.';
        chatMessagesEl.appendChild(div);

        // Atualiza a memória para este agente
        agentHistories[activeAgent] = chatMessagesEl.innerHTML;
        saveState();
    });
}

// Global initialization for QR
setTimeout(updateAccessQRCode, 1000);

// Global toggle for all panels
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.floating-panel').forEach(p => p.classList.remove('active'));
        saveState();
    }
});

// Inicialização Final: Carrega o estado salvo
window.addEventListener('load', () => {
    console.log('DOM carregado, restaurando estado...');
    loadState();
});

// --- Gesture & System Controls (Elite Module) ---
function showGestureToast(text) {
    const toast = document.getElementById('gesture-toast');
    if (!toast) return;

    toast.textContent = text;
    toast.classList.add('show');

    // Auto-hide after 2 seconds
    if (window.toastTimeout) clearTimeout(window.toastTimeout);
    window.toastTimeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 2000);
}

function switchHUDAgent(direction) {
    const tabs = Array.from(document.querySelectorAll('.agent-tab'));
    const currentIndex = tabs.findIndex(t => t.dataset.agent === activeAgent);
    let nextIndex;

    if (direction === 'next') {
        nextIndex = (currentIndex + 1) % tabs.length;
    } else {
        nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    }

    const nextTab = tabs[nextIndex];
    if (nextTab) {
        nextTab.click(); // Re-utiliza a lógica existente de clique
    }
}

socket.on('gui_command', (data) => {
    console.log('GUI Command received:', data);
    const action = data.action;

    if (action === 'gesture_notify') {
        showGestureToast(data.gesture || 'Gesto Detectado');
    } else if (action === 'next_agent') {
        switchHUDAgent('next');
    } else if (action === 'prev_agent') {
        switchHUDAgent('prev');
    } else if (action === 'minimize_all') {
        // Minimiza terminal e outros painéis se estiverem abertos
        if (!isCollapsed) {
            const collapseBtn = document.getElementById('collapse-btn');
            if (collapseBtn) collapseBtn.click();
        }
        // Fecha outros painéis flutuantes ativos
        document.querySelectorAll('.floating-panel.active').forEach(p => {
            const closeBtn = p.querySelector('.close-panel');
            if (closeBtn) closeBtn.click();
        });
    }
});
