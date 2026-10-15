'use strict';
// Runs before Sulvana's page. It carries over the conversations saved by the previous JavaFX
// window once, and gives the page one capability: asking the user to pick a project folder.
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('sulvanaElectron', {
  chooseFolder: () => ipcRenderer.invoke('sulvana-choose-folder'),
});

const KEY = 'sulvana.desktop.v1';
try {
  if (location.origin === 'http://127.0.0.1:8766' && window.localStorage.getItem(KEY) === null) {
    const saved = ipcRenderer.sendSync('sulvana-legacy-history');
    if (saved) {
      JSON.parse(saved);   // refuse anything that is not valid JSON
      window.localStorage.setItem(KEY, saved);
      ipcRenderer.send('sulvana-legacy-history-imported');
    }
  }
} catch { /* start with an empty history rather than fail to open */ }
