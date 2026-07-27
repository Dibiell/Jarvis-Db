/**
 * J.A.R.V.I.S. Cinematic Data Background
 * Manages the background HUD, code streams, and tech-grids
 */

class DataBackground {
    constructor() {
        this.container = document.getElementById('background-layer');
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.container.appendChild(this.canvas);

        this.columns = 0;
        this.drops = [];
        this.fontSize = 12;

        // Dados fictícios inspirados no Jarvis
        this.charSet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<>[]{}/\\|!@#$%^&*()_+-=010101";
        this.dataSnippets = [
            "SYSTEM_ONLINE", "ENCRYPTING", "CORE_SYNC", "PROTO_JBS_01",
            "UPDATING_DRIVERS", "LOCALIZING_NODE", "REBOOTING_SENSORS",
            "SCANNING_VULN", "TRACE_DETECTED", "WAKE_WORD_READY",
            "OLLAMA_CONNECTED", "GROQ_LATENCY_20MS", "SWARM_ACTIVE"
        ];

        this.resize();
        window.addEventListener('resize', () => this.resize());

        this.animate();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.columns = Math.floor(this.canvas.width / this.fontSize);
        this.drops = [];
        for (let i = 0; i < this.columns; i++) {
            this.drops[i] = Math.random() * -100;
        }
    }

    getAccentColor() {
        const root = document.documentElement;
        const body = document.body;
        // Pega a cor principal baseada no tema atual
        return getComputedStyle(body).getPropertyValue('--accent').trim() || '#00d2ff';
    }

    animate() {
        // Overlay leve para rastro de movimento
        this.ctx.fillStyle = 'rgba(5, 10, 15, 0.15)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        const accentColor = this.getAccentColor();
        this.ctx.fillStyle = accentColor;
        this.ctx.font = this.fontSize + 'px Orbitron';
        this.ctx.textAlign = 'center';

        for (let i = 0; i < this.drops.length; i++) {
            const char = this.charSet[Math.floor(Math.random() * this.charSet.length)];
            this.ctx.globalAlpha = 0.3; // Rain is more subtle
            this.ctx.fillText(char, i * this.fontSize, this.drops[i] * this.fontSize);
            this.ctx.globalAlpha = 1.0;

            if (this.drops[i] * this.fontSize > this.canvas.height && Math.random() > 0.975) {
                this.drops[i] = 0;
            }
            this.drops[i]++;
        }

        this.drawGrid();
        this.drawPanels(accentColor);

        requestAnimationFrame(() => this.animate());
    }

    drawPanels(color) {
        // Desenha alguns "painéis de status" aleatórios
        this.ctx.strokeStyle = color;
        this.ctx.fillStyle = color;
        this.ctx.lineWidth = 1;

        // Semente de aleatoriedade baseada no tempo para os painéis não piscarem toda hora
        const seed = Math.floor(Date.now() / 2000);

        for (let i = 0; i < 5; i++) {
            const x = (seed * (i + 1) * 123) % (this.canvas.width - 200);
            const y = (seed * (i + 1) * 456) % (this.canvas.height - 100);

            this.ctx.globalAlpha = 0.1;
            this.ctx.strokeRect(x, y, 150, 80);
            this.ctx.globalAlpha = 0.05;
            this.ctx.fillRect(x, y, 150, 20);

            this.ctx.globalAlpha = 0.4;
            this.ctx.font = '8px Orbitron';
            this.ctx.textAlign = 'left';
            this.ctx.fillText(this.dataSnippets[(seed + i) % this.dataSnippets.length], x + 5, y + 13);

            // Desenha algumas linhas de "dados" dentro do painel
            for (let j = 0; j < 3; j++) {
                this.ctx.globalAlpha = 0.2;
                this.ctx.fillRect(x + 5, y + 30 + (j * 15), 100 + Math.random() * 40, 2);
            }
        }
        this.ctx.globalAlpha = 1.0;
    }

    drawGrid() {
        this.ctx.strokeStyle = 'rgba(0, 210, 255, 0.03)';
        this.ctx.lineWidth = 0.5;
        const gridSize = 100;

        this.ctx.beginPath();
        for (let x = 0; x <= this.canvas.width; x += gridSize) {
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
        }
        for (let y = 0; y <= this.canvas.height; y += gridSize) {
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
        }
        this.ctx.stroke();
    }
}

// Inicializa quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.jarvisBG = new DataBackground();
});
