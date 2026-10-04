const { app, BrowserWindow, Menu, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow = null;
let pythonProcess = null;
const SERVER_URL = 'http://127.0.0.1:5000';

// Enable audio playback without autoplay restrictions
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
app.commandLine.appendSwitch('disable-features', 'HardwareMediaKeyHandling');

// Enforce single-instance lock to prevent Windows cache lock conflicts (0x5)
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  console.log('[Electron] Another instance is already running. Quitting duplicate process.');
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
      mainWindow.webContents.focus();
      mainWindow.webContents.executeJavaScript(`
        const el = document.getElementById('user-input');
        if (el) { el.focus(); }
      `).catch(() => {});
    }
  });
}

// Register standard Edit and Navigation shortcuts for Electron
function setupApplicationMenu() {
  const template = [
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'delete' },
        { role: 'selectAll' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function checkServerReady(timeoutMs = 120000) {
  const startTime = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get(SERVER_URL, (res) => {
        if (res.statusCode === 200 || res.statusCode === 302 || res.statusCode === 404) {
          resolve(true);
        } else {
          retry();
        }
      });

      req.on('error', () => {
        retry();
      });

      req.setTimeout(2000, () => {
        req.destroy();
        retry();
      });
    };

    const retry = () => {
      if (Date.now() - startTime > timeoutMs) {
        reject(new Error('V.O.I.D. Python backend startup timed out after 120s.'));
      } else {
        setTimeout(check, 1000);
      }
    };

    check();
  });
}

function startPythonBackend() {
  const projectRoot = path.resolve(__dirname, '..');
  const pythonScript = path.join(projectRoot, 'app.py');

  console.log(`[Electron] Launching V.O.I.D. backend: python -u ${pythonScript}`);
  const pythonExec = process.platform === 'win32' ? 'python' : 'python3';

  pythonProcess = spawn(pythonExec, ['-u', pythonScript], {
    cwd: projectRoot,
    stdio: 'pipe',
    shell: true,
  });

  pythonProcess.stdout.on('data', (data) => {
    const text = data.toString().trim();
    if (text) console.log(`[V.O.I.D. Backend]: ${text}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    const text = data.toString().trim();
    if (text) console.error(`[V.O.I.D. Backend Stderr]: ${text}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Electron] Python backend process exited with code ${code}`);
  });
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1300,
    height: 880,
    minWidth: 960,
    minHeight: 600,
    backgroundColor: '#121316',
    title: 'V.O.I.D. | Virtual Operator of Information & Development',
    icon: path.join(__dirname, 'icon.png'),
    autoHideMenuBar: true,
    focusable: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: false,
    },
  });

  // Sleek Splash Screen with auto-retry and official brand emblem
  let emblemB64 = '';
  try {
    const symbolPath = path.join(__dirname, '..', 'static', 'void-symbol.png');
    if (fs.existsSync(symbolPath)) {
      emblemB64 = fs.readFileSync(symbolPath).toString('base64');
    }
  } catch (err) {
    console.warn('[Electron] Could not load void-symbol.png for splash screen:', err);
  }

  mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(`
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body {
            background-color: #121316;
            color: #f0efe9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            user-select: none;
          }
          .logo-container {
            width: 110px;
            height: 86px;
            margin-bottom: 20px;
            animation: pulseGlow 2s ease-in-out infinite;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          .logo-container img {
            width: 100%;
            height: 100%;
            object-fit: contain;
          }
          @keyframes pulseGlow {
            0%, 100% { transform: scale(1); filter: drop-shadow(0 0 12px rgba(255, 85, 0, 0.45)); }
            50% { transform: scale(1.04); filter: drop-shadow(0 0 24px rgba(255, 85, 0, 0.8)); }
          }
          h2 { font-weight: 800; margin: 0 0 4px 0; color: #ff5500; letter-spacing: 4px; font-size: 26px; }
          .tagline { color: #b0b0a8; font-size: 11px; font-weight: 600; letter-spacing: 2.5px; text-transform: uppercase; margin-bottom: 18px; }
          p { color: #9e9d96; font-size: 13.5px; margin: 0; text-align: center; max-width: 420px; line-height: 1.5; }
          .status-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #ff5500;
            margin-top: 20px;
            opacity: 0.9;
          }
          .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ff5500;
            box-shadow: 0 0 8px #ff5500;
            animation: blink 1.2s infinite;
          }
          @keyframes blink { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
        </style>
      </head>
      <body>
        <div class="logo-container">
          <img src="${emblemB64 ? 'data:image/png;base64,' + emblemB64 : ''}" alt="V.O.I.D.">
        </div>
        <p>Initializing PyTorch Neural Weights, Vector Memory &amp; Local Voice Engine...</p>
        <div class="status-bar">
          <div class="status-dot"></div>
          <span>Connecting to local neural engine...</span>
        </div>
      </body>
    </html>
  `)}`);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Ensure DOM and input element receive focus when loaded
  mainWindow.webContents.on('dom-ready', () => {
    if (mainWindow) {
      mainWindow.focus();
      mainWindow.webContents.focus();
      mainWindow.webContents.executeJavaScript(`
        (function() {
          const el = document.getElementById('user-input');
          if (el) {
            el.focus();
            el.removeAttribute('disabled');
            el.removeAttribute('readonly');
          }
        })();
      `).catch(() => {});
    }
  });

  mainWindow.webContents.on('did-finish-load', () => {
    if (mainWindow) {
      mainWindow.focus();
      mainWindow.webContents.focus();
      mainWindow.webContents.executeJavaScript(`
        setTimeout(() => {
          const el = document.getElementById('user-input');
          if (el) {
            el.focus();
            el.removeAttribute('disabled');
            el.removeAttribute('readonly');
          }
        }, 150);
      `).catch(() => {});
    }
  });

  mainWindow.on('focus', () => {
    if (mainWindow && mainWindow.webContents) {
      mainWindow.webContents.focus();
    }
  });

  checkServerReady()
    .then(() => {
      console.log('[Electron] Backend confirmed ready! Loading main interface...');
      if (mainWindow) {
        mainWindow.loadURL(SERVER_URL);
      }
    })
    .catch((err) => {
      console.error(`[Electron] Startup timeout or error: ${err.message}`);
      if (mainWindow) {
        mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(`
          <!DOCTYPE html>
          <html>
            <head>
              <meta charset="UTF-8">
              <style>
                body {
                  background-color: #1b1b18;
                  color: #f0efe9;
                  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                  display: flex;
                  flex-direction: column;
                  align-items: center;
                  justify-content: center;
                  height: 100vh;
                  margin: 0;
                }
                .card {
                  background: #22221f;
                  border: 1px solid #3b3b36;
                  padding: 30px;
                  border-radius: 16px;
                  max-width: 480px;
                  text-align: center;
                }
                h3 { color: #d97757; margin-top: 0; }
                p { color: #9e9d96; font-size: 14px; line-height: 1.6; }
                button {
                  background: #d97757;
                  color: white;
                  border: none;
                  padding: 10px 20px;
                  border-radius: 8px;
                  font-weight: 600;
                  cursor: pointer;
                  margin-top: 16px;
                }
                button:hover { opacity: 0.9; }
              </style>
            </head>
            <body>
              <div class="card">
                <h3>V.O.I.D. Engine Connecting</h3>
                <p>The local Python neural engine is taking longer than usual to initialize the PyTorch model checkpoint.</p>
                <button onclick="location.href='${SERVER_URL}'">Retry Connection</button>
              </div>
            </body>
          </html>
        `)}`);
      }
    });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  setupApplicationMenu();

  // Test if server is already running on port 5000, otherwise launch it
  const req = http.get(SERVER_URL, () => {
    console.log('[Electron] Existing V.O.I.D. server detected on port 5000.');
    createMainWindow();
  });

  req.on('error', () => {
    console.log('[Electron] No active server on port 5000. Spawning Python backend...');
    startPythonBackend();
    createMainWindow();
  });

  req.setTimeout(1000, () => {
    req.destroy();
    console.log('[Electron] Server check timed out. Spawning Python backend...');
    startPythonBackend();
    createMainWindow();
  });
});

app.on('window-all-closed', () => {
  if (pythonProcess) {
    console.log('[Electron] Terminating Python backend...');
    if (process.platform === 'win32') {
      try {
        spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t'], { stdio: 'ignore' });
      } catch (_) {}
    } else {
      try {
        pythonProcess.kill('SIGTERM');
      } catch (_) {}
    }
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
