const fs = require('fs');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const publicDir = path.join(rootDir, 'public');

// Ensure public directory exists
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

// 1. Copy index.html
fs.copyFileSync(path.join(rootDir, 'index.html'), path.join(publicDir, 'index.html'));

// 2. Copy static assets
const staticSrc = path.join(rootDir, 'static');
const staticDest = path.join(publicDir, 'static');
fs.cpSync(staticSrc, staticDest, { recursive: true });

// 3. Copy templates
const templatesSrc = path.join(rootDir, 'templates');
const templatesDest = path.join(publicDir, 'templates');
fs.cpSync(templatesSrc, templatesDest, { recursive: true });

console.log('✓ V.O.I.D. public assets generated successfully in public/');
