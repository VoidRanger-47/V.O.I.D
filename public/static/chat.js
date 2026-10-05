/**
 * V.O.I.D. Interface Logic
 * Implements a Gemini-like experience with persistence, file handling,
 * and dynamic DOM manipulation.
 */

class ChatInterface {
    constructor() {
        // State
        this.currentSessionId = Date.now();
        this.chats = JSON.parse(localStorage.getItem('void_chats')) || {};
        this.uploadedFiles = [];
        this.isGenerating = false;
        this.theme = localStorage.getItem('void_theme') || 'dark';
        
        // Settings State
        this.settings = JSON.parse(localStorage.getItem('void_settings')) || {
            temperature: 0.7,
            maxTokens: 150
        };

        // User Name State
        this.userName = localStorage.getItem('void_user_name') || 'User';

        // Multi-Modal Toggles & Voice State
        this.thinkingMode = false;
        this.forceSearch = false;
        this.autoSpeak = localStorage.getItem('void_auto_speak') === 'true';
        this.voiceEngine = localStorage.getItem('void_voice_engine') || 'browser';
        this.speechSynth = ('speechSynthesis' in window) ? window.speechSynthesis : null;
        this.availableVoices = [];
        this.selectedVoice = localStorage.getItem('void_voice') || 'default';
        this.speechRate = parseFloat(localStorage.getItem('void_speech_rate')) || 1.0;
        this.currentAudioElement = null;

        // Voice Recording State
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.voiceAvailable = false;

        // DOM Elements
        this.elements = {
            input: document.getElementById('user-input'),
            sendBtn: document.getElementById('send-btn'),
            chatBox: document.getElementById('message-container'),
            historyList: document.getElementById('history-list'),
            fileInput: document.getElementById('file-upload'),
            filePreview: document.getElementById('file-preview-area'),
            thinking: document.getElementById('thinking-indicator'),
            welcome: document.getElementById('welcome-screen'),
            sidebar: document.getElementById('sidebar'),
            sidebarOverlay: document.getElementById('sidebar-overlay'),
            dragOverlay: document.getElementById('drag-overlay'),
            
            // Settings Modal Elements
            settingsModal: document.getElementById('settings-modal'),
            tempRange: document.getElementById('temperature'),
            tempValue: document.getElementById('temp-value'),
            tokensRange: document.getElementById('max-tokens'),
            tokensValue: document.getElementById('tokens-value'),
            voiceEngineSelect: document.getElementById('voice-engine-select'),
            voiceSelectGroup: document.getElementById('voice-select-group'),
            voiceSelect: document.getElementById('voice-select'),
            voiceRate: document.getElementById('voice-rate'),
            voiceRateVal: document.getElementById('voice-rate-val'),
            autoSpeakCheckbox: document.getElementById('auto-speak-checkbox'),
            testVoiceBtn: document.getElementById('test-voice-btn'),
            
            // Name Customization
            welcomeGreeting: document.getElementById('welcome-greeting'),
            namePrompt: document.getElementById('name-prompt'),
            userNameInput: document.getElementById('user-name-input'),
            userAvatar: document.getElementById('user-avatar'),
            
            // Voice & Multi-Modal Controls
            voiceBtn: document.getElementById('voice-btn'),
            voiceStatus: document.getElementById('voice-status'),
            voiceStatusText: document.getElementById('voice-status-text'),
            thinkingToggleBtn: document.getElementById('thinking-toggle-btn'),
            searchToggleBtn: document.getElementById('search-toggle-btn'),
            autoSpeakBtn: document.getElementById('auto-speak-btn'),
            networkBadge: document.getElementById('network-badge'),

            // Claude Canvas Elements
            appContainer: document.querySelector('.app-container'),
            artifactsPanel: document.getElementById('artifacts-panel'),
            artifactTitleText: document.getElementById('artifact-title-text'),
            artifactIframe: document.getElementById('artifact-iframe'),
            artifactCodeWrapper: document.getElementById('artifact-code-wrapper'),
            artifactPreviewWrapper: document.getElementById('artifact-preview-wrapper'),
            artifactCodeElement: document.getElementById('artifact-code-element'),
            artifactTabPreview: document.getElementById('artifact-tab-preview'),
            artifactTabCode: document.getElementById('artifact-tab-code'),

            // Attachment Plus Button & Neural Action Menu
            attachmentPlusBtn: document.getElementById('attachment-plus-btn'),
            attachmentMenu: document.getElementById('attachment-action-menu'),
            attachmentMenuBackdrop: document.getElementById('attachment-menu-backdrop'),
            attachmentCloseBtn: document.getElementById('void-menu-close-btn'),
            visionUploadInput: document.getElementById('vision-upload')
        };

        this.currentArtifact = { title: "Artifact Preview", code: "", type: "html" };
        this.init();
    }


    init() {
        this.applyTheme(this.theme);
        this.loadSettings();
        this.loadUserName();
        this.renderHistory();
        this.setupEventListeners();
        this.initSpeechVoices();
        this.checkVoiceAvailability();
        this.checkNetworkStatus();
        
        // STRICT CAMERA ACCESS POLICY: Ensure camera hardware is decoupled when on chat page
        fetch('/api/vision/stop', { method: 'POST' }).catch(() => {});
        window.addEventListener('focus', () => {
            fetch('/api/vision/stop', { method: 'POST' }).catch(() => {});
        });

        // Auto-focus input
        if (this.elements.input) this.elements.input.focus();
    }

    checkNetworkStatus() {
        fetch('/api/network/status')
            .then(r => r.json())
            .then(data => {
                if (this.elements.networkBadge) {
                    if (data.offline_mode) {
                        this.elements.networkBadge.className = 'network-badge offline';
                        this.elements.networkBadge.innerHTML = '<i class="fa-solid fa-shield-halved"></i> <span>🌐 Offline (100% Local)</span>';
                        this.elements.networkBadge.title = 'No Internet Access: Web Search Unavailable • All Local AI Tools Active';
                    } else {
                        this.elements.networkBadge.className = 'network-badge online';
                        this.elements.networkBadge.innerHTML = '<i class="fa-solid fa-wifi"></i> <span>⚡ Online (Web Active)</span>';
                        this.elements.networkBadge.title = 'Internet Connected: Live Web Search Available';
                    }
                }
            })
            .catch(() => {
                if (this.elements.networkBadge) {
                    this.elements.networkBadge.className = 'network-badge offline';
                    this.elements.networkBadge.innerHTML = '<i class="fa-solid fa-shield-halved"></i> <span>🌐 Offline (100% Local)</span>';
                    this.elements.networkBadge.title = 'Offline Mode Active';
                }
            });
    }


    /* --- Speech Voices --- */
    initSpeechVoices() {
        // Auto-select server audio in Electron or environments without Web Speech voices
        const isElectron = !!(window.voidDesktop || (navigator.userAgent && navigator.userAgent.includes('Electron')));
        if (isElectron) {
            this.voiceEngine = 'server';
            if (this.elements.voiceEngineSelect) this.elements.voiceEngineSelect.value = 'server';
            if (this.elements.voiceSelectGroup) this.elements.voiceSelectGroup.style.display = 'none';
        }

        if (!this.speechSynth) {
            this.voiceEngine = 'server';
            return;
        }
        
        const populateVoices = () => {
            this.availableVoices = this.speechSynth.getVoices();
            if (this.elements.voiceSelect) {
                this.elements.voiceSelect.innerHTML = '<option value="default">Default System Voice</option>';
                this.availableVoices.forEach((voice, index) => {
                    const opt = document.createElement('option');
                    opt.value = index;
                    opt.textContent = `${voice.name} (${voice.lang})`;
                    if (this.selectedVoice === index.toString()) opt.selected = true;
                    this.elements.voiceSelect.appendChild(opt);
                });
            }

            // If no browser voices are registered, default to local server TTS
            if (this.availableVoices.length === 0 && !isElectron) {
                this.voiceEngine = 'server';
            }
        };

        populateVoices();
        if (this.speechSynth.onvoiceschanged !== undefined) {
            this.speechSynth.onvoiceschanged = populateVoices;
        }
    }


    /* --- Event Listeners --- */
    setupEventListeners() {
        // Input Auto-resize & Send on Enter
        if (this.elements.input) {
            this.elements.input.addEventListener('input', (e) => {
                e.target.style.height = 'auto';
                e.target.style.height = e.target.scrollHeight + 'px';
                if (e.target.value === '') e.target.style.height = 'auto';
            });

            this.elements.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        if (this.elements.sendBtn) {
            this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
        }

        // Input container click-to-focus delegation
        const inputWrapper = document.querySelector('.input-wrapper');
        if (inputWrapper) {
            inputWrapper.addEventListener('click', (e) => {
                if (!e.target.closest('button') && !e.target.closest('input') && !e.target.closest('select')) {
                    if (this.elements.input) {
                        this.elements.input.focus();
                    }
                }
            });
        }

        // Auto-focus input on startup
        setTimeout(() => {
            if (this.elements.input) {
                this.elements.input.focus();
            }
        }, 150);

        // Multi-Modal Toggles
        if (this.elements.thinkingToggleBtn) {
            this.elements.thinkingToggleBtn.addEventListener('click', () => {
                this.thinkingMode = !this.thinkingMode;
                this.elements.thinkingToggleBtn.classList.toggle('thinking-active', this.thinkingMode);
            });
        }

        if (this.elements.searchToggleBtn) {
            this.elements.searchToggleBtn.addEventListener('click', () => {
                this.forceSearch = !this.forceSearch;
                this.elements.searchToggleBtn.classList.toggle('search-active', this.forceSearch);
                this.checkNetworkStatus();
            });
        }

        if (this.elements.autoSpeakBtn) {
            this.updateAutoSpeakUI();
            this.elements.autoSpeakBtn.addEventListener('click', () => {
                this.autoSpeak = !this.autoSpeak;
                localStorage.setItem('void_auto_speak', this.autoSpeak);
                this.updateAutoSpeakUI();
            });
        }

        // File Upload Handling
        if (this.elements.fileInput) {
            this.elements.fileInput.addEventListener('change', (e) => this.handleFiles(e.target.files));
        }

        // Dedicated Vision Image Upload Handling
        if (this.elements.visionUploadInput) {
            this.elements.visionUploadInput.addEventListener('change', (e) => this.handleFiles(e.target.files));
        }

        // Attachment Plus Button Toggle
        if (this.elements.attachmentPlusBtn) {
            this.elements.attachmentPlusBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleAttachmentMenu();
            });
        }

        // Attachment Action Menu Close Button
        if (this.elements.attachmentCloseBtn) {
            this.elements.attachmentCloseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.closeAttachmentMenu();
            });
        }

        // Mobile Attachment Menu Backdrop Click
        if (this.elements.attachmentMenuBackdrop) {
            this.elements.attachmentMenuBackdrop.addEventListener('click', (e) => {
                e.stopPropagation();
                this.closeAttachmentMenu();
            });
        }

        // Attachment Action Menu Tile Clicks
        document.querySelectorAll('.void-action-tile').forEach(tile => {
            tile.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = tile.getAttribute('data-action');
                this.handleMenuAction(action);
            });
        });

        // Close Attachment Menu on outside click
        document.addEventListener('click', (e) => {
            if (this.elements.attachmentMenu && !this.elements.attachmentMenu.classList.contains('hidden')) {
                if (!this.elements.attachmentMenu.contains(e.target) && 
                    !this.elements.attachmentPlusBtn?.contains(e.target)) {
                    this.closeAttachmentMenu();
                }
            }
        });

        // Close Attachment Menu when focusing or clicking input textarea
        if (this.elements.input) {
            this.elements.input.addEventListener('focus', () => {
                this.closeAttachmentMenu();
            });
        }
        
        // Drag and Drop
        if (this.elements.dragOverlay) {
            window.addEventListener('dragover', (e) => {
                e.preventDefault();
                this.elements.dragOverlay.classList.remove('hidden');
            });
            this.elements.dragOverlay.addEventListener('dragleave', (e) => {
                this.elements.dragOverlay.classList.add('hidden');
            });
            this.elements.dragOverlay.addEventListener('drop', (e) => {
                e.preventDefault();
                this.elements.dragOverlay.classList.add('hidden');
                this.handleFiles(e.dataTransfer.files);
            });
        }

        // Mobile Menu & Backdrop
        const mobileMenuBtn = document.getElementById('mobile-menu-btn');
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', () => this.openSidebar());
        }
        const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
        if (toggleSidebarBtn) {
            toggleSidebarBtn.addEventListener('click', () => this.closeSidebar());
        }
        if (this.elements.sidebarOverlay) {
            this.elements.sidebarOverlay.addEventListener('click', () => this.closeSidebar());
        }

        // Settings Modal Open
        document.querySelectorAll('[data-modal-target="#settings-modal"]').forEach(btn => {
            btn.addEventListener('click', () => this.openSettingsModal());
        });

        // Knowledge Core & Learning Dashboard Modal Open
        const learningDashboardBtn = document.getElementById('learning-dashboard-btn');
        if (learningDashboardBtn) {
            learningDashboardBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openLearningDashboard();
            });
        }
        document.querySelectorAll('[data-modal-target="#learning-modal"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openLearningDashboard();
            });
        });

        // Intelligence Hub Modal Open
        const intelHubBtn = document.getElementById('intelligence-hub-btn');
        if (intelHubBtn) {
            intelHubBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openIntelligenceHub();
            });
        }
        document.querySelectorAll('[data-modal-target="#intelligence-modal"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openIntelligenceHub();
            });
        });

        // Remote Dashboard Modal Open
        const remoteDashboardBtn = document.getElementById('remote-dashboard-btn');
        if (remoteDashboardBtn) {
            remoteDashboardBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openRemoteDashboard();
            });
        }
        document.querySelectorAll('[data-modal-target="#remote-dashboard-modal"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openRemoteDashboard();
            });
        });

        // Memory Inspector Modal Open
        // Memory Inspector Modal Open
        const memoryInspectorBtn = document.getElementById('memory-inspector-btn');
        if (memoryInspectorBtn) {
            memoryInspectorBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openMemoryInspector();
            });
        }
        document.querySelectorAll('[data-modal-target="#memory-modal"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openMemoryInspector();
            });
        });

        // Image Studio & Gallery Modal Open
        const imageStudioBtn = document.getElementById('image-studio-btn');
        if (imageStudioBtn) {
            imageStudioBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openImageStudio();
            });
        }
        document.querySelectorAll('[data-modal-target="#image-studio-modal"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openImageStudio();
            });
        });

        // Desktop MCP Modal Open
        const desktopMcpBtn = document.getElementById('desktop-mcp-btn');
        if (desktopMcpBtn) {
            desktopMcpBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openDesktopMcpModal();
            });
        }
        document.querySelectorAll('[data-modal-target="#desktop-mcp-modal"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openDesktopMcpModal();
            });
        });

        // Settings Modal Close Buttons
        const closeBtn = document.getElementById('modal-close-icon-btn');
        if (closeBtn) closeBtn.addEventListener('click', () => this.closeSettingsModal());

        const saveBtn = document.getElementById('modal-save-btn');
        if (saveBtn) saveBtn.addEventListener('click', () => this.closeSettingsModal());

        // Generic Modal Close handler
        document.querySelectorAll('[data-modal-close]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetSelector = btn.getAttribute('data-modal-close');
                const modal = document.querySelector(targetSelector);
                if (modal) modal.classList.add('hidden');
                if (targetSelector === '#remote-dashboard-modal') {
                    this.closeRemoteDashboard();
                }
                if (targetSelector === '#learning-modal') {
                    this.closeLearningDashboard();
                }
                if (targetSelector === '#intelligence-modal') {
                    this.closeIntelligenceHub();
                }
                if (targetSelector === '#image-studio-modal') {
                    this.closeImageStudio();
                }
                if (targetSelector === '#desktop-mcp-modal') {
                    this.closeDesktopMcpModal();
                }
            });
        });

        // Close on Backdrop Click
        if (this.elements.settingsModal) {
            this.elements.settingsModal.addEventListener('click', (e) => {
                if (e.target === this.elements.settingsModal) {
                    this.closeSettingsModal();
                }
            });
        }

        const remoteModal = document.getElementById('remote-dashboard-modal');
        if (remoteModal) {
            remoteModal.addEventListener('click', (e) => {
                if (e.target === remoteModal) {
                    this.closeRemoteDashboard();
                }
            });
        }

        const intelModal = document.getElementById('intelligence-modal');
        if (intelModal) {
            intelModal.addEventListener('click', (e) => {
                if (e.target === intelModal) {
                    this.closeIntelligenceHub();
                }
            });
        }

        const memModal = document.getElementById('memory-modal');
        if (memModal) {
            memModal.addEventListener('click', (e) => {
                if (e.target === memModal) {
                    memModal.classList.add('hidden');
                }
            });
        }

        const learningModal = document.getElementById('learning-modal');
        if (learningModal) {
            learningModal.addEventListener('click', (e) => {
                if (e.target === learningModal) {
                    this.closeLearningDashboard();
                }
            });
        }

        const imageStudioModal = document.getElementById('image-studio-modal');
        if (imageStudioModal) {
            imageStudioModal.addEventListener('click', (e) => {
                if (e.target === imageStudioModal) {
                    this.closeImageStudio();
                }
            });
        }

        const desktopMcpModal = document.getElementById('desktop-mcp-modal');
        if (desktopMcpModal) {
            desktopMcpModal.addEventListener('click', (e) => {
                if (e.target === desktopMcpModal) {
                    this.closeDesktopMcpModal();
                }
            });
        }

        // Close on Escape Key
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.elements.attachmentMenu && !this.elements.attachmentMenu.classList.contains('hidden')) {
                    this.closeAttachmentMenu();
                }
                if (this.elements.settingsModal && !this.elements.settingsModal.classList.contains('hidden')) {
                    this.closeSettingsModal();
                }
                if (remoteModal && !remoteModal.classList.contains('hidden')) {
                    this.closeRemoteDashboard();
                }
                if (intelModal && !intelModal.classList.contains('hidden')) {
                    this.closeIntelligenceHub();
                }
                if (memModal && !memModal.classList.contains('hidden')) {
                    memModal.classList.add('hidden');
                }
                if (learningModal && !learningModal.classList.contains('hidden')) {
                    this.closeLearningDashboard();
                }
            }
        });

        // Slider Listeners
        if (this.elements.tempRange) {
            this.elements.tempRange.addEventListener('input', (e) => {
                this.updateSettings('temperature', parseFloat(e.target.value));
            });
        }
        if (this.elements.tokensRange) {
            this.elements.tokensRange.addEventListener('input', (e) => {
                this.updateSettings('maxTokens', parseInt(e.target.value));
            });
        }

        const testVoiceBtn = document.getElementById('test-voice-btn');
        if (testVoiceBtn) {
            testVoiceBtn.addEventListener('click', () => this.testVoice());
        }

        if (this.elements.voiceSelect) {
            this.elements.voiceSelect.addEventListener('change', (e) => {
                this.selectedVoice = e.target.value;
                localStorage.setItem('void_voice', this.selectedVoice);
            });
        }

        if (this.elements.voiceEngineSelect) {
            this.elements.voiceEngineSelect.addEventListener('change', (e) => {
                this.voiceEngine = e.target.value;
                localStorage.setItem('void_voice_engine', this.voiceEngine);
                if (this.elements.voiceSelectGroup) {
                    this.elements.voiceSelectGroup.style.display = this.voiceEngine === 'server' ? 'none' : 'block';
                }
            });
        }

        if (this.elements.autoSpeakCheckbox) {
            this.elements.autoSpeakCheckbox.addEventListener('change', (e) => {
                this.autoSpeak = e.target.checked;
                localStorage.setItem('void_auto_speak', this.autoSpeak);
                this.updateAutoSpeakUI();
            });
        }

        if (this.elements.voiceRate) {
            this.elements.voiceRate.addEventListener('input', (e) => {
                this.speechRate = parseFloat(e.target.value);
                if (this.elements.voiceRateVal) this.elements.voiceRateVal.textContent = this.speechRate.toFixed(1) + 'x';
                localStorage.setItem('void_speech_rate', this.speechRate);
            });
        }

        // Voice Recording Listener
        if (this.elements.voiceBtn) {
            this.elements.voiceBtn.addEventListener('click', () => this.toggleVoiceRecording());
        }
    }


    updateAutoSpeakUI() {
        if (this.elements.autoSpeakBtn) {
            if (this.autoSpeak) {
                this.elements.autoSpeakBtn.innerHTML = '<i class="fa-solid fa-volume-high" style="color: var(--accent-color);"></i>';
                this.elements.autoSpeakBtn.title = "Auto-Speak Enabled (Click to Mute)";
            } else {
                this.elements.autoSpeakBtn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i>';
                this.elements.autoSpeakBtn.title = "Auto-Speak Disabled (Click to Enable)";
            }
        }
        if (this.elements.autoSpeakCheckbox) {
            this.elements.autoSpeakCheckbox.checked = this.autoSpeak;
        }
    }

    /* --- Speech & Voice Helpers --- */
    cleanTextForSpeech(text) {
        if (!text) return "";
        return text.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '')
                   .replace(/```[\s\S]*?```/g, ' Code block omitted. ')
                   .replace(/`[^`]+`/g, ' ')
                   .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
                   .replace(/[*#_~`\[\]()<>]/g, ' ')
                   .replace(/https?:\/\/\S+/g, ' link ')
                   .replace(/\s+/g, ' ')
                   .trim();
    }

    stopSpeech() {
        if (this.speechSynth) {
            try { this.speechSynth.cancel(); } catch (e) {}
        }
        if (this.currentAudioElement) {
            try {
                this.currentAudioElement.pause();
                this.currentAudioElement.currentTime = 0;
            } catch (e) {}
            this.currentAudioElement = null;
        }
        try {
            fetch('/api/voice/stop', { method: 'POST' }).catch(() => {});
        } catch (_) {}

        document.querySelectorAll('.speak-msg-btn').forEach(b => {
            b.classList.remove('speaking');
            b.dataset.speaking = "false";
            b.innerHTML = '<i class="fa-solid fa-volume-high"></i> Speak';
        });
    }

    testVoice() {
        this.speakText("Hello! I am V.O.I.D., speaking to you live through your local neural engine.", document.getElementById('test-voice-btn'));
    }

    /* --- Speak Response (Dual-Engine TTS) --- */
    speakText(text, btnElement = null) {
        const wasSpeakingThis = btnElement && btnElement.dataset.speaking === "true";
        
        // Barge-in: Stop any existing speech playback immediately
        this.stopSpeech();

        if (wasSpeakingThis) {
            return; // Toggle off if clicked on active button
        }

        const cleanText = this.cleanTextForSpeech(text);
        if (!cleanText) return;

        const isElectron = !!(window.voidDesktop || (navigator.userAgent && navigator.userAgent.includes('Electron')));

        if (this.voiceEngine === 'server' || isElectron || !this.speechSynth || this.availableVoices.length === 0) {
            // Direct Local Server Audio (Piper / Windows SAPI)
            this.speakWithServerTTS(cleanText, btnElement);
        } else {
            // Browser Web Speech API with fallback
            this.speakWithWebSpeech(cleanText, btnElement);
        }
    }

    async speakWithServerTTS(cleanText, btnElement = null) {
        if (btnElement) {
            btnElement.classList.add('speaking');
            btnElement.dataset.speaking = "true";
            btnElement.innerHTML = '<i class="fa-solid fa-volume-high fa-beat" style="color: var(--accent-color);"></i> Speaking...';
        }

        const restoreButton = () => {
            if (btnElement) {
                btnElement.classList.remove('speaking');
                btnElement.dataset.speaking = "false";
                btnElement.innerHTML = '<i class="fa-solid fa-volume-high"></i> Speak';
            }
        };

        try {
            const res = await fetch(`/api/voice/speak?text=${encodeURIComponent(cleanText.substring(0, 1500))}&t=${Date.now()}`);
            if (!res.ok) {
                throw new Error(`Server returned ${res.status}`);
            }
            const blob = await res.blob();
            const blobUrl = URL.createObjectURL(blob);
            const audio = new Audio(blobUrl);
            audio.playbackRate = this.speechRate || 1.0;
            this.currentAudioElement = audio;

            audio.onended = () => {
                URL.revokeObjectURL(blobUrl);
                this.currentAudioElement = null;
                restoreButton();
            };

            audio.onerror = (e) => {
                console.warn("Audio playback error, falling back to direct PC audio:", e);
                URL.revokeObjectURL(blobUrl);
                this.currentAudioElement = null;
                // Hardware fallback
                fetch('/api/voice/play', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: cleanText })
                }).finally(() => {
                    setTimeout(restoreButton, 3500);
                });
            };

            await audio.play();
        } catch (err) {
            console.warn("Server TTS fetch/play failed, falling back to direct PC audio:", err);
            // Hardware fallback via Python
            fetch('/api/voice/play', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: cleanText })
            }).finally(() => {
                setTimeout(restoreButton, 3500);
            });
        }
    }


    speakWithWebSpeech(cleanText, btnElement = null) {
        if (!this.speechSynth || this.availableVoices.length === 0) {
            this.speakWithServerTTS(cleanText, btnElement);
            return;
        }

        try {
            this.speechSynth.cancel();
            this.speechSynth.resume();
        } catch (_) {}

        if (btnElement) {
            btnElement.classList.add('speaking');
            btnElement.dataset.speaking = "true";
            btnElement.innerHTML = '<i class="fa-solid fa-volume-high fa-beat" style="color: var(--accent-color);"></i> Speaking...';
        }

        const sentences = cleanText.match(/[^.!?]+[.!?]+|\S+/g) || [cleanText];
        let chunks = [];
        let cur = "";

        for (const s of sentences) {
            if ((cur + " " + s).length < 180) {
                cur = cur ? cur + " " + s : s;
            } else {
                if (cur) chunks.push(cur);
                cur = s;
            }
        }
        if (cur) chunks.push(cur);

        let idx = 0;
        const speakNextChunk = () => {
            if (idx >= chunks.length) {
                if (btnElement) {
                    btnElement.classList.remove('speaking');
                    btnElement.dataset.speaking = "false";
                    btnElement.innerHTML = '<i class="fa-solid fa-volume-high"></i> Speak';
                }
                return;
            }

            const chunkText = chunks[idx++];
            const utterance = new SpeechSynthesisUtterance(chunkText);
            utterance.rate = this.speechRate || 1.0;

            if (this.selectedVoice !== 'default' && this.availableVoices[this.selectedVoice]) {
                utterance.voice = this.availableVoices[this.selectedVoice];
            }

            utterance.onend = () => {
                speakNextChunk();
            };

            utterance.onerror = (e) => {
                console.warn("SpeechSynthesis error, falling back to Server TTS:", e);
                if (btnElement) {
                    btnElement.classList.remove('speaking');
                    btnElement.dataset.speaking = "false";
                    btnElement.innerHTML = '<i class="fa-solid fa-volume-high"></i> Speak';
                }
                this.speakWithServerTTS(cleanText, btnElement);
            };

            this.speechSynth.speak(utterance);
        };

        speakNextChunk();
    }

    /* --- Name Customization --- */
    loadUserName() {
        const hour = new Date().getHours();
        const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
        if (this.userName !== 'User') {
            this.elements.welcomeGreeting.innerHTML = `${greeting}, <span class="void-accent">${this.userName}</span>.`;
            this.elements.namePrompt.classList.add('hidden');
            this.elements.userAvatar.textContent = this.userName.charAt(0).toUpperCase();
        } else {
            this.elements.welcomeGreeting.innerHTML = `Good to see you, <span class="void-accent">User</span>.`;
            this.elements.namePrompt.classList.remove('hidden');
        }
    }

    setUserName() {
        const name = this.elements.userNameInput.value.trim();
        if (name) {
            this.userName = name;
            localStorage.setItem('void_user_name', name);
            this.loadUserName();
        } else {
            this.elements.userNameInput.focus();
        }
    }

    /* --- Core Logic --- */

    async sendMessage() {
        const text = this.elements.input.value.trim();
        if ((!text && this.uploadedFiles.length === 0) || this.isGenerating) return;

        // Barge-in: Stop any ongoing speech playback
        this.stopSpeech();

        // UI Updates
        this.elements.welcome.style.display = 'none';
        this.elements.input.value = '';
        this.elements.input.style.height = 'auto';
        this.elements.filePreview.innerHTML = '';
        
        // Add User Message
        this.appendMessage('user', text, this.uploadedFiles);
        
        // Prepare Payload
        const fileData = this.uploadedFiles.map(f => ({ name: f.name, size: f.size }));
        this.uploadedFiles = []; // Clear queue

        // Save to History
        this.saveToHistory('user', text);

        // API Call
        this.isGenerating = true;
        this.elements.thinking.classList.remove('hidden');
        this.scrollToBottom();

        try {
            const geminiKey = localStorage.getItem('void_gemini_api_key') || '';
            const payload = { 
                message: text, 
                files: fileData,
                settings: this.settings,
                thinking_mode: this.thinkingMode,
                force_search: this.forceSearch,
                gemini_api_key: geminiKey
            };

            let response = null;
            let isDirectGemini = false;

            try {
                response = await fetch("/api/chat/stream", {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "x-gemini-api-key": geminiKey
                    },
                    body: JSON.stringify(payload)
                });
            } catch (netErr) {
                console.warn("/api/chat/stream network fetch error:", netErr);
            }

            // Client-side fallback if server endpoint is 404 or down and Gemini key is configured
            if ((!response || !response.ok) && geminiKey) {
                try {
                    const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?alt=sse&key=${encodeURIComponent(geminiKey.trim())}`;
                    const geminiRes = await fetch(geminiUrl, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            systemInstruction: { parts: [{ text: "You are V.O.I.D. (Versatile Omnipresent Intelligent Device), an ultra-advanced cybernetic AI companion and autonomous assistant. Answer concisely and articulately with a sleek dark aesthetic." }] },
                            contents: [{ role: "user", parts: [{ text: text }] }],
                            generationConfig: {
                                temperature: this.settings.temperature || 0.7,
                                maxOutputTokens: this.settings.maxTokens || 1024
                            }
                        })
                    });
                    if (geminiRes.ok) {
                        response = geminiRes;
                        isDirectGemini = true;
                    }
                } catch (gemErr) {
                    console.warn("Direct Gemini client fallback error:", gemErr);
                }
            }

            if (!response || !response.ok) {
                throw new Error(response ? `Server returned HTTP ${response.status}` : 'Unable to connect to local or cloud V.O.I.D. core');
            }

            this.elements.thinking.classList.add('hidden');
            const { row, contentDiv, toolBadge, speakBtn } = this.appendStreamingMessage();

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedText = "";
            let buffer = "";
            let streamDoneReceived = false;
            const processBlock = (block) => {
                const lines = block.split(/\r?\n/);
                for (const rawLine of lines) {
                    const line = rawLine.trim();
                    if (!line.startsWith("data:")) continue;
                    const jsonStr = line.replace(/^data:\s*/, '').trim();
                    if (!jsonStr || jsonStr === '[DONE]') continue;

                    try {
                        const evt = JSON.parse(jsonStr);

                        if (isDirectGemini) {
                            const partText = evt.candidates?.[0]?.content?.parts?.[0]?.text;
                            if (partText) {
                                accumulatedText += partText;
                                contentDiv.innerHTML = this.formatText(accumulatedText) + ' <span class="cursor-blink"></span>';
                                this.detectAndRenderArtifacts(accumulatedText);
                                this.attachCopyListeners(row);
                                this.attachSpeakListeners(row, accumulatedText);
                                this.scrollToBottom();
                            }
                            if (evt.candidates?.[0]?.finishReason) {
                                streamDoneReceived = true;
                                this.isGenerating = false;
                                contentDiv.innerHTML = this.formatText(accumulatedText);
                                this.detectAndRenderArtifacts(accumulatedText);
                                this.saveToHistory('void', accumulatedText);
                                this.attachCopyListeners(row);
                                this.attachSpeakListeners(row, accumulatedText);
                                this.scrollToBottom();
                                if (this.autoSpeak) {
                                    this.speakText(accumulatedText, speakBtn);
                                }
                            }
                            continue;
                        }

                        if (evt.type === 'tool_call') {
                            toolBadge.innerHTML += `<div class="tool-badge-card"><span class="tool-badge-icon">${evt.icon || '⚡'}</span> <span>Executed <strong>${evt.name || evt.tool}</strong></span></div>`;
                            toolBadge.style.display = 'block';
                        } else if (evt.token !== undefined) {
                            accumulatedText += evt.token;
                            contentDiv.innerHTML = this.formatText(accumulatedText) + ' <span class="cursor-blink"></span>';
                            this.detectAndRenderArtifacts(accumulatedText);
                            this.attachCopyListeners(row);
                            this.attachSpeakListeners(row, accumulatedText);
                            this.scrollToBottom();
                        } else if (evt.replace_all !== undefined) {
                            accumulatedText = evt.replace_all;
                            contentDiv.innerHTML = this.formatText(accumulatedText) + ' <span class="cursor-blink"></span>';
                            this.detectAndRenderArtifacts(accumulatedText);
                            this.attachCopyListeners(row);
                            this.attachSpeakListeners(row, accumulatedText);
                            this.scrollToBottom();
                        } else if (evt.error) {
                            accumulatedText += (accumulatedText ? "\n\n" : "") + `⚠️ **Error**: ${evt.error}`;
                            contentDiv.innerHTML = this.formatText(accumulatedText);
                            this.scrollToBottom();
                        }

                        if (evt.done) {
                            streamDoneReceived = true;
                            this.isGenerating = false;
                            contentDiv.innerHTML = this.formatText(accumulatedText);
                            this.detectAndRenderArtifacts(accumulatedText);
                            this.saveToHistory('void', accumulatedText);
                            this.attachCopyListeners(row);
                            this.attachSpeakListeners(row, accumulatedText);
                            this.scrollToBottom();
                            if (this.autoSpeak) {
                                this.speakText(accumulatedText, speakBtn);
                            }
                        }
                    } catch (e) {
                        console.error("SSE JSON Parse Error:", e, jsonStr);
                    }
                }
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split(/\r?\n\r?\n/);
                buffer = parts.pop() || "";

                for (const part of parts) {
                    processBlock(part);
                }
            }

            if (buffer.trim()) {
                processBlock(buffer);
            }

            if (!streamDoneReceived && accumulatedText) {
                contentDiv.innerHTML = this.formatText(accumulatedText);
                this.detectAndRenderArtifacts(accumulatedText);
                this.saveToHistory('void', accumulatedText);
                this.attachCopyListeners(row);
                this.attachSpeakListeners(row, accumulatedText);
                this.scrollToBottom();
            }

            this.isGenerating = false;

        } catch (error) {
            console.error("Streaming error:", error);
            this.elements.thinking.classList.add('hidden');
            this.appendMessage('void', `**System Notice**: Stream disconnected or encountered an error (${error.message}).`);
            this.isGenerating = false;
        }
    }

    appendStreamingMessage() {
        const row = document.createElement('div');
        row.className = 'message-row void-msg';
        row.innerHTML = `
            <div class="avatar-void"><img src="/static/void-symbol.svg" alt="V.O.I.D." class="void-avatar-icon"></div>
            <div class="message-content">
                <div class="tool-badge-container" style="display:none;"></div>
                <div class="text-body"><span class="cursor-blink"></span></div>
                <div class="msg-actions" style="margin-top:8px;">
                    <button class="speak-msg-btn" title="Speak Response"><i class="fa-solid fa-volume-high"></i> Speak</button>
                </div>
            </div>
        `;
        this.elements.chatBox.appendChild(row);
        this.scrollToBottom();

        return {
            row: row,
            contentDiv: row.querySelector('.text-body'),
            toolBadge: row.querySelector('.tool-badge-container'),
            speakBtn: row.querySelector('.speak-msg-btn')
        };
    }

    appendMessage(sender, text, files = []) {
        const row = document.createElement('div');
        row.className = `message-row ${sender}-msg`;
        
        let fileHtml = '';
        if(files.length > 0) {
            fileHtml = `<div style="font-size:0.8em; color:#888; margin-bottom:5px;">
                <i class="fa-solid fa-paperclip"></i> Attached: ${files.map(f => f.name).join(', ')}
            </div>`;
        }

        let formattedText = this.formatText(text);

        const avatar = sender === 'void' 
            ? `<div class="avatar-void"><img src="/static/void-symbol.svg" alt="V.O.I.D." class="void-avatar-icon"></div>` 
            : ``;

        const speakAction = sender === 'void'
            ? `<div class="msg-actions" style="margin-top:8px;"><button class="speak-msg-btn" title="Speak Response"><i class="fa-solid fa-volume-high"></i> Speak</button></div>`
            : ``;

        row.innerHTML = `
            ${sender === 'void' ? avatar : ''}
            <div class="message-content">
                ${fileHtml}
                <div>${formattedText}</div>
                ${speakAction}
            </div>
        `;

        this.elements.chatBox.appendChild(row);
        this.scrollToBottom();
        
        if (sender === 'void') {
            this.attachCopyListeners(row);
            this.attachSpeakListeners(row, text);
        }
    }

    attachSpeakListeners(element, text) {
        element.querySelectorAll('.speak-msg-btn').forEach(button => {
            button.onclick = (e) => {
                this.speakText(text, button);
            };
        });
    }

    // NEW FUNCTION: Code Block Copy Logic
    attachCopyListeners(element) {
        element.querySelectorAll('.copy-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                // Get the text content of the preceding code element
                const codeElement = e.target.previousElementSibling;
                if (codeElement) {
                    const codeText = codeElement.textContent;
                    // Use a temporary textarea to decode HTML entities if necessary
                    const tempTextArea = document.createElement('textarea');
                    tempTextArea.innerHTML = codeText;
                    
                    navigator.clipboard.writeText(tempTextArea.value.trim()).then(() => {
                        // Simple feedback
                        const originalText = button.innerHTML;
                        button.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                        setTimeout(() => {
                            button.innerHTML = originalText;
                        }, 2000);
                    }).catch(err => {
                        console.error('Could not copy text: ', err);
                    });
                }
            });
        });
    }

    formatText(text) {
        if (!text) return "";

        // Claude Reasoning Accordions: <thinking> ... </thinking>
        let safe = text.replace(/<thinking>([\s\S]*?)<\/thinking>/gi, (m, thought) => {
            return `<details class="claude-thought-accordion" open><summary><i class="fa-solid fa-brain"></i> Thinking Process</summary><div class="thought-body">${thought.trim()}</div></details>`;
        });

        // Safe HTML escaping for remaining content
        safe = safe.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        
        // Restore details tags
        safe = safe.replace(/&lt;details class="claude-thought-accordion" open&gt;&lt;summary&gt;&lt;i class="fa-solid fa-brain"&gt;&lt;\/i&gt; Thinking Process&lt;\/summary&gt;&lt;div class="thought-body"&gt;/g, '<details class="claude-thought-accordion" open><summary><i class="fa-solid fa-brain"></i> Thinking Process</summary><div class="thought-body">')
                   .replace(/&lt;\/div&gt;&lt;\/details&gt;/g, '</div></details>');

        // Code Blocks with Copy Button
        safe = safe.replace(/```(\w+)?\n?([\s\S]*?)```/g, (match, lang, codeContent) => {
            const escapedCode = codeContent.trim();
            const langLabel = lang ? lang.toUpperCase() : 'CODE';
            return `<div class="code-block-wrapper"><div class="code-block-header"><span>${langLabel}</span><button class="copy-btn"><i class="fa-solid fa-copy"></i> Copy</button></div><pre><code>${escapedCode}</code></pre></div>`;
        });
        
        // Inline Code
        safe = safe.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Bold
        safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Markdown Links: [text](url)
        safe = safe.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="chat-link">$1</a>');

        // Raw URLs: (https://...) not already in href
        safe = safe.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer" class="chat-link">$2</a>');

        // Newlines
        safe = safe.replace(/\n/g, '<br>');
        
        return safe;
    }


    scrollToBottom() {
        this.elements.chatBox.parentElement.scrollTop = this.elements.chatBox.parentElement.scrollHeight;
    }

    /* --- History Management --- */
    saveToHistory(sender, text) {
        if (!this.chats[this.currentSessionId]) {
            // NEW: Trim the title properly (original was messy)
            const titleText = text.length > 30 ? text.substring(0, 30).trim() + "..." : text;
            this.chats[this.currentSessionId] = {
                title: titleText,
                timestamp: Date.now(),
                messages: []
            };
            this.renderHistory();
        }
        this.chats[this.currentSessionId].messages.push({ sender, text });
        localStorage.setItem('void_chats', JSON.stringify(this.chats));
    }
    
    // ... (renderHistory, loadSession, newSession, clearAllData, exportChat remain similar) ...

    /* --- Settings Management --- */
    loadSettings() {
        if (this.elements.tempRange) {
            this.elements.tempRange.value = this.settings.temperature;
            this.elements.tempValue.textContent = this.settings.temperature.toFixed(1);
        }
        if (this.elements.tokensRange) {
            this.elements.tokensRange.value = this.settings.maxTokens;
            this.elements.tokensValue.textContent = this.settings.maxTokens;
        }
        if (this.elements.voiceEngineSelect) {
            this.elements.voiceEngineSelect.value = this.voiceEngine;
        }
        if (this.elements.voiceSelectGroup) {
            this.elements.voiceSelectGroup.style.display = this.voiceEngine === 'server' ? 'none' : 'block';
        }
        if (this.elements.autoSpeakCheckbox) {
            this.elements.autoSpeakCheckbox.checked = this.autoSpeak;
        }
        if (this.elements.voiceRate) {
            this.elements.voiceRate.value = this.speechRate;
            if (this.elements.voiceRateVal) this.elements.voiceRateVal.textContent = this.speechRate.toFixed(1) + 'x';
        }
        const geminiInput = document.getElementById('gemini-api-key-input');
        if (geminiInput) {
            geminiInput.value = localStorage.getItem('void_gemini_api_key') || '';
        }
    }

    updateSettings(key, value) {
        this.settings[key] = value;
        if (key === 'temperature') {
            if (this.elements.tempValue) this.elements.tempValue.textContent = value.toFixed(1);
        } else if (key === 'maxTokens') {
            if (this.elements.tokensValue) this.elements.tokensValue.textContent = value + ' tokens';
        }
        localStorage.setItem('void_settings', JSON.stringify(this.settings));
    }


    openSettingsModal() {
        this.elements.settingsModal.classList.remove('hidden');
        this.loadSettings(); // Reload settings in case they were changed in another tab
    }

    closeSettingsModal() {
        const geminiInput = document.getElementById('gemini-api-key-input');
        if (geminiInput) {
            localStorage.setItem('void_gemini_api_key', geminiInput.value.trim());
        }
        this.elements.settingsModal.classList.add('hidden');
    }
    
    // Original methods that remain the same:

    handleFiles(fileList) {
        if (!fileList.length) return;
        
        Array.from(fileList).forEach(file => {
            this.uploadedFiles.push(file);
            const tag = document.createElement('div');
            tag.className = 'file-tag';
            tag.innerHTML = `<i class="fa-solid fa-file"></i> ${file.name} <i class="fa-solid fa-times" onclick="ChatApp.removeFile('${file.name}')"></i>`;
            this.elements.filePreview.appendChild(tag);
        });
        
        this.elements.fileInput.value = '';
    }

    removeFile(fileName) {
        this.uploadedFiles = this.uploadedFiles.filter(f => f.name !== fileName);
        this.elements.filePreview.innerHTML = '';
        this.uploadedFiles.forEach(file => {
            const tag = document.createElement('div');
            tag.className = 'file-tag';
            tag.innerHTML = `<i class="fa-solid fa-file"></i> ${file.name} <i class="fa-solid fa-times" onclick="ChatApp.removeFile('${file.name}')"></i>`;
            this.elements.filePreview.appendChild(tag);
        });
    }

    renderHistory() {
        this.elements.historyList.innerHTML = '';
        const sortedIds = Object.keys(this.chats).sort((a,b) => b - a); // Newest first

        sortedIds.forEach(id => {
            const chat = this.chats[id];
            const item = document.createElement('div');
            item.className = 'history-item';
            if (id == this.currentSessionId) item.classList.add('active');

            const titleSpan = document.createElement('span');
            titleSpan.className = 'history-item-title';
            titleSpan.textContent = chat.title || 'Conversation';

            const leftContent = document.createElement('div');
            leftContent.className = 'history-item-left';
            leftContent.innerHTML = '<i class="fa-regular fa-message"></i> ';
            leftContent.appendChild(titleSpan);

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'history-delete-btn';
            deleteBtn.title = 'Delete conversation';
            deleteBtn.innerHTML = '<i class="fa-solid fa-trash-can"></i>';
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                this.deleteSession(id);
            };

            item.appendChild(leftContent);
            item.appendChild(deleteBtn);
            item.onclick = () => this.loadSession(id);
            this.elements.historyList.appendChild(item);
        });
    }

    deleteSession(id) {
        if (!this.chats[id]) return;
        delete this.chats[id];
        localStorage.setItem('void_chats', JSON.stringify(this.chats));

        // Sync deletion with backend
        fetch(`/api/history?id=${encodeURIComponent(id)}`, { method: 'DELETE' }).catch(() => {});

        if (this.currentSessionId == id) {
            const remainingIds = Object.keys(this.chats).sort((a, b) => b - a);
            if (remainingIds.length > 0) {
                this.loadSession(remainingIds[0]);
            } else {
                this.newSession();
            }
        } else {
            this.renderHistory();
        }
    }

    openSidebar() {
        if (this.elements.sidebar) this.elements.sidebar.classList.add('open');
        if (this.elements.sidebarOverlay) this.elements.sidebarOverlay.classList.remove('hidden');
    }

    closeSidebar() {
        if (this.elements.sidebar) this.elements.sidebar.classList.remove('open');
        if (this.elements.sidebarOverlay) this.elements.sidebarOverlay.classList.add('hidden');
    }

    /* --- V.O.I.D. Attachment Plus Button & Action Menu Methods --- */
    toggleAttachmentMenu() {
        if (!this.elements.attachmentMenu) return;
        const isHidden = this.elements.attachmentMenu.classList.contains('hidden');
        if (isHidden) {
            this.openAttachmentMenu();
        } else {
            this.closeAttachmentMenu();
        }
    }

    openAttachmentMenu() {
        if (!this.elements.attachmentMenu) return;
        this.elements.attachmentMenu.classList.remove('hidden');
        if (this.elements.attachmentMenuBackdrop) {
            this.elements.attachmentMenuBackdrop.classList.remove('hidden');
        }
        if (this.elements.attachmentPlusBtn) {
            this.elements.attachmentPlusBtn.classList.add('active');
            this.elements.attachmentPlusBtn.setAttribute('aria-expanded', 'true');
        }
    }

    closeAttachmentMenu() {
        if (!this.elements.attachmentMenu) return;
        this.elements.attachmentMenu.classList.add('hidden');
        if (this.elements.attachmentMenuBackdrop) {
            this.elements.attachmentMenuBackdrop.classList.add('hidden');
        }
        if (this.elements.attachmentPlusBtn) {
            this.elements.attachmentPlusBtn.classList.remove('active');
            this.elements.attachmentPlusBtn.setAttribute('aria-expanded', 'false');
        }
    }

    handleMenuAction(action) {
        this.closeAttachmentMenu();
        switch (action) {
            case 'vision':
                if (this.elements.visionUploadInput) {
                    this.elements.visionUploadInput.click();
                } else if (this.elements.fileInput) {
                    this.elements.fileInput.click();
                }
                break;
            case 'files':
                if (this.elements.fileInput) {
                    this.elements.fileInput.click();
                }
                break;
            case 'generate':
                if (typeof this.openImageStudio === 'function') {
                    this.openImageStudio();
                } else if (this.elements.input) {
                    this.elements.input.value = '/imagine ';
                    this.elements.input.focus();
                }
                break;
            case 'memory':
                if (typeof this.openMemoryInspector === 'function') {
                    this.openMemoryInspector();
                }
                break;
            case 'think':
                if (this.elements.thinkingToggleBtn) {
                    this.elements.thinkingToggleBtn.click();
                } else {
                    this.forceThinking = !this.forceThinking;
                }
                break;
            case 'search':
                if (this.elements.searchToggleBtn) {
                    this.elements.searchToggleBtn.click();
                } else {
                    this.forceSearch = !this.forceSearch;
                    this.elements.searchToggleBtn?.classList.toggle('search-active', this.forceSearch);
                }
                break;
            default:
                break;
        }
    }

    loadSession(id) {
        this.currentSessionId = id;
        this.elements.chatBox.innerHTML = '';
        this.elements.welcome.style.display = 'none';
        
        const messages = this.chats[id].messages;
        messages.forEach(msg => this.appendMessage(msg.sender, msg.text));
        
        this.renderHistory();
        this.closeSidebar();
    }

    newSession() {
        this.currentSessionId = Date.now();
        this.elements.chatBox.innerHTML = '';
        this.elements.welcome.style.display = 'flex';
        this.loadUserName(); // Reset welcome screen state
        this.renderHistory();
        this.closeSidebar();
    }

    clearAllData() {
        if(confirm("Are you sure? This will delete all local memories.")) {
            localStorage.removeItem('void_chats');
            this.chats = {};
            this.newSession();
        }
    }
    
    exportChat() {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.chats));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", "void_memory_dump.json");
        document.body.appendChild(downloadAnchorNode);
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    }

    /* --- Theme --- */
    toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        this.applyTheme(this.theme);
        localStorage.setItem('void_theme', this.theme);
    }

    applyTheme(themeName) {
        document.body.setAttribute('data-theme', themeName);
        document.body.className = themeName === 'dark' ? 'theme-dark' : 'theme-light';
        const icon = document.getElementById('theme-icon');
        if(themeName === 'light') {
            icon.className = 'fa-solid fa-moon';
        } else {
            icon.className = 'fa-solid fa-sun';
        }
    }

    /* --- Settings Modal --- */
    loadSettings() {
        if (this.elements.tempRange) {
            this.elements.tempRange.value = this.settings.temperature;
            if (this.elements.tempValue) this.elements.tempValue.textContent = this.settings.temperature;
        }
        if (this.elements.tokensRange) {
            this.elements.tokensRange.value = this.settings.maxTokens;
            if (this.elements.tokensValue) this.elements.tokensValue.textContent = `${this.settings.maxTokens} tokens`;
        }
        if (this.elements.autoSpeakCheckbox) {
            this.elements.autoSpeakCheckbox.checked = this.autoSpeak;
        }
        if (this.elements.voiceEngineSelect) {
            this.elements.voiceEngineSelect.value = this.voiceEngine;
        }
    }

    updateSettings(key, value) {
        this.settings[key] = value;
        localStorage.setItem('void_settings', JSON.stringify(this.settings));
        if (key === 'temperature' && this.elements.tempValue) {
            this.elements.tempValue.textContent = value;
        } else if (key === 'maxTokens' && this.elements.tokensValue) {
            this.elements.tokensValue.textContent = `${value} tokens`;
        }
    }

    openSettingsModal() {
        if (this.elements.settingsModal) {
            this.elements.settingsModal.classList.remove('hidden');
            this.loadSettings();
        }
    }

    closeSettingsModal() {
        if (this.elements.settingsModal) {
            this.elements.settingsModal.classList.add('hidden');
        }
    }
    
    quickPrompt(text) {
        this.elements.input.value = text;
        this.elements.input.focus();
    }

    /* --- Voice Recording --- */
    checkVoiceAvailability() {
        // Check if browser supports Web Audio API and MediaRecorder
        const audioContext = window.AudioContext || window.webkitAudioContext;
        const hasGetUserMedia = navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
        const hasMediaRecorder = !!window.MediaRecorder;
        
        this.voiceAvailable = !!(audioContext && hasGetUserMedia && hasMediaRecorder);
        
        console.log('🎤 Voice Availability Check:', {
            audioContext: !!audioContext,
            getUserMedia: !!hasGetUserMedia,
            mediaRecorder: !!hasMediaRecorder,
            voiceAvailable: this.voiceAvailable
        });
        
        if (!this.voiceAvailable) {
            this.elements.voiceBtn.disabled = true;
            this.elements.voiceBtn.title = 'Voice recording not supported in your browser';
            this.elements.voiceBtn.style.opacity = '0.5';
            console.warn('⚠️ Voice not available - missing:', {
                audioContext: !audioContext,
                getUserMedia: !hasGetUserMedia,
                mediaRecorder: !hasMediaRecorder
            });
        } else {
            console.log('✅ Voice recording is available');
        }

        // Check server-side voice availability
        fetch('/api/voice/status')
            .then(r => r.json())
            .then(data => {
                console.log('🔌 Server voice status:', data);
                if (!data.voice_available) {
                    console.warn('⚠️ Server voice module not available');
                    this.elements.voiceBtn.disabled = true;
                    this.elements.voiceBtn.title = 'Voice module not available on server';
                    this.elements.voiceBtn.style.opacity = '0.5';
                }
            })
            .catch(e => console.warn('Could not check voice availability:', e));
    }

    toggleVoiceRecording() {
        if (!this.voiceAvailable) {
            alert('Voice recording is not available. Please check your browser permissions.');
            return;
        }

        if (this.isRecording) {
            this.stopVoiceRecording();
        } else {
            this.startVoiceRecording();
        }
    }

    startVoiceRecording() {
        console.log('🎤 Starting voice recording...');
        // Barge-in: Stop any ongoing speech playback
        this.stopSpeech();
        this.audioChunks = [];
        
        // Try multiple constraint options to find what works
        const constraintOptions = [
            // Most permissive
            { audio: true },
            // With specific settings
            { audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } },
            // With optimization
            { audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } },
            // Specific device request (try first microphone)
            { audio: { deviceId: 'default' } }
        ];

        const tryNextConstraint = (index) => {
            if (index >= constraintOptions.length) {
                console.error('❌ All constraint options failed');
                alert('Unable to access microphone after trying all options. Check Windows Privacy Settings.');
                this.elements.voiceBtn.classList.remove('recording');
                this.elements.voiceStatus.style.display = 'none';
                return;
            }

            const constraints = constraintOptions[index];
            console.log(`🔍 Attempt ${index + 1}:`, constraints);

            navigator.mediaDevices.getUserMedia(constraints)
                .then(stream => {
                    console.log('✅ Microphone access granted with constraints:', constraints);
                    console.log('Audio tracks:', stream.getAudioTracks());
                    
                    this.mediaRecorder = new MediaRecorder(stream);
                    console.log('MediaRecorder created:', this.mediaRecorder);
                    
                    this.mediaRecorder.ondataavailable = (event) => {
                        console.log('📦 Audio data chunk received:', event.data.size, 'bytes');
                        this.audioChunks.push(event.data);
                    };
                    
                    this.mediaRecorder.onerror = (event) => {
                        console.error('❌ MediaRecorder error:', event.error);
                        alert('Recording error: ' + event.error);
                    };
                    
                    this.mediaRecorder.onstop = () => {
                        console.log('⏹️ Recording stopped, total chunks:', this.audioChunks.length);
                        this.processAudioRecording();
                    };
                    
                    this.mediaRecorder.start();
                    console.log('▶️ Recording started');
                    
                    this.isRecording = true;
                    this.elements.voiceBtn.classList.add('recording');
                    this.elements.voiceStatus.style.display = 'block';
                    this.elements.voiceStatusText.textContent = '🎤 Recording... (click to stop)';
                })
                .catch(error => {
                    console.warn(`❌ Attempt ${index + 1} failed:`, error.name, error.message);
                    tryNextConstraint(index + 1);
                });
        };

        tryNextConstraint(0);
    }

    stopVoiceRecording() {
        if (this.mediaRecorder && this.isRecording) {
            console.log('⏹️ Stopping recording...');
            this.mediaRecorder.stop();
            
            // Stop all audio tracks
            const stream = this.mediaRecorder.stream;
            if (stream) {
                stream.getTracks().forEach(track => {
                    console.log('🔇 Stopping track:', track.kind, track.readyState);
                    track.stop();
                });
            }
            
            this.isRecording = false;
            this.elements.voiceBtn.classList.remove('recording');
            this.elements.voiceStatusText.textContent = '⏳ Processing audio...';
        }
    }

    processAudioRecording() {
        console.log('📊 Processing audio recording...');
        
        if (this.audioChunks.length === 0) {
            console.error('❌ No audio chunks recorded');
            alert('No audio was recorded. Please try again.');
            this.elements.voiceStatus.style.display = 'none';
            return;
        }

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        console.log('🎵 Audio blob created:', {
            size: audioBlob.size,
            type: audioBlob.type,
            chunks: this.audioChunks.length
        });

        if (audioBlob.size === 0) {
            console.error('❌ Audio blob is empty');
            alert('Recording was empty. Please try again.');
            this.elements.voiceStatus.style.display = 'none';
            return;
        }

        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');

        // Show thinking indicator
        this.elements.thinking.classList.remove('hidden');
        this.elements.voiceStatusText.textContent = '🧠 Transcribing...';
        console.log('📤 Sending audio to server...');

        fetch('/api/voice/chat', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log('📥 Response received:', response.status, response.statusText);
            return response.json();
        })
        .then(data => {
            console.log('✅ Voice chat response:', data);
            this.elements.voiceStatus.style.display = 'none';
            this.elements.thinking.classList.add('hidden');

            if (data.status === 'error') {
                console.error('❌ Server error:', data.error);
                alert('Voice chat error: ' + data.error);
                return;
            }

            // Add user message (transcribed)
            this.appendMessage('user', data.transcribed_text);
            this.saveToHistory('user', data.transcribed_text);
            
            // Add response
            this.appendMessage('void', data.response_text);
            this.saveToHistory('void', data.response_text);

            // Play audio response through web
            this.playAudioResponse(data.audio_available, data.response_text);
        })
        .catch(error => {
            console.error('❌ Voice chat network error:', error);
            this.elements.voiceStatus.style.display = 'none';
            this.elements.thinking.classList.add('hidden');
            alert('Network error processing voice: ' + error.message);
        });
    }

    playAudioResponse(audioAvailable, responseText) {
        if (!responseText) return;
        console.log('🔊 Speaking model response through web audio...');
        this.speakText(responseText);
    }

    /* --- Claude Canvas / Artifacts Implementation --- */
    detectAndRenderArtifacts(text) {
        if (!text) return;
        // Detect HTML, SVG, React, JavaScript, CSS or interactive blocks
        const htmlMatch = text.match(/```(?:html|svg|xml)\n?([\s\S]*?)```/i);
        const codeMatch = text.match(/```(\w+)?\n?([\s\S]*?)```/);

        if (htmlMatch && htmlMatch[1].trim()) {
            const rawCode = htmlMatch[1].trim();
            const isSvg = rawCode.startsWith('<svg');
            const title = isSvg ? "Vector Graphic" : "Interactive Web Artifact";
            this.openArtifactPanel(title, rawCode, isSvg ? "svg" : "html");
        } else if (codeMatch && codeMatch[2] && codeMatch[2].trim().length > 120 && this.elements.artifactsPanel && !this.elements.artifactsPanel.classList.contains('hidden')) {
            const lang = (codeMatch[1] || 'code').toUpperCase();
            this.openArtifactPanel(`${lang} Artifact`, codeMatch[2].trim(), lang.toLowerCase());
        }
    }

    openArtifactPanel(title, code, type = "html") {
        if (!this.elements.artifactsPanel) return;
        this.currentArtifact = { title, code, type };

        if (this.elements.artifactTitleText) {
            this.elements.artifactTitleText.textContent = title;
        }

        if (this.elements.artifactCodeElement) {
            this.elements.artifactCodeElement.textContent = code;
        }

        if (this.elements.artifactIframe) {
            if (type === "svg") {
                this.elements.artifactIframe.srcdoc = `
                    <!DOCTYPE html>
                    <html>
                    <head><style>body { margin:0; display:flex; align-items:center; justify-content:center; height:100vh; background:#1e1e1e; }</style></head>
                    <body>${code}</body>
                    </html>
                `;
            } else if (type === "html") {
                this.elements.artifactIframe.srcdoc = code;
            }
        }

        this.elements.artifactsPanel.classList.remove('hidden');
        if (this.elements.appContainer) {
            this.elements.appContainer.classList.add('with-artifacts');
        }
    }

    closeArtifactPanel() {
        if (this.elements.artifactsPanel) {
            this.elements.artifactsPanel.classList.add('hidden');
        }
        if (this.elements.appContainer) {
            this.elements.appContainer.classList.remove('with-artifacts');
        }
    }

    switchArtifactTab(tab) {
        if (tab === 'preview') {
            if (this.elements.artifactTabPreview) this.elements.artifactTabPreview.classList.add('active');
            if (this.elements.artifactTabCode) this.elements.artifactTabCode.classList.remove('active');
            if (this.elements.artifactPreviewWrapper) this.elements.artifactPreviewWrapper.classList.remove('hidden');
            if (this.elements.artifactCodeWrapper) this.elements.artifactCodeWrapper.classList.add('hidden');
        } else {
            if (this.elements.artifactTabPreview) this.elements.artifactTabPreview.classList.remove('active');
            if (this.elements.artifactTabCode) this.elements.artifactTabCode.classList.add('active');
            if (this.elements.artifactPreviewWrapper) this.elements.artifactPreviewWrapper.classList.add('hidden');
            if (this.elements.artifactCodeWrapper) this.elements.artifactCodeWrapper.classList.remove('hidden');
        }
    }

    copyArtifactContent() {
        if (!this.currentArtifact || !this.currentArtifact.code) return;
        navigator.clipboard.writeText(this.currentArtifact.code).then(() => {
            alert('Artifact code copied to clipboard!');
        }).catch(err => {
            console.error('Could not copy artifact:', err);
        });
    }

    downloadArtifactFile() {
        if (!this.currentArtifact || !this.currentArtifact.code) return;
        const type = this.currentArtifact.type || 'html';
        const ext = type === 'html' ? 'html' : type === 'svg' ? 'svg' : type === 'python' ? 'py' : type === 'javascript' ? 'js' : 'txt';
        const filename = `void_artifact_${Date.now()}.${ext}`;

        const blob = new Blob([this.currentArtifact.code], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // ==========================================
    // MEMORY ENGINE INSPECTOR METHODS
    // ==========================================

    openMemoryInspector() {
        const modal = document.getElementById('memory-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.currentMemoryTier = 'all';
            this.loadMemories('all');
            this.loadMemoryStats();
        }
    }

    async loadMemoryStats() {
        try {
            const res = await fetch('/api/memory/stats');
            const data = await res.json();
            const totalEl = document.getElementById('stat-total-mem');
            const nodesEl = document.getElementById('stat-graph-nodes');
            const sizeEl = document.getElementById('stat-db-size');
            if (totalEl) totalEl.textContent = data.total_memories || 0;
            if (nodesEl) nodesEl.textContent = data.knowledge_nodes_count || 0;
            if (sizeEl) sizeEl.textContent = data.db_size_kb || 0;
        } catch (e) {
            console.error('Failed to load memory stats:', e);
        }
    }

    async loadMemories(tier = 'all', query = '') {
        const container = document.getElementById('memory-cards-list');
        if (!container) return;
        container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading memories...</div>';

        try {
            let url = '/api/memory?limit=100';
            if (tier && tier !== 'all') {
                if (tier === 'archived') {
                    url += '&status=archived';
                } else {
                    url += `&tier=${encodeURIComponent(tier)}`;
                }
            }
            if (query) {
                url += `&q=${encodeURIComponent(query)}`;
            }

            const res = await fetch(url);
            const data = await res.json();
            this.cachedMemories = data.memories || [];
            this.renderMemoryCards(this.cachedMemories);
        } catch (e) {
            console.error('Error fetching memories:', e);
            container.innerHTML = '<div class="empty-state">Failed to load memories.</div>';
        }
    }

    renderMemoryCards(memories) {
        const container = document.getElementById('memory-cards-list');
        if (!container) return;

        if (!memories || memories.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-brain"></i>
                    <p>No memory records found in this tier.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = memories.map(m => {
            const content = m.content || m.text || '';
            const tier = m.memory_type || m.tier || 'semantic';
            const importance = Math.round((m.importance || 0.5) * 100);
            const isPinned = m.pinned ? 'pinned' : '';
            const dateStr = m.created_at ? new Date(m.created_at * 1000).toLocaleDateString() : 'Active';

            return `
                <div class="memory-card ${isPinned}" data-id="${m.id}">
                    <div class="memory-card-header">
                        <span class="memory-tier-badge tier-${tier}">${tier.toUpperCase()}</span>
                        <div class="memory-importance-meter" title="Importance: ${importance}%">
                            <span class="meter-fill" style="width: ${importance}%"></span>
                            <span class="meter-text">${importance}%</span>
                        </div>
                        <span class="memory-date">${dateStr}</span>
                    </div>
                    <div class="memory-card-body">
                        <p class="memory-text">${this.escapeHtml(content)}</p>
                    </div>
                    <div class="memory-card-footer">
                        <span class="memory-category"><i class="fa-solid fa-tag"></i> ${m.category || 'general'}</span>
                        <div class="memory-card-actions">
                            <button class="action-icon-btn ${m.pinned ? 'active' : ''}" onclick="ChatApp.togglePinMemory('${m.id}', ${!m.pinned})" title="${m.pinned ? 'Unpin' : 'Pin'}">
                                <i class="fa-solid fa-thumbtack"></i>
                            </button>
                            <button class="action-icon-btn" onclick="ChatApp.editMemory('${m.id}', '${this.escapeHtml(content).replace(/'/g, "\\'")}')" title="Edit">
                                <i class="fa-solid fa-pen-to-square"></i>
                            </button>
                            <button class="action-icon-btn danger" onclick="ChatApp.deleteMemory('${m.id}')" title="Delete">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    filterMemories() {
        const input = document.getElementById('memory-search-input');
        const query = input ? input.value.trim() : '';
        this.loadMemories(this.currentMemoryTier, query);
    }

    switchMemoryTier(tier) {
        this.currentMemoryTier = tier;
        document.querySelectorAll('.tier-tab').forEach(t => {
            if (t.getAttribute('data-tier') === tier) {
                t.classList.add('active');
            } else {
                t.classList.remove('active');
            }
        });
        const input = document.getElementById('memory-search-input');
        const query = input ? input.value.trim() : '';
        this.loadMemories(tier, query);
    }

    async consolidateMemory() {
        try {
            const btn = document.querySelector('.memory-action-buttons button');
            if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Consolidating...';
            const res = await fetch('/api/memory/consolidate', { method: 'POST' });
            const data = await res.json();
            alert(`⚡ Consolidation pass completed!\n- Merged duplicates: ${data.duplicates_merged || 0}\n- Contradictions resolved: ${data.contradictions_resolved || 0}`);
            this.loadMemories(this.currentMemoryTier);
            this.loadMemoryStats();
            if (btn) btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Consolidate';
        } catch (e) {
            console.error('Consolidation failed:', e);
            alert('Failed to execute consolidation pass.');
        }
    }

    async exportMemoryData() {
        try {
            const res = await fetch('/api/memory/export');
            const data = await res.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `void_memory_backup_${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Export failed:', e);
            alert('Failed to export memory backup.');
        }
    }

    async showAddMemoryPrompt() {
        const text = prompt('Enter memory content or fact to remember:');
        if (!text || !text.trim()) return;
        try {
            await fetch('/api/memory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: text.trim(), tier: 'semantic', importance: 0.85 })
            });
            this.loadMemories(this.currentMemoryTier);
            this.loadMemoryStats();
        } catch (e) {
            console.error('Failed to add memory:', e);
        }
    }

    async togglePinMemory(id, newPinned) {
        try {
            await fetch('/api/memory', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, pinned: newPinned })
            });
            this.loadMemories(this.currentMemoryTier);
        } catch (e) {
            console.error('Failed to toggle pin:', e);
        }
    }

    async editMemory(id, currentText) {
        const updated = prompt('Edit memory content:', currentText);
        if (updated === null || updated.trim() === '') return;
        try {
            await fetch('/api/memory', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, content: updated.trim() })
            });
            this.loadMemories(this.currentMemoryTier);
        } catch (e) {
            console.error('Failed to update memory:', e);
        }
    }

    async deleteMemory(id) {
        if (!confirm('Are you sure you want to delete this memory record?')) return;
        try {
            await fetch('/api/memory', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            });
            this.loadMemories(this.currentMemoryTier);
            this.loadMemoryStats();
        } catch (e) {
            console.error('Failed to delete memory:', e);
        }
    }

    // ==========================================
    // 🌐 REMOTE DASHBOARD & SYSTEM MONITOR METHODS
    // ==========================================

    openRemoteDashboard() {
        const modal = document.getElementById('remote-dashboard-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.switchRemoteTab('monitor');
            this.fetchLiveSystemStats();
            this.loadTunnelInfo();
            if (!this.monitorInterval) {
                this.monitorInterval = setInterval(() => {
                    const chk = document.getElementById('monitor-auto-refresh');
                    if (chk && chk.checked) {
                        this.fetchLiveSystemStats();
                    }
                }, 2000);
            }
        }
    }

    closeRemoteDashboard() {
        const modal = document.getElementById('remote-dashboard-modal');
        if (modal) modal.classList.add('hidden');
        if (this.monitorInterval) {
            clearInterval(this.monitorInterval);
            this.monitorInterval = null;
        }
    }

    switchRemoteTab(tabId) {
        const tabs = ['monitor', 'tunnel', 'mobile-hud', 'terminal', 'security'];
        tabs.forEach(t => {
            const btn = document.getElementById(`tab-btn-${t}`);
            const panel = document.getElementById(`panel-${t}`);
            if (btn) btn.classList.toggle('active', t === tabId);
            if (panel) panel.classList.toggle('hidden', t !== tabId);
        });

        if (tabId === 'monitor') {
            this.fetchLiveSystemStats();
        } else if (tabId === 'tunnel') {
            this.loadTunnelInfo();
        } else if (tabId === 'mobile-hud') {
            this.loadMobileHUD();
        }
    }

    async loadMobileHUD() {
        try {
            const res = await fetch('/api/phone/telemetry');
            const data = await res.json();
            const pulse = document.getElementById('phone-pulse-dot');
            const statusText = document.getElementById('phone-status-text');

            if (data.status === 'success' && data.success) {
                if (pulse) pulse.style.background = '#10b981';
                if (statusText) statusText.textContent = `Online (${data.serial} • ${data.connection_type.toUpperCase()})`;

                const modelVal = document.getElementById('phone-model-val');
                if (modelVal) modelVal.textContent = `${data.device.manufacturer} ${data.device.model}`;

                const osVal = document.getElementById('phone-os-val');
                if (osVal) osVal.textContent = `${data.device.android_version} • ${data.device.sdk_version}`;

                const connBadge = document.getElementById('phone-conn-badge');
                if (connBadge) connBadge.textContent = data.connection_type.toUpperCase();

                // Battery
                const battPct = data.battery.level !== null ? `${data.battery.level}%` : '--%';
                const battVal = document.getElementById('phone-batt-val');
                if (battVal) battVal.textContent = battPct;
                const battBadge = document.getElementById('phone-batt-pct-badge');
                if (battBadge) battBadge.textContent = battPct;
                const battBar = document.getElementById('phone-batt-bar');
                if (battBar && data.battery.level !== null) battBar.style.width = `${data.battery.level}%`;
                const battStatus = document.getElementById('phone-batt-status-val');
                if (battStatus) battStatus.textContent = `Status: ${data.battery.status} (${data.battery.plugged}) • Temp: ${data.battery.temperature_c ?? '--'}°C`;

                // Display & Foreground App
                const appVal = document.getElementById('phone-app-val');
                if (appVal) appVal.textContent = data.foreground_app.package;
                const screenStateBadge = document.getElementById('phone-screen-state-badge');
                if (screenStateBadge) screenStateBadge.textContent = `Screen: ${data.display.is_screen_on ? 'ON' : 'OFF'}`;
                const resVal = document.getElementById('phone-res-val');
                if (resVal) resVal.textContent = `Resolution: ${data.display.width}x${data.display.height}`;

                // Network
                const ipVal = document.getElementById('phone-ip-val');
                if (ipVal) ipVal.textContent = data.network.ip_address || 'No IP';
                const ssidVal = document.getElementById('phone-ssid-val');
                if (ssidVal) ssidVal.textContent = `WiFi: ${data.network.ssid}`;
            } else {
                if (pulse) pulse.style.background = '#ef4444';
                if (statusText) statusText.textContent = 'Disconnected (No authorized device)';
                const modelVal = document.getElementById('phone-model-val');
                if (modelVal) modelVal.textContent = 'No Device Connected';
            }
        } catch (e) {
            console.error('Error loading mobile telemetry:', e);
        }
    }

    async capturePhoneScreen() {
        const img = document.getElementById('phone-screen-img');
        const placeholder = document.getElementById('phone-screen-placeholder');
        if (placeholder) placeholder.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem;"></i><br>Capturing phone frame...';

        try {
            const res = await fetch('/api/phone/screen?format=base64&max_dim=720');
            const data = await res.json();
            if (data.status === 'success' && data.data_url) {
                if (img) {
                    img.src = data.data_url;
                    img.style.display = 'block';
                }
                if (placeholder) placeholder.style.display = 'none';
            } else {
                if (placeholder) {
                    placeholder.style.display = 'block';
                    placeholder.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color: #ef4444; font-size: 2rem;"></i><br>${data.message || data.error || 'Failed to capture frame'}`;
                }
            }
        } catch (e) {
            if (placeholder) {
                placeholder.style.display = 'block';
                placeholder.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color: #ef4444; font-size: 2rem;"></i><br>Capture error: ${e.message}`;
            }
        }
    }

    async sendPhoneNotification() {
        const titleInput = document.getElementById('phone-notif-title');
        const msgInput = document.getElementById('phone-notif-msg');
        const title = (titleInput && titleInput.value.trim()) || 'V.O.I.D. Alert';
        const message = msgInput ? msgInput.value.trim() : '';

        if (!message) {
            alert('Please enter a notification message.');
            return;
        }

        try {
            const res = await fetch('/api/phone/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, message, priority: 'high' })
            });
            const data = await res.json();
            if (data.status === 'success') {
                if (msgInput) msgInput.value = '';
                const comms = document.getElementById('phone-comms-output');
                if (comms) comms.textContent = `[${new Date().toLocaleTimeString()}] ✅ Pushed notification: "${title}" - "${message}"`;
            } else {
                alert(`Notification failed: ${data.error || data.message}`);
            }
        } catch (e) {
            alert(`Error sending notification: ${e.message}`);
        }
    }

    async sendPhoneToast() {
        const msgInput = document.getElementById('phone-notif-msg');
        const message = msgInput ? msgInput.value.trim() : '';
        if (!message) {
            alert('Please enter a toast message.');
            return;
        }

        try {
            const res = await fetch('/api/phone/toast', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            const data = await res.json();
            if (data.status === 'success') {
                const comms = document.getElementById('phone-comms-output');
                if (comms) comms.textContent = `[${new Date().toLocaleTimeString()}] 💬 Toast displayed on phone display: "${message}"`;
            } else {
                alert(`Toast failed: ${data.error || data.message}`);
            }
        } catch (e) {
            alert(`Error sending toast: ${e.message}`);
        }
    }

    async loadPhoneSMS() {
        const comms = document.getElementById('phone-comms-output');
        if (comms) comms.textContent = 'Querying SMS inbox from Android telephony provider...';

        try {
            const res = await fetch('/api/phone/sms?limit=5');
            const data = await res.json();
            if (data.status === 'success' && data.messages && data.messages.length > 0) {
                const formatted = data.messages.map(m => `📩 [${m.date || 'Unknown'}] From ${m.sender}:\n"${m.body}"`).join('\n\n');
                if (comms) comms.textContent = formatted;
            } else {
                if (comms) comms.textContent = data.error ? `⚠️ ${data.error}` : 'No recent SMS messages found.';
            }
        } catch (e) {
            if (comms) comms.textContent = `Error querying SMS: ${e.message}`;
        }
    }

    async loadPhoneBriefing() {
        const comms = document.getElementById('phone-comms-output');
        if (comms) comms.textContent = 'Generating executive phone briefing...';

        try {
            const res = await fetch('/api/phone/briefing');
            const data = await res.json();
            if (data.status === 'success' && data.briefing) {
                if (comms) comms.textContent = data.briefing;
            } else {
                if (comms) comms.textContent = 'Failed to generate briefing.';
            }
        } catch (e) {
            if (comms) comms.textContent = `Error generating briefing: ${e.message}`;
        }
    }

    toggleMonitorAutoRefresh() {
        const chk = document.getElementById('monitor-auto-refresh');
        if (chk && chk.checked) {
            if (!this.monitorInterval) {
                this.monitorInterval = setInterval(() => this.fetchLiveSystemStats(), 2000);
            }
        } else {
            if (this.monitorInterval) {
                clearInterval(this.monitorInterval);
                this.monitorInterval = null;
            }
        }
    }

    async fetchLiveSystemStats() {
        try {
            const res = await fetch('/api/system/live_stats');
            if (!res.ok) return;
            const data = await res.json();
            if (data.status !== 'success') return;

            // CPU
            const cpu = data.cpu || {};
            const cpuVal = document.getElementById('cpu-usage-val');
            const cpuBar = document.getElementById('cpu-bar');
            const cpuFreq = document.getElementById('cpu-freq-val');
            const cpuCores = document.getElementById('cpu-cores-badge');
            if (cpuVal) cpuVal.textContent = `${cpu.usage_percent || 0}%`;
            if (cpuBar) cpuBar.style.width = `${Math.min(100, cpu.usage_percent || 0)}%`;
            if (cpuFreq) cpuFreq.textContent = `Clock: ${cpu.frequency_mhz || '--'} MHz`;
            if (cpuCores) cpuCores.textContent = `${cpu.logical_cores || 0} Cores`;

            // GPU
            const gpu = data.gpu || {};
            const gpuName = document.getElementById('gpu-name-val');
            const vramBar = document.getElementById('vram-bar');
            const vramUsage = document.getElementById('vram-usage-val');
            const gpuAvail = document.getElementById('gpu-avail-badge');
            if (gpuName) gpuName.textContent = gpu.name || 'CPU Only';
            if (vramBar) vramBar.style.width = `${Math.min(100, gpu.vram_percent || 0)}%`;
            if (vramUsage) vramUsage.textContent = `VRAM: ${gpu.vram_used_gb || 0} / ${gpu.vram_total_gb || 0} GB (${gpu.vram_percent || 0}%)`;
            if (gpuAvail) {
                gpuAvail.textContent = gpu.available ? 'CUDA Active' : 'CPU';
                gpuAvail.style.color = gpu.available ? '#10b981' : 'inherit';
            }

            // RAM
            const ram = data.ram || {};
            const ramUsed = document.getElementById('ram-used-val');
            const ramBar = document.getElementById('ram-bar');
            const ramTotal = document.getElementById('ram-total-val');
            const ramPct = document.getElementById('ram-pct-badge');
            if (ramUsed) ramUsed.textContent = `${ram.used_gb || 0} GB`;
            if (ramBar) ramBar.style.width = `${Math.min(100, ram.percent || 0)}%`;
            if (ramTotal) ramTotal.textContent = `Total: ${ram.total_gb || 0} GB`;
            if (ramPct) ramPct.textContent = `${ram.percent || 0}%`;

            // Storage
            const disk = data.storage || {};
            const diskFree = document.getElementById('disk-free-val');
            const diskBar = document.getElementById('disk-bar');
            const diskTotal = document.getElementById('disk-total-val');
            const diskPct = document.getElementById('disk-pct-badge');
            if (diskFree) diskFree.textContent = `${disk.free_gb || 0} GB Free`;
            if (diskBar) diskBar.style.width = `${Math.min(100, disk.percent || 0)}%`;
            if (diskTotal) diskTotal.textContent = `Used: ${disk.used_gb || 0} / ${disk.total_gb || 0} GB`;
            if (diskPct) diskPct.textContent = `${disk.percent || 0}%`;

            // Temperature & Power
            const temps = data.temperatures || {};
            const tempVal = document.getElementById('temp-val');
            const powerVal = document.getElementById('power-status-val');
            const tempKeys = Object.keys(temps);
            if (tempVal) {
                if (tempKeys.length > 0) {
                    tempVal.textContent = tempKeys.map(k => `${k}: ${temps[k]}°C`).join(' • ');
                } else {
                    tempVal.textContent = "Hardware Nominal";
                }
            }
            if (powerVal) {
                const batt = data.battery || {};
                const battStr = batt.percent !== null ? `Battery: ${batt.percent}%` : `AC Powered`;
                const plugStr = batt.plugged ? ` • Plugged In` : ` • On Battery`;
                powerVal.textContent = battStr + (batt.percent !== null ? plugStr : '');
            }

            // Host & Uptime
            const sys = data.system || {};
            const uptimeVal = document.getElementById('uptime-val');
            const hostOs = document.getElementById('host-os-val');
            if (uptimeVal) uptimeVal.textContent = sys.uptime_formatted || '--';
            if (hostOs) hostOs.textContent = `${sys.os || 'Windows'} • ${sys.hostname || 'Host'}`;

        } catch (e) {
            console.warn('Live stats fetch error:', e);
        }
    }

    async loadTunnelInfo() {
        try {
            const res = await fetch('/api/remote/tunnel_info');
            const data = await res.json();
            const urlInput = document.getElementById('tunnel-primary-url');
            const statusPill = document.getElementById('tunnel-status-pill');

            if (urlInput) urlInput.value = data.primary_url;
            if (statusPill) {
                statusPill.innerHTML = '<i class="fa-solid fa-wifi"></i> Local LAN Active';
                statusPill.style.background = 'rgba(16, 185, 129, 0.15)';
                statusPill.style.color = '#10b981';
            }

            this.renderQRCode(data.primary_url);
        } catch (e) {
            console.warn('Failed to load connection info:', e);
        }
    }

    renderQRCode(url) {
        const box = document.getElementById('qr-code-box');
        if (!box) return;
        const encoded = encodeURIComponent(url);
        box.innerHTML = `<img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encoded}" alt="QR Code" style="width:100%;height:100%;object-fit:contain;" onerror="this.onerror=null;this.parentElement.innerHTML='<div style=\\'display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;text-align:center;font-size:11px;color:#222;\\'><strong>🔗 Direct URL</strong><a href=\\'${url}\\' target=\\'_blank\\' style=\\'word-break:break-all;color:#d97757;margin-top:4px;\\'>${url}</a></div>'">`;
    }

    copyTunnelUrl() {
        const input = document.getElementById('tunnel-primary-url');
        if (input) {
            navigator.clipboard.writeText(input.value).then(() => {
                const btn = document.querySelector('.tunnel-url-group button');
                if (btn) {
                    const orig = btn.innerHTML;
                    btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                    setTimeout(() => { btn.innerHTML = orig; }, 2000);
                }
            });
        }
    }

    // Remote Terminal & Confirmation System
    runTerminalPreset(cmd) {
        const input = document.getElementById('terminal-cmd-input');
        if (input) {
            input.value = cmd;
            this.executeRemoteCommand();
        }
    }

    async executeRemoteCommand(confirmToken = null) {
        const input = document.getElementById('terminal-cmd-input');
        const termBox = document.getElementById('terminal-output');
        const confirmBanner = document.getElementById('cmd-confirm-banner');
        if (!input || !termBox) return;

        const cmd = confirmToken ? this.pendingConfirmCmd : input.value.trim();
        if (!cmd) return;

        if (!confirmToken) {
            input.value = '';
            termBox.innerHTML += `<div class="term-line"><span class="term-prompt">admin@void:~$</span> <span class="term-cmd">${this.escapeHtml(cmd)}</span></div>`;
            termBox.scrollTop = termBox.scrollHeight;
        }

        try {
            const res = await fetch('/api/remote/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd, confirm_token: confirmToken })
            });
            const data = await res.json();

            if (data.status === 'requires_confirmation') {
                this.pendingConfirmToken = data.token;
                this.pendingConfirmCmd = data.command;

                if (confirmBanner) {
                    confirmBanner.classList.remove('hidden');
                    const reasonEl = document.getElementById('confirm-reason-text');
                    const codeEl = document.getElementById('confirm-cmd-text');
                    if (reasonEl) reasonEl.textContent = data.message || data.reason;
                    if (codeEl) codeEl.textContent = data.command;
                }
                termBox.innerHTML += `<div class="term-line term-err">⚠️ [Security Guardian] Command requires explicit user approval before execution.</div>`;
                termBox.scrollTop = termBox.scrollHeight;
                return;
            }

            if (confirmBanner) confirmBanner.classList.add('hidden');

            if (data.status === 'success') {
                if (data.stdout && data.stdout.trim()) {
                    termBox.innerHTML += `<div class="term-line term-out">${this.escapeHtml(data.stdout)}</div>`;
                }
                if (data.stderr && data.stderr.trim()) {
                    termBox.innerHTML += `<div class="term-line term-err">${this.escapeHtml(data.stderr)}</div>`;
                }
                termBox.innerHTML += `<div class="term-line term-success">✔ Process finished (exit code ${data.exit_code}, ${data.duration_ms}ms)</div>`;
            } else {
                termBox.innerHTML += `<div class="term-line term-err">❌ Error: ${this.escapeHtml(data.error || 'Execution failed')}</div>`;
            }
            termBox.scrollTop = termBox.scrollHeight;

        } catch (err) {
            termBox.innerHTML += `<div class="term-line term-err">❌ Network error: ${this.escapeHtml(err.message)}</div>`;
            termBox.scrollTop = termBox.scrollHeight;
        }
    }

    approveRemoteCommand() {
        if (this.pendingConfirmToken) {
            this.executeRemoteCommand(this.pendingConfirmToken);
            this.pendingConfirmToken = null;
        }
    }

    denyRemoteCommand() {
        const confirmBanner = document.getElementById('cmd-confirm-banner');
        if (confirmBanner) confirmBanner.classList.add('hidden');
        if (this.pendingConfirmToken) {
            fetch('/api/remote/confirm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: this.pendingConfirmToken, action: 'deny' })
            }).catch(() => {});
            this.pendingConfirmToken = null;
        }
        const termBox = document.getElementById('terminal-output');
        if (termBox) {
            termBox.innerHTML += `<div class="term-line term-comment">Execution cancelled by user.</div>`;
            termBox.scrollTop = termBox.scrollHeight;
        }
    }

    toggleEmergencyStop() {
        this.emergencyActive = !this.emergencyActive;
        const btn = document.getElementById('remote-emergency-btn');
        if (btn) {
            if (this.emergencyActive) {
                btn.innerHTML = '<i class="fa-solid fa-lock-open"></i> Reset Emergency Lockdown';
                btn.style.background = '#10b981';
                alert('🚨 EMERGENCY LOCKDOWN ACTIVATED! Autonomous tool execution is halted.');
            } else {
                btn.innerHTML = '<i class="fa-solid fa-hand"></i> Trigger Emergency Stop';
                btn.style.background = '#dc2626';
                alert('Lockdown reset. Normal operation resumed.');
            }
        }
    }

    triggerSystemPower(action) {
        if (action === 'shutdown') {
            if (!confirm("Are you sure you want to shut down this computer?\nA 15-second grace timer will start.")) {
                return;
            }
            this.switchRemoteTab('terminal');
            const input = document.getElementById('remote-cmd-input');
            if (input) input.value = 'shutdown /s /t 15 /c "V.O.I.D. Power Down"';
            this.executeRemoteCommand();
        } else if (action === 'restart') {
            if (!confirm("Are you sure you want to restart this computer?\nA 15-second grace timer will start.")) {
                return;
            }
            this.switchRemoteTab('terminal');
            const input = document.getElementById('remote-cmd-input');
            if (input) input.value = 'shutdown /r /t 15 /c "V.O.I.D. Reboot"';
            this.executeRemoteCommand();
        } else if (action === 'abort') {
            this.switchRemoteTab('terminal');
            const input = document.getElementById('remote-cmd-input');
            if (input) input.value = 'shutdown /a';
            this.executeRemoteCommand();
        }
    }

    updatePermissionLevel(level) {
        alert(`Remote Permission Scope updated to Level ${level}.`);
    }

    // ===================================================
    // 🧠 V.O.I.D. INTELLIGENCE HUB & MULTI-AGENT METHODS
    // ===================================================

    openIntelligenceHub() {
        const modal = document.getElementById('intelligence-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.switchIntelTab('tasks');
            this.loadTasks();
            this.loadReflections();
            this.loadCodebaseStructure();
        }
    }

    closeIntelligenceHub() {
        const modal = document.getElementById('intelligence-modal');
        if (modal) modal.classList.add('hidden');
    }

    switchIntelTab(tabId) {
        const tabs = ['tasks', 'pipeline', 'reflections', 'codebase', 'router'];
        tabs.forEach(t => {
            const btn = document.getElementById(`tab-btn-${t}`);
            const panel = document.getElementById(`panel-${t}`);
            if (btn) btn.classList.toggle('active', t === tabId);
            if (panel) panel.classList.toggle('hidden', t !== tabId);
        });

        if (tabId === 'tasks') this.loadTasks();
        else if (tabId === 'reflections') this.loadReflections();
        else if (tabId === 'codebase') this.loadCodebaseStructure();
    }

    // --- Task Queue & Missions ---
    async loadTasks() {
        const container = document.getElementById('tasks-list');
        if (!container) return;
        container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading tasks...</div>';

        try {
            const res = await fetch('/api/tasks');
            const data = await res.json();
            const tasks = data.tasks || [];

            if (tasks.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-list-check"></i>
                        <p>No active tasks in queue. Enqueue a new mission above!</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = tasks.map(t => {
                const statusClass = (t.status || 'queued').toLowerCase().replace(' ', '_');
                const progress = t.progress || 0;
                const dateStr = t.created_at ? new Date(t.created_at * 1000).toLocaleString() : '';

                const stepsHtml = (t.steps || []).map((s, idx) => `
                    <div class="task-step-item ${s.completed ? 'completed' : ''}" onclick="ChatApp.toggleTaskStep(${t.id}, ${idx})">
                        <i class="fa-solid ${s.completed ? 'fa-square-check' : 'fa-square'}"></i>
                        <span>${this.escapeHtml(s.title || s)}</span>
                    </div>
                `).join('');

                return `
                    <div class="task-card" id="task-card-${t.id}">
                        <div class="task-card-header">
                            <span class="task-card-title"><i class="fa-solid fa-bullseye" style="color:#38bdf8;"></i> ${this.escapeHtml(t.title)}</span>
                            <span class="task-status-badge ${statusClass}">${t.status}</span>
                        </div>
                        <p class="task-card-goal">${this.escapeHtml(t.goal)}</p>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" style="width: ${progress}%; background: linear-gradient(135deg, #38bdf8, #0284c7);"></div>
                        </div>
                        <div class="task-steps-list">
                            ${stepsHtml || '<div style="font-size:0.78rem;color:var(--text-muted);">No granular steps defined.</div>'}
                        </div>
                        <div class="task-card-footer">
                            <span><i class="fa-regular fa-clock"></i> ${dateStr}</span>
                            <button class="action-icon-btn danger" onclick="ChatApp.deleteTask(${t.id})" title="Delete Task">
                                <i class="fa-solid fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                `;
            }).join('');

        } catch (e) {
            console.error('Failed to load tasks:', e);
            container.innerHTML = '<div class="empty-state">Error loading tasks from server.</div>';
        }
    }

    async enqueueTask() {
        const titleInput = document.getElementById('new-task-title');
        const goalInput = document.getElementById('new-task-goal');
        if (!titleInput || !goalInput) return;

        const title = titleInput.value.trim() || 'Untitled Mission';
        const goal = goalInput.value.trim();
        if (!goal) {
            alert('Please provide a description/goal for the task.');
            return;
        }

        try {
            await fetch('/api/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, goal })
            });
            titleInput.value = '';
            goalInput.value = '';
            this.loadTasks();
        } catch (e) {
            console.error('Failed to enqueue task:', e);
        }
    }

    async toggleTaskStep(taskId, stepIndex) {
        try {
            await fetch(`/api/tasks/${taskId}/toggle_step`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ step_index: stepIndex })
            });
            this.loadTasks();
        } catch (e) {
            console.error('Failed to toggle step:', e);
        }
    }

    async deleteTask(taskId) {
        if (!confirm('Are you sure you want to remove this task from the queue?')) return;
        try {
            await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
            this.loadTasks();
        } catch (e) {
            console.error('Failed to delete task:', e);
        }
    }

    async runNextTask() {
        try {
            const res = await fetch('/api/tasks/run_next', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'empty') {
                alert('No pending or in-progress tasks found in queue.');
                return;
            }
            alert(`Task #${data.task_id} completed through multi-agent pipeline!`);
            this.loadTasks();
            this.switchIntelTab('pipeline');
            if (data.pipeline_result) {
                this.renderPipelineResult(data.pipeline_result);
            }
        } catch (e) {
            console.error('Failed to run next task:', e);
        }
    }

    // --- Multi-Agent Pipeline Runner ---
    async runAgentPipeline() {
        const input = document.getElementById('pipeline-goal-input');
        const outputBox = document.getElementById('pipeline-output-box');
        const runBtn = document.getElementById('pipeline-run-btn');
        if (!input || !outputBox) return;

        const goal = input.value.trim();
        if (!goal) {
            alert('Please enter an objective for the multi-agent pipeline.');
            return;
        }

        // Reset flowchart nodes
        const nodes = ['planner', 'researcher', 'coder', 'executor', 'verifier'];
        nodes.forEach(n => {
            const el = document.getElementById(`node-${n}`);
            if (el) el.className = 'agent-node';
        });

        outputBox.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Initializing Planner ➔ Researcher ➔ Coder ➔ Executor ➔ Verifier...</div>';
        if (runBtn) runBtn.disabled = true;

        try {
            const res = await fetch('/api/agent/pipeline', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal })
            });
            const data = await res.json();
            this.renderPipelineResult(data);
        } catch (e) {
            outputBox.innerHTML = `<div class="empty-state">Pipeline execution error: ${this.escapeHtml(e.message)}</div>`;
        } finally {
            if (runBtn) runBtn.disabled = false;
        }
    }

    renderPipelineResult(data) {
        const outputBox = document.getElementById('pipeline-output-box');
        if (!outputBox) return;

        const stages = data.stages || [];
        const reflection = data.reflection || {};

        // Mark all flowchart nodes completed
        ['planner', 'researcher', 'coder', 'executor', 'verifier'].forEach(n => {
            const el = document.getElementById(`node-${n}`);
            if (el) el.className = 'agent-node completed';
        });

        let stagesHtml = stages.map(s => `
            <div class="stage-card">
                <div class="stage-card-header">
                    <span><i class="fa-solid fa-microchip" style="color:#38bdf8;"></i> Stage ${s.stage}: ${this.escapeHtml(s.name || s.agent)}</span>
                    <span class="task-status-badge ${s.status === 'SUCCESS' ? 'completed' : 'failed'}">${s.status || 'DONE'}</span>
                </div>
                <div class="stage-card-body">${this.escapeHtml(s.output || '(No output)')}</div>
            </div>
        `).join('');

        let refHtml = '';
        if (reflection.lesson_learned) {
            refHtml = `
                <div class="reflection-card ref-${reflection.success ? 'success' : 'fail'}" style="margin-top:10px;">
                    <div class="reflection-header">
                        <span class="reflection-goal"><i class="fa-solid fa-brain"></i> Self-Reflection & Learned Lesson</span>
                        <span class="task-status-badge ${reflection.success ? 'completed' : 'failed'}">${reflection.success ? 'VERIFIED' : 'NEEDS REFINEMENT'}</span>
                    </div>
                    <div class="ref-lesson">${this.escapeHtml(reflection.lesson_learned)}</div>
                </div>
            `;
        }

        outputBox.innerHTML = `
            <div style="font-size:0.88rem; font-weight:600; color:var(--text-primary); margin-bottom:6px;">
                🎯 Objective: ${this.escapeHtml(data.goal || '')} (${data.duration_ms || 0}ms)
            </div>
            ${stagesHtml}
            ${refHtml}
        `;
    }

    // --- Self-Reflection Journal ---
    async loadReflections() {
        const container = document.getElementById('reflections-list');
        if (!container) return;
        container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading reflections...</div>';

        try {
            const res = await fetch('/api/agent/reflect');
            const data = await res.json();
            const reflections = data.reflections || [];

            if (reflections.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-solid fa-book-journal-whills"></i>
                        <p>No reflections recorded yet. As tasks are executed, V.O.I.D. will evaluate what worked and what failed here.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = reflections.map(r => {
                const isSuccess = r.success === 1 || r.success === true;
                const dateStr = r.timestamp ? new Date(r.timestamp * 1000).toLocaleString() : '';

                return `
                    <div class="reflection-card ${isSuccess ? 'ref-success' : 'ref-fail'}">
                        <div class="reflection-header">
                            <span class="reflection-goal"><i class="fa-solid ${isSuccess ? 'fa-circle-check' : 'fa-triangle-exclamation'}"></i> ${this.escapeHtml(r.goal)}</span>
                            <span class="task-status-badge ${isSuccess ? 'completed' : 'failed'}">${isSuccess ? 'SUCCESS' : 'FAILED'}</span>
                        </div>
                        <div class="reflection-body">
                            <div class="ref-worked">
                                <div class="ref-section-title">💡 What Worked</div>
                                <div>${this.escapeHtml(r.what_worked || 'Executed as planned')}</div>
                            </div>
                            <div class="ref-failed">
                                <div class="ref-section-title">⚠️ Bottlenecks & Failure Modes</div>
                                <div>${this.escapeHtml(r.what_failed || 'None')}</div>
                            </div>
                            <div class="ref-lesson">
                                <strong>🧠 Consolidated Lesson:</strong> ${this.escapeHtml(r.lesson_learned || '')}
                            </div>
                        </div>
                        <div style="font-size:0.74rem;color:var(--text-muted);margin-top:4px;">
                            <span><i class="fa-regular fa-clock"></i> ${dateStr}</span>
                        </div>
                    </div>
                `;
            }).join('');

        } catch (e) {
            console.error('Failed to load reflections:', e);
            container.innerHTML = '<div class="empty-state">Error loading reflections.</div>';
        }
    }

    // --- Project Codebase Awareness ---
    async loadCodebaseStructure() {
        try {
            const res = await fetch('/api/project/structure');
            const data = await res.json();
            const summary = data.summary || {};
            const tree = data.tree || {};

            const filesEl = document.getElementById('codebase-total-files');
            const symsEl = document.getElementById('codebase-total-symbols');
            const sizeEl = document.getElementById('codebase-total-size');

            if (filesEl) filesEl.textContent = summary.total_files || '--';
            if (symsEl) {
                const syms = summary.symbols_count || {};
                symsEl.textContent = `${syms.classes || 0} Classes • ${syms.functions || 0} Funcs`;
            }
            if (sizeEl) sizeEl.textContent = `${summary.total_size_mb || 0} MB`;

            // Modules Grid
            const modGrid = document.getElementById('codebase-modules-list');
            if (modGrid && summary.module_roles) {
                modGrid.innerHTML = Object.entries(summary.module_roles).map(([mod, role]) => `
                    <div class="module-card">
                        <span class="module-name"><i class="fa-solid fa-folder"></i> ${this.escapeHtml(mod)}</span>
                        <span class="module-role">${this.escapeHtml(role)}</span>
                    </div>
                `).join('');
            }

            // File Tree
            const treeBox = document.getElementById('file-tree-viewer');
            if (treeBox) {
                treeBox.innerHTML = this.renderTreeHTML(tree);
            }

        } catch (e) {
            console.error('Failed to load codebase structure:', e);
        }
    }

    renderTreeHTML(node) {
        if (!node) return '';
        if (!node.is_dir) {
            return `<div class="tree-node"><i class="fa-solid fa-file-code" style="color:var(--text-muted);margin-right:4px;"></i> ${this.escapeHtml(node.name)} <span style="color:var(--text-muted);font-size:0.74rem;">(${node.size_kb || 0} KB)</span></div>`;
        }

        const childrenHtml = (node.children || []).map(child => this.renderTreeHTML(child)).join('');
        return `
            <div class="tree-node is-dir">
                <i class="fa-solid fa-folder-open" style="color:#38bdf8;margin-right:4px;"></i> ${this.escapeHtml(node.name)}/
                <div style="margin-left: 12px; border-left: 1px dashed rgba(255,255,255,0.1); padding-left: 6px;">
                    ${childrenHtml}
                </div>
            </div>
        `;
    }

    // --- Skill Router Inspector ---
    async inspectSkillRoute() {
        const input = document.getElementById('router-test-input');
        const card = document.getElementById('router-result-card');
        if (!input || !card) return;

        const query = input.value.trim();
        if (!query) return;

        card.classList.remove('hidden');
        card.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Classifying intent...</div>';

        try {
            const res = await fetch('/api/skills/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            const d = data.decision || {};
            const pct = Math.round((d.confidence || 0) * 100);

            card.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span class="router-badge"><i class="fa-solid fa-bolt"></i> Skill: ${this.escapeHtml(d.skill || 'chat').toUpperCase()}</span>
                    <span style="font-size:0.84rem;font-weight:700;color:#38bdf8;">${pct}% Confidence</span>
                </div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" style="width:${pct}%;background:#38bdf8;"></div></div>
                <div style="font-size:0.86rem;color:#e2e8f0;line-height:1.4;">
                    <strong>🧠 Routing Rationale:</strong> ${this.escapeHtml(d.reason || '')}
                </div>
                <div style="font-size:0.78rem;color:var(--text-muted);">
                    <strong>Execution Mode:</strong> ${d.is_deterministic ? '⚡ Deterministic Tool Execution (Zero LLM Overhead)' : '🤖 Generative Neural Persona'}
                </div>
            `;
        } catch (e) {
            card.innerHTML = `<div class="empty-state">Classification error: ${this.escapeHtml(e.message)}</div>`;
        }
    }

    // ==========================================
    // V.O.I.D. VISION & PERCEPTION HUD CONTROLLER
    // ==========================================
    openVisionModal() {
        const modal = document.getElementById('vision-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.loadVisionDevices();
            this.fetchVisionStatus();
            this.startVisionPolling();
        }
    }

    switchVisionTab(tabName) {
        document.querySelectorAll('.vision-subtabs .intel-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        document.querySelectorAll('.vision-tab-content').forEach(panel => {
            panel.classList.add('hidden');
        });

        const activePanel = document.getElementById(`vision-tab-${tabName}`);
        if (activePanel) activePanel.classList.remove('hidden');

        if (tabName === 'enroll') {
            this.loadEnrolledProfiles();
        } else if (tabName === 'memory') {
            this.loadVisualMemory();
        }
    }

    async loadVisionDevices() {
        const select = document.getElementById('vision-camera-select');
        if (!select) return;
        try {
            const res = await fetch('/api/vision/devices');
            const data = await res.json();
            if (data.devices && data.devices.length > 0) {
                select.innerHTML = data.devices.map(d => 
                    `<option value="${d.index}">${this.escapeHtml(d.name)} (${d.width}x${d.height})</option>`
                ).join('');
            }
        } catch (e) {
            console.error('Failed to enumerate vision devices:', e);
        }
    }

    async switchVisionCamera(deviceIndex) {
        try {
            await fetch('/api/vision/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_index: parseInt(deviceIndex) })
            });
            this.fetchVisionStatus();
        } catch (e) {
            console.error('Failed to switch camera:', e);
        }
    }

    async setVisionMode(mode) {
        document.querySelectorAll('.mode-pill').forEach(p => {
            p.classList.toggle('active', p.dataset.mode === mode);
        });

        try {
            await fetch('/api/vision/mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode })
            });
        } catch (e) {
            console.error('Failed to set vision mode:', e);
        }
    }

    openVisionModal() {
        // Camera access is strictly confined to the dedicated /vision webpage
        window.location.href = '/vision';
    }

    async toggleVisionCamera(forceStart = null) {
        // Camera access is strictly confined to the dedicated /vision webpage
        window.location.href = '/vision';
    }

    toggleStreamHUD(enabled) {
        const feedImg = document.getElementById('vision-feed-img');
        if (feedImg && !feedImg.classList.contains('hidden')) {
            feedImg.src = `/api/vision/feed?hud=${enabled}&t=${Date.now()}`;
        }
    }

    async triggerVisionSnapshot() {
        try {
            this.showNotification('Capturing and analyzing frame...', 'info');
            const res = await fetch('/api/vision/snapshot', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                const count = (data.objects || []).length;
                const faces = (data.faces || []).length;
                this.showNotification(`Snapshot complete: ${count} objects, ${faces} people detected`, 'success');
                this.updateVisionTelemetryUI({ perception: data, telemetry: {} });
            }
        } catch (e) {
            this.showNotification('Snapshot failed: ' + e.message, 'error');
        }
    }

    async triggerVisionScan() {
        try {
            this.showNotification('Running full environment scan...', 'info');
            const res = await fetch('/api/vision/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: 'Deep scan environment and describe everything.' })
            });
            const data = await res.json();
            if (data.result && data.result.natural_response) {
                const summaryEl = document.getElementById('vision-scene-summary');
                if (summaryEl) summaryEl.innerText = `"${data.result.natural_response}"`;
                this.showNotification('Scene scan complete', 'success');
            }
        } catch (e) {
            this.showNotification('Scan failed: ' + e.message, 'error');
        }
    }

    startVisionPolling() {
        if (this._visionPollInterval) clearInterval(this._visionPollInterval);
        this._visionPollInterval = setInterval(() => {
            const modal = document.getElementById('vision-modal');
            if (modal && !modal.classList.contains('hidden')) {
                this.fetchVisionStatus();
            } else {
                this.stopVisionPolling();
            }
        }, 1200);
    }

    stopVisionPolling() {
        if (this._visionPollInterval) {
            clearInterval(this._visionPollInterval);
            this._visionPollInterval = null;
        }
    }

    async fetchVisionStatus() {
        try {
            const res = await fetch('/api/vision/status');
            const data = await res.json();
            if (data.status === 'success' && data.data) {
                this.updateVisionTelemetryUI(data.data);
            }
        } catch (e) {
            // Silently ignore poll errors
        }
    }

    updateVisionTelemetryUI(data) {
        const p = data.perception || {};
        const t = data.telemetry || {};
        const cam = t.camera || {};
        const hw = t.hardware || {};
        const scene = p.scene || {};

        // 1. Identity
        const faces = p.faces || [];
        const idName = document.getElementById('vision-id-name');
        const idStatus = document.getElementById('vision-id-status');
        const idConf = document.getElementById('vision-id-conf');

        if (faces.length > 0) {
            const owner = faces.find(f => f.identity === 'owner');
            if (owner) {
                if (idName) idName.innerText = owner.name;
                if (idStatus) idStatus.innerText = 'Enrolled Owner Recognized';
                if (idConf) idConf.innerText = `${Math.round((owner.confidence || 0.9) * 100)}%`;
            } else {
                const unknownCount = faces.length;
                if (idName) idName.innerText = unknownCount === 1 ? 'Unknown Person' : `${unknownCount} People`;
                if (idStatus) idStatus.innerText = 'Unenrolled Presence';
                if (idConf) idConf.innerText = '--%';
            }
        } else {
            if (idName) idName.innerText = 'No Person';
            if (idStatus) idStatus.innerText = 'Standby';
            if (idConf) idConf.innerText = '--%';
        }

        // 2. Objects
        const objs = p.objects || [];
        const objCount = document.getElementById('vision-obj-count');
        const objList = document.getElementById('vision-objects-list');
        if (objCount) objCount.innerText = objs.length;
        if (objList) {
            if (objs.length === 0) {
                objList.innerHTML = '<span class="empty-tag">No objects highlighted</span>';
            } else {
                objList.innerHTML = objs.map(o => 
                    `<span class="obj-tag">${this.escapeHtml(o.label)} <span class="obj-tag-conf">${Math.round(o.confidence * 100)}%</span></span>`
                ).join('');
            }
        }

        // 3. Scene
        const envEl = document.getElementById('vision-scene-env');
        const lightEl = document.getElementById('vision-scene-lighting');
        const actEl = document.getElementById('vision-scene-activity');
        const peopleEl = document.getElementById('vision-scene-people');
        const summaryEl = document.getElementById('vision-scene-summary');

        if (envEl) envEl.innerText = (scene.environment || 'Indoor').toUpperCase();
        if (lightEl) lightEl.innerText = (scene.lighting || 'Normal').toUpperCase();
        if (actEl) actEl.innerText = (scene.activity_level || 'Static').replace('_', ' ').toUpperCase();
        if (peopleEl) peopleEl.innerText = scene.people_count !== undefined ? scene.people_count : faces.length;
        if (summaryEl && scene.summary) summaryEl.innerText = `"${scene.summary}"`;

        // 4. Hardware Matrix
        const fpsEl = document.getElementById('vision-fps-val');
        const cpuEl = document.getElementById('vision-cpu-val');
        const ramEl = document.getElementById('vision-ram-val');
        const gpuEl = document.getElementById('vision-gpu-val');

        if (fpsEl) {
            const actFps = cam.actual_fps || 0.0;
            const detFps = cam.detection_fps || (telemetry && telemetry.detection_fps);
            fpsEl.innerText = (detFps && detFps > 0) ? `${actFps} FPS (DET: ${detFps})` : `${actFps} FPS`;
        }
        if (cpuEl) cpuEl.innerText = `${Math.round(hw.cpu_percent || 0)}%`;
        if (ramEl) ramEl.innerText = `${hw.ram_used_mb || 0} MB (${hw.ram_percent || 0}%)`;
        if (gpuEl) gpuEl.innerText = hw.gpu_name || 'CPU Mode';
    }

    async startFaceEnrollment() {
        const input = document.getElementById('enroll-name-input');
        const name = (input ? input.value : '').trim() || 'Owner';
        const progress = document.getElementById('enroll-progress-area');
        const statusText = document.getElementById('enroll-status-text');

        if (progress) progress.classList.remove('hidden');
        if (statusText) statusText.innerText = `Capturing facial samples for '${name}'...`;

        try {
            const res = await fetch('/api/vision/enroll', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, samples: 8 })
            });
            const data = await res.json();
            if (data.status === 'success') {
                this.showNotification(`Face enrollment successful for ${name}!`, 'success');
                if (input) input.value = '';
                this.loadEnrolledProfiles();
            } else {
                this.showNotification('Enrollment failed: ' + (data.result?.error || 'Unknown error'), 'error');
            }
        } catch (e) {
            this.showNotification('Enrollment request failed: ' + e.message, 'error');
        } finally {
            if (progress) progress.classList.add('hidden');
        }
    }

    async loadEnrolledProfiles() {
        const container = document.getElementById('enrolled-profiles-list');
        if (!container) return;
        container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading profiles...</div>';

        try {
            const res = await fetch('/api/vision/profiles');
            const data = await res.json();
            const profiles = data.profiles || [];

            if (profiles.length === 0) {
                container.innerHTML = '<div class="empty-state">No facial recognition profiles enrolled yet. Use the form above to enroll.</div>';
                return;
            }

            container.innerHTML = profiles.map(p => `
                <div class="profile-card">
                    <div class="profile-info">
                        <span class="profile-name"><i class="fa-solid fa-user-check" style="color:#22c55e;"></i> ${this.escapeHtml(p.name)}</span>
                        <span class="profile-meta">${p.is_owner ? 'Primary Owner' : 'Enrolled Member'} • ${p.sample_count} samples</span>
                    </div>
                    <span class="vision-badge active">ENROLLED</span>
                </div>
            `).join('');
        } catch (e) {
            container.innerHTML = `<div class="empty-state">Error loading profiles: ${this.escapeHtml(e.message)}</div>`;
        }
    }

    async loadVisualMemory() {
        const listEl = document.getElementById('visual-memory-list');
        const pillsEl = document.getElementById('today-objects-pills');
        if (!listEl) return;

        listEl.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading observations...</div>';

        try {
            const res = await fetch('/api/vision/memory?limit=30');
            const data = await res.json();
            const obs = data.observations || [];
            const todayObjs = data.today_objects || [];

            if (pillsEl) {
                pillsEl.innerHTML = todayObjs.length > 0 ? 
                    todayObjs.map(o => `<span class="today-pill">${this.escapeHtml(o)}</span>`).join('') :
                    '<span style="font-size:0.75rem;color:var(--text-muted);">None yet</span>';
            }

            if (obs.length === 0) {
                listEl.innerHTML = '<div class="empty-state">No visual memories recorded yet.</div>';
                return;
            }

            this._cachedVisualMemories = obs;
            this.renderVisualMemories(obs);
        } catch (e) {
            listEl.innerHTML = `<div class="empty-state">Error loading visual memory: ${this.escapeHtml(e.message)}</div>`;
        }
    }

    filterVisualMemory() {
        const query = (document.getElementById('vis-memory-search-input')?.value || '').toLowerCase().trim();
        if (!this._cachedVisualMemories) return;
        const filtered = this._cachedVisualMemories.filter(o => 
            (o.object && o.object.toLowerCase().includes(query)) ||
            (o.event_type && o.event_type.toLowerCase().includes(query)) ||
            (o.context && o.context.toLowerCase().includes(query))
        );
        this.renderVisualMemories(filtered);
    }

    renderVisualMemories(items) {
        const listEl = document.getElementById('visual-memory-list');
        if (!listEl) return;

        if (items.length === 0) {
            listEl.innerHTML = '<div class="empty-state">No matching visual observations found.</div>';
            return;
        }

        listEl.innerHTML = items.map(r => `
            <div class="vis-mem-item">
                <div class="vis-mem-left">
                    <div class="vis-mem-icon"><i class="fa-solid fa-eye"></i></div>
                    <div class="vis-mem-details">
                        <span class="vis-mem-title">${this.escapeHtml(r.object || r.event_type)} <span style="font-size:0.72rem;color:var(--text-muted);">[${this.escapeHtml(r.context || 'workspace')}]</span></span>
                        <span class="vis-mem-time">${this.escapeHtml(r.iso_time)} - Event: ${this.escapeHtml(r.event_type)}</span>
                    </div>
                </div>
                <span class="vis-mem-score">IMP: ${Math.round(r.importance * 100)}%</span>
            </div>
        `).join('');
    }

    // ========================================================
    // V.O.I.D. KNOWLEDGE CORE & LEARNING DASHBOARD CONTROLLER
    // ========================================================

    /** Escapes HTML special characters to prevent XSS. */
    escapeHtml(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    openLearningDashboard() {
        const modal = document.getElementById('learning-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.loadLearningStats();
        }
    }

    closeLearningDashboard() {
        const modal = document.getElementById('learning-modal');
        if (modal) modal.classList.add('hidden');
    }

    showNotification(message, type = 'info') {
        let container = document.getElementById('void-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'void-toast-container';
            container.className = 'void-toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `void-toast toast-${type}`;
        
        let icon = 'fa-circle-info';
        if (type === 'success') icon = 'fa-circle-check';
        else if (type === 'error') icon = 'fa-triangle-exclamation';
        else if (type === 'warning') icon = 'fa-bell';

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${this.escapeHtml(message)}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-8px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    async loadLearningStats() {
        const grid = document.getElementById('recent-learning-grid');
        if (!grid) return;

        try {
            const res = await fetch('/api/learning/stats');
            const resData = await res.json();
            if (resData.status !== 'success' || !resData.data) return;

            const d = resData.data;

            const totEl = document.getElementById('stat-total-knowledge');
            const verEl = document.getElementById('stat-verified-knowledge');
            const penEl = document.getElementById('stat-pending-knowledge');
            const outEl = document.getElementById('stat-outdated-knowledge');
            const srcEl = document.getElementById('stat-unique-sources');
            const confEl = document.getElementById('stat-conflicted-knowledge');
            const autoBtn = document.getElementById('autolearn-toggle-btn');

            if (totEl) totEl.innerText = (d.total_records || 0).toLocaleString();
            if (verEl) verEl.innerText = (d.verified_records || 0).toLocaleString();
            if (penEl) penEl.innerText = (d.pending_records || 0).toLocaleString();
            if (outEl) outEl.innerText = (d.outdated_records || 0).toLocaleString();
            if (srcEl) srcEl.innerText = `From ${d.unique_sources || 0} unique web sources`;
            if (confEl) confEl.innerText = `${d.conflicted_records || 0} conflicts detected`;

            if (autoBtn) {
                if (d.auto_learning) {
                    autoBtn.innerHTML = '<i class="fa-solid fa-toggle-on"></i> ON';
                    autoBtn.style.color = '#22c55e';
                    autoBtn.style.borderColor = '#22c55e';
                } else {
                    autoBtn.innerHTML = '<i class="fa-solid fa-toggle-off"></i> OFF';
                    autoBtn.style.color = '#ff5500';
                    autoBtn.style.borderColor = '#ff5500';
                }
            }

            const topics = d.recent_topics || [];
            if (topics.length === 0) {
                grid.innerHTML = `
                    <div class="empty-state" style="grid-column: 1 / -1; padding: 20px; text-align: center; color: var(--text-muted);">
                        <i class="fa-solid fa-graduation-cap" style="font-size: 24px; color: #ff5500; margin-bottom: 8px;"></i>
                        <p>No internet knowledge acquired yet. Use the prompt box above or say "Void, learn about &lt;topic&gt;".</p>
                    </div>
                `;
                return;
            }

            grid.innerHTML = topics.map(t => `
                <div class="stat-card" style="padding: 12px 14px; background: #16171d; border: 1px solid #2e303a; border-radius: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <span style="font-weight: 700; font-size: 0.92rem; color: #fff;">${this.escapeHtml(t.topic)}</span>
                        <span style="font-size: 0.76rem; font-weight: 700; color: #ff5500; background: rgba(255,85,0,0.1); padding: 2px 7px; border-radius: 6px;">${t.confidence}%</span>
                    </div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 8px;">
                        <span><i class="fa-solid fa-layer-group"></i> ${t.facts} Facts</span> • 
                        <span><i class="fa-regular fa-clock"></i> ${t.time}</span>
                    </div>
                    <div style="display: flex; gap: 6px; justify-content: flex-end;">
                        <button class="icon-btn" title="Inspect Sources" onclick="ChatApp.showTopicSources('${this.escapeHtml(t.topic)}')" style="width: 28px; height: 28px; font-size: 0.75rem;">
                            <i class="fa-solid fa-circle-info"></i>
                        </button>
                        <button class="icon-btn" title="Forget Topic" onclick="ChatApp.forgetTopic('${this.escapeHtml(t.topic)}')" style="width: 28px; height: 28px; font-size: 0.75rem; color: #ef4444;">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </div>
            `).join('');

        } catch (e) {
            console.error('Failed to load learning stats:', e);
        }
    }

    async triggerLearnTopic() {
        const input = document.getElementById('learn-topic-input');
        const termBox = document.getElementById('learning-terminal-box');
        const termContent = document.getElementById('learning-terminal-content');
        const actionBtn = document.getElementById('learn-action-btn');

        if (!input) return;
        const topic = input.value.trim();
        if (!topic) {
            alert('Please enter a topic to acquire and study.');
            return;
        }

        if (termBox) termBox.classList.remove('hidden');
        if (termContent) {
            termContent.innerHTML = `
                <div style="color: #ff5500;">⚡ [V.O.I.D. Knowledge Pipeline Activated]</div>
                <div>Target Topic: <strong>${this.escapeHtml(topic)}</strong></div>
                <div style="color: #94a3b8;"><i class="fa-solid fa-spinner fa-spin"></i> Step 1/5: Querying multi-tier internet sources via DuckDuckGo...</div>
            `;
        }
        if (actionBtn) actionBtn.disabled = true;

        try {
            const res = await fetch('/api/learning/learn', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic })
            });
            const data = await res.json();

            if (termContent) {
                if (data.status === 'offline') {
                    termContent.innerHTML += `<div style="color: #f59e0b; margin-top: 8px;">⚠️ ${this.escapeHtml(data.message)}</div>`;
                } else if (data.status === 'success') {
                    termContent.innerHTML += `
                        <div style="color: #22c55e; margin-top: 8px;">✔ Step 2/5: Sources analyzed: ${data.sources_analyzed} (${data.useful_facts} facts extracted)</div>
                        <div style="color: #22c55e;">✔ Step 3/5: Verification: ${data.verified_facts} facts verified across sources (${data.conflicting_claims} conflicts)</div>
                        <div style="color: #22c55e;">✔ Step 4/5: Knowledge Graph linked: ${data.knowledge_graph_relationships} new entity relations created</div>
                        <div style="color: #38bdf8; font-weight: 700; margin-top: 8px;">✔ Step 5/5: Stored ${data.new_knowledge_records} records in local SQLite with ${data.confidence_percent}% confidence!</div>
                    `;
                } else {
                    termContent.innerHTML += `<div style="color: #ef4444; margin-top: 8px;">❌ ${this.escapeHtml(data.message || data.error || 'Failed')}</div>`;
                }
                termBox.scrollTop = termBox.scrollHeight;
            }

            this.loadLearningStats();
            input.value = '';
        } catch (err) {
            if (termContent) {
                termContent.innerHTML += `<div style="color: #ef4444; margin-top: 8px;">❌ Request error: ${this.escapeHtml(err.message)}</div>`;
            }
        } finally {
            if (actionBtn) actionBtn.disabled = false;
        }
    }

    async showTopicSources(topic) {
        try {
            const res = await fetch(`/api/learning/sources?topic=${encodeURIComponent(topic)}`);
            const data = await res.json();
            if (data.found) {
                alert(data.report_text);
            } else {
                alert(`No detailed source records found for '${topic}'.`);
            }
        } catch (e) {
            alert('Failed to retrieve sources: ' + e.message);
        }
    }

    async forgetTopic(topic) {
        if (!confirm(`Are you sure you want V.O.I.D. to forget all learned knowledge about '${topic}'?`)) {
            return;
        }

        try {
            const res = await fetch('/api/learning/forget', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic })
            });
            const data = await res.json();
            this.showNotification(data.message || 'Topic forgotten', 'info');
            this.loadLearningStats();
        } catch (e) {
            this.showNotification('Failed to delete knowledge: ' + e.message, 'error');
        }
    }

    async toggleAutoLearn() {
        try {
            const res = await fetch('/api/learning/autolearn/toggle', { method: 'POST' });
            const data = await res.json();
            const autoBtn = document.getElementById('autolearn-toggle-btn');
            if (autoBtn) {
                if (data.auto_learning) {
                    autoBtn.innerHTML = '<i class="fa-solid fa-toggle-on"></i> ON';
                    autoBtn.style.color = '#22c55e';
                    autoBtn.style.borderColor = '#22c55e';
                    this.showNotification('Autonomous Learning enabled. V.O.I.D. will proactively fill knowledge gaps.', 'success');
                } else {
                    autoBtn.innerHTML = '<i class="fa-solid fa-toggle-off"></i> OFF';
                    autoBtn.style.color = '#ff5500';
                    autoBtn.style.borderColor = '#ff5500';
                    this.showNotification('Autonomous Learning disabled. Knowledge acquired strictly upon user command.', 'info');
                }
            }
        } catch (e) {
            this.showNotification('Toggle failed: ' + e.message, 'error');
        }
    }
    // ══════════════════════════════════════════════════════════
    // 🤖 FULL AUTO MODE — Autonomous Self-Training Controller
    // ══════════════════════════════════════════════════════════

    _getFullAutoEl(id) { return document.getElementById(id); }

    _setFullAutoBadge(state) {
        const badge = this._getFullAutoEl('fullauto-state-badge');
        const phase = this._getFullAutoEl('fullauto-phase');
        const abortBtn = this._getFullAutoEl('fullauto-abort-btn');
        const scoutBtn = this._getFullAutoEl('fullauto-scout-btn');
        const stateConfig = {
            'IDLE':                   { color: '#aaa',    bg: 'rgba(100,100,100,0.3)', label: 'IDLE' },
            'SCOUTING':               { color: '#eab308', bg: 'rgba(234,179,8,0.15)',  label: 'SCOUTING' },
            'AWAITING_AUTHORIZATION': { color: '#c4b5fd', bg: 'rgba(139,92,246,0.2)',  label: 'AWAITING AUTH' },
            'AUTHORIZED':             { color: '#10b981', bg: 'rgba(16,185,129,0.15)', label: 'AUTHORIZED' },
            'DOWNLOADING':            { color: '#38bdf8', bg: 'rgba(56,189,248,0.15)', label: 'DOWNLOADING' },
            'BUILDING_CORPUS':        { color: '#fb923c', bg: 'rgba(251,146,60,0.15)', label: 'BUILDING CORPUS' },
            'TRAINING':               { color: '#8b5cf6', bg: 'rgba(139,92,246,0.2)',  label: 'TRAINING' },
            'COMPLETE':               { color: '#22c55e', bg: 'rgba(34,197,94,0.15)',  label: 'COMPLETE' },
            'ABORTED':                { color: '#ef4444', bg: 'rgba(239,68,68,0.15)',  label: 'ABORTED' },
            'ERROR':                  { color: '#ef4444', bg: 'rgba(239,68,68,0.15)',  label: 'ERROR' },
        };
        const cfg = stateConfig[state] || stateConfig['IDLE'];
        if (badge) { badge.textContent = cfg.label; badge.style.color = cfg.color; badge.style.background = cfg.bg; }
        if (phase) { phase.textContent = state; phase.style.color = cfg.color; }
        const active = !['IDLE', 'COMPLETE', 'ABORTED', 'ERROR'].includes(state);
        if (abortBtn) { abortBtn.classList.toggle('hidden', !active); }
        if (scoutBtn) { scoutBtn.disabled = active; scoutBtn.style.opacity = active ? '0.4' : '1'; }
    }

    _fullautoLog(msg) {
        const terminal = this._getFullAutoEl('fullauto-terminal');
        const content = this._getFullAutoEl('fullauto-terminal-content');
        if (!terminal || !content) return;
        terminal.classList.remove('hidden');
        const line = document.createElement('div');
        const ts = new Date().toTimeString().slice(0, 8);
        let color = '#e2e8f0';
        if (msg.includes('ERROR') || msg.includes('FAILED')) color = '#ef4444';
        else if (msg.includes('Done') || msg.includes('complete') || msg.includes('COMPLETE')) color = '#22c55e';
        else if (msg.includes('AWAITING') || msg.includes('Authorization')) color = '#c4b5fd';
        else if (msg.includes('ABORTED')) color = '#ef4444';
        else if (msg.includes('Downloading')) color = '#38bdf8';
        else if (msg.includes('Training') || msg.includes('step')) color = '#8b5cf6';
        line.innerHTML = '<span style="color:#555">[' + ts + ']</span> <span style="color:' + color + '">' + this.escapeHtml(msg) + '</span>';
        content.appendChild(line);
        terminal.scrollTop = terminal.scrollHeight;
    }

    _renderDatasetList(candidates) {
        const list = this._getFullAutoEl('fullauto-dataset-list');
        if (!list) return;
        list.innerHTML = '';
        const domainColors = { cybersecurity: '#ef4444', coding: '#38bdf8', language: '#22c55e', general: '#eab308' };
        (candidates || []).filter(c => c.selected !== false).forEach(c => {
            const color = domainColors[c.domain] || '#aaa';
            const qualityPct = Math.round((c.quality_score || 0) * 100);
            const el = document.createElement('label');
            el.style.cssText = 'display:flex;align-items:flex-start;gap:10px;background:rgba(16,16,24,0.8);border:1px solid #2e303a;border-radius:10px;padding:12px;cursor:pointer;';
            el.innerHTML = '<input type="checkbox" name="fullauto_dataset" value="' + this.escapeHtml(c.name) + '" checked style="margin-top:3px;accent-color:#8b5cf6;width:16px;height:16px;flex-shrink:0;">'
                + '<div style="flex:1;min-width:0;">'
                + '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
                + '<span style="font-weight:700;font-size:0.85rem;color:#fff;">' + this.escapeHtml(c.name) + '</span>'
                + '<span style="font-size:0.7rem;padding:2px 8px;border-radius:12px;background:' + color + '22;color:' + color + ';font-weight:600;">' + (c.domain||'').toUpperCase() + '</span>'
                + '<span style="font-size:0.7rem;color:#aaa;margin-left:auto;">' + (c.estimated_mb||0).toFixed(0) + ' MB</span>'
                + '</div>'
                + '<div style="font-size:0.78rem;color:#888;margin-top:4px;">' + this.escapeHtml(c.description||'') + '</div>'
                + '<div style="font-size:0.75rem;color:#555;margin-top:3px;font-style:italic;">' + this.escapeHtml(c.reason||'') + '</div>'
                + '<div style="margin-top:6px;display:flex;align-items:center;gap:6px;">'
                + '<div style="flex:1;height:4px;background:#1e1f28;border-radius:2px;"><div style="width:' + qualityPct + '%;height:4px;background:linear-gradient(90deg,#8b5cf6,#10b981);border-radius:2px;"></div></div>'
                + '<span style="font-size:0.7rem;color:#aaa;">Quality ' + qualityPct + '%</span></div></div>';
            list.appendChild(el);
        });
    }

    _updateProgressBars(progressData) {
        const container = this._getFullAutoEl('fullauto-progress-container');
        const bars = this._getFullAutoEl('fullauto-progress-bars');
        if (!container || !bars) return;
        container.classList.remove('hidden');
        Object.entries(progressData).forEach(([name, pct]) => {
            let bar = document.getElementById('pbar-' + name);
            if (!bar) {
                bars.innerHTML += '<div id="pbar-' + name + '" style="margin-bottom:6px;">'
                    + '<div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#aaa;margin-bottom:3px;">'
                    + '<span>' + this.escapeHtml(name) + '</span><span id="pbar-pct-' + name + '">' + pct + '%</span></div>'
                    + '<div style="height:6px;background:#1e1f28;border-radius:3px;">'
                    + '<div id="pbar-fill-' + name + '" style="width:' + pct + '%;height:6px;background:linear-gradient(90deg,#38bdf8,#8b5cf6);border-radius:3px;transition:width 0.3s;"></div>'
                    + '</div></div>';
            } else {
                const fillEl = document.getElementById('pbar-fill-' + name);
                const pctEl = document.getElementById('pbar-pct-' + name);
                if (fillEl) fillEl.style.width = pct + '%';
                if (pctEl) pctEl.textContent = pct + '%';
            }
        });
    }

    async requestFullAuto() {
        try {
            this._setFullAutoBadge('SCOUTING');
            this._fullautoLog('V.O.I.D. initiating autonomous dataset scouting...');
            const res = await fetch('/api/learning/fullauto/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: 'Admin-triggered autonomous self-improvement cycle' })
            });
            const data = await res.json();
            if (data.status === 'started') {
                this._fullautoLog('Session ' + data.session_id + ' started. Scanning catalog...');
                this.showNotification('V.O.I.D. is scouting datasets. You will be asked to authorize before anything downloads.', 'info');
                this._subscribeFullAutoSSE();
            } else {
                this._fullautoLog('ERROR: ' + (data.error || 'Unknown'));
                this.showNotification(data.error || 'Failed to start', 'error');
                this._setFullAutoBadge('IDLE');
            }
        } catch (e) {
            this._setFullAutoBadge('ERROR');
            this._fullautoLog('ERROR: ' + e.message);
            this.showNotification('Full Auto Mode error: ' + e.message, 'error');
        }
    }

    async refreshFullAutoStatus() {
        try {
            const res = await fetch('/api/learning/fullauto/status');
            const data = await res.json();
            if (data.status === 'success') {
                const d = data.data;
                this._setFullAutoBadge(d.state);
                if (d.session) {
                    if (d.session.log_lines) d.session.log_lines.slice(-20).forEach(l => this._fullautoLog(l));
                    if (d.state === 'AWAITING_AUTHORIZATION' && d.session.candidates) {
                        this._renderDatasetList(d.session.candidates);
                        const authPanel = this._getFullAutoEl('fullauto-auth-panel');
                        if (authPanel) authPanel.classList.remove('hidden');
                    }
                    if (d.session.download_progress) this._updateProgressBars(d.session.download_progress);
                    if (d.session.training_step > 0) {
                        const stepEl = this._getFullAutoEl('fullauto-step-count');
                        const lossEl = this._getFullAutoEl('fullauto-loss');
                        const statsEl = this._getFullAutoEl('fullauto-training-stats');
                        if (stepEl) stepEl.textContent = d.session.training_step;
                        if (lossEl) lossEl.textContent = parseFloat(d.session.training_loss).toFixed(4);
                        if (statsEl) statsEl.classList.remove('hidden');
                    }
                }
            }
        } catch (e) {
            this.showNotification('Status refresh failed: ' + e.message, 'error');
        }
    }

    async authorizeFullAuto() {
        try {
            const adminName = (this._getFullAutoEl('fullauto-admin-name') || {}).value || 'Admin';
            const checkboxes = document.querySelectorAll('input[name="fullauto_dataset"]:checked');
            const selectedNames = Array.from(checkboxes).map(cb => cb.value);
            this._fullautoLog('[' + adminName + '] Authorization granted for ' + selectedNames.length + ' dataset(s). Initiating pipeline...');
            const authPanel = this._getFullAutoEl('fullauto-auth-panel');
            if (authPanel) authPanel.classList.add('hidden');
            this._setFullAutoBadge('DOWNLOADING');
            const res = await fetch('/api/learning/fullauto/authorize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ admin_name: adminName.trim(), selected_datasets: selectedNames.length > 0 ? selectedNames : null })
            });
            const data = await res.json();
            if (data.status === 'authorized') {
                this.showNotification('Authorized! V.O.I.D. downloading ' + (data.selected_datasets ? data.selected_datasets.length : 0) + ' datasets.', 'success');
                const progContainer = this._getFullAutoEl('fullauto-progress-container');
                if (progContainer) progContainer.classList.remove('hidden');
            } else {
                this._fullautoLog('ERROR: ' + (data.error || 'Authorization failed'));
                this.showNotification(data.error || 'Authorization failed', 'error');
            }
        } catch (e) {
            this._fullautoLog('ERROR: ' + e.message);
            this.showNotification('Authorization error: ' + e.message, 'error');
        }
    }

    async abortFullAuto() {
        if (!confirm('Abort the autonomous training operation? This will stop all downloads and training immediately.')) return;
        try {
            await fetch('/api/learning/fullauto/abort', { method: 'POST' });
            this._setFullAutoBadge('ABORTED');
            this._fullautoLog('Operation aborted by admin.');
            const authPanel = this._getFullAutoEl('fullauto-auth-panel');
            if (authPanel) authPanel.classList.add('hidden');
            this.showNotification('Autonomous training aborted.', 'warning');
            if (this._fullAutoSSE) { this._fullAutoSSE.close(); this._fullAutoSSE = null; }
        } catch (e) {
            this.showNotification('Abort error: ' + e.message, 'error');
        }
    }

    _subscribeFullAutoSSE() {
        if (this._fullAutoSSE) this._fullAutoSSE.close();
        this._fullAutoSSE = new EventSource('/api/learning/fullauto/stream');
        this._fullAutoSSE.onmessage = (event) => {
            try {
                const ev = JSON.parse(event.data);
                const { type, data } = ev;
                if (type === 'state_change') {
                    this._setFullAutoBadge(data.state);
                } else if (type === 'scout_update') {
                    this._fullautoLog((data.reachable ? '  OK ' : '  SKIP ') + data.name);
                } else if (type === 'awaiting_authorization') {
                    this._setFullAutoBadge('AWAITING_AUTHORIZATION');
                    const selected = (data.candidates || []).filter(c => c.selected !== false);
                    this._renderDatasetList(selected);
                    const authPanel = this._getFullAutoEl('fullauto-auth-panel');
                    if (authPanel) authPanel.classList.remove('hidden');
                    this._fullautoLog('Scouting complete. ' + selected.length + ' datasets ready (~' + Math.round(data.total_mb || 0) + ' MB).');
                    this._fullautoLog('Waiting for admin authorization...');
                    this.showNotification('V.O.I.D. found training datasets! Authorization required in Knowledge Dashboard.', 'warning');
                } else if (type === 'authorized') {
                    this._fullautoLog('Authorized by ' + data.admin + '. Starting downloads...');
                } else if (type === 'download_start') {
                    this._fullautoLog('Downloading: ' + data.name);
                } else if (type === 'download_progress') {
                    this._updateProgressBars({ [data.name]: data.pct });
                } else if (type === 'training_progress') {
                    const stepEl = this._getFullAutoEl('fullauto-step-count');
                    const lossEl = this._getFullAutoEl('fullauto-loss');
                    const statsEl = this._getFullAutoEl('fullauto-training-stats');
                    if (stepEl) stepEl.textContent = data.step;
                    if (lossEl) lossEl.textContent = parseFloat(data.loss || 0).toFixed(4);
                    if (statsEl) statsEl.classList.remove('hidden');
                    if (data.log) this._fullautoLog(data.log);
                } else if (type === 'complete') {
                    this._setFullAutoBadge('COMPLETE');
                    this._fullautoLog('Full Auto training cycle complete!');
                    this.showNotification('V.O.I.D. autonomous training complete!', 'success');
                    if (this._fullAutoSSE) { this._fullAutoSSE.close(); this._fullAutoSSE = null; }
                } else if (type === 'aborted') {
                    this._setFullAutoBadge('ABORTED');
                    this._fullautoLog('Aborted: ' + (data.reason || ''));
                    if (this._fullAutoSSE) { this._fullAutoSSE.close(); this._fullAutoSSE = null; }
                } else if (type === 'error') {
                    this._setFullAutoBadge('ERROR');
                    this._fullautoLog('ERROR: ' + data.error);
                    this.showNotification('Training error: ' + data.error, 'error');
                    if (this._fullAutoSSE) { this._fullAutoSSE.close(); this._fullAutoSSE = null; }
                }
            } catch (e) { /* ignore */ }
        };
        this._fullAutoSSE.onerror = () => { if (this._fullAutoSSE) { this._fullAutoSSE.close(); this._fullAutoSSE = null; } };
    }

    // =========================================================================
    // DESKTOP GUI AUTOMATION & MCP LAYER HANDLERS
    // =========================================================================

    openDesktopMcpModal() {
        const modal = document.getElementById('desktop-mcp-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.refreshDesktopWindows();
            this.loadMcpStatus();
        }
    }

    closeDesktopMcpModal() {
        const modal = document.getElementById('desktop-mcp-modal');
        if (modal) modal.classList.add('hidden');
    }

    switchDesktopTab(tab) {
        const tabs = ['windows', 'actions', 'mcp'];
        tabs.forEach(t => {
            const btn = document.getElementById(`tab-btn-desktop-${t === 'windows' ? 'wins' : t}`);
            const content = document.getElementById(`desktop-tab-${t}`);
            if (btn) btn.classList.toggle('active', t === tab);
            if (content) content.classList.toggle('hidden', t !== tab);
        });
    }

    async refreshDesktopWindows() {
        const listContainer = document.getElementById('desktop-windows-list');
        const countBadge = document.getElementById('desktop-window-count');
        if (!listContainer) return;

        listContainer.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Scanning desktop windows...</div>';

        try {
            const res = await fetch('/api/computer/windows?visible_only=true');
            const data = await res.json();
            if (data.status === 'success' && data.windows) {
                if (countBadge) countBadge.textContent = `(${data.count} detected)`;
                if (data.windows.length === 0) {
                    listContainer.innerHTML = '<div style="grid-column: 1/-1; color: #64748b; text-align: center; padding: 24px;">No active top-level windows detected.</div>';
                    return;
                }

                listContainer.innerHTML = data.windows.map(w => `
                    <div style="background: rgba(20, 25, 36, 0.85); border: 1px solid #283347; border-radius: 10px; padding: 12px; display: flex; flex-direction: column; justify-content: space-between; gap: 8px;">
                        <div>
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-size: 0.72rem; color: #38bdf8; font-family: var(--font-code); font-weight: 600;">${w.process_name || 'App'}</span>
                                <span style="font-size: 0.68rem; color: #64748b; font-family: var(--font-code);">PID: ${w.pid}</span>
                            </div>
                            <div style="font-size: 0.88rem; font-weight: 600; color: #fff; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;" title="${w.title}">
                                ${w.title}
                            </div>
                            <div style="font-size: 0.7rem; color: #64748b; margin-top: 4px;">
                                Size: ${w.rect ? `${w.rect.width}x${w.rect.height}` : 'N/A'} ${w.is_minimized ? '(Minimized)' : ''}
                            </div>
                        </div>
                        <div style="display: flex; gap: 6px; margin-top: 6px;">
                            <button class="primary-btn btn-sm" style="flex: 1; padding: 6px;" onclick="ChatApp.focusDesktopWindow('${w.hwnd}')">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i> Focus
                            </button>
                            <button class="secondary-btn btn-sm" style="padding: 6px 10px;" onclick="ChatApp.sendDesktopAction('close', {target: '${w.hwnd}'})" title="Close Window">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                listContainer.innerHTML = `<div style="grid-column: 1/-1; color: #ef4444; padding: 16px;">Failed to scan windows: ${data.message || 'Unknown error'}</div>`;
            }
        } catch (e) {
            listContainer.innerHTML = `<div style="grid-column: 1/-1; color: #ef4444; padding: 16px;">Network error: ${e.message}</div>`;
        }
    }

    async focusDesktopWindow(target) {
        try {
            const res = await fetch('/api/computer/focus', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            });
            const data = await res.json();
            if (data.status === 'success') {
                this.showNotification(`Focused window: ${target}`, 'success');
                setTimeout(() => this.refreshDesktopWindows(), 400);
            } else {
                this.showNotification(`Failed to focus: ${data.message || 'Window not found'}`, 'error');
            }
        } catch (e) {
            this.showNotification(`Error: ${e.message}`, 'error');
        }
    }

    async sendDesktopAction(action, params = {}) {
        try {
            const res = await fetch('/api/computer/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, params })
            });
            const data = await res.json();
            if (data.status === 'success') {
                this.showNotification(`Desktop Action '${action}' executed`, 'success');
            } else {
                this.showNotification(`Action failed: ${data.error || 'Execution error'}`, 'error');
            }
        } catch (e) {
            this.showNotification(`Error: ${e.message}`, 'error');
        }
    }

    async sendDesktopType() {
        const input = document.getElementById('desktop-type-input');
        if (!input || !input.value.trim()) return;
        const text = input.value;
        await this.sendDesktopAction('type', { text, delay_ms: 15 });
        input.value = '';
    }

    async sendDesktopHotkey(keys) {
        await this.sendDesktopAction('hotkey', { keys });
    }

    async captureDesktopScreen() {
        const previewEl = document.getElementById('desktop-screen-preview');
        if (!previewEl) return;
        previewEl.innerHTML = '<span style="color: #38bdf8;"><i class="fa-solid fa-spinner fa-spin"></i> Capturing desktop screen...</span>';

        try {
            const res = await fetch('/api/computer/screenshot?format=base64');
            const data = await res.json();
            if (data.status === 'success' && data.image_data) {
                previewEl.innerHTML = `
                    <img src="${data.image_data}" alt="Desktop Screenshot" style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 6px; cursor: pointer;" onclick="window.open(this.src)">
                `;
                this.showNotification(`Desktop screenshot captured (${data.width}x${data.height})`, 'success');
            } else {
                previewEl.innerHTML = `<span style="color: #ef4444;">Capture failed: ${data.message || 'Unknown error'}</span>`;
            }
        } catch (e) {
            previewEl.innerHTML = `<span style="color: #ef4444;">Error: ${e.message}</span>`;
        }
    }

    async loadMcpStatus() {
        const snippetEl = document.getElementById('mcp-config-snippet');
        if (!snippetEl) return;

        try {
            const res = await fetch('/api/mcp/status');
            const data = await res.json();
            if (data.client_config) {
                snippetEl.textContent = JSON.stringify(data.client_config, null, 2);
            }
        } catch (e) {
            snippetEl.textContent = '// Could not load MCP configuration from backend.';
        }
    }

    copyMcpConfig() {
        const snippetEl = document.getElementById('mcp-config-snippet');
        if (snippetEl && snippetEl.textContent) {
            navigator.clipboard.writeText(snippetEl.textContent);
            this.showNotification('MCP Configuration JSON copied to clipboard!', 'success');
        }
    }

    // ==========================================
    // OFFLINE IMAGE STUDIO & GALLERY LOGIC
    // ==========================================
    openImageStudio(tab = 'create') {
        const modal = document.getElementById('image-studio-modal');
        if (!modal) return;
        modal.classList.remove('hidden');
        this.switchStudioTab(tab);
        this.loadImageSettings();
        this.loadGallery();
    }

    closeImageStudio() {
        const modal = document.getElementById('image-studio-modal');
        if (modal) modal.classList.add('hidden');
    }

    switchStudioTab(tabId) {
        // Toggle tab headers
        document.querySelectorAll('#image-studio-modal .tier-tab').forEach(b => b.classList.remove('active'));
        const activeBtn = document.getElementById(`tab-btn-image-${tabId}`);
        if (activeBtn) activeBtn.classList.add('active');

        // Toggle tab panes
        document.querySelectorAll('#image-studio-modal .studio-pane').forEach(p => p.classList.add('hidden'));
        const activePane = document.getElementById(`studio-pane-${tabId}`);
        if (activePane) activePane.classList.remove('hidden');

        if (tabId === 'gallery') {
            this.loadGallery();
        } else if (tabId === 'settings') {
            this.loadImageSettings();
        }
    }

    selectImageStyle(styleName, btnEl) {
        document.querySelectorAll('#studio-style-chips .chip').forEach(c => c.classList.remove('active'));
        if (btnEl) btnEl.classList.add('active');
        this._selectedImageStyle = styleName;
    }

    async generateStudioImage() {
        const promptInput = document.getElementById('studio-prompt-input');
        const prompt = promptInput ? promptInput.value.trim() : '';
        if (!prompt) {
            this.showNotification('Please enter an image prompt description.', 'warning');
            return;
        }

        const aspectSelect = document.getElementById('studio-aspect-select');
        const [widthStr, heightStr] = (aspectSelect ? aspectSelect.value : '512x512').split('x');
        const width = parseInt(widthStr, 10) || 512;
        const height = parseInt(heightStr, 10) || 512;

        const seedInput = document.getElementById('studio-seed-input');
        const seed = seedInput && seedInput.value ? parseInt(seedInput.value, 10) : null;

        const negInput = document.getElementById('studio-neg-input');
        const negativePrompt = negInput ? negInput.value.trim() : '';

        const stylePreset = this._selectedImageStyle || 'none';

        const btn = document.getElementById('studio-generate-btn');
        const outputBox = document.getElementById('studio-output-box');
        const loadingBox = document.getElementById('studio-loading');
        const resultView = document.getElementById('studio-result-view');

        if (outputBox) outputBox.classList.remove('hidden');
        if (loadingBox) loadingBox.classList.remove('hidden');
        if (resultView) resultView.classList.add('hidden');
        if (btn) btn.disabled = true;

        try {
            const res = await fetch('/api/image/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    style_preset: stylePreset,
                    width,
                    height,
                    seed,
                    negative_prompt: negativePrompt
                })
            });
            const data = await res.json();
            if (data.status === 'success' && data.image) {
                const img = data.image;
                const resultImg = document.getElementById('studio-result-img');
                const promptMeta = document.getElementById('studio-meta-prompt');
                const detailsMeta = document.getElementById('studio-meta-details');
                const dlLink = document.getElementById('studio-download-link');

                if (resultImg) resultImg.src = img.web_url;
                if (promptMeta) promptMeta.textContent = `"${img.prompt}"`;
                if (detailsMeta) {
                    detailsMeta.textContent = `Resolution: ${img.width}×${img.height}px | Seed: ${img.seed} | Latency: ${img.generation_time_sec}s | Engine: ${img.engine}`;
                }
                if (dlLink) {
                    dlLink.href = img.web_url;
                    dlLink.download = `void_${img.image_id}.png`;
                }

                this._lastGeneratedPrompt = img.prompt;

                if (loadingBox) loadingBox.classList.add('hidden');
                if (resultView) resultView.classList.remove('hidden');
                this.showNotification('Image generated offline successfully!', 'success');
                this.loadGallery();
            } else {
                throw new Error(data.message || 'Generation failed');
            }
        } catch (e) {
            if (loadingBox) loadingBox.classList.add('hidden');
            this.showNotification(`Error: ${e.message}`, 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    copyGeneratedPrompt() {
        if (this._lastGeneratedPrompt) {
            navigator.clipboard.writeText(this._lastGeneratedPrompt);
            this.showNotification('Prompt copied to clipboard!', 'success');
        }
    }

    async loadGallery(query = '') {
        const grid = document.getElementById('studio-gallery-grid');
        const badgeCount = document.getElementById('gallery-badge-count');
        if (!grid) return;

        try {
            const url = query ? `/api/image/gallery?q=${encodeURIComponent(query)}` : '/api/image/gallery';
            const res = await fetch(url);
            const data = await res.json();

            if (data.status === 'success') {
                const items = data.items || [];
                if (badgeCount) badgeCount.textContent = data.total || items.length;

                if (items.length === 0) {
                    grid.innerHTML = `<div style="color: #94a3b8; font-size: 0.88rem; grid-column: 1/-1; text-align: center; padding: 40px 0;">No offline images generated yet. Go to "Synthesize Image" to create one!</div>`;
                    return;
                }

                grid.innerHTML = items.map(it => {
                    const dateStr = new Date(it.timestamp * 1000).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                    let expiryBadge = '';
                    if (it.expires_at) {
                        const daysLeft = Math.max(0, Math.round((it.expires_at - Date.now() / 1000) / 86400));
                        expiryBadge = `<span style="font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; background: rgba(234, 179, 8, 0.2); color: #facc15;"><i class="fa-solid fa-hourglass-half"></i> ${daysLeft}d left</span>`;
                    }
                    const cleanPrompt = (it.prompt || 'Artwork').replace(/"/g, '&quot;');
                    return `
                        <div class="gallery-card" style="background: #0d111a; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; transition: transform 0.2s, border-color 0.2s;">
                            <div style="position: relative; height: 160px; background: #000; overflow: hidden; cursor: pointer;" onclick="window.open('${it.web_url}', '_blank')">
                                <img src="${it.web_url}" alt="${cleanPrompt}" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                <div style="position: absolute; top: 6px; right: 6px; display: flex; gap: 4px;">
                                    ${expiryBadge}
                                </div>
                            </div>
                            <div style="padding: 10px; flex: 1; display: flex; flex-direction: column; justify-content: space-between;">
                                <div>
                                    <div style="font-size: 0.82rem; font-weight: 600; color: #fff; margin-bottom: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${cleanPrompt}">
                                        ${cleanPrompt}
                                    </div>
                                    <div style="font-size: 0.72rem; color: #64748b; margin-bottom: 8px;">
                                        ${dateStr} • ${it.width}×${it.height}
                                    </div>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 6px;">
                                    <button class="icon-btn" onclick="navigator.clipboard.writeText('${cleanPrompt}'); ChatApp.showNotification('Prompt copied!', 'success')" title="Copy Prompt" style="padding: 4px 6px; font-size: 0.78rem;"><i class="fa-solid fa-copy"></i></button>
                                    <a href="${it.web_url}" download="void_${it.image_id}.png" class="icon-btn" title="Download Image" style="padding: 4px 6px; font-size: 0.78rem; text-decoration: none; color: #38bdf8;"><i class="fa-solid fa-download"></i></a>
                                    <button class="icon-btn" onclick="ChatApp.deleteGalleryImage('${it.image_id}')" title="Delete Image" style="padding: 4px 6px; font-size: 0.78rem; color: #ef4444;"><i class="fa-solid fa-trash-can"></i></button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        } catch (e) {
            console.error('Error loading gallery:', e);
        }
    }

    searchGallery(query) {
        clearTimeout(this._gallerySearchTimer);
        this._gallerySearchTimer = setTimeout(() => {
            this.loadGallery(query);
        }, 300);
    }

    async deleteGalleryImage(imageId) {
        if (!confirm('Are you sure you want to delete this generated image?')) return;
        try {
            const res = await fetch(`/api/image/${imageId}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.status === 'success') {
                this.showNotification('Image deleted successfully.', 'success');
                this.loadGallery();
            } else {
                throw new Error(data.message || 'Delete failed');
            }
        } catch (e) {
            this.showNotification(`Error: ${e.message}`, 'error');
        }
    }

    async loadImageSettings() {
        try {
            const res = await fetch('/api/image/settings');
            const data = await res.json();
            if (data.status === 'success' && data.settings) {
                const s = data.settings;
                const daysInput = document.getElementById('setting-retention-days');
                const autoPurgeCb = document.getElementById('setting-autopurge-enabled');
                const noticeEl = document.getElementById('gallery-retention-notice');

                if (daysInput) daysInput.value = s.retention_days ?? 7;
                if (autoPurgeCb) autoPurgeCb.checked = s.auto_purge_enabled ?? true;
                if (noticeEl) {
                    const days = s.retention_days ?? 7;
                    noticeEl.innerHTML = days > 0 ?
                        `<i class="fa-solid fa-shield-halved" style="color: #10b981;"></i> Auto-purge: ${days} days` :
                        `<i class="fa-solid fa-infinity" style="color: #38bdf8;"></i> Permanent Retention`;
                }
            }
        } catch (e) {
            console.error('Error loading image settings:', e);
        }
    }

    async saveImageSettings() {
        const daysInput = document.getElementById('setting-retention-days');
        const autoPurgeCb = document.getElementById('setting-autopurge-enabled');

        const retentionDays = daysInput ? parseInt(daysInput.value, 10) : 7;
        const autoPurgeEnabled = autoPurgeCb ? autoPurgeCb.checked : true;

        try {
            const res = await fetch('/api/image/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    retention_days: retentionDays,
                    auto_purge_enabled: autoPurgeEnabled
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                this.showNotification('Retention policy updated successfully!', 'success');
                this.loadImageSettings();
                this.loadGallery();
            }
        } catch (e) {
            this.showNotification(`Error saving settings: ${e.message}`, 'error');
        }
    }

    async triggerPurgeNow() {
        if (!confirm('Purge all images older than your retention policy now?')) return;
        try {
            const res = await fetch('/api/image/purge', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') {
                this.showNotification(`Purge complete: Removed ${data.pruned_count} expired images.`, 'success');
                this.loadGallery();
            }
        } catch (e) {
            this.showNotification(`Purge error: ${e.message}`, 'error');
        }
    }
}

// Initialize App & bind to window
const ChatApp = new ChatInterface();
window.ChatApp = ChatApp;


