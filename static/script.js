const video = document.getElementById('video');
const overlay = document.getElementById('overlay');
const ctx = overlay.getContext('2d');
const startBtn = document.getElementById('startBtn');
const captureBtn = document.getElementById('captureBtn');
const registerBtn = document.getElementById('registerBtn');
const nameInput = document.getElementById('nameInput');
const statusEl = document.getElementById('status');
const resultBox = document.getElementById('resultBox');

let stream = null;

function setStatus(msg) {
  statusEl.textContent = msg || '';
}

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
    video.srcObject = stream;
    await video.play();
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
    setStatus('Camera started');
  } catch (err) {
    console.error(err);
    setStatus('Camera error: ' + err.message);
  }
}

function grabFrameDataURL() {
  const tmp = document.createElement('canvas');
  tmp.width = video.videoWidth;
  tmp.height = video.videoHeight;
  const tctx = tmp.getContext('2d');
  tctx.drawImage(video, 0, 0, tmp.width, tmp.height);
  return tmp.toDataURL('image/png');
}

function drawBoxes(items) {
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  ctx.lineWidth = 2;
  ctx.font = '16px monospace';
  ctx.textBaseline = 'top';

  items.forEach(item => {
    const { top, right, bottom, left } = item.box;
    ctx.strokeStyle = '#22d3ee';
    ctx.strokeRect(left, top, right - left, bottom - top);
    const label = `${item.name}${item.distance !== null && item.distance !== undefined ? ` (${item.distance.toFixed(2)})` : ''}`;
    const tw = ctx.measureText(label).width + 8;
    const th = 20;
    ctx.fillStyle = '#22d3ee';
    ctx.fillRect(left, top - th, tw, th);
    ctx.fillStyle = '#000';
    ctx.fillText(label, left + 4, top - th + 2);
  });
}

async function identifyOnce() {
  const image = grabFrameDataURL();
  setStatus('Identifying...');
  resultBox.textContent = '';
  try {
    const res = await fetch('/identify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image })
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Server error');
    drawBoxes(data.results || []);
    resultBox.textContent = JSON.stringify(data, null, 2);
    setStatus(`Found ${data.count} face(s)`);
  } catch (e) {
    console.error(e);
    setStatus('Identify failed: ' + e.message);
  }
}

async function registerFace() {
  const name = nameInput.value.trim();
  if (!name) {
    setStatus('Enter a name to register');
    return;
  }
  const image = grabFrameDataURL();
  setStatus('Registering...');
  try {
    const res = await fetch('/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, image })
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Server error');
    setStatus('Registered: ' + name);
  } catch (e) {
    console.error(e);
    setStatus('Register failed: ' + e.message);
  }
}

startBtn.addEventListener('click', startCamera);
captureBtn.addEventListener('click', identifyOnce);
registerBtn.addEventListener('click', registerFace);