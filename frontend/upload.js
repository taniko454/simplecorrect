/* global window, fetch, FileReader */
const fileInput   = document.getElementById('fileInput');
const fileNameLbl = document.getElementById('fileName');
const startBtn    = document.getElementById('startBtn');
const statusP     = document.getElementById('status');
const downloadA   = document.getElementById('downloadLink');

let selectedFile = null;
const API = window.APP_CONFIG.API_ENDPOINT.replace(/\/$/, ''); // trailing slash 無し

fileInput.addEventListener('change', ev => {
  selectedFile = ev.target.files[0];
  fileNameLbl.textContent = selectedFile ? selectedFile.name : '選択されていません';
  startBtn.disabled = !selectedFile;
});

startBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  startBtn.disabled = true;
  statusP.textContent = 'アップロード中...';

  // 1) presign URL 取得
  const res  = await fetch(`${API}/presign/upload?filename=${encodeURIComponent(selectedFile.name)}`);
  const { url, key } = await res.json();

  // 2) PUT アップロード
  await fetch(url, { method: 'PUT', body: selectedFile });

  statusP.textContent = '校正中......';
  pollForResult(key);
});

async function pollForResult(inputKey) {
  const pollInterval = 3000;
  const res = await fetch(`${API}/presign/download?key=${encodeURIComponent(inputKey)}`);
  if (res.status === 404) {
    setTimeout(() => pollForResult(inputKey), pollInterval);
    return;
  }

  const { url } = await res.json();
  statusP.textContent = '完成しました！';
  downloadA.href      = url;
  downloadA.classList.remove('is-hidden');
}
