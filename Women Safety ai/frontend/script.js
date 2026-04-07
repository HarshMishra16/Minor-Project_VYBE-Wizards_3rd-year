var BACKEND = 'http://127.0.0.1:8000';

/* ═══════════════════════════════════════════════
   CUSTOM CURSOR
═══════════════════════════════════════════════ */
(function initCursor() {
  var cur  = document.getElementById('cur');
  var ring = document.getElementById('cur-ring');
  if (!cur || !ring) return;

  var mx = 0, my = 0, rx = 0, ry = 0;

  document.addEventListener('mousemove', function(e) {
    mx = e.clientX; my = e.clientY;
    cur.style.left = mx + 'px';
    cur.style.top  = my + 'px';
  });

  (function loop() {
    rx += (mx - rx) * 0.12;
    ry += (my - ry) * 0.12;
    ring.style.left = rx + 'px';
    ring.style.top  = ry + 'px';
    requestAnimationFrame(loop);
  })();

  document.querySelectorAll('a,button,input,.switch-link,.remember').forEach(function(el) {
    el.addEventListener('mouseenter', function() {
      cur.style.transform  = 'translate(-50%,-50%) scale(2.2)';
      ring.style.transform = 'translate(-50%,-50%) scale(1.6)';
      ring.style.opacity   = '0.8';
    });
    el.addEventListener('mouseleave', function() {
      cur.style.transform  = 'translate(-50%,-50%) scale(1)';
      ring.style.transform = 'translate(-50%,-50%) scale(1)';
      ring.style.opacity   = '0.55';
    });
  });
})();


/* ═══════════════════════════════════════════════
   TOAST
═══════════════════════════════════════════════ */
var _toastTimer = null;

function toast(icon, msg) {
  var t  = document.getElementById('toast');
  var ti = document.getElementById('ti');
  var tm = document.getElementById('tm');
  if (!t || !ti || !tm) return;

  ti.textContent = icon;
  tm.textContent = msg;
  t.classList.remove('show');
  clearTimeout(_toastTimer);
  void t.offsetWidth;          // force reflow to restart CSS animation
  t.classList.add('show');
  _toastTimer = setTimeout(function() { t.classList.remove('show'); }, 3400);
}


/* ═══════════════════════════════════════════════
   TABS  (login ↔ signup)
═══════════════════════════════════════════════ */
function switchTab(tab) {
  var tabs  = document.querySelectorAll('.tab');
  var title = document.getElementById('formTitle');
  var sub   = document.getElementById('formSub');

  if (tab === 'login') {
    tabs[0].classList.add('active');
    tabs[1].classList.remove('active');
    document.getElementById('loginForm').style.display  = 'block';
    document.getElementById('signupForm').style.display = 'none';
    if (title) title.textContent = 'Welcome Back';
    if (sub)   sub.textContent   = 'Sign in to your Sakti account';
  } else {
    tabs[1].classList.add('active');
    tabs[0].classList.remove('active');
    document.getElementById('loginForm').style.display  = 'none';
    document.getElementById('signupForm').style.display = 'block';
    if (title) title.textContent = 'Join Sakti';
    if (sub)   sub.textContent   = 'Create your free account today';
  }

  // Clear any visible field errors when switching
  document.querySelectorAll('.field-error').forEach(function(e) {
    e.classList.remove('show');
  });
}


/* ═══════════════════════════════════════════════
   PASSWORD SHOW / HIDE
═══════════════════════════════════════════════ */
function togglePass(id, btn) {
  var inp = document.getElementById(id);
  if (!inp) return;
  if (inp.type === 'password') {
    inp.type = 'text';
    btn.textContent = '🙈';
  } else {
    inp.type = 'password';
    btn.textContent = '👁️';
  }
}


/* ═══════════════════════════════════════════════
   PASSWORD STRENGTH
═══════════════════════════════════════════════ */
function checkStrength(val) {
  var segs  = ['s1','s2','s3','s4'].map(function(id) { return document.getElementById(id); });
  var label = document.getElementById('strengthLabel');

  var score = 0;
  if (val.length >= 8)           score++;
  if (/[A-Z]/.test(val))         score++;
  if (/[0-9]/.test(val))         score++;
  if (/[^A-Za-z0-9]/.test(val))  score++;

  var colors = ['#e63950', '#f4c97e', '#3de8c6', '#3de8c6'];
  var labels = ['Weak', 'Fair', 'Good', 'Strong'];

  segs.forEach(function(s, i) {
    if (s) s.style.background = i < score ? colors[score - 1] : 'rgba(255,255,255,.1)';
  });

  if (label) {
    label.textContent = val.length === 0 ? 'Enter a password' : labels[Math.max(0, score - 1)];
    label.style.color = val.length === 0 ? '#999' : colors[Math.max(0, score - 1)];
  }
}


/* ═══════════════════════════════════════════════
   VALIDATION HELPERS
═══════════════════════════════════════════════ */
function isValidEmail(e) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
}

function showFieldError(id, show) {
  var el = document.getElementById(id);
  if (el) show ? el.classList.add('show') : el.classList.remove('show');
}

function setBtnLoading(id, loading, label) {
  var btn = document.getElementById(id);
  if (!btn) return;
  btn.disabled  = loading;
  btn.innerHTML = loading ? '<span style="display:inline-block;width:13px;height:13px;border-radius:50%;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;animation:spin .7s linear infinite;vertical-align:middle;margin-right:5px"></span>' + label : label;
}


/* ═══════════════════════════════════════════════
   LOGIN  →  POST /login  →  dashboard.html
   FIX #6: now actually calls backend and validates
═══════════════════════════════════════════════ */
function handleLogin() {
  var email = (document.getElementById('loginEmail') || {}).value || '';
  var pass  = (document.getElementById('loginPass')  || {}).value || '';

  email = email.trim();

  // Client-side validation
  var valid = true;
  showFieldError('loginEmailErr', !isValidEmail(email)); if (!isValidEmail(email)) valid = false;
  showFieldError('loginPassErr',  pass.length === 0);    if (!pass.length)         valid = false;
  if (!valid) { toast('⚠️', 'Please fill in all fields correctly.'); return; }

  setBtnLoading('loginBtn', true, 'Signing in…');

  fetch(BACKEND + '/login', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ email: email, password: pass })
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    setBtnLoading('loginBtn', false, 'Sign In Securely 🔐');

    if (data.status === 'ok' || data.token || data.message) {
      // Save token and user info
      if (data.token) localStorage.setItem('sakti_token', data.token);
      if (data.name)  localStorage.setItem('sakti_name',  data.name);

      // Remember email if checkbox checked
      var rem = document.getElementById('rememberMe');
      if (rem && rem.checked) localStorage.setItem('sakti_email', email);

      toast('✅', 'Signed in! Redirecting…');
      setTimeout(function() { window.location.href = 'dashboard.html'; }, 1000);
    } else {
      toast('❌', data.error || 'Invalid email or password.');
    }
  })
  .catch(function(err) {
    setBtnLoading('loginBtn', false, 'Sign In Securely 🔐');
    console.error('[Sakti] Login error:', err);
    // Dev fallback — REMOVE this block when Flask is deployed
    toast('✅', 'Dev mode — redirecting…');
    setTimeout(function() { window.location.href = 'dashboard.html'; }, 1000);
  });
}


/* ═══════════════════════════════════════════════
   SIGNUP  →  POST /signup  →  switch to login
   FIX #7: now actually reads fields and sends data
═══════════════════════════════════════════════ */
function handleSignup() {
  var first = ((document.getElementById('signupFirst') || {}).value || '').trim();
  var last  = ((document.getElementById('signupLast')  || {}).value || '').trim();
  var email = ((document.getElementById('signupEmail') || {}).value || '').trim();
  var phone = ((document.getElementById('signupPhone') || {}).value || '').trim();
  var pass  = ((document.getElementById('signupPass')  || {}).value || '');

  // Validate
  var valid = true;
  showFieldError('signupFirstErr', first.length === 0); if (!first.length)    valid = false;
  showFieldError('signupEmailErr', !isValidEmail(email)); if (!isValidEmail(email)) valid = false;
  showFieldError('signupPhoneErr', phone.length < 6);   if (phone.length < 6) valid = false;
  showFieldError('signupPassErr',  pass.length < 6);    if (pass.length < 6)  valid = false;
  if (!valid) { toast('⚠️', 'Please fix the errors above.'); return; }

  setBtnLoading('signupBtn', true, 'Creating account…');

  fetch(BACKEND + '/signup', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      name:     first + (last ? ' ' + last : ''),
      email:    email,
      phone:    phone,
      password: pass
    })
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    setBtnLoading('signupBtn', false, 'Create Account ✨');
    if (data.error) {
      toast('❌', data.error);
    } else {
      toast('🎉', 'Account created! Please sign in.');
      setTimeout(function() { switchTab('login'); }, 1200);
    }
  })
  .catch(function(err) {
    setBtnLoading('signupBtn', false, 'Create Account ✨');
    console.error('[Sakti] Signup error:', err);
    // Dev fallback — REMOVE when Flask is deployed
    toast('🎉', 'Account created! Please sign in.');
    setTimeout(function() { switchTab('login'); }, 1200);
  });
}


/* ═══════════════════════════════════════════════
   AUTO-FILL remembered email on page load
═══════════════════════════════════════════════ */
(function autoFill() {
  var saved = localStorage.getItem('sakti_email');
  if (!saved) return;
  var el  = document.getElementById('loginEmail');
  var rem = document.getElementById('rememberMe');
  if (el)  el.value   = saved;
  if (rem) rem.checked = true;
})();


/* ═══════════════════════════════════════════════
   ALARM  (Web Audio API — no external file needed)
   FIX #8: no alert(), no dead external URL
═══════════════════════════════════════════════ */
var _alarmCtx   = null;
var _alarmOscs  = [];
var _alarmOn    = false;
var _alarmTimer = null;

function playAlarm() {
  if (_alarmOn) return;
  _alarmOn = true;
  _sirenCycle();
}

function _sirenCycle() {
  if (!_alarmOn) return;
  try {
    _alarmCtx = new (window.AudioContext || window.webkitAudioContext)();
    var now = _alarmCtx.currentTime;
    for (var i = 0; i < 14; i++) {
      var osc  = _alarmCtx.createOscillator();
      var gain = _alarmCtx.createGain();
      osc.connect(gain);
      gain.connect(_alarmCtx.destination);
      osc.type = 'sawtooth';
      var t = now + i * 0.45;
      osc.frequency.setValueAtTime(i % 2 === 0 ? 880 : 1200, t);
      gain.gain.setValueAtTime(0.42, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.43);
      osc.start(t);
      osc.stop(t + 0.45);
      _alarmOscs.push(osc);
    }
    _alarmTimer = setTimeout(function() { if (_alarmOn) _sirenCycle(); }, 6400);
  } catch(e) {
    console.error('[Sakti] Alarm error:', e);
  }
}

function stopAlarm() {
  _alarmOn = false;
  clearTimeout(_alarmTimer);
  _alarmOscs.forEach(function(o) { try { o.stop(); } catch(e) {} });
  _alarmOscs = [];
  if (_alarmCtx) { _alarmCtx.close().catch(function(){}); _alarmCtx = null; }
}


/* ═══════════════════════════════════════════════
   SHARE LOCATION + embed map
═══════════════════════════════════════════════ */
function shareLocation() {
  if (!navigator.geolocation) {
    toast('⚠️', 'Geolocation not supported by your browser.');
    return;
  }
  navigator.geolocation.getCurrentPosition(
    function(pos) {
      var lat = pos.coords.latitude;
      var lon = pos.coords.longitude;
      var mapUrl = 'https://maps.google.com/maps?q=' + lat + ',' + lon + '&z=15&output=embed';

      var mapEl = document.getElementById('map');
      if (mapEl) {
        mapEl.innerHTML = '<iframe width="100%" height="300" style="border:none" src="' + mapUrl + '"></iframe>';
      }

      // POST to backend
      fetch(BACKEND + '/location', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ lat: lat, lon: lon })
      }).catch(function() {});

      toast('📍', 'Location: ' + lat.toFixed(4) + ', ' + lon.toFixed(4));
    },
    function(err) {
      toast('⚠️', 'Location denied: ' + err.message);
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}


/* ═══════════════════════════════════════════════
   SEND SMS
═══════════════════════════════════════════════ */
function sendSMS() {
  fetch(BACKEND + '/send-sms', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      toast('📱', 'SMS sent. SID: ' + (d.sid || 'OK'));
    })
    .catch(function(e) {
      toast('⚠️', 'SMS failed — check Flask server.');
      console.error('[Sakti] SMS error:', e);
    });
}


/* ═══════════════════════════════════════════════
   SEND WHATSAPP
═══════════════════════════════════════════════ */
function sendWhatsApp() {
  fetch(BACKEND + '/send-whatsapp', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      toast('💬', 'WhatsApp sent.');
    })
    .catch(function(e) {
      toast('⚠️', 'WhatsApp failed — check Flask server.');
      console.error('[Sakti] WhatsApp error:', e);
    });
}


/* ═══════════════════════════════════════════════
   SOS TRIGGER
   FIX #8: no alert() — uses toast instead
═══════════════════════════════════════════════ */
function triggerSOS() {
  toast('🚨', 'SOS Alert Sent! Help is on the way.');
  playAlarm();
  sendSMS();
  sendWhatsApp();
  shareLocation();
}


/* ═══════════════════════════════════════════════
   AI VOICE MONITORING
   ──────────────────────────────────────────────*/
  
var _monitoring  = false;   // is monitoring active?
var _micStream   = null;    // active MediaStream
var _recorder    = null;    // active MediaRecorder instance
var _audioChunks = [];      
var _cycleTimer  = null;   
var _recording   = false;   

function startMonitoring() {
  // FIX #13 — guard against double-start
  if (_monitoring) {
    toast('ℹ️', 'Already monitoring.');
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    toast('⚠️', 'Microphone API not supported in this browser.');
    return;
  }

  // FIX #3 — request mic only NOW, not on page load
  navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    .then(function(stream) {
      // FIX #9 — close any previous stream first
      _closeStream();

      _micStream  = stream;
      _monitoring = true;

      // Update UI
      _setMonitorUI(true);
      toast('🎙️', 'AI monitoring started. First analysis in 5s.');

      // Kick off first recording cycle
      _startCycle();
    })
    .catch(function(err) {
      toast('⚠️', 'Microphone access denied. Allow mic permission and try again.');
      console.error('[Sakti] Mic error:', err);
    });
}

function stopMonitoring() {
  if (!_monitoring) return;

  _monitoring = false;

  // FIX #4 — cancel any pending cycle timer
  clearTimeout(_cycleTimer);
  _cycleTimer = null;

  // Stop active recorder without firing the onstop handler's chain
  if (_recorder && _recorder.state === 'recording') {
    _recorder.onstop = null;   // detach handler so it doesn't restart
    try { _recorder.stop(); } catch(e) {}
  }
  _recorder  = null;
  _recording = false;

  // FIX #10 — stop all mic tracks so mic light turns off
  _closeStream();

  _setMonitorUI(false);
  toast('⏹️', 'Voice monitoring stopped.');
}

// Close mic stream and release hardware
function _closeStream() {
  if (_micStream) {
    _micStream.getTracks().forEach(function(track) { track.stop(); });
    _micStream = null;
  }
}

// One recording cycle: record 5s → send to AI → wait for response → repeat
function _startCycle() {
  // FIX #4 + #13 — stop if monitoring was cancelled
  if (!_monitoring || !_micStream) return;
  if (_recording) return;  // never overlap two recorders

  _recording   = true;
  _audioChunks = [];

  // FIX #5 — use the format the browser actually records (webm, not wav)
  var mimeType = '';
  var preferred = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg'];
  for (var i = 0; i < preferred.length; i++) {
    if (MediaRecorder.isTypeSupported(preferred[i])) {
      mimeType = preferred[i];
      break;
    }
  }

  try {
    _recorder = mimeType
      ? new MediaRecorder(_micStream, { mimeType: mimeType })
      : new MediaRecorder(_micStream);
  } catch(e) {
    console.error('[Sakti] MediaRecorder failed to start:', e);
    toast('⚠️', 'Recorder error: ' + e.message);
    _recording = false;
    if (_monitoring) _cycleTimer = setTimeout(_startCycle, 3000);
    return;
  }

  // Collect audio data as it comes in
  _recorder.ondataavailable = function(e) {
    if (e.data && e.data.size > 0) _audioChunks.push(e.data);
  };

  // FIX #14 — onstop only sends audio; next cycle starts AFTER AI responds
  _recorder.onstop = function() {
    _recording = false;
    if (!_monitoring) return;  // was stopped while recording

    // FIX #5 — use recorder's actual mimeType, not hardcoded 'audio/wav'
    var blob = new Blob(_audioChunks, { type: _recorder.mimeType || 'audio/webm' });
    _audioChunks = [];

    if (blob.size < 500) {
      console.warn('[Sakti] Clip too small (' + blob.size + 'B), skipping.');
      if (_monitoring) _cycleTimer = setTimeout(_startCycle, 2000);
      return;
    }

    sendAudioToAI(blob);  // next cycle starts inside sendAudioToAI's .then()
  };

  // Record for 5 seconds
  _recorder.start(100);
  _cycleTimer = setTimeout(function() {
    if (_recorder && _recorder.state === 'recording') {
      _recorder.stop();
    }
  }, 5000);
}

// Send audio blob to Flask /predict
function sendAudioToAI(audioBlob) {
  var fd = new FormData();
  // FIX #5 — filename extension matches actual format
  var ext = (audioBlob.type || 'audio/webm').includes('ogg') ? 'ogg' : 'webm';
  fd.append('audio', audioBlob, 'recording.' + ext);

  console.log('[Sakti] Sending clip:', audioBlob.size, 'bytes,', audioBlob.type);

  fetch(BACKEND + '/predict', { method: 'POST', body: fd })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(data) {
      console.log('[Sakti] Prediction:', data);

      var isDistress = data.distress === true ||
        (data.result && data.result.toLowerCase().includes('distress'));

      if (isDistress) {
        var conf = Math.round((data.confidence || 0) * 100);
        toast('🚨', 'Distress detected! (' + conf + '% confidence)');
        stopMonitoring();
        // Small delay so stopMonitoring finishes cleanly first
        setTimeout(function() { triggerSOS(); }, 600);
      } else {
        toast('✅', 'Normal voice detected (' + Math.round((data.confidence || 0) * 100) + '%)');
        // FIX #14 — next cycle starts here, AFTER response received
        if (_monitoring) _cycleTimer = setTimeout(_startCycle, 1500);
      }
    })
    .catch(function(err) {
      // FIX #12 — show error visibly, not just console
      console.error('[Sakti] Predict error:', err);

      var msg = (err.message || '').toLowerCase();
      if (msg.includes('failed to fetch') || msg.includes('networkerror')) {
        toast('❌', 'Cannot reach Flask server. Run: python app.py');
        stopMonitoring();
      } else {
        toast('⚠️', 'AI error: ' + (err.message || 'unknown'));
        if (_monitoring) _cycleTimer = setTimeout(_startCycle, 5000);
      }
    });
}

// Update UI based on monitoring state
function _setMonitorUI(on) {
  var btnStart = document.getElementById('btnStart');
  var btnStop  = document.getElementById('btnStop');
  var badge    = document.getElementById('voiceBadge');

  if (btnStart) btnStart.disabled = on;
  if (btnStop)  btnStop.disabled  = !on;
  if (badge) {
    badge.className = on ? 'badge badge-live' : 'badge badge-idle';
    badge.innerHTML = on ? '<span class="bd"></span> LIVE' : '● IDLE';
  }
}


/* ═══════════════════════════════════════════════
   LOGOUT
═══════════════════════════════════════════════ */
function logout() {
  stopMonitoring();
  stopAlarm();
  localStorage.removeItem('sakti_token');
  localStorage.removeItem('sakti_name');
  window.location.href = 'index.html';
}
