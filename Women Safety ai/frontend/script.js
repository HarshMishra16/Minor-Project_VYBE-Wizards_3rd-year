/* =========================
CUSTOM CURSOR
========================= */

const cur = document.getElementById('cur');
const ring = document.getElementById('cur-ring');

let mx = 0, my = 0, rx = 0, ry = 0;

document.addEventListener('mousemove', e => {
mx = e.clientX;
my = e.clientY;

if(cur){
cur.style.left = mx + 'px';
cur.style.top = my + 'px';
}
});

(function loop(){
rx += (mx - rx) * .12;
ry += (my - ry) * .12;

if(ring){
ring.style.left = rx + 'px';
ring.style.top = ry + 'px';
}

requestAnimationFrame(loop);
})();

document.querySelectorAll('a,button,input,.switch-link,.remember').forEach(el=>{
el.addEventListener('mouseenter',()=>{
if(cur) cur.style.transform='translate(-50%,-50%) scale(2.2)';
if(ring){
ring.style.transform='translate(-50%,-50%) scale(1.6)';
ring.style.opacity='.8';
}
});

el.addEventListener('mouseleave',()=>{
if(cur) cur.style.transform='translate(-50%,-50%) scale(1)';
if(ring){
ring.style.transform='translate(-50%,-50%) scale(1)';
ring.style.opacity='.55';
}
});
});

/* =========================
TABS (LOGIN / SIGNUP)
========================= */

function switchTab(tab) {

const tabs = document.querySelectorAll('.tab');
const title = document.getElementById('formTitle');
const sub = document.getElementById('formSub');

if (tab === 'login') {


tabs[0].classList.add('active');
tabs[1].classList.remove('active');

document.getElementById('loginForm').style.display = 'block';
document.getElementById('signupForm').style.display = 'none';

title.textContent = 'Welcome Back';
sub.textContent = 'Sign in to your Sakti account';


} else {


tabs[1].classList.add('active');
tabs[0].classList.remove('active');

document.getElementById('loginForm').style.display = 'none';
document.getElementById('signupForm').style.display = 'block';

title.textContent = 'Join Sakti';
sub.textContent = 'Create your free account today';


}

}

/* =========================
PASSWORD SHOW / HIDE
========================= */

function togglePass(id, btn) {

const inp = document.getElementById(id);

if (inp.type === 'password') {
inp.type = 'text';
btn.textContent = '🙈';
}
else {
inp.type = 'password';
btn.textContent = '👁️';
}

}

/* =========================
PASSWORD STRENGTH
========================= */

function checkStrength(val){

const segs = [
document.getElementById('s1'),
document.getElementById('s2'),
document.getElementById('s3'),
document.getElementById('s4')
];

const label = document.getElementById('strengthLabel');

let score = 0;

if(val.length >= 8) score++;
if(/[A-Z]/.test(val)) score++;
if(/[0-9]/.test(val)) score++;
if(/[^A-Za-z0-9]/.test(val)) score++;

const colors = ['#e63950','#f4c97e','#3de8c6','#3de8c6'];
const labels = ['Weak','Fair','Good','Strong'];

segs.forEach((s,i)=>{
if(s) s.style.background = i < score ? colors[score-1] : 'rgba(255,255,255,.1)';
});

if(label){
label.textContent = val.length === 0 ? 'Enter a password' : labels[Math.max(0,score-1)];
label.style.color = val.length === 0 ? '#999' : colors[Math.max(0,score-1)];
}

}

/* =========================
TOAST MESSAGE
========================= */

let tt;

function toast(icon,msg){

const t = document.getElementById('toast');

document.getElementById('ti').textContent = icon;
document.getElementById('tm').textContent = msg;

t.classList.remove('show');

clearTimeout(tt);

void t.offsetWidth;

t.classList.add('show');

tt = setTimeout(()=>t.classList.remove('show'),3400);

}

/* =========================
LOGIN
========================= */

function handleLogin(){

const email = document.getElementById('loginEmail').value;
const pass = document.getElementById('loginPass').value;

if(!email || !pass){
toast('⚠️','Please fill in all fields');
return;
}

toast('⏳','Signing you in...');

setTimeout(()=>{
window.location.href = 'dashboard.html';
},1200);

}

/* =========================
SIGNUP
========================= */

function handleSignup(){

toast('⏳','Creating your account...');

setTimeout(()=>{
window.location.href = 'dashboard.html';
},1200);

}

/* =====================================
VOICE DISTRESS DETECTION SYSTEM
===================================== */

let recorder;
let audioChunks = [];

navigator.mediaDevices.getUserMedia({ audio: true })
.then(stream => {

recorder = new MediaRecorder(stream);

recorder.ondataavailable = e => {
audioChunks.push(e.data);
};

recorder.onstop = () => {


const audioBlob = new Blob(audioChunks,{type:'audio/wav'});

audioChunks = [];

sendAudioToAI(audioBlob);


};

})
.catch(err => {
console.error("Microphone access denied",err);
});

/* START RECORDING */

function startRecording(){

if(recorder){
audioChunks = [];
recorder.start();


toast("🎤","Listening for distress...");


}

}

/* STOP RECORDING */

function stopRecording(){

if(recorder){
recorder.stop();


toast("⏳","Analyzing voice...");


}

}

/* SEND AUDIO TO AI MODEL */

function sendAudioToAI(audioBlob){

const formData = new FormData();
formData.append("audio",audioBlob);

fetch("http://127.0.0.1:8000/predict",{
method:"POST",
body:formData
})
.then(res=>res.json())
.then(data=>{


console.log("AI RESULT:",data);

if(data.result === "Distress Detected"){
  triggerEmergency();
}
else{
  toast("✅","No distress detected");
}


})
.catch(err=>{
console.error(err);
});

}

/* EMERGENCY TRIGGER */

function triggerEmergency(){

toast("🚨","Distress detected!");

alert("⚠️ EMERGENCY DETECTED");

const alarm = new Audio("alarm.mp3");
alarm.play();

}

let recorder;
let audioChunks=[];
let monitoring=false;

async function startMonitoring(){

const stream = await navigator.mediaDevices.getUserMedia({audio:true});

recorder = new MediaRecorder(stream);

monitoring=true;

recorder.ondataavailable = e=>{
audioChunks.push(e.data)
};

recorder.onstop = ()=>{
const blob = new Blob(audioChunks,{type:"audio/wav"});
audioChunks=[];
sendAudioToAI(blob)

if(monitoring){
setTimeout(()=>recorder.start(),1000)
}
};

recorder.start();

setTimeout(()=>recorder.stop(),5000);

alert("AI Voice Monitoring Started")

}

function stopMonitoring(){

monitoring=false;

if(recorder){
recorder.stop()
}

alert("Monitoring Stopped")

}

function sendAudioToAI(audioBlob){

const formData=new FormData();
formData.append("audio",audioBlob);

fetch("http://127.0.0.1:8000/predict",{
method:"POST",
body:formData
})
.then(res=>res.json())
.then(data=>{

console.log(data);

if(data.result==="Distress Detected"){

triggerSOS()

}

})

.catch(err=>console.error(err))

}

function triggerSOS(){

alert("🚨 DISTRESS DETECTED! Sending SOS...")

playAlarm()

sendSMS()

shareLocation()

}

function sendSMS(){

fetch("http://127.0.0.1:8000/send-sms",{
method:"POST"
})
.then(res=>res.json())
.then(data=>console.log(data))

}

function shareLocation(){

if(!navigator.geolocation){
alert("Geolocation not supported")
return
}

navigator.geolocation.getCurrentPosition(function(pos){

const lat=pos.coords.latitude
const lon=pos.coords.longitude

const mapUrl=`https://maps.google.com/maps?q=${lat},${lon}&z=15&output=embed`

document.getElementById("map").innerHTML=
`<iframe width="100%" height="300" src="${mapUrl}"></iframe>`

fetch("http://127.0.0.1:8000/location",{

method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({lat:lat,lon:lon})

})

})

}

function playAlarm(){

let alarm=new Audio("https://www.soundjay.com/misc/sounds/siren-01.mp3")

alarm.play()

}
