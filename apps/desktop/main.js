// Chill desktop shell: serves the Expo web export from 127.0.0.1 (a secure
// context, so the microphone works) and shows it in a window. Same code as mobile.
const { app, BrowserWindow, session, shell } = require('electron');
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = app.isPackaged
  ? path.join(process.resourcesPath, 'web')
  : path.join(__dirname, '..', 'mobile', 'dist');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.ico': 'image/x-icon', '.ttf': 'font/ttf', '.svg': 'image/svg+xml' };

function serve() {
  const server = http.createServer((req, res) => {
    const clean = decodeURIComponent(req.url.split('?')[0]);
    let file = path.normalize(path.join(ROOT, clean));
    if (!file.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      const page = path.join(file, 'index.html');
      file = fs.existsSync(page) ? page : fs.existsSync(file + '.html') ? file + '.html' : path.join(ROOT, 'index.html');
    }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok(server.address().port)));
}

app.whenReady().then(async () => {
  const port = await serve();
  const origin = `http://127.0.0.1:${port}`;
  // Only Chill's own page may use the microphone, and only because the user taps to speak.
  session.defaultSession.setPermissionRequestHandler((wc, permission, cb) =>
    cb(permission === 'media' && wc.getURL().startsWith(origin)));
  const win = new BrowserWindow({
    width: 1180, height: 800, minWidth: 420, minHeight: 640,
    title: 'Chill', backgroundColor: '#F6F0E6',
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  win.loadURL(origin);
});

app.on('window-all-closed', () => app.quit());
