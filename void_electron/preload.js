// void_electron/preload.js
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('voidDesktop', {
  platform: process.platform,
  isDesktopApp: true,
});
