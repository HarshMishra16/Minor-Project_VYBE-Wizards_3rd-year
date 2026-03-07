
  /* CURSOR */
  const cur=document.getElementById('cur'), ring=document.getElementById('cur-ring');
  let mx=0,my=0,rx=0,ry=0;
  document.addEventListener('mousemove',e=>{mx=e.clientX;my=e.clientY;cur.style.left=mx+'px';cur.style.top=my+'px';});
  (function loop(){rx+=(mx-rx)*.12;ry+=(my-ry)*.12;ring.style.left=rx+'px';ring.style.top=ry+'px';requestAnimationFrame(loop);})();
  document.querySelectorAll('a,button,input,.switch-link,.remember').forEach(el=>{
    el.addEventListener('mouseenter',()=>{cur.style.transform='translate(-50%,-50%) scale(2.2)';ring.style.transform='translate(-50%,-50%) scale(1.6)';ring.style.opacity='.8';});
    el.addEventListener('mouseleave',()=>{cur.style.transform='translate(-50%,-50%) scale(1)';ring.style.transform='translate(-50%,-50%) scale(1)';ring.style.opacity='.55';});
  });

  /* TABS */
  function switchTab(tab) {
    const tabs = document.querySelectorAll('.tab');
    const title = document.getElementById('formTitle');
    const sub = document.getElementById('formSub');
    if (tab === 'login') {
      tabs[0].classList.add('active'); tabs[1].classList.remove('active');
      document.getElementById('loginForm').style.display = 'block';
      document.getElementById('signupForm').style.display = 'none';
      title.textContent = 'Welcome Back'; sub.textContent = 'Sign in to your SafeHer account';
    } else {
      tabs[1].classList.add('active'); tabs[0].classList.remove('active');
      document.getElementById('loginForm').style.display = 'none';
      document.getElementById('signupForm').style.display = 'block';
      title.textContent = 'Join 💕Ṧά𝕜𝓽ⲓ💖'; sub.textContent = 'Create your free account today';
    }
  }

  /* TOGGLE PASSWORD */
  function togglePass(id, btn) {
    const inp = document.getElementById(id);
    if (inp.type === 'password') { inp.type = 'text'; btn.textContent = '🙈'; }
    else { inp.type = 'password'; btn.textContent = '👁️'; }
  }

  /* PASSWORD STRENGTH */
  function checkStrength(val) {
    const segs = [document.getElementById('s1'),document.getElementById('s2'),document.getElementById('s3'),document.getElementById('s4')];
    const label = document.getElementById('strengthLabel');
    let score = 0;
    if (val.length >= 8) score++;
    if (/[A-Z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;
    const colors = ['#e63950','#f4c97e','#3de8c6','#3de8c6'];
    const labels = ['Weak','Fair','Good','Strong'];
    segs.forEach((s,i) => s.style.background = i < score ? colors[score-1] : 'rgba(255,255,255,.1)');
    label.textContent = val.length === 0 ? 'Enter a password' : (score === 0 ? 'Too weak' : labels[score-1]);
    label.style.color = val.length === 0 ? 'var(--muted)' : colors[Math.max(0,score-1)];
  }

  /* TOAST */
  let tt;
  function toast(icon, msg) {
    const t = document.getElementById('toast');
    document.getElementById('ti').textContent = icon;
    document.getElementById('tm').textContent = msg;
    t.classList.remove('show'); clearTimeout(tt); void t.offsetWidth;
    t.classList.add('show');
    tt = setTimeout(() => t.classList.remove('show'), 3400);
  }

  /* LOGIN */
  function handleLogin() {
    const email = document.getElementById('loginEmail').value;
    const pass = document.getElementById('loginPass').value;
    if (!email || !pass) { toast('⚠️','Please fill in all fields.'); return; }
    toast('⏳','Signing you in...');
    setTimeout(() => { window.location.href = 'dashboard.html'; }, 1200);
  }

  /* SIGNUP */
  function handleSignup() {
    toast('⏳','Creating your account...');
    setTimeout(() => { window.location.href = 'dashboard.html'; }, 1200);
  }
