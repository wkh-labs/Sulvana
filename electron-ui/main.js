'use strict';
// Sulvana's desktop window: a Chromium (Electron) shell around the local web interface.
// It is the default shell because the JavaFX WebView cannot shape Khmer text: vowels that
// belong before or around their consonant are drawn in the wrong place there.
// The window shows only Sulvana's own interface on this computer; it has no Node access.

const { app, BrowserWindow, dialog, ipcMain, session, shell } = require('electron');
const fs = require('fs');
const path = require('path');

const APP = path.resolve(__dirname, '..');
const ORIGIN = 'http://127.0.0.1:8766';
const DATA = path.join(APP, '.runtime', 'sulvana-electron');
const LEGACY_HISTORY = path.join(DATA, 'javafx-history.json');

app.setName('Sulvana');
app.setPath('userData', DATA);

let window = null;

function createWindow() {
  window = new BrowserWindow({
    width: 1180, height: 780, minWidth: 780, minHeight: 600,
    title: 'Sulvana', icon: path.join(APP, 'sulvana-icon.png'),
    backgroundColor: '#1C1C1E', autoHideMenuBar: true, show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: false,
    },
  });
  window.removeMenu();
  window.once('ready-to-show', () => window.show());
  window.on('page-title-updated', event => event.preventDefault());
  window.on('closed', () => { window = null; });

  // Never leave Sulvana's own page, and never open other windows.
  window.webContents.on('will-navigate', (event, url) => { if (!url.startsWith(ORIGIN + '/')) event.preventDefault(); });
  // A source link the user clicks opens in their own browser; nothing else may open a window.
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });

  // The engine may still be starting: keep trying for a while instead of showing an error page.
  let attempts = 0;
  window.webContents.on('did-fail-load', (_event, _code, _description, _url, isMainFrame) => {
    if (isMainFrame && window && attempts++ < 60) setTimeout(() => window && window.loadURL(ORIGIN + '/'), 1000);
  });
  window.loadURL(ORIGIN + '/');
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!window) return;
    if (window.isMinimized()) window.restore();
    window.show();
    window.focus();
  });

  // Conversations saved by the previous (JavaFX) window, handed to the page once.
  ipcMain.on('sulvana-legacy-history', event => {
    try { event.returnValue = fs.existsSync(LEGACY_HISTORY) ? fs.readFileSync(LEGACY_HISTORY, 'utf8') : ''; }
    catch { event.returnValue = ''; }
  });
  // Coding mode: the user picks the one project folder Sulvana may work in.
  ipcMain.handle('sulvana-choose-folder', async event => {
    if (!window || event.sender !== window.webContents) return null;
    const result = await dialog.showOpenDialog(window, {
      title: 'Choose a project folder for Sulvana', defaultPath: app.getPath('home'),
      properties: ['openDirectory', 'createDirectory'],
    });
    return result.canceled || !result.filePaths.length ? null : result.filePaths[0];
  });
  ipcMain.on('sulvana-legacy-history-imported', () => {
    try { fs.renameSync(LEGACY_HISTORY, LEGACY_HISTORY + '.imported'); } catch { /* nothing to tidy up */ }
  });

  app.whenReady().then(() => {
    // The interface needs no camera, microphone, location or notifications.
    session.defaultSession.setPermissionRequestHandler((_contents, _permission, decide) => decide(false));
    // "Save image" downloads a generated picture: ask where to put it.
    session.defaultSession.on('will-download', (_event, item) => {
      item.setSaveDialogOptions({ title: 'Save generated image', defaultPath: path.join(app.getPath('pictures'), item.getFilename()) });
    });
    createWindow();
  });
  app.on('window-all-closed', () => app.quit());
}
