// AI Privacy Risk Simulator - Application Logic & State Management

let currentState = {
  activeView: 'landing',
  uploadedFiles: [],
  scanInProgress: false,
  scanProgress: 68,
  privacyScore: 68,
  threats: [
    { id: 'SIM-8829-X', name: 'Llama-3-70b-Infra-Audit', score: 24, level: 'critical', date: 'Oct 24, 2026 • 14:22 UTC' },
    { id: 'SIM-8710-V', name: 'Customer-Support-Bot-V2', score: 62, level: 'medium', date: 'Oct 23, 2026 • 09:15 UTC' },
    { id: 'SIM-8692-K', name: 'Internal-HR-Assistant', score: 94, level: 'stable', date: 'Oct 22, 2026 • 18:04 UTC' }
  ]
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupDragAndDrop();
  setupGlobalSearch();
  updateRadialGauge(currentState.privacyScore);
  startLogStreaming();
});

// View Navigation Handler
function navigateTo(viewName) {
  currentState.activeView = viewName;

  // Hide all view panels
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.add('hidden');
  });

  // Show requested view
  const targetView = document.getElementById(`view-${viewName}`);
  if (targetView) {
    targetView.classList.remove('hidden');
  }

  // Toggle Sidebar visibility for landing vs app views
  const sidebar = document.getElementById('app-sidebar');
  if (sidebar) {
    if (viewName === 'landing') {
      sidebar.classList.add('hidden');
    } else {
      sidebar.classList.remove('hidden');
    }
  }

  // Update nav highlight states
  document.querySelectorAll('.nav-btn').forEach(btn => {
    if (btn.dataset.view === viewName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  document.querySelectorAll('.sidebar-item').forEach(item => {
    if (item.dataset.sidebar === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Trigger view specific logic
  if (viewName === 'results') {
    updateRadialGauge(currentState.privacyScore);
  }
}

function setupNavigation() {
  navigateTo('landing');
}

// Drag & Drop File Handler
function setupDragAndDrop() {
  const dropZone = document.getElementById('drop-zone');
  if (!dropZone) return;

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    }, false);
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
      dropZone.classList.add('bg-primary-container/20', 'border-primary');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
      dropZone.classList.remove('bg-primary-container/20', 'border-primary');
    }, false);
  });

  dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    handleFiles(files);
  });
}

function handleFileSelect(event) {
  const files = event.target.files;
  handleFiles(files);
}

function handleFiles(files) {
  if (!files || files.length === 0) return;

  const fileArray = Array.from(files);
  currentState.uploadedFiles = fileArray;

  const titleEl = document.getElementById('upload-title');
  const subtextEl = document.getElementById('upload-subtext');

  if (titleEl && subtextEl) {
    titleEl.textContent = `Selected ${fileArray.length} file(s): ${fileArray[0].name}`;
    subtextEl.textContent = `Ready for neural scanning and privacy verification.`;
  }

  triggerToast(`Loaded ${fileArray[0].name} into ephemeral sandbox.`);
}

// Start Simulation Run
function startSimulationRun() {
  if (currentState.uploadedFiles.length > 0) {
    const filename = currentState.uploadedFiles[0].name;
    const targetNameEl = document.getElementById('live-target-name');
    if (targetNameEl) targetNameEl.textContent = filename;
  }

  navigateTo('live-scan');
  triggerToast('Initiating neural privacy telemetry scan...');
  simulateLiveScanning();
}

// Live Scan Telemetry Simulation
function simulateLiveScanning() {
  currentState.scanInProgress = true;
  let progress = 10;

  const progressBar = document.getElementById('overall-progress-bar');
  const progressText = document.getElementById('overall-progress-text');
  const stage2Bar = document.getElementById('stage2-bar');
  const stage3Bar = document.getElementById('stage3-bar');

  const interval = setInterval(() => {
    progress += Math.floor(Math.random() * 15) + 5;
    if (progress > 100) progress = 100;

    if (progressBar) progressBar.style.width = `${progress}%`;
    if (progressText) progressText.textContent = `${progress}%`;
    if (stage2Bar) stage2Bar.style.width = `${Math.min(100, progress + 15)}%`;
    if (stage3Bar) stage3Bar.style.width = `${Math.min(100, progress)}%`;

    appendKernelLog(`[${new Date().toLocaleTimeString()}] NEURAL_PASS_CHUNKS: ${progress}% processed...`);

    if (progress >= 100) {
      clearInterval(interval);
      currentState.scanInProgress = false;
      appendKernelLog(`[${new Date().toLocaleTimeString()}] SCAN_COMPLETE: Generating Gemini Risk Assessment...`);
      triggerToast('Scan finished. View comprehensive risk report.');

      // Update calculated privacy score randomly between 55 and 82 for demo
      currentState.privacyScore = Math.floor(Math.random() * 27) + 55;
    }
  }, 700);
}

// Update Gauge Score Animation
function updateRadialGauge(score) {
  const gaugeCircle = document.getElementById('gauge-circle');
  const scoreValue = document.getElementById('gauge-score-value');

  if (scoreValue) scoreValue.textContent = score;

  if (gaugeCircle) {
    const circumference = 282.7; // 2 * pi * r (r=45)
    const offset = circumference * (1 - score / 100);
    gaugeCircle.style.strokeDashoffset = offset;
  }
}

// Log Console Output Streamer
function startLogStreaming() {
  const sampleLogs = [
    'PARSING_SPATIAL_MESH... 14 nodes validated',
    'EXIF_GPS_EXTRACTOR: Coordinates locked (40.7128, -74.0060)',
    'OCR_PII_SCANNER: 3 string patterns evaluated',
    'DIFFERENTIAL_PRIVACY_BUDGET: ε = 0.8 enforced',
    'DECODING_PRIVACY_HEADERS... OK',
    'WASM_EPHEMERAL_WORKER: Subsystem latency 14ms'
  ];

  setInterval(() => {
    if (currentState.activeView === 'live-scan') {
      const log = sampleLogs[Math.floor(Math.random() * sampleLogs.length)];
      appendKernelLog(`[${new Date().toLocaleTimeString()}] ${log}`);

      // Random jitter for CPU & Latency
      const latencyEl = document.getElementById('live-latency');
      if (latencyEl) latencyEl.textContent = `${Math.floor(Math.random() * 6) + 12}ms`;
    }
  }, 2500);
}

function appendKernelLog(msg) {
  const consoleEl = document.getElementById('log-console');
  if (!consoleEl) return;

  const p = document.createElement('p');
  p.innerHTML = `<span class="text-primary">${msg.split(']')[0]}]</span> ${msg.split(']')[1] || ''}`;
  consoleEl.appendChild(p);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

function clearConsoleLog() {
  const consoleEl = document.getElementById('log-console');
  if (consoleEl) consoleEl.innerHTML = '';
}

// Execute Hardening Protocol Action
function executeHardeningProtocol() {
  triggerToast('Executing Automated EXIF Scrub & OCR Anonymization...');
  
  setTimeout(() => {
    currentState.privacyScore = 95;
    updateRadialGauge(95);
    triggerToast('Privacy Health Index upgraded to 95/100 (Protected)!');
  }, 1200);
}

// History Filters
function filterHistory(level) {
  document.querySelectorAll('.history-pill').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');

  document.querySelectorAll('.history-row').forEach(row => {
    if (level === 'all' || row.dataset.risk === level) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

function purgeHistoryData() {
  if (confirm('Confirm permanent deletion of all simulation history? This cannot be undone.')) {
    const tableBody = document.getElementById('history-table-body');
    if (tableBody) tableBody.innerHTML = '<tr><td colspan="5" class="py-8 text-center text-outline text-xs">All simulation history has been purged.</td></tr>';
    triggerToast('Audit trail successfully purged.');
  }
}

// Global Search Bar
function setupGlobalSearch() {
  const searchInput = document.getElementById('global-search');
  if (!searchInput) return;

  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      triggerToast(`Searching system for "${searchInput.value}"...`);
      navigateTo('history');
    }
  });
}

// Toast Notifications Helper
function triggerToast(message) {
  const toastContainer = document.getElementById('toast-container');
  const toastMsg = document.getElementById('toast-message');
  
  if (!toastContainer || !toastMsg) return;

  toastMsg.textContent = message;
  toastContainer.classList.remove('translate-y-[-20px]', 'opacity-0', 'pointer-events-none');

  setTimeout(() => {
    toastContainer.classList.add('translate-y-[-20px]', 'opacity-0', 'pointer-events-none');
  }, 3500);
}
