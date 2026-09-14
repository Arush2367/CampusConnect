const A = {
  role: 'student', signupRole: 'student', token: true, user: null, view: 'dashboard', detailId: null,
  signupVerification: { email: '', verificationId: '', retryAt: 0, expiresAt: 0 },
  filters: { floor: 'all', room: 'all', status: 'all', q: '' }, qrToken: new URLSearchParams(location.search).get('qr')
};
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>\"]/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));
const fmt = s => s ? new Date(s).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'}) : '—';
const statusLabel = s => ({available:'Vacant',occupied:'Occupied',pending:'Pending',maintenance:'Maintenance',submitted:'Submitted',assigned:'Assigned',approved:'Approved',rejected:'Rejected',cancelled:'Cancelled',expired:'Expired',in_repair:'In repair',acknowledged:'Acknowledged',reported:'Reported',resolved:'Resolved'}[s] || s);
const badgeClass = s => ({available:'green',occupied:'red',pending:'yellow',maintenance:'gray',assigned:'green',approved:'green',rejected:'red',cancelled:'gray',expired:'gray',in_repair:'yellow',acknowledged:'yellow',reported:'yellow',resolved:'green'}[s]||'gray');

const ASSET2='/CampusConnect-assets/icons/';
const DEFAULT_AVATAR=ASSET2+'custom-profile.png';
function avatarMarkup(photo,name,cls='avatar'){const src=photo||DEFAULT_AVATAR;return `<span class="${cls}"><img src="${src}" alt="Profile photo" onerror="this.onerror=null;this.src='${DEFAULT_AVATAR}'"></span>`;}

const CUSTOM_ASSET2='/CampusConnect-assets/icons/transparent/';
const ICONS={
  dashboard:'custom-dashboard.png',events:'custom-events.png',clubs:'custom-clubs.png','my-clubs':'custom-my-clubs.png',
  'campus-services':'custom-campus-services.png',locker:'custom-locker.png',lockers:'custom-locker.png',
  notifications:'custom-notifications.png',todo:'custom-to-do.png',requests:'custom-requests.png',
  profile:'custom-profile.png',lostfound:'custom-lost-and-found.png',problems:'custom-reports.png',
  students:'system-users.png',maintenance:'custom-maintenance.png',manage:'custom-settings.png',
  audit:'custom-audit-log.png',search:'custom-search.png',settings:'custom-settings.png',
  help:'custom-help-support.png',back:'custom-back.png',forward:'custom-forward.png',
  add:'custom-add-create.png',delete:'custom-delete.png',edit:'custom-edit.png',close:'custom-close.png'
};
const iconImg=(name,alt='',className='ui-icon')=>{const file=ICONS[name]||name; const src=file.startsWith('custom-')?`${CUSTOM_ASSET2}${file}`:`${ASSET2}${file}`; return `<img class="${className}" src="${src}" alt="${esc(alt)}" loading="lazy">`;};
const navIcon=(name,alt='')=>`<span class="nav-icon">${iconImg(name,alt,'nav-icon-img')}</span>`;

function toast(message, type='success'){const x=$('#toast');x.textContent=message;x.className=`toast show ${type}`;clearTimeout(toast.t);toast.t=setTimeout(()=>x.className='toast',3000)}
async function api(url, options={}){
  const headers={'Content-Type':'application/json',...(options.headers||{})};
  const res=await fetch(url,{...options,headers,credentials:'same-origin'});let data={};try{data=await res.json()}catch{}
  if(res.status===401){A.user=null;showAuth();throw new Error(data.error||'Please sign in again.')}
  if(!res.ok)throw new Error(data.error||'Something went wrong');
  return data;
}
function applyTheme(){
  const dark=localStorage.getItem('campuslock_theme')==='dark';
  document.body.classList.toggle('dark',dark);
  const themeBtn=$('#themeBtn');
  if(themeBtn){
    const img=themeBtn.querySelector('img');
    if(img) img.src=dark?`${ASSET2}misc-sun-light.png`:`${ASSET2}misc-moon-dark.png`;
    themeBtn.title=dark?'Switch to light mode':'Switch to dark mode';
  }
  const authBtn=$('#themeBtnAuth');
  if(authBtn) authBtn.innerHTML=dark?`<img src="${ASSET2}misc-sun-light.png" alt=""> Light mode`:`<img src="${ASSET2}misc-moon-dark.png" alt=""> Dark mode`;
  document.documentElement.style.colorScheme=dark?'dark':'light'
}
function toggleTheme(){localStorage.setItem('campuslock_theme',document.body.classList.contains('dark')?'light':'dark');applyTheme();if(A.user)profileThemeButtons()}
function showAuth(){$('#authScreen').classList.remove('hidden');$('#mainScreen').classList.add('hidden');$('#loginPanel').classList.remove('hidden');$('#signupPanel').classList.add('hidden');$('#otpPanel')?.classList.add('hidden');clearInterval(window.__otpTimer);role('student');applyTheme()}
function role(v){A.role=v;document.querySelectorAll('.role-btn').forEach(b=>b.classList.toggle('active',b.dataset.role===v));$('#loginRoleSelector')?.style.setProperty('--role-index',v==='student'?0:1);$('#loginIdLabel').textContent=v==='student'?'Student ID / Login ID':'Admin / Staff ID';$('#loginId').placeholder=v==='student'?'e.g. STU1001':'e.g. ADMIN001';$('#authMessage').textContent=''}
function signupRole(v){A.signupRole=v;document.querySelectorAll('.signup-role-btn').forEach(b=>b.classList.toggle('active',b.dataset.signupRole===v));$('#signupRoleSelector')?.style.setProperty('--role-index',v==='student'?0:1);const staff=v==='admin';$('#signupRoleNotice').classList.toggle('staff-mode',staff);$('#signupRoleNotice').classList.toggle('student-mode',!staff);$('#signupRoleNotice').innerHTML=staff?'<strong>Staff access request</strong><span>Staff access is never granted directly. Your request is routed to the primary administrator for review.</span>':'<strong>Student account</strong><span>Students can register directly. Your student ID can be added now or later.';$('#suBranchLabel').textContent=staff?'DEPARTMENT / BRANCH':'BRANCH';$('#suBranch').placeholder=staff?'Department / faculty area':'CSE / BBA / etc.';$('#suIdLabel').innerHTML=(staff?'STAFF / COLLEGE ID':'STUDENT / COLLEGE ID')+' <em>OPTIONAL</em>';$('#suStudentId').placeholder=staff?'e.g. FAC1026':'e.g. STU1026';$('#suSemester').required=!staff;$('#suEmail').required=!staff;$('#semesterField').classList.toggle('optional-field',staff);$('#suEmailLabel').innerHTML='EMAIL'+(staff?' <em>OPTIONAL</em>':' <em>REQUIRED</em>');$('#signupRoleHelp').textContent=staff?'Workflow: submitted → primary administrator review → approved account.':'Currently available for Dwarka Campus. Additional campuses will be added soon.';$('#signupSubmitBtn').innerHTML=staff?'Send approval request <span>→</span>':'Create account <span>→</span>'}
async function compressPhoto(file){if(!file)return null;return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{const c=document.createElement('canvas'),m=512;let w=img.width,h=img.height;if(w>h){w=m;h=Math.round(h*m/img.width)}else{h=m;w=Math.round(w*m/img.height)}c.width=w;c.height=h;c.getContext('2d').drawImage(img,0,0,w,h);resolve(c.toDataURL('image/jpeg',.78))};img.onerror=reject;const r=new FileReader();r.onload=()=>img.src=r.result;r.onerror=reject;r.readAsDataURL(file)})}
function showOtpPanel(email,verificationId,expiresIn,retryAfter){A.signupVerification={email,verificationId,retryAt:Date.now()+retryAfter*1000,expiresAt:Date.now()+expiresIn*1000};$('#signupPanel').classList.add('hidden');$('#otpPanel').classList.remove('hidden');$('#otpEmailLabel').textContent=email;$('#otpCode').value='';$('#otpMessage').textContent='';startOtpTimers();setTimeout(()=>$('#otpCode')?.focus(),80)}
function startOtpTimers(){clearInterval(window.__otpTimer);const tick=()=>{const n=Date.now(),r=Math.max(0,A.signupVerification.retryAt-n),e=Math.max(0,A.signupVerification.expiresAt-n);const b=$('#resendOtpBtn');if(b){b.disabled=r>0;b.textContent=r>0?`Resend code (${Math.ceil(r/1000)}s)`:'Resend code'}const x=$('#otpExpiryText');if(x)x.textContent=e>0?`Code expires in ${Math.ceil(e/60000)} min`:'Code expired — resend a new code.';if(e<=0&&!$('#otpMessage')?.textContent)$('#otpMessage').textContent='Code expired. Request a new one.';if(e<=0&&r<=0)clearInterval(window.__otpTimer)};tick();window.__otpTimer=setInterval(tick,1000)}
async function verifyOtp(){const b=$('#verifyOtpBtn'),otp=$('#otpCode').value.trim();if(!/^\d{6}$/.test(otp)){$('#otpMessage').textContent='Enter the 6-digit verification code.';return}b.disabled=true;$('#otpMessage').textContent='';try{const d=await api('/api/auth/verify-otp',{method:'POST',body:JSON.stringify({email:A.signupVerification.email,verificationId:A.signupVerification.verificationId,otp})});clearInterval(window.__otpTimer);$('#otpPanel').classList.add('hidden');$('#loginPanel').classList.remove('hidden');role('student');$('#loginId').value=d.loginId;$('#loginPassword').value='';$('#authMessage').className='form-message success';$('#authMessage').innerHTML=`Account created successfully! Your login ID is <b>${esc(d.loginId)}</b>. Enter your password below to sign in.`;toast('Account created successfully.');setTimeout(()=>$('#loginPassword')?.focus(),80)}catch(x){$('#otpMessage').className='form-message';$('#otpMessage').textContent=x.message;if(x.status===410)A.signupVerification.verificationId=''}finally{b.disabled=false}}
async function resendOtp(){const b=$('#resendOtpBtn');if(b.disabled)return;b.disabled=true;try{const d=await api('/api/auth/resend-otp',{method:'POST',body:JSON.stringify({email:A.signupVerification.email})});A.signupVerification.verificationId=d.verificationId;A.signupVerification.retryAt=Date.now()+d.retryAfter*1000;A.signupVerification.expiresAt=Date.now()+d.expiresIn*1000;$('#otpMessage').className='form-message success';$('#otpMessage').textContent='A new verification code has been sent.';startOtpTimers()}catch(x){$('#otpMessage').className='form-message';$('#otpMessage').textContent=x.message;startOtpTimers()}}

async function login(e){e.preventDefault();const btn=$('#loginForm .auth-cta-primary');btn.disabled=true;try{const d=await api('/api/auth/login',{method:'POST',body:JSON.stringify({role:A.role,studentId:$('#loginId').value.trim(),password:$('#loginPassword').value})});A.user=d.user;openApp();toast('Signed in successfully.')}catch(x){$('#authMessage').textContent=x.message}finally{btn.disabled=false}}
async function signup(e){e.preventDefault();const btn=$('#signupSubmitBtn');btn.disabled=true;$('#signupMessage').textContent='';try{const photo=await compressPhoto($('#suPhoto').files[0]);const d=await api('/api/auth/signup',{method:'POST',body:JSON.stringify({role:A.signupRole,name:$('#suName').value.trim(),branch:$('#suBranch').value.trim(),semester:$('#suSemester').value,campus:$('#suCampus').value,studentId:$('#suStudentId').value.trim(),mobile:$('#suMobile').value.trim(),email:$('#suEmail').value.trim(),password:$('#suPassword').value,profilePhoto:photo})});if(A.signupRole==='admin'){$('#signupMessage').className='form-message success';$('#signupMessage').innerHTML=`Request <b>${esc(d.requestCode)}</b> submitted to <b>${esc(d.assignedAdmin)}</b>. Your staff account activates only after approval.`;$('#signupForm').reset();$('#suCampus').value='Dwarka Campus';$('#campusButton').innerHTML='Dwarka Campus <span>⌄</span>';signupRole('admin');toast('Staff request submitted.');return}showOtpPanel(d.email,d.verificationId,d.expiresIn,d.retryAfter);toast('Verification code sent.')}catch(x){$('#signupMessage').className='form-message';$('#signupMessage').textContent=x.message}finally{btn.disabled=false}}

async function logout(){try{await api('/api/auth/logout',{method:'POST'})}catch{}A.user=null;showAuth()}
function permissions(){const role=A.user?.accessRole||'student';return new Set({super_admin:['view_students','view_private_student_data','view_lockers','create_lockers','modify_lockers','approve_locker_requests','manage_maintenance','review_staff_requests','manage_staff','view_audit_logs','view_notifications','manage_system_settings'],locker_manager:['view_students','view_private_student_data','view_lockers','create_lockers','modify_lockers','approve_locker_requests','release_lockers','manage_maintenance','view_audit_logs','view_notifications'],staff:['view_students','view_private_student_data','view_lockers','approve_locker_requests','release_lockers','manage_maintenance','view_notifications'],student:['view_lockers','release_lockers','view_notifications']}[role]||[])}
function can(p){return permissions().has(p)}
function openApp(){if(!A.user)return;$('#authScreen').classList.add('hidden');$('#mainScreen').classList.remove('hidden');$('#signedName').textContent=A.user.name;$('#signedRole').textContent=A.user.accessRole==='super_admin'?'Primary Administrator':A.user.accessRole==='staff'?'Staff':A.user.accessRole==='locker_manager'?'Locker Manager':'Student';$('#avatar').outerHTML=avatarMarkup(A.user.profilePhoto,A.user.name,'avatar topbar-avatar');applyTheme();nav();go(A.user.accessRole==='student'?'dashboard':'dashboard');pollNotifications();if(A.qrToken){setTimeout(()=>qrFromLanding(A.qrToken),500)}}
function nav(){
  let items;
  if(A.user.accessRole==='student') {
    items = [
      ['dashboard','Dashboard'],
      ['events','Events'],
      ['clubs','Clubs & Societies'],
      ['my-clubs','My Clubs'],
      ['lockers','Campus Lock'],
      ['notifications','Notices'],
      ['todo','To-Do'],
      ['requests','My Requests'],
      ['lostfound','Lost & Found'],
      ['problems','Report Issue']
    ];
  } else {
    items=[
      ['dashboard','Operations'],['events','Events'],['todo','To-Do'],['clubs','Clubs'],
      ['lostfound','Lost & Found'],['problems','Problems'],['lockers','All Lockers'],
      ['requests','Requests'],['students','Students'],['maintenance','Maintenance']
    ];
    if(can('create_lockers'))items.splice(6,0,['manage','Locker Management']);
    if(can('view_audit_logs'))items.push(['audit','Audit Log']);
    if(can('view_notifications'))items.push(['notifications','Notifications']);
  }
  $('#sideNav').innerHTML=items.map(([v,t])=>`<button class="nav-btn ${A.view===v?'active':''}" data-v="${v}">${navIcon(v,t)}<span class="nav-label">${esc(t)}</span></button>`).join('');
  document.querySelectorAll('.nav-btn').forEach(b=>b.onclick=()=>go(b.dataset.v));
}
function go(v){
  A.view=v;
  nav();
  const titles={
    dashboard:['CAMPUS CONNECT','Dashboard'],
    events:['CAMPUS CONNECT','Campus Events'],
    todo:['CAMPUS CONNECT','My To-Do'],
    clubs:['CAMPUS CONNECT','Clubs & Societies'],
    'my-clubs':['CAMPUS CONNECT','My Clubs'],
    'club-detail':['CAMPUS CONNECT','Club Profile'],
    lostfound:['CAMPUS CONNECT','Lost & Found'],
    problems:['CAMPUS CONNECT','Report Issue'],
    lockers:[A.user.accessRole==='student'?'CAMPUS CONNECT':'LOCKER OPERATIONS',A.user.accessRole==='student'?'Campus Lock':'All Lockers'],
    requests:[A.user.accessRole==='student'?'STUDENT PORTAL':'ADMIN PORTAL',A.user.accessRole==='student'?'My Requests':'Requests'],
    students:['ADMIN PORTAL','Student Directory'],
    maintenance:['OPERATIONS','Maintenance'],
    manage:['ADMIN PORTAL','Locker Management'],
    profile:[A.user.accessRole==='student'?'STUDENT PORTAL':'STAFF PORTAL','My Profile'],
    notifications:['CAMPUS CONNECT','Notices'],
    audit:['SECURITY','Audit Log'],
    my:['STUDENT PORTAL','My Locker'],
    'locker-detail':['LOCKER OPERATIONS','Locker Detail']
  };
  const t=titles[v]||titles.dashboard;
  $('#pageEyebrow').textContent=t[0];
  $('#pageTitle').textContent=t[1];
  $('#viewContainer').innerHTML=skeletonFor(v);
  view();
}
function skeletonFor(v){
  if(v==='dashboard')return `<div class="view"><div class="skel skel-hero"></div><div class="skel-row"><div class="skel skel-card"></div><div class="skel skel-card"></div><div class="skel skel-card"></div></div></div>`;
  return `<div class="view"><div class="skel skel-bar"></div><div class="skel-row"><div class="skel skel-card"></div><div class="skel skel-card"></div></div><div class="skel skel-block"></div></div>`;
}
async function view(){
  try{
    const m={
      dashboard:dash, lockers, requests, students, maintenance, manage, profile, notifications, audit, my, todo, 'locker-detail':lockerDetailView,
      events, clubs, 'my-clubs':myClubs, 'club-detail':clubDetailPage, lostfound, problems
    };
    if(m[A.view])await m[A.view]()
  }catch(e){
    $('#viewContainer').innerHTML=`<div class="view"><div class="panel"><div class="empty">${esc(e.message)}</div></div></div>`
  }
}
function metricCard(label,value,meta){return `<div class="stat-card"><span class="stat-label">${label}</span><strong class="stat-value">${esc(value)}</strong><span class="stat-meta">${esc(meta)}</span></div>`}
function greetingWord(){const h=new Date().getHours();if(h<12)return'Good Morning';if(h<17)return'Good Afternoon';return'Good Evening'}
const TODO_KEY='campus_connect_todos_v1';
function todoStorageKey(){const id=A.user?.id||A.user?.loginId||A.user?.studentId||'guest';return `${TODO_KEY}_${id}`}
function getTodos(){try{const key=todoStorageKey();const raw=localStorage.getItem(key);if(raw!==null)return JSON.parse(raw);const legacy=JSON.parse(localStorage.getItem(TODO_KEY)||'[]');if(legacy.length&&A.user){localStorage.setItem(key,JSON.stringify(legacy));localStorage.removeItem(TODO_KEY);return legacy}return legacy}catch{return[]}}
function saveTodos(items){localStorage.setItem(todoStorageKey(),JSON.stringify(items))}
function todoSummary(items){const pending=items.filter(t=>!t.done);const overdue=pending.filter(t=>t.due&&new Date(t.due+'T23:59:59')<new Date()).length;return {pending,overdue,done:items.length-pending.length}}
function todoCard(t){
  const repeatLabel = t.repeat?.mode && t.repeat.mode!=='none' ? ` · ↻ ${esc(t.repeat.label||t.repeat.mode)}` : '';
  const quote = t.quote ? `<em class=\"cc-todo-quote\">“${esc(t.quote)}”</em>` : '';
  return `<div class=\"cc-todo-row ${t.done?'done':''}\">
  <button class=\"cc-todo-check ${t.done?'checked':''}\" aria-label=\"${t.done?'Mark task incomplete':'Complete task'}\" onclick=\"toggleTodo('${esc(t.id)}')\">${t.done?'✓':''}</button>
  <div class=\"cc-todo-main\"><strong>${esc(t.title)}</strong><span>${t.priority==='high'?'High priority · ':''}${t.due?`Due ${esc(new Date(t.due+'T00:00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short'}))}`:'No due date'}${repeatLabel}</span>${quote}</div>
  <button class=\"cc-todo-delete\" aria-label=\"Delete task\" onclick=\"deleteTodo('${esc(t.id)}')\">×</button>
</div>`
}

function nextRecurringDate(task){
  if(!task.due || !task.repeat || task.repeat.mode==='none') return null;
  const d=new Date(task.due+'T00:00:00');
  const r=task.repeat;
  const fmtDate=x=>x.toISOString().slice(0,10);
  if(r.mode==='daily'){ d.setDate(d.getDate()+1); return fmtDate(d); }
  const pattern=r.mode==='custom' ? r.pattern : r.mode;
  if(pattern==='weekly'){
    const allowed=(r.weekdays||[1,2,3,4,5]).map(Number);
    for(let i=1;i<=14;i++){ d.setDate(d.getDate()+1); if(allowed.includes(d.getDay())) return fmtDate(d); }
  }
  if(pattern==='monthly'){
    const months=(r.months||[]).map(Number);
    for(let i=0;i<24;i++){
      d.setMonth(d.getMonth()+1);
      if(!months.length || months.includes(d.getMonth()+1)) return fmtDate(d);
    }
  }
  return null;
}
window.toggleTodo=(id)=>{
  const items=getTodos();
  const target=items.find(t=>t.id===id);
  if(!target) return;
  const wasDone=target.done;
  target.done=!wasDone;
  target.completedAt=target.done?new Date().toISOString():null;
  if(target.done){
    const next=nextRecurringDate(target);
    if(next){
      items.unshift({...target,id:crypto.randomUUID?.()||String(Date.now()+Math.random()),due:next,done:false,completedAt:null,createdAt:new Date().toISOString()});
      toast(`Next repeat scheduled for ${new Date(next+'T00:00:00').toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}.`);
    }
  }
  saveTodos(items);renderTodoInline();if(A.view==='todo')todo();
}
window.deleteTodo=(id)=>{saveTodos(getTodos().filter(t=>t.id!==id));renderTodoInline();if(A.view==='todo')todo()}
function renderTodoInline(){const el=$('#dashTodoList');if(!el)return;const items=getTodos().filter(t=>!t.done).sort((a,b)=>(a.due||'9999').localeCompare(b.due||'9999')).slice(0,4);el.innerHTML=items.length?items.map(todoCard).join(''):'<div class=\"cc-todo-empty\">Your list is clear. Add a task to keep the day moving.</div>';const c=$('#dashTodoCount');if(c){const s=todoSummary(getTodos());c.textContent=`${s.pending.length} active`;}}
function openTodoModal(){
  modal(`<div class=\"modal-head\"><h3>Add a task</h3><button id=\"closeM\" class=\"close-btn\">✕</button></div>
    <div class=\"modal-form\">
      <label>TASK TITLE *</label><input id=\"todoTitle\" placeholder=\"e.g. Submit assignment\" maxlength=\"120\">
      <label style=\"margin-top:10px;display:block;\">DUE DATE</label><input id=\"todoDue\" type=\"date\">
      <label style=\"margin-top:10px;display:block;\">PRIORITY</label><select id=\"todoPriority\"><option value=\"normal\">Normal</option><option value=\"high\">High</option><option value=\"low\">Low</option></select>
      <label style=\"margin-top:10px;display:block;\">REPETITION <em>OPTIONAL</em></label>
      <select id=\"todoRepeat\"><option value=\"none\">Does not repeat</option><option value=\"daily\">Daily</option><option value=\"weekly\">Weekly</option><option value=\"monthly\">Monthly</option><option value=\"custom\">Custom</option></select>
      <div id=\"customPatternRow\" class=\"hidden\" style=\"margin-top:8px;\">
        <label>CUSTOM REPEAT TYPE</label>
        <select id=\"repeatCustomType\"><option value=\"weekly\">Weekly (choose days)</option><option value=\"monthly\">Monthly (choose months)</option></select>
      </div>
      <div id=\"todoRepeatOptions\" class=\"cc-repeat-options hidden\">
        <label id=\"repeatDaysLabel\">WEEK DAYS</label><div id=\"repeatDays\" class=\"cc-check-grid\">${[['1','Mon'],['2','Tue'],['3','Wed'],['4','Thu'],['5','Fri'],['6','Sat'],['0','Sun']].map(([v,l])=>`<label><input type=\"checkbox\" value=\"${v}\"> ${l}</label>`).join('')}</div>
        <label style=\"margin-top:8px;display:block;\" id=\"repeatMonthsLabel\">ACTIVE MONTHS</label><div id=\"repeatMonths\" class=\"cc-check-grid months\">${['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].map((m,i)=>`<label><input type=\"checkbox\" value=\"${i+1}\"> ${m}</label>`).join('')}</div>
      </div>
      <label style=\"margin-top:10px;display:block;\">MOTIVATION QUOTE <em>OPTIONAL</em></label><input id=\"todoQuote\" maxlength=\"180\" placeholder=\"e.g. You’ve got this!\">
      <p id=\"todoRepeatHint\" class=\"form-help\">Repetition is optional. For repeating tasks, choose a due date so the next occurrence can be scheduled automatically.</p>
    </div>
    <div class=\"modal-actions\"><button class=\"ghost-btn\" onclick=\"closeM()\">Cancel</button><button class=\"primary-btn\" id=\"saveTodoBtn\">Add task</button></div>`);
  const repeat=$('#todoRepeat'), opts=$('#todoRepeatOptions'), customRow=$('#customPatternRow'), customType=$('#repeatCustomType');
  const syncRepeat=()=>{
    const mode=repeat.value;
    opts.classList.toggle('hidden',mode==='none'||mode==='daily');
    customRow.classList.toggle('hidden',mode!=='custom');
    const pattern=mode==='custom'?customType.value:mode;
    $('#repeatDaysLabel').textContent=pattern==='weekly'?'WEEK DAYS':'CUSTOM WEEK DAYS';
    $('#repeatMonthsLabel').textContent=pattern==='monthly'?'ACTIVE MONTHS':'CUSTOM ACTIVE MONTHS';
    $('#repeatDays').parentElement?.classList.toggle('hidden',pattern!=='weekly');
    $('#repeatMonths').parentElement?.classList.toggle('hidden',pattern!=='monthly');
  };
  repeat.onchange=syncRepeat; customType.onchange=syncRepeat; syncRepeat();
  $('#saveTodoBtn').onclick=()=>{
    const title=$('#todoTitle').value.trim(), due=$('#todoDue').value||'', mode=repeat.value;
    if(!title){toast('Add a task title.','error');return}
    if(mode!=='none'&&!due){toast('Choose a due date for a repeating task.','error');return}
    const pattern=mode==='custom'?customType.value:mode;
    let repeatData={mode,label:mode};
    if(pattern==='weekly'){
      repeatData.weekdays=[...document.querySelectorAll('#repeatDays input:checked')].map(x=>Number(x.value));
      if(!repeatData.weekdays.length) repeatData.weekdays=[1,2,3,4,5];
    }
    if(pattern==='monthly'){
      repeatData.months=[...document.querySelectorAll('#repeatMonths input:checked')].map(x=>Number(x.value));
      if(!repeatData.months.length) repeatData.months=[1,2,3,4,5,6,7,8,9,10,11,12];
    }
    if(mode==='custom'){repeatData.pattern=pattern;repeatData.label=pattern==='weekly'?'Custom weekly':'Custom monthly';}
    const items=getTodos();items.unshift({id:crypto.randomUUID?.()||String(Date.now()+Math.random()),title,due,priority:$('#todoPriority').value,repeat:repeatData,quote:$('#todoQuote').value.trim(),done:false,createdAt:new Date().toISOString()});saveTodos(items);closeM();renderTodoInline();if(A.view==='todo')todo();toast('Task added.')}
}
async function todo(){const items=getTodos();const s=todoSummary(items);const sections={today:items.filter(t=>!t.done&&t.due===new Date().toISOString().slice(0,10)),upcoming:items.filter(t=>!t.done&&t.due&&t.due>new Date().toISOString().slice(0,10)),nodue:items.filter(t=>!t.done&&!t.due),completed:items.filter(t=>t.done)};$('#viewContainer').innerHTML=`<div class="view cc-todo-page"><section class="todo-hero"><div><span class="cb-kicker">CAMPUS CONNECT · ORGANIZE YOUR DAY</span><h1>Small steps. Less stress.</h1><p>Keep assignments, campus errands and personal priorities in one calm place.</p></div><button class="primary-btn" onclick="openTodoModal()">＋ Add task</button></section><div class="todo-stat-row"><div class="stat-card"><span class="stat-label">ACTIVE</span><strong class="stat-value">${s.pending.length}</strong><span class="stat-meta">Tasks still to do</span></div><div class="stat-card"><span class="stat-label">OVERDUE</span><strong class="stat-value ${s.overdue?'warn':''}">${s.overdue}</strong><span class="stat-meta">Needs attention</span></div><div class="stat-card"><span class="stat-label">COMPLETED</span><strong class="stat-value">${s.done}</strong><span class="stat-meta">Finished tasks</span></div></div><div class="todo-grid">${[['Today',sections.today],['Upcoming',sections.upcoming],['No Due Date',sections.nodue],['Completed',sections.completed]].map(([title,list])=>`<section class="panel todo-panel"><div class="panel-head"><div><h3>${title}</h3><p>${list.length} task${list.length===1?'':'s'}</p></div></div><div class="cc-todo-list">${list.length?list.map(todoCard).join(''):`<div class="todo-empty-state"><img src="/CampusConnect-assets/empty-states/no-to-dos.png" alt=""><strong>${title==='Completed'?'Nothing completed yet.':'Nothing here right now.'}</strong><span>${title==='Completed'?'Finish a task and it will appear here.':'Add a task whenever something needs your attention.'}</span></div>`}</div></section>`).join('')}</div></div>`}
function openProposalFromNotice(){
  go('clubs');
  setTimeout(()=>$('#createClubBtn')?.click(),80);
}
function openMeetingsFromNotice(){go('my-clubs')}
function openNewEventFromNotice(){go('events')}
function openClubMemoriesFromNotice(){go('my-clubs')}
function noticeActionCards(){
  const cards=[
    ['custom-my-clubs.png','Club Memories','Open your club memories','openClubMemoriesFromNotice()'],
    ['custom-add-create.png','Propose New Club','Suggest a new campus club','openProposalFromNotice()'],
    ['system-calendar.png','Schedule Meeting','Plan a club meeting','openMeetingsFromNotice()'],
    ['custom-events.png','New Event','Browse or create events','openNewEventFromNotice()'],
    ['custom-notifications.png','Notification Center','Read your latest notices','go(\'notifications\')'],
    ['custom-requests.png','My Request','Track every request','go(\'notifications\')']
  ];
  return cards.map(([icon,title,desc,action])=>`<button class=\"cc-notice-action-card cc-action-card\" onclick=\"${action}\"><span class=\"cc-notice-action-icon\">${iconImg(icon,title,'')}</span><span class=\"cc-notice-action-copy\"><strong>${title}</strong><small>${desc}</small></span><span class=\"cc-notice-action-arrow\">→</span></button>`).join('');
}

async function dash(){
  let stats={counts:{},myLocker:null};
  try{stats=await api('/api/dashboard')}catch(e){}
  if(A.user.accessRole==='student'){
    let clubs=[],events=[],notifList=[],notifCount=0,lfCount=0,probCount=0;
    try{const d=await api('/api/clubs');clubs=d.clubs||[]}catch(e){}
    try{const d=await api('/api/events');events=d.events||[]}catch(e){}
    try{const d=await api('/api/notifications');notifList=d.notifications||[];notifCount=d.unread||0}catch(e){}
    try{const d=await api('/api/lostfound');lfCount=(d.items||[]).filter(i=>i.status==='open').length}catch(e){}
    try{const d=await api('/api/problems');probCount=(d.problems||[]).filter(p=>p.status!=='resolved'&&p.status!=='rejected').length}catch(e){}
    const joined=clubs.filter(c=>c.my_status==='active');
    const registered=events.filter(e=>e.my_status==='registered');
    const name=esc(A.user.name.split(' ')[0]);
    const initials=esc(A.user.name.split(' ').map(x=>x[0]).slice(0,2).join('').toUpperCase());

    const eventCards=events.slice(0,3).map(e=>`<article class="cb-event-card"><div class="cb-event-date"><strong>${esc((e.event_date||'--').slice(8,10)||'--')}</strong><span>${esc((e.event_date||'').slice(5,7))}</span></div><div class="cb-event-main"><div class="cb-event-tag">${esc(e.type||'EVENT')}</div><h4>${esc(e.title)}</h4><p>${esc(e.club_name||'Campus activity')} · ${esc(e.time_start||'Time TBA')} · ${esc(e.location||'Campus')}</p><div class="cb-event-action">${e.my_status==='registered'?(e.is_paid&&e.my_payment_status!=='verified'?`<span class="badge yellow">Payment ${esc(e.my_payment_status||'pending')}</span>`:'<span class="cb-registered">✓ Registered</span>'):`<button class="primary-btn" onclick="openRegisterFlow(${e.id})">${e.is_paid?`Register · ₹${e.price}`:'Register'}</button>`}</div></div></article>`).join('') || '<div class="empty-card"><b>No upcoming events yet.</b><span>New campus activities will appear here.</span></div>';

    const registeredCards=registered.slice(0,4).map(e=>`<div class="cc-sched-row"><div class="cc-sched-dot"></div><div><strong>${esc(e.title)}</strong><span>${esc(e.event_date||'')} · ${esc(e.time_start||'Time TBA')} · ${esc(e.location||'Campus')}</span></div></div>`).join('') || (joined.slice(0,4).map(c=>`<div class="cc-sched-row"><div class="cc-sched-dot club"></div><div><strong>${esc(c.name)}</strong><span>${esc(c.category||'Club')} · ${esc(c.member_count||0)} members</span></div></div>`).join('') || '<div class="empty-card"><b>Nothing scheduled yet.</b><span>Register for an event or join a club to see it here.</span></div>');

    const announceCards=notifList.slice(0,3).map(n=>`<div class="cc-announce-row"><span class="cc-announce-dot"></span><div><strong>${esc(n.title)}</strong><span>${esc((n.body||'').slice(0,70))}${(n.body||'').length>70?'…':''} · ${fmt(n.created_at)}</span></div></div>`).join('') || '<div class="empty-card"><b>No announcements yet.</b><span>Campus notices will show up here.</span></div>';

    const quickActions=[
      ['events','Browse Events'],['clubs','Join a Club'],['lockers','Campus Services'],
      ['problems','Report an Issue'],['lostfound','Lost & Found'],['notifications','View Notices']
    ].map(([v,l])=>`<button class="cc-qa-tile" onclick="go('${v}')">${navIcon(v,l)}<span>${esc(l)}</span></button>`).join('');

    const exploreItems=[
      ['clubs','Clubs & Societies','Find your community','/CampusConnect-assets/icons/transparent/custom-clubs.png','clubs'],
      ['lockers','Campus Lock','Storage, simplified','/CampusConnect-assets/icons/transparent/custom-campus-services.png','services'],
      ['lostfound','Lost & Found','Reunite with your things','/CampusConnect-assets/icons/transparent/custom-lost-and-found.png','lost'],
      ['problems','Report & Support','Help make campus better','/CampusConnect-assets/icons/transparent/custom-reports.png','report'],
      ['todo','To-Do','Keep your day moving','/CampusConnect-assets/icons/transparent/custom-to-do.png','todo'],
    ].map(([v,t,s,src,iconClass])=>`<button class="cc-service-dock-item" onclick="go('${v}')" aria-label="${esc(t)}" title="${esc(t)}"><span class="cc-service-dock-icon ${iconClass}"><img src="${src}" alt=""></span><span class="cc-service-dock-copy"><strong>${t}</strong><small>${s}</small></span></button>`).join('');

    $('#viewContainer').innerHTML=`<div class="cc-dashboard">
      <section class="cc-dash-hero">
        <div class="cc-dash-hero-illustration" aria-hidden="true"><img src="/CampusConnect-assets/backgrounds/dashboard-hero.png" alt=""></div>
        <span class="cc-dash-hero-quote">Learn<br>Connect<br>Create<br>Belong</span>
        <div class="cc-dash-hero-text">
          <span class="cb-kicker">CAMPUS CONNECT · ${esc(A.user.campus||'CAMPUS')}</span>
          <h1>${greetingWord()}, ${name}!</h1>
          <p>"Same Campus. Brighter Together."</p>
        </div>
      </section>

      <div class="cc-dash-grid">
        <div class="cc-dash-main">
          <section class="cc-section">
            <div class="cc-section-heading"><h3>Quick Actions</h3></div>
            <div class="cc-qa-grid">${quickActions}</div>
          </section>

          <section class="cc-section">
            <div class="cc-dash-2col">
              <div class="cb-panel">
                <div class="cb-panel-head"><div><h4>Upcoming Events</h4><p>Campus activities happening soon.</p></div><button class="text-link" onclick="go('events')">View All →</button></div>
                <div class="cb-event-list">${eventCards}</div>
              </div>
              <div class="cb-panel">
                <div class="cb-panel-head"><div><h4>My Schedule</h4><p>Events you're registered for, and your clubs.</p></div><button class="text-link" onclick="go('${registered.length?'events':'clubs'}')">View All →</button></div>
                <div class="cc-sched-list">${registeredCards}</div>
              </div>
            </div>
          </section>

          <section class="cc-section">
            <div class="cc-dash-2col">
              <div class="cb-panel">
                <div class="cb-panel-head"><div><h4>My To-Do</h4><p>Keep today's priorities visible.</p></div><div><span id="dashTodoCount" class="badge gray">0 active</span> <button class="text-link" onclick="go('todo')">Open →</button></div></div>
                <div id="dashTodoList" class="cc-todo-list cc-dash-todo-list"></div>
              </div>
              <div class="cc-quote-card cc-quote-soft"><p>“A little progress, every day, adds up.”</p><button class="text-link" onclick="openTodoModal()">Add a task →</button></div>
            </div>
          </section>

          <section class="cc-section">
            <div class="cc-section-heading"><h3>Explore Campus</h3></div>
            <div class="cc-service-dock">${exploreItems}</div>
          </section>
        </div>

        <aside class="cc-dash-aside">
          <div class="cb-panel">
            <div class="cb-panel-head"><div><h4>Announcements</h4></div><button class="text-link" onclick="go('notifications')">View All →</button></div>
            <div class="cc-announce-list">${announceCards}</div>
          </div>

          <div class="cc-quote-card">
            <p>"A community that grows together, goes further."</p>
          </div>

          <div class="cb-panel">
            <div class="cb-panel-head"><div><h4>Campus Snapshot</h4></div></div>
            <div class="cc-snapshot-list">
              <button class="cc-snapshot-row" onclick="go('lockers')"><span>CampusLock</span><strong>${stats.myLocker?'Locker '+esc(stats.myLocker.locker_id):'Find a locker'}</strong></button>
              <button class="cc-snapshot-row" onclick="go('lostfound')"><span>Lost & Found</span><strong>${lfCount} open</strong></button>
              <button class="cc-snapshot-row" onclick="go('problems')"><span>Campus Problems</span><strong>${probCount} active</strong></button>
              <button class="cc-snapshot-row" onclick="go('notifications')"><span>Notices</span><strong>${notifCount} unread</strong></button>
            </div>
          </div>
        </aside>
      </div>
    </div>`;
    renderTodoInline();
  }else{
    const c=stats.counts||{};
    let reqCount=0, maintenanceCount=0, noticeCount=0, eventCount=0, clubCount=0;
    try{reqCount=(await api('/api/requests')).requests?.filter(r=>r.status==='pending').length||0}catch{}
    try{maintenanceCount=(await api('/api/maintenance')).maintenance?.filter(r=>r.status!=='resolved').length||0}catch{}
    try{noticeCount=(await api('/api/notifications')).unread||0}catch{}
    try{eventCount=(await api('/api/events')).events?.length||0}catch{}
    try{clubCount=(await api('/api/clubs')).clubs?.length||0}catch{}
    const adminActions=[
      ['requests','Review Requests',reqCount,'Items awaiting your decision.'],
      ['maintenance','Maintenance',maintenanceCount,'Operational issues needing attention.'],
      ['events','Manage Events',eventCount,'Published and upcoming campus events.'],
      ['clubs','Manage Clubs',clubCount,'Clubs and community activity.'],
      ['students','Student Directory',c.total||0,'Verified campus records.'],
      ['audit','Audit Log',noticeCount,'Recent platform and security activity.']
    ].map(([v,t,count,desc])=>`<button class="admin-action-card" onclick="go('${v}')"><span class="admin-action-icon">${navIcon(v,t)}</span><span class="admin-action-copy"><strong>${esc(t)}</strong><small>${esc(desc)}</small><b>${esc(count)}</b></span></button>`).join('');
    $('#viewContainer').innerHTML=`<div class="view admin-dashboard">
      <section class="admin-welcome">
        <div><span class="cb-kicker">CAMPUS CONNECT · OPERATIONS CENTER</span><h1>Good ${greetingWord().replace('Good ','')}, ${esc(A.user.name.split(' ')[0])}.</h1><p>A calm, connected view of the people, services and activity that need attention across your campus.</p></div>
        <div class="admin-welcome-mark">${iconImg('custom-dashboard.png','Operations','admin-welcome-icon')}<span><strong>Campus operations</strong><small>Everything in one place</small></span></div>
      </section>
      <section class="admin-metrics">
        ${metricCard('LOCKERS',c.total||0,'Total managed')}
        ${metricCard('AVAILABLE',c.available||0,'Ready to assign')}
        ${metricCard('PENDING',c.pending||0,'Awaiting action')}
        ${metricCard('MAINTENANCE',c.maintenance||0,'Needs attention')}
      </section>
      <section class="admin-section-head"><div><h3>Action center</h3><p>Review requests and move through the campus work that matters most.</p></div></section>
      <section class="admin-action-grid">${adminActions}</section>
      <section class="admin-dashboard-grid">
        <div class="panel"><div class="panel-head"><div><h3>Operational focus</h3><p>Quick signals for today's work.</p></div><button class="text-link" onclick="go('requests')">Open requests →</button></div>
          <div class="admin-focus-list">
            <div><span class="focus-dot terra"></span><strong>${esc(reqCount)} pending requests</strong><small>Student and staff submissions waiting for a decision.</small></div>
            <div><span class="focus-dot sage"></span><strong>${esc(maintenanceCount)} active maintenance items</strong><small>Keep campus resources available and safe.</small></div>
            <div><span class="focus-dot gold"></span><strong>${esc(noticeCount)} unread notifications</strong><small>Stay current on campus activity and updates.</small></div>
          </div>
        </div>
        <div class="admin-illustration-card"><img src="/CampusConnect-assets/backgrounds/clubs-events-background.png" alt="Campus Connect operations"><div><span class="cb-kicker">ONE CONNECTED CAMPUS</span><h3>People, services and campus life in one connected workspace.</h3><button class="ghost-btn admin-visual-btn" onclick="go('clubs')">Open campus activity →</button></div></div>
      </section>
    </div>`
  }
}
async function loadDashNotifications(){const d=await api('/api/notifications');$('#dashNotifications').innerHTML=d.notifications.slice(0,4).map(n=>`<div class="activity-row"><div class="activity-dot"></div><div><strong>${esc(n.title)}</strong><span>${esc(n.body)} • ${fmt(n.created_at)}</span></div></div>`).join('')||'<div class="empty">No notifications.</div>'}
async function lockers(){A.filters.q=A.filters.q||'';const qs=new URLSearchParams(A.filters);const d=await api('/api/lockers?'+qs);const groups={};for(const l of d.lockers){(groups[l.floor]??={code:l.floorCode,items:[]}).items.push(l)}const floorBlocks=Object.entries(groups).map(([f,g])=>{const byGroup={};g.items.forEach(x=>(byGroup[x.group]??=[]).push(x));return `<section class="floor-block"><div class="floor-header"><div><strong>${g.code} · Floor ${f}</strong><span>Visual locker wall</span></div><span>${g.items.length} lockers</span></div>${Object.entries(byGroup).map(([grp,items])=>`<div class="group-block"><div class="group-heading"><span>Group ${esc(grp)}</span><span>${items.length} positions</span></div><div class="locker-grid">${items.map(lockerCard).join('')}</div></div>`).join('')}</section>`}).join('')||'<div class="panel"><div class="empty">No lockers match your filters.</div></div>';$('#viewContainer').innerHTML=`<div class="view"><div class="toolbar"><input id="lockerSearch" class="search-input" placeholder="Search locker code or group" value="${esc(A.filters.q)}"><select id="floorFilter" class="filter-select"><option value="all">All floors</option>${[1,2,3,4].map(f=>`<option value="${f}" ${A.filters.floor==f?'selected':''}>${'ABCD'[f-1]} · Floor ${f}</option>`).join('')}</select><select id="statusFilter" class="filter-select"><option value="all">All statuses</option><option value="available" ${A.filters.status==='available'?'selected':''}>Vacant</option><option value="pending" ${A.filters.status==='pending'?'selected':''}>Pending</option><option value="occupied" ${A.filters.status==='occupied'?'selected':''}>Occupied</option><option value="maintenance" ${A.filters.status==='maintenance'?'selected':''}>Maintenance</option></select>${A.user.accessRole==='student'?'<button id="recommendedBtn" class="primary-btn">✦ Find best available</button>':''}</div><div class="legend-row"><span><i class="legend-dot available"></i>Vacant</span><span><i class="legend-dot occupied"></i>Occupied</span><span><i class="legend-dot pending"></i>Pending</span><span><i class="legend-dot maintenance"></i>Maintenance</span></div><div class="panel recommendation-banner hidden" id="recommendationBanner"></div><div class="locker-groups">${floorBlocks}</div></div>`;$('#lockerSearch').oninput=debounce(e=>{A.filters.q=e.target.value;lockers()},250);$('#floorFilter').onchange=e=>{A.filters.floor=e.target.value;lockers()};$('#statusFilter').onchange=e=>{A.filters.status=e.target.value;lockers()};$('#recommendedBtn')?.addEventListener('click',recommendLocker);document.querySelectorAll('.locker-card.clickable').forEach(c=>c.onclick=e=>{if(e.target.closest('button'))return;A.detailId=c.dataset.id;go('locker-detail')});document.querySelectorAll('[data-locker-action="request"]').forEach(b=>b.onclick=()=>requestLocker(b.dataset.id));document.querySelectorAll('[data-locker-action="release"]').forEach(b=>b.onclick=()=>releaseLocker(b.dataset.id));document.querySelectorAll('[data-locker-action="maint"]').forEach(b=>b.onclick=()=>maintenancePrompt(b.dataset.id))}
function lockerCard(l){const student=A.user.accessRole!=='student'&&l.studentName?`<div class="locker-student">${esc(l.studentName)} • ${esc(l.studentId||'No ID')}</div>`:l.isMine?'<div class="locker-student">Your locker</div>':'';let action='';if(A.user.accessRole==='student'&&l.status==='available')action=`<button class="locker-action primary" data-locker-action="request" data-id="${esc(l.id)}">Request</button>`;if(A.user.accessRole==='student'&&l.isMine)action=`<button class="locker-action danger" data-locker-action="release" data-id="${esc(l.id)}">Release</button>`;if(A.user.accessRole!=='student'&&l.status==='occupied'&&can('modify_lockers'))action=`<button class="locker-action danger" data-locker-action="release" data-id="${esc(l.id)}">Release</button>`;return `<article class="locker-card ${l.status} ${A.user.accessRole!=='student'?'clickable':''}" data-id="${esc(l.id)}"><div><div class="locker-top"><strong class="locker-id">${esc(l.id)}</strong><span class="status-dot ${l.status}"></span></div><div class="locker-room">${esc(l.roomName||('Group '+l.group))}</div><span class="locker-status ${l.status}">${statusLabel(l.status)}</span>${student}</div><div class="locker-actions">${action||'<span class="locker-action disabled">'+(A.user.accessRole==='student'?'View status':'Open details')+'</span>'}</div></article>`}
async function recommendLocker(){A.filters.status='available';A.filters.q='';const d=await api('/api/lockers?status=available');const first=d.lockers[0];if(!first){toast('No vacant lockers are currently available.','error');return}const ban=$('#recommendationBanner');ban.classList.remove('hidden');ban.innerHTML=`<div><span class="eyebrow">RECOMMENDED</span><h3>${esc(first.id)}</h3><p>${esc(first.floorCode)} · Floor ${first.floor} · Group ${first.group}. This recommendation prioritizes the first currently vacant locker in the canonical campus order.</p></div><button class="primary-btn" data-id="${esc(first.id)}">Open</button>`;ban.querySelector('button').onclick=()=>{A.detailId=first.id;go('locker-detail')}}
function debounce(fn,ms){let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms)}}
async function lockerDetailView(){const d=await api('/api/lockers/'+encodeURIComponent(A.detailId));const l=d.locker;const s=d.student;const actions=A.user.accessRole==='student'?(s?`<button class="danger-btn" id="detailRelease">Release locker</button>`:l.status==='available'?`<button class="primary-btn" id="detailRequest">Request locker</button>`:''):'';const adminActions=A.user.accessRole!=='student'&&can('release_lockers')&&l.status==='occupied'?'<button class="danger-btn" id="detailRelease">Release locker</button>':'';const maintAction=can('manage_maintenance')?(l.status==='maintenance'?'<button class="ghost-btn" id="detailMaintOff">Resolve maintenance</button>':'<button class="ghost-btn" id="detailMaintOn">Report maintenance</button>'):'';const history=(d.events||[]).map(e=>`<div class="timeline-item"><b>${statusLabel(e.new_state||e.event_type)}</b><span>${esc(e.event_type)} • ${esc(e.actor)} • ${fmt(e.created_at)}</span>${e.notes?`<p>${esc(e.notes)}</p>`:''}</div>`).join('')||'<div class="empty">No history yet.</div>';const maint=(d.maintenance||[]).map(m=>`<div class="timeline-item"><b>${statusLabel(m.status)} • ${esc(m.severity)}</b><span>${fmt(m.reported_at)} • ${esc(m.reason)}</span></div>`).join('')||'<div class="empty">No maintenance records.</div>';$('#viewContainer').innerHTML=`<div class="view"><button class="ghost-btn back-btn" id="backLockers">← Back to lockers</button><div class="detail-page-grid"><div class="panel"><div class="detail-page-body"><div class="locker-detail-banner"><div><strong>${esc(l.id)}</strong><span>${esc(l.floorCode)} · Floor ${l.floor} · Group ${esc(l.group)} · ${esc(l.roomName)}</span></div><span class="badge ${badgeClass(l.status)}">${statusLabel(l.status)}</span></div>${s?`<div class="section-title">CURRENT ASSIGNMENT</div><div class="info-grid">${[['Name',s.name],['Branch',s.branch],['Year',s.year],['Student ID',s.studentId],['Phone',s.mobile],['Date joined',s.joinedAt]].map(([a,b])=>`<div><span>${a}</span><strong>${esc(b)}</strong></div>`).join('')}</div>`:`<div class="empty-card"><b>No student assignment</b><span>This locker is not currently assigned to a student.</span></div>`}<div class="detail-page-actions">${actions}${adminActions}${maintAction}</div></div></div><div class="panel"><div class="panel-head"><div><h3>Physical identity</h3><p>Stable, non-guessable QR route; no private student data is embedded.</p></div></div><div class="qr-panel"><img src="/api/lockers/${encodeURIComponent(l.id)}/qr.png" alt="Locker QR" loading="lazy"><div><b>${esc(l.id)}</b><span>Scan route requires authentication.</span><button class="ghost-btn" id="copyQr">Copy QR URL</button></div></div></div></div><div class="panel timeline-panel"><div class="panel-head"><div><h3>Locker history</h3><p>Append-oriented assignment, release and state events.</p></div></div><div class="timeline">${history}</div></div><div class="panel timeline-panel"><div class="panel-head"><div><h3>Maintenance history</h3><p>Operational lifecycle is separate from normal locker assignment.</p></div></div><div class="timeline">${maint}</div></div></div>`;$('#backLockers').onclick=()=>go('lockers');$('#detailRelease')?.addEventListener('click',()=>releaseLocker(l.id));$('#detailRequest')?.addEventListener('click',()=>requestLocker(l.id));$('#detailMaintOn')?.addEventListener('click',()=>maintenancePrompt(l.id));$('#detailMaintOff')?.addEventListener('click',()=>api('/api/lockers/'+encodeURIComponent(l.id)+'/maintenance',{method:'POST',body:JSON.stringify({maintenance:false})}).then(()=>{toast('Maintenance resolved.');lockerDetailView()}));$('#copyQr')?.addEventListener('click',async()=>{try{const x=await api('/api/lockers/'+encodeURIComponent(l.id)+'/qr');await navigator.clipboard.writeText(x.url);toast('QR URL copied.')}catch(e){toast(e.message,'error')}})}
async function requestLocker(id){if(!confirm(`Request locker ${id}?`))return;try{const d=await api('/api/lockers/'+encodeURIComponent(id)+'/request',{method:'POST'});toast(`Request ${d.requestCode} submitted.`);go('requests')}catch(e){toast(e.message,'error')}}
async function releaseLocker(id){if(!confirm(`Release locker ${id}? This will make it available again.`))return;try{await api('/api/lockers/'+encodeURIComponent(id)+'/release',{method:'POST'});toast('Locker released.');go(A.user.accessRole==='student'?'my':'lockers')}catch(e){toast(e.message,'error')}}
async function maintenancePrompt(id){const reason=prompt('Maintenance reason','Physical inspection required');if(reason===null)return;try{await api('/api/lockers/'+encodeURIComponent(id)+'/maintenance',{method:'POST',body:JSON.stringify({maintenance:true,reason,severity:'medium'})});toast('Maintenance reported.');go('maintenance')}catch(e){toast(e.message,'error')}}
async function requests(){
  const mine=A.user.accessRole==='student';
  if(mine){
    const rq=await api('/api/my-requests');
    const statusBadge=s=>s==='pending'?'<span class=\"badge yellow\">Pending</span>':s==='approved'?'<span class=\"badge green\">Approved</span>':s==='declined'?'<span class=\"badge red\">Declined</span>':`<span class=\"badge gray\">${esc(s)}</span>`;
    const rows=rq.myRequests.map(r=>`<article class=\"my-request-row cc-action-card\"><div class=\"my-request-main\"><span class=\"my-request-kind\">${esc(r.kind)}</span><strong>${esc(r.title)}</strong><span class=\"my-request-detail\">${esc(r.detail||'')}</span></div><div class=\"my-request-side\">${statusBadge(r.status)}<span class=\"my-request-date\">${fmt(r.created_at)}</span></div></article>`).join('');
    $('#viewContainer').innerHTML=`<div class=\"view\"><section class=\"panel priority-panel\"><div class=\"panel-head\"><div><h3>My Requests</h3><p>Every request you submit — clubs, memberships, events, lockers, Lost & Found, and problem reports — in one place.</p></div><span class=\"badge gray\">${rq.myRequests.length} total</span></div><div class=\"my-requests-list\">${rows||'<div class=\"empty\">You have not made any requests yet.</div>'}</div></section></div>`;
    return;
  }
  const d=await api('/api/requests');
  const staff=d.staffRequests||[];

  // Club proposals + membership requests (staff/admin only — this is what
  // used to be scattered inside individual club pages).
  let clubQueue = {clubProposals:[], membershipRequests:[]};
  if (!mine && can('review_staff_requests')) {
    try { clubQueue = await api('/api/clubs/requests-queue'); } catch(e) { /* non-staff, ignore */ }
  }

  const clubProposalsPanel = (!mine && can('review_staff_requests')) ? `<section class="panel priority-panel">
    <div class="panel-head"><div><h3>Club proposals</h3><p>New clubs students have proposed, waiting on staff review.</p></div><span class="badge yellow">${clubQueue.clubProposals.length} pending</span></div>
    <div class="priority-grid">${clubQueue.clubProposals.map(x=>`<div class="priority-card">
      <div class="priority-main"><div><span class="priority-code">CLUB</span><h4>${esc(x.name)}</h4><p>${esc(x.category||'General')} · Proposed by ${esc(x.founder_name||'—')}</p></div><span class="priority-badge">NEW CLUB</span></div>
      <div class="request-details"><span style="grid-column:1/-1;"><b>Description</b>${esc((x.description||'').slice(0,140))}</span><span><b>Founder ID</b>${esc(x.founder_student_id||'—')}</span><span><b>Submitted</b>${fmt(x.created_at)}</span></div>
      <div class="request-actions"><button class="small-btn green" data-club="${x.id}" data-cx-action="approve">Accept</button><button class="danger-btn" data-club="${x.id}" data-cx-action="reject">Decline</button></div>
    </div>`).join('') || '<div class="empty">No pending club proposals.</div>'}</div>
  </section>` : '';

  const membershipPanel = (!mine && can('review_staff_requests')) ? `<section class="panel priority-panel">
    <div class="panel-head"><div><h3>Club join requests</h3><p>Students waiting to be approved into a club, across every club on campus.</p></div><span class="badge yellow">${clubQueue.membershipRequests.length} pending</span></div>
    <div class="priority-grid">${clubQueue.membershipRequests.map(x=>`<div class="priority-card">
      <div class="priority-main"><div><span class="priority-code">JOIN</span><h4>${esc(x.full_name)}</h4><p>${esc(x.branch||'—')} · ${esc(x.year||'—')} → <b>${esc(x.club_name)}</b></p></div><span class="priority-badge">MEMBERSHIP</span></div>
      <div class="request-details"><span><b>Student ID</b>${esc(x.student_id||'—')}</span><span><b>Requested</b>${fmt(x.joined_at)}</span></div>
      <div class="request-actions"><button class="small-btn green" data-mem="${x.club_id}:${x.member_id}" data-cx-action="approve">Accept</button><button class="danger-btn" data-mem="${x.club_id}:${x.member_id}" data-cx-action="reject">Decline</button></div>
    </div>`).join('') || '<div class="empty">No pending join requests.</div>'}</div>
  </section>` : '';

  const staffPanel=!mine&&can('review_staff_requests')?`<section class="panel priority-panel"><div class="panel-head"><div><h3>Priority staff onboarding</h3><p>New staff applications are routed to the primary administrator first.</p></div><span class="badge yellow">${staff.filter(x=>x.status==='pending').length} pending</span></div><div class="priority-grid">${staff.filter(x=>x.status==='pending').map(x=>`<div class="priority-card"><div class="priority-main"><div><span class="priority-code">${esc(x.request_code)}</span><h4>${esc(x.full_name)}</h4><p>${esc(x.branch||'Staff')} • ${esc(x.campus)}</p></div><span class="priority-badge">TOP PRIORITY</span></div><div class="request-details"><span><b>ID</b>${esc(x.requested_login_id||'Auto-generate')}</span><span><b>Mobile</b>${esc(x.mobile)}</span><span><b>Submitted</b>${fmt(x.created_at)}</span><span><b>Assigned</b>${esc(x.assigned_admin)}</span></div><div class="request-actions"><button class="small-btn green" data-staff="${esc(x.request_code)}" data-action="approve">Approve</button><button class="danger-btn" data-staff="${esc(x.request_code)}" data-action="reject">Reject</button></div></div>`).join('')||'<div class="empty">No pending staff access requests.</div>'}</div></section>`:'';
  const rows=d.requests.map(x=>`<tr><td><b>${esc(x.request_code)}</b></td><td>${esc(x.full_name)}${mine?'':'<br><span>'+esc(x.student_id||'No ID')+'</span>'}</td><td>${mine?'—':esc(x.branch||x.course||'—')}</td><td><b>${esc(x.locker_id)}</b></td><td>${fmt(x.created_at)}</td><td><span class="badge ${badgeClass(x.status)}">${statusLabel(x.status)}</span></td><td>${x.status==='pending'&&!mine?'<button class="small-btn green" data-req="'+x.request_code+'" data-action="approve">Accept</button> <button class="danger-btn" data-req="'+x.request_code+'" data-action="reject">Decline</button>':x.status==='pending'&&mine?'<button class="small-btn" data-req="'+x.request_code+'" data-action="cancel">Cancel</button>':(x.rejection_reason?esc(x.rejection_reason):'Closed')}</td></tr>`).join('')||'<tr><td colspan="7" class="empty">No locker requests yet.</td></tr>';
  $('#viewContainer').innerHTML=`<div class="view">${clubProposalsPanel}${membershipPanel}${staffPanel}<div class="panel"><div class="panel-head"><div><h3>${mine?'My Requests':'Locker request queue'}</h3><p>${mine?'All requests you have submitted across campus services are tracked here.':'Approve, reject and audit locker allocation decisions.'}</p></div></div><div class="table-wrap"><table><thead><tr><th>REQUEST</th><th>STUDENT</th><th>BRANCH</th><th>LOCKER</th><th>SUBMITTED</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>${rows}</tbody></table></div></div></div>`;
  document.querySelectorAll('[data-req]').forEach(b=>b.onclick=()=>reviewRequest(b.dataset.req,b.dataset.action));
  document.querySelectorAll('[data-staff]').forEach(b=>b.onclick=()=>reviewStaffRequest(b.dataset.staff,b.dataset.action));
  document.querySelectorAll('[data-club]').forEach(b=>b.onclick=()=>reviewClubFromQueue(b.dataset.club,b.dataset.cxAction));
  document.querySelectorAll('[data-mem]').forEach(b=>{const [clubId,memberId]=b.dataset.mem.split(':');b.onclick=()=>reviewMembershipFromQueue(clubId,memberId,b.dataset.cxAction);});
}

window.reviewClubFromQueue = async (clubId, action) => {
  let reason = '';
  if (action === 'reject') {
    reason = prompt('Reason for declining (optional)', 'Club proposal does not meet current requirements.');
    if (reason === null) return;
  }
  try {
    await api('/api/clubs/'+clubId+'/review/'+(action==='approve'?'approve':'reject'), {method:'POST', body:JSON.stringify({reason})});
    toast(action==='approve'?'Club approved!':'Club declined.');
    requests();
  } catch(e) { toast(e.message,'error'); }
};

window.reviewMembershipFromQueue = async (clubId, memberId, action) => {
  try {
    await api(`/api/clubs/${clubId}/members/${memberId}/${action==='approve'?'approve':'reject'}`, {method:'POST'});
    toast(action==='approve'?'Membership approved!':'Request declined.');
    requests();
  } catch(e) { toast(e.message,'error'); }
};
async function reviewRequest(code,action){let reason='';if(action==='reject'){reason=prompt('Rejection reason','Request could not be approved at this time.');if(reason===null)return}try{await api('/api/requests/'+encodeURIComponent(code)+'/'+action,{method:'POST',body:JSON.stringify({reason})});toast(action==='approve'?'Request approved and assigned.':action==='reject'?'Request rejected.':'Request cancelled.');requests()}catch(e){toast(e.message,'error')}}
async function reviewStaffRequest(code,action){let reason='';if(action==='reject'){reason=prompt('Rejection reason','Application does not meet current approval requirements.');if(reason===null)return}try{const d=await api('/api/staff-requests/'+encodeURIComponent(code)+'/'+action,{method:'POST',body:JSON.stringify({reason})});toast(action==='approve'?`Staff account approved. Login: ${d.loginId}`:'Staff application rejected.');requests()}catch(e){toast(e.message,'error')}}
async function students(){const d=await api('/api/students');$('#viewContainer').innerHTML=`<div class="view"><div class="toolbar"><input id="studentSearch" class="search-input" placeholder="Search student ID, name or branch"><button class="primary-btn" id="addStudentBtn">＋ Add student</button></div><div class="panel"><div class="panel-head"><div><h3>Student directory</h3><p>Staff-only student details are returned by the protected backend query.</p></div><span class="badge gray">${d.students.length} records</span></div><div class="table-wrap"><table><thead><tr><th>ID</th><th>NAME</th><th>BRANCH</th><th>YEAR</th><th>SEMESTER</th><th>MOBILE</th><th>LOCKER</th></tr></thead><tbody id="studentRows">${studentRows(d.students)}</tbody></table></div></div></div>`;$('#studentSearch').oninput=debounce(async e=>{const x=await api('/api/students?q='+encodeURIComponent(e.target.value));$('#studentRows').innerHTML=studentRows(x.students)},250);$('#addStudentBtn').onclick=addStudentModal}
function studentRows(a){return a.map(x=>`<tr><td><b>${esc(x.student_id||x.username)}</b></td><td>${esc(x.full_name)}</td><td>${esc(x.branch||x.course||'—')}</td><td>${esc(x.year||'—')}</td><td>${esc(x.semester||'—')}</td><td>${esc(x.mobile||'—')}</td><td>${esc(x.locker_id||'—')}</td></tr>`).join('')||'<tr><td colspan="7" class="empty">No students found.</td></tr>'}
function addStudentModal(){modal(`<div class="modal-head"><h3>Create student account</h3><button id="closeM" class="close-btn">✕</button></div><form id="sf" class="modal-form"><div class="form-grid"><div><label>STUDENT ID</label><input id="sid" required></div><div><label>MOBILE</label><input id="sm" inputmode="numeric" required></div></div><div class="form-grid"><div><label>FULL NAME</label><input id="sn" required></div><div><label>SEMESTER</label><input id="sy" required></div></div><label>BRANCH</label><input id="sc" required><label>EMAIL</label><input id="se" type="email"><label>INITIAL PASSWORD</label><input id="sp" type="password" value="student123"><div class="modal-actions"><button type="button" id="cm" class="ghost-btn">Cancel</button><button class="primary-btn">Create student</button></div></form>`);$('#cm').onclick=closeM;$('#sf').onsubmit=async e=>{e.preventDefault();try{await api('/api/students',{method:'POST',body:JSON.stringify({studentId:$('#sid').value,name:$('#sn').value,branch:$('#sc').value,semester:$('#sy').value,mobile:$('#sm').value,email:$('#se').value,password:$('#sp').value,campus:'Dwarka Campus'})});closeM();toast('Student created.');students()}catch(x){toast(x.message,'error')}}}
async function manage(){const d=await api('/api/rooms');$('#viewContainer').innerHTML=`<div class="view"><div class="panel"><div class="panel-head"><div><h3>Locker management</h3><p>Create a single locker or a group of five using the standardized code.</p></div><button class="primary-btn" id="customAdd">＋ Add lockers</button></div><div class="room-admin-grid">${d.rooms.map(r=>`<div class="room-admin"><div><b>${'ABCD'[r.floor_number-1]} · Group ${esc(r.room_code)}</b><span>${esc(r.room_name)} • ${r.locker_count} lockers</span></div><button class="ghost-btn addRoom" data-floor="${r.floor_number}" data-group="${esc(r.room_code)}">Add</button></div>`).join('')}</div></div></div>`;document.querySelectorAll('.addRoom').forEach(b=>b.onclick=()=>addLockerModal(+b.dataset.floor,b.dataset.group));$('#customAdd').onclick=()=>addLockerModal(1,'1')}
function modal(html){$('#modalRoot').innerHTML=`<div class="modal-backdrop" id="mb"><div class="modal">${html}</div></div>`;$('#mb').onclick=e=>{if(e.target.id==='mb')closeM()};$('#closeM')?.addEventListener('click',closeM)}function closeM(){$('#modalRoot').innerHTML=''}
async function addLockerModal(floor=1,group='1'){modal(`<div class="modal-head"><h3>Add lockers</h3><button id="closeM" class="close-btn">✕</button></div><form id="lf" class="modal-form"><div class="form-grid"><div><label>FLOOR</label><select id="lfloor">${[1,2,3,4].map(f=>`<option value="${f}" ${f===floor?'selected':''}>${'ABCD'[f-1]} · Floor ${f}</option>`).join('')}</select></div><div><label>LOCKER GROUP</label><input id="lgroup" value="${esc(group)}" inputmode="numeric" required></div></div><div class="form-grid"><div><label>QUANTITY</label><select id="lq"><option value="1">1 locker</option><option value="5" selected>5 lockers</option></select></div><div><label>STARTING NUMBER</label><input id="lstart" type="number" min="1" max="999" value="1" required></div></div><div class="code-preview">Preview: <b id="codePreview"></b></div><p class="section-note">Example: A1-001 = Ground Floor, Group 1, locker 001.</p><div class="modal-actions"><button type="button" id="cm" class="ghost-btn">Cancel</button><button class="primary-btn">Add lockers</button></div></form>`);$('#cm').onclick=closeM;const upd=()=>{const f=+$('#lfloor').value,g=$('#lgroup').value||'1',q=+$('#lq').value,s=+$('#lstart').value||1;$('#codePreview').textContent=`${'ABCD'[f-1]}${g}-${String(s).padStart(3,'0')} → ${'ABCD'[f-1]}${g}-${String(s+q-1).padStart(3,'0')}`};['#lfloor','#lgroup','#lq','#lstart'].forEach(s=>$(s).oninput=$(s).onchange=upd);upd();$('#lf').onsubmit=async e=>{e.preventDefault();try{const x=await api('/api/lockers/bulk',{method:'POST',body:JSON.stringify({floor:+$('#lfloor').value,group:$('#lgroup').value,quantity:+$('#lq').value,startNumber:+$('#lstart').value})});closeM();toast(`${x.created.length} locker${x.created.length>1?'s':''} added.`);manage()}catch(x){toast(x.message,'error')}}}
async function maintenance(){if(!can('manage_maintenance'))return;const d=await api('/api/maintenance');const rows=d.maintenance.map(m=>`<tr><td><b>${esc(m.locker_code||m.locker_id)}</b></td><td>${esc(m.reason)}</td><td><span class="badge ${badgeClass(m.status)}">${statusLabel(m.status)}</span></td><td>${esc(m.severity)}</td><td>${fmt(m.reported_at)}</td><td>${m.status==='reported'?'<button class="small-btn" data-mid="'+m.id+'" data-act="acknowledge">Acknowledge</button>':m.status==='acknowledged'?'<button class="small-btn" data-mid="'+m.id+'" data-act="repair">Start repair</button>':m.status==='in_repair'?'<button class="small-btn green" data-mid="'+m.id+'" data-act="resolve">Resolve</button>':'Resolved'}</td></tr>`).join('')||'<tr><td colspan="6" class="empty">No maintenance records.</td></tr>';$('#viewContainer').innerHTML=`<div class="view"><div class="panel"><div class="panel-head"><div><h3>Maintenance operations</h3><p>Lifecycle: Reported → Acknowledged → In repair → Resolved → Available.</p></div></div><div class="table-wrap"><table><thead><tr><th>LOCKER</th><th>REASON</th><th>STATUS</th><th>SEVERITY</th><th>REPORTED</th><th>ACTION</th></tr></thead><tbody>${rows}</tbody></table></div></div></div>`;document.querySelectorAll('[data-mid]').forEach(b=>b.onclick=async()=>{try{await api('/api/maintenance/'+b.dataset.mid+'/'+b.dataset.act,{method:'POST'});toast('Maintenance state updated.');maintenance()}catch(e){toast(e.message,'error')}})}
async function profile(){
  const u=await api('/api/me').then(x=>x.user);
  A.user=u;
  $('#signedName').textContent=u.name;
  $('#signedRole').textContent=u.accessRole==='super_admin'?'Primary Administrator':u.accessRole==='staff'?'Staff':u.accessRole==='locker_manager'?'Locker Manager':'Student';
  
  let clubsHtml = '';
  let eventsHtml = '';
  
  if (A.user.accessRole === 'student') {
    try {
      const clubsData = await api('/api/clubs');
      const myClubs = clubsData.clubs.filter(c => c.my_status === 'active');
      const clubsList = myClubs.length ? myClubs.map(c => `
        <div class="activity-row">
          <div class="activity-dot"></div>
          <div><strong>${esc(c.name)}</strong><span>${esc(c.category)}</span></div>
        </div>
      `).join('') : '<div class="empty">You haven\'t joined any clubs yet.</div>';
      
      clubsHtml = `<div class="panel"><div class="panel-head"><div><h3>Joined Clubs</h3><p>Clubs you are a member of.</p></div></div><div class="activity-list">${clubsList}</div></div>`;

      const eventsData = await api('/api/events');
      const myEvents = eventsData.events.filter(e => e.my_status === 'registered');
      const eventsList = myEvents.length ? myEvents.map(e => `
        <div class="activity-row">
          <div class="activity-dot"></div>
          <div><strong>${esc(e.title)}</strong><span>${esc(e.event_date)} ${esc(e.time_start)}</span></div>
        </div>
      `).join('') : '<div class="empty">No registered events.</div>';
      
      eventsHtml = `<div class="panel"><div class="panel-head"><div><h3>Registered Events</h3><p>Your upcoming campus events.</p></div></div><div class="activity-list">${eventsList}</div></div>`;
    } catch (e) {
      console.error(e);
      clubsHtml = '<div class="empty">Error loading clubs</div>';
      eventsHtml = '<div class="empty">Error loading events</div>';
    }
  }

  $('#viewContainer').innerHTML=`<div class="view">
    <div class="profile-grid">
      <div>
        <div class="profile-card">
          <div class="profile-hero">
            <div class="profile-big-avatar"><img src="${u.profilePhoto||DEFAULT_AVATAR}" alt="Profile photo" onerror="this.onerror=null;this.src='${DEFAULT_AVATAR}'"></div>
            <div><p class="eyebrow">${esc(u.accessRole).toUpperCase()}</p><h3>${esc(u.name)}</h3><span>${esc(u.loginId)}</span></div>
          </div>
          <form id="pf" class="modal-form profile-form">
            <div class="form-grid"><div><label>FULL NAME</label><input id="pn" value="${esc(u.name)}" required></div><div><label>BRANCH / DEPARTMENT</label><input id="pb" value="${esc(u.branch||'')}" required></div></div>
            <div class="form-grid"><div><label>SEMESTER</label><input id="ps" value="${esc(u.semester||'')}"></div><div><label>CAMPUS</label><select id="pc"><option selected>Dwarka Campus</option></select></div></div>
            <div class="form-grid"><div><label>STUDENT / COLLEGE ID</label><input id="pi" value="${esc(u.studentId||'')}" placeholder="Optional"></div><div><label>MOBILE</label><input id="pm" value="${esc(u.mobile||'')}" required></div></div>
            <div class="form-grid"><div><label>EMAIL</label><input id="pe" value="${esc(u.email||'')}" type="email"></div><div><label>PROFILE PHOTO</label><input id="pp" type="file" accept="image/*"></div></div>
            <button class="primary-btn">Save profile</button>
          </form>
        </div>
        <div class="panel preferences-panel" style="margin-top:16px;">
          <div class="panel-head"><div><h3>Appearance</h3><p>Theme is saved locally for this browser.</p></div></div>
          <div class="theme-choice-row" style="padding:16px; display:flex; gap:10px; justify-content:center;">
            <button type="button" class="theme-choice ${document.body.classList.contains('dark')?'':'active'}" data-theme-choice="light">☀ Light</button>
            <button type="button" class="theme-choice ${document.body.classList.contains('dark')?'active':''}" data-theme-choice="dark">◐ Dark</button>
          </div>
        </div>
      </div>
      <div>
        ${clubsHtml}
        <div style="margin-top:16px;"></div>
        ${eventsHtml}
      </div>
    </div>
  </div>`;
  
  $('#pf').onsubmit=async e=>{
    e.preventDefault();
    try{
      const photo=$('#pp').files[0] ? await compressPhoto($('#pp').files[0]) : u.profilePhoto;
      const x=await api('/api/profile/update',{method:'POST',body:JSON.stringify({name:$('#pn').value.trim(),branch:$('#pb').value.trim(),semester:$('#ps').value.trim(),campus:$('#pc').value,studentId:$('#pi').value.trim(),mobile:$('#pm').value.trim(),email:$('#pe').value.trim(),profilePhoto:photo})});
      A.user=x.user;openApp();go('profile');toast('Profile saved.')
    }catch(e){toast(e.message,'error')}
  };
  profileThemeButtons();
}
function profileThemeButtons(){document.querySelectorAll('[data-theme-choice]').forEach(b=>b.onclick=()=>{localStorage.setItem('campuslock_theme',b.dataset.themeChoice);applyTheme();profileThemeButtons()});document.querySelectorAll('[data-theme-choice]').forEach(b=>b.classList.toggle('active',(b.dataset.themeChoice==='dark')===document.body.classList.contains('dark')))}
async function notifications(){
  const d=await api('/api/notifications');
  const isStaff = A.user.accessRole !== 'student';
  $('#viewContainer').innerHTML=`<div class="view"><div class="panel"><div class="panel-head"><div><h3>Notification center</h3><p>Stay on top of campus notices, updates, and important changes.</p></div><div>${isStaff?'<button class="primary-btn" id="postNoticeBtn" style="margin-right:8px;">＋ Post Notice</button>':''}<span class="badge yellow">${d.unread} unread</span> <button class="ghost-btn" id="readAll">Mark all read</button></div></div><div class="notification-list">${d.notifications.map(n=>`<button class="notification-item cc-action-card ${n.read_at?'':'unread'}" data-nid="${n.id}"><div class="notification-icon">${n.type.includes('reject')?'!':n.type.includes('approved')||n.type.includes('verified')?'✓':'•'}</div><div><strong>${esc(n.title)}</strong><p>${esc(n.body)}</p><span>${fmt(n.created_at)}</span></div></button>`).join('')||'<div class="empty">No notifications yet.</div>'}</div></div></div>`;
  $('#readAll').onclick=async()=>{await api('/api/notifications/read-all',{method:'POST'});notifications();pollNotifications()};
  document.querySelectorAll('[data-nid]').forEach(b=>b.onclick=async()=>{await api('/api/notifications/'+b.dataset.nid+'/read',{method:'POST'});notifications();pollNotifications()});
  if (isStaff) $('#postNoticeBtn').onclick = openPostNoticeModal;
}

function openPostNoticeModal(){
  modal(`<div class="modal-head"><h3>Post a Notice</h3><button id="closeM" class="close-btn">✕</button></div>
    <form id="noticeForm" class="modal-form">
      <p class="modal-wide-note" style="padding:0;">This will be sent to every student as a notification.</p>
      <div><label for="ntTitle">TITLE *</label><input id="ntTitle" required placeholder="e.g. Mid-sem exam schedule released"></div>
      <div><label for="ntBody">MESSAGE *</label><textarea id="ntBody" rows="4" required placeholder="Write the full notice here..."></textarea></div>
      <div class="modal-actions">
      <button type="button" class="ghost-btn" onclick="closeM()">Cancel</button>
        <button type="submit" class="primary-btn" id="submitNoticeBtn">Post Notice</button>
      </div>
    </form>`);
  $('#noticeForm').onsubmit = async (e) => { e.preventDefault();
    const title = $('#ntTitle').value.trim(), body = $('#ntBody').value.trim();
    if (!title || !body) { toast('Title and message are required','error'); return; }
    $('#submitNoticeBtn').disabled = true;
    try {
      const r = await api('/api/notices/broadcast', {method:'POST', body:JSON.stringify({title, body})});
      toast(r.message); closeM(); notifications();
    } catch(e) { toast(e.message,'error'); $('#submitNoticeBtn').disabled=false; }
  };
}
async function pollNotifications(){if(!A.user||!can('view_notifications'))return;try{const d=await api('/api/notifications');const b=$('#notificationBadge');if(d.unread){b.textContent=d.unread;b.classList.remove('hidden')}else b.classList.add('hidden')}catch{}clearTimeout(pollNotifications.t);pollNotifications.t=setTimeout(pollNotifications,20000)}
async function audit(){const d=await api('/api/audit');$('#viewContainer').innerHTML=`<div class="view"><div class="panel"><div class="panel-head"><div><h3>Security audit trail</h3><p>Actor, role, action, entity, transition and correlation context.</p></div></div><div class="table-wrap"><table><thead><tr><th>TIME</th><th>ACTOR</th><th>ROLE</th><th>ACTION</th><th>ENTITY</th><th>TRANSITION</th><th>CORRELATION</th></tr></thead><tbody>${d.audit.map(a=>`<tr><td>${fmt(a.created_at)}</td><td>${esc(a.actor)}</td><td>${esc(a.actor_role||'System')}</td><td><b>${esc(a.action)}</b></td><td>${esc(a.entity_type||'')} ${esc(a.entity_id||'')}</td><td>${esc(a.previous_state||'—')} → ${esc(a.new_state||'—')}</td><td>${esc(a.correlation_id||'—')}</td></tr>`).join('')||'<tr><td colspan="7" class="empty">No audit events.</td></tr>'}</tbody></table></div></div></div>`}
async function my(){const d=await api('/api/dashboard');$('#viewContainer').innerHTML=`<div class="view"><div class="grid-2"><div class="panel"><div class="panel-head"><div><h3>My locker</h3><p>Current assignment from the central database.</p></div></div>${d.myLocker?`<div class="my-locker-card"><strong>${esc(d.myLocker.locker_id)}</strong><span>${statusLabel(d.myLocker.status)} • Assigned ${fmt(d.myLocker.assigned_at)}</span><button class="primary-btn" id="openMine">View locker</button></div>`:'<div class="empty-card"><b>No locker assigned</b><span>Go to Find a Locker to request one.</span></div>'}</div><div class="panel"><div class="panel-head"><div><h3>Latest request</h3><p>Explicit request state and decision timeline.</p></div></div>${d.myRequest?`<div class="my-locker-card"><strong>${esc(d.myRequest.request_code)}</strong><span>${esc(d.myRequest.locker_id)} • ${statusLabel(d.myRequest.status)}</span>${d.myRequest.rejection_reason?`<p>${esc(d.myRequest.rejection_reason)}</p>`:''}</div>`:'<div class="empty-card"><b>No recent request</b><span>Your request history will appear here.</span></div>'}</div></div></div>`;$('#openMine')?.addEventListener('click',()=>{A.detailId=d.myLocker.locker_id;go('locker-detail')})}
async function qrFromLanding(token){try{await api('/api/qr/'+encodeURIComponent(token));const d=await api('/api/qr/'+encodeURIComponent(token));A.detailId=d.locker.locker_id;history.replaceState({},'',location.pathname);if(A.user.accessRole==='student')go('locker-detail');else go('locker-detail')}catch{}}
function init(){$('#verifyOtpBtn')?.addEventListener('click',verifyOtp);$('#resendOtpBtn')?.addEventListener('click',resendOtp);$('#backToSignupBtn')?.addEventListener('click',()=>{$('#otpPanel').classList.add('hidden');$('#signupPanel').classList.remove('hidden');});$('#otpCode')?.addEventListener('input',e=>{e.target.value=e.target.value.replace(/\D/g,'').slice(0,6)});document.querySelectorAll('.role-btn').forEach(b=>b.onclick=()=>role(b.dataset.role));document.querySelectorAll('.signup-role-btn').forEach(b=>b.onclick=()=>signupRole(b.dataset.signupRole));$('#loginForm').onsubmit=login;$('#signupForm').onsubmit=signup;$('#showSignupBtn').onclick=()=>{$('#loginPanel').classList.add('hidden');$('#signupPanel').classList.remove('hidden');signupRole(A.signupRole)};$('#showLoginBtn').onclick=showAuth;$('#campusButton')?.addEventListener('click',()=>$('.campus-select-wrap').classList.toggle('open'));document.querySelectorAll('#campusMenu button').forEach(b=>b.onclick=()=>{if(b.dataset.campus!=='Dwarka Campus'){toast('That campus is displayed for future rollout and cannot be selected yet.','error');return}$('#suCampus').value=b.dataset.campus;$('#campusButton').innerHTML=`${esc(b.dataset.campus)} <span>⌄</span>`;$('.campus-select-wrap').classList.remove('open')});$('#logoutBtn').onclick=logout;$('#themeBtn')?.addEventListener('click',toggleTheme);$('#themeBtnAuth')?.addEventListener('click',toggleTheme);$('#notificationBtn')?.addEventListener('click',()=>go('notifications'));$('#mobileNavBtn')?.addEventListener('click',()=>$('.sidebar').classList.toggle('open'));role('student');signupRole('student');applyTheme();
  $('#topbarProfileBtn')?.addEventListener('click',(e)=>{e.stopPropagation();$('#topbarProfileMenu').classList.toggle('hidden');});
  document.addEventListener('click',(e)=>{if(!e.target.closest('#topbarProfile'))$('#topbarProfileMenu')?.classList.add('hidden');if(!e.target.closest('#topbarSearchWrap'))$('#topbarSearchResults')?.classList.add('hidden');});
  $('#profileMenuProfile')?.addEventListener('click',()=>{$('#topbarProfileMenu').classList.add('hidden');go('profile');});
  $('#profileMenuSettings')?.addEventListener('click',()=>{$('#topbarProfileMenu').classList.add('hidden');go('profile');});
  $('#sidebarSettingsBtn')?.addEventListener('click',()=>go('profile'));
  $('#topbarSearch')?.addEventListener('input',debounce(runTopbarSearch,250));
  $('#topbarSearch')?.addEventListener('focus',()=>{if($('#topbarSearch').value.trim())runTopbarSearch();});
  $('#togglePwBtn')?.addEventListener('click',()=>{const i=$('#loginPassword');i.type=i.type==='password'?'text':'password';});
  $('#forgotPwLink')?.addEventListener('click',()=>toast('Contact your campus administrator to reset your password.'));
  document.querySelectorAll('.auth-sso-btn').forEach(b=>b.addEventListener('click',()=>toast('Single sign-on is coming soon — please sign in with your campus ID for now.')));
  $('#topGetStartedBtn')?.addEventListener('click',()=>$('#authCardFloating')?.scrollIntoView({behavior:'smooth',block:'center'}));
  $('#heroGetStartedBtn')?.addEventListener('click',()=>{$('#authCardFloating')?.scrollIntoView({behavior:'smooth',block:'center'});$('#loginId')?.focus();});
  $('#heroLearnMoreBtn')?.addEventListener('click',()=>$('#features')?.scrollIntoView({behavior:'smooth'}));
  document.querySelectorAll('.auth-topnav-links a').forEach(a=>a.addEventListener('click',()=>{
    document.querySelectorAll('.auth-topnav-links a').forEach(x=>x.classList.remove('active'));
    a.classList.add('active');
    const id=a.dataset.scroll;
    if(id==='top')window.scrollTo({top:0,behavior:'smooth'});
    else document.getElementById(id)?.scrollIntoView({behavior:'smooth'});
  }));
  const savedId=localStorage.getItem('campuslock_remember_id');
  if(savedId){$('#loginId').value=savedId;$('#rememberMe').checked=true;}
  $('#loginForm')?.addEventListener('submit',()=>{
    if($('#rememberMe').checked)localStorage.setItem('campuslock_remember_id',$('#loginId').value.trim());
    else localStorage.removeItem('campuslock_remember_id');
  });
  api('/api/me').then(d=>{A.user=d.user;openApp()}).catch(()=>showAuth());
}
async function runTopbarSearch(){
  const q=($('#topbarSearch').value||'').trim().toLowerCase();
  const box=$('#topbarSearchResults');
  if(!q){box.classList.add('hidden');box.innerHTML='';return;}
  let clubs=[],events=[];
  try{const d=await api('/api/clubs');clubs=(d.clubs||[]).filter(c=>c.name.toLowerCase().includes(q));}catch(e){}
  try{const d=await api('/api/events');events=(d.events||[]).filter(e=>e.title.toLowerCase().includes(q));}catch(e){}
  const rows=[
    ...clubs.slice(0,4).map(c=>`<button class="topbar-search-row" data-kind="club" data-id="${c.id}"><span class="topbar-search-row-icon">${iconImg('custom-clubs.png','Club')}</span><span><strong>${esc(c.name)}</strong><small>Club · ${esc(c.category||'General')}</small></span></button>`),
    ...events.slice(0,4).map(e=>`<button class="topbar-search-row" data-kind="event" data-id="${e.id}"><span class="topbar-search-row-icon">${iconImg('custom-events.png','Event')}</span><span><strong>${esc(e.title)}</strong><small>Event · ${esc(e.event_date||'')}</small></span></button>`)
  ];
  box.innerHTML = rows.length ? rows.join('') : `<div class="topbar-search-empty">No matches for "${esc(q)}"</div>`;
  box.classList.remove('hidden');
  box.querySelectorAll('.topbar-search-row').forEach(r=>r.onclick=()=>{
    box.classList.add('hidden');$('#topbarSearch').value='';
    if(r.dataset.kind==='club'){openClubDetail(Number(r.dataset.id));}else{go('events');}
  });
}
init();

// ══════════════════════════════════════════════════════════
// CLUBS — Full Featured
// ══════════════════════════════════════════════════════════

async function myClubs(){
  const d = await api('/api/clubs');
  const mine = d.clubs.filter(c=>c.my_status==='active');

  const card = c => `<div class="cb-club-card-full" onclick="openClubDetail(${c.id})">
      <div class="cb-club-cover" style="--club-tint:${clubAccent(c.category)};background-image:linear-gradient(180deg,rgba(36,54,75,.08),rgba(36,54,75,.24)),url('${esc(c.logo || '/CampusConnect-assets/backgrounds/clubs-events-background.png')}')">
        ${c.logo?'':`<div class="cb-club-cover-mark">${esc(c.name.slice(0,2).toUpperCase())}</div>`}
        <div class="cb-club-cover-badge"><span class="badge blue">${esc(c.my_role||'member')}</span></div>
      </div>
      <div class="cb-club-card-body">
        <strong style="font-size:14px;">${esc(c.name)}</strong>
        <div style="font-size:11px;color:var(--muted);margin-top:2px;">${esc(c.category||'General')} · ${c.member_count||0} members</div>
        <p style="font-size:12px;color:var(--muted);margin:10px 0 12px;min-height:32px;">${esc((c.description||'').slice(0,90))}${(c.description||'').length>90?'…':''}</p>
        <button class="ghost-btn" style="font-size:11px;padding:4px 10px;" onclick="event.stopPropagation();openClubDetail(${c.id})">Open club →</button>
      </div>
    </div>`;

  $('#viewContainer').innerHTML = `<div class="view">
    <div class="panel">
      <div class="panel-head"><div><h3>My Clubs</h3><p>Every club you belong to, in one place. Leaders and co-leaders can create events, schedule meetings and manage memories straight from here.</p></div><span class="badge gray">${mine.length} joined</span></div>
      <div class="cb-clubs-grid">${mine.map(card).join('') || '<div class="empty-card"><b>You have not joined a club yet.</b><span>Browse the Clubs page and request to join one that interests you.</span><button class="primary-btn" style="margin-top:12px;" onclick="go(\'clubs\')">Browse clubs →</button></div>'}</div>
    </div>
  </div>`;
}

async function clubs(){
  const d = await api('/api/clubs');
  const isStaff = A.user.accessRole !== 'student';

  const statusBadge = s => s==='active'?'<span class="badge green">Active</span>':s==='pending_staff'?'<span class="badge yellow">Pending Approval</span>':'<span class="badge gray">'+esc(s)+'</span>';

  const pendingClubs = d.clubs.filter(c=>c.status==='pending_staff');
  const activeClubs = d.clubs.filter(c=>c.status==='active');

  const clubCard = c => {
    const myRole = c.my_role;
    const myStatus = c.my_status;
    let membershipBtn = '';
    if (!isStaff) {
      if (myStatus === 'active') {
        membershipBtn = `<button class="ghost-btn" onclick="leaveClub(${c.id})">Leave</button>`;
      } else if (myStatus === 'pending') {
        membershipBtn = `<span class="badge yellow">Request Pending</span>`;
      } else {
        membershipBtn = `<button class="primary-btn" onclick="joinClub(${c.id})">Request to Join</button>`;
      }
    }
    const roleTag = myRole ? `<span class="badge blue">${esc(myRole)}</span>` : '';
    return `<div class="cb-club-card-full" onclick="openClubDetail(${c.id})">
      <div class="cb-club-cover" style="--club-tint:${clubAccent(c.category)};background-image:linear-gradient(180deg,rgba(36,54,75,.08),rgba(36,54,75,.24)),url('${esc(c.logo || '/CampusConnect-assets/backgrounds/clubs-events-background.png')}')">
        ${c.logo?'':`<div class="cb-club-cover-mark">${esc(c.name.slice(0,2).toUpperCase())}</div>`}
        <div class="cb-club-cover-badge">${statusBadge(c.status)}</div>
      </div>
      <div class="cb-club-card-body">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <strong style="font-size:14px;">${esc(c.name)}</strong>
          ${roleTag}
        </div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px;">${esc(c.category||'General')} · ${c.member_count||0} members${c.department?` · ${esc(c.department)}`:''}</div>
        <p style="font-size:12px;color:var(--muted);margin:10px 0 12px;min-height:32px;">${esc((c.description||'').slice(0,90))}${(c.description||'').length>90?'…':''}</p>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
          <button class="ghost-btn" style="font-size:11px;padding:4px 10px;" onclick="event.stopPropagation();openClubDetail(${c.id})">View Profile →</button>
          <div onclick="event.stopPropagation();">${membershipBtn}</div>
        </div>
      </div>
    </div>`;
  };

  const staffPendingSection = isStaff && pendingClubs.length ? `
    <div class="panel" style="margin-bottom:16px;">
      <div class="panel-head"><div><h3>⏳ Pending Club Proposals</h3><p>Review and approve student club proposals before they go live.</p></div><span class="badge yellow">${pendingClubs.length} pending</span></div>
      <div class="cb-clubs-grid">${pendingClubs.map(clubCard).join('')}</div>
    </div>` : '';

  const createBtn = `<button class="primary-btn" id="createClubBtn">＋ Propose New Club</button>`;
  const createEventBtn = isStaff ? `<button class="ghost-btn" id="createEventBtn">＋ Create Event</button>` : '';

  $('#viewContainer').innerHTML=`<div class="view clubs-view">
    <div class="toolbar">${createBtn}${createEventBtn}</div>
    ${staffPendingSection}
    <div class="panel">
      <div class="panel-head"><div><h3>Clubs & Societies</h3><p>Click any club to view details, members, and events.</p></div><span class="badge gray">${activeClubs.length} clubs</span></div>
      <div class="cb-clubs-grid">${activeClubs.map(clubCard).join('') || '<div class="empty">No active clubs yet.</div>'}</div>
    </div>
  </div>`;

  $('#createClubBtn').onclick = openCreateClubModal;
  if (isStaff) $('#createEventBtn').onclick = () => openCreateEventModal(null);
}

function clubAccent(cat){const m={Technical:'#A9BBC8',Cultural:'#C68F87',Sports:'#788875',Creative:'#C7A66A',Social:'#6F8F8B',Academic:'#6A7C8E'};return m[cat]||'#C68F87'}
function clubGradient(cat){
  const g = {
    Technical:'linear-gradient(135deg,#1d4ed8,#0891b2)',
    Cultural:'linear-gradient(135deg,#7c3aed,#c026d3)',
    Sports:'linear-gradient(135deg,#059669,#65a30d)',
    Creative:'linear-gradient(135deg,#db2777,#f59e0b)',
    Social:'linear-gradient(135deg,#0d9488,#22d3ee)',
    Academic:'linear-gradient(135deg,#1e293b,#475569)',
  };
  return g[cat] || 'linear-gradient(135deg,#334155,#0f172a)';
}

window.openClubDetail = (clubId) => { A.detailId = clubId; A.clubTab = 'overview'; go('club-detail'); };

async function clubDetailPage(){
  const clubId = A.detailId;
  let d;
  try { d = await api('/api/clubs/'+clubId); } catch(e) { toast(e.message,'error'); go('clubs'); return; }
  const {club, members, pendingRequests, isLeader, isStaff} = d;
  const canManage = isLeader || isStaff;
  const activeMembers = members.filter(m=>m.status==='active');
  const statusColors = {active:'green',pending_staff:'yellow',rejected:'red',archived:'gray'};

  const tabs = [
    ['overview','Overview'],
    ['members', `Members (${activeMembers.length})`],
    ['events','Events'],
    ['meetings','Meetings'],
    ['gallery','Memories'],
  ];
  const tabBar = `<div class="cb-tabs">${tabs.map(([k,label])=>`<button class="cb-tab ${A.clubTab===k?'active':''}" data-tab="${k}">${esc(label)}</button>`).join('')}</div>`;

  const heroAction = (() => {
    if (isStaff) return '';
    const myStatus = club.my_membership_status;
    if (myStatus === 'active') return `<button class="ghost-btn cb-hero-btn" onclick="leaveClub(${club.id})">Leave Club</button>`;
    if (myStatus === 'pending') return `<span class="badge yellow">Request Pending</span>`;
    return `<button class="primary-btn cb-hero-btn" onclick="joinClub(${club.id})">Request to Join</button>`;
  })();

  const hero = `<div class="cb-club-hero" style="background-image:linear-gradient(90deg,rgba(36,54,75,.78),rgba(36,54,75,.44)),url('/CampusConnect-assets/backgrounds/clubs-events-background.png')">
    <button class="ghost-btn back-btn cb-hero-back" id="backClubs">← All Clubs</button>
    <div class="cb-club-hero-row">
      <div class="cb-club-hero-mark">${esc(club.name.slice(0,2).toUpperCase())}</div>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
          <h2 class="cb-hero-title">${esc(club.name)}</h2>
          <span class="badge ${statusColors[club.status]||'gray'}">${club.status==='active'?'Active':club.status==='pending_staff'?'Awaiting Approval':esc(club.status)}</span>
        </div>
        <p class="cb-hero-sub">${esc(club.category||'General')}${club.department?' · '+esc(club.department):''} · ${activeMembers.length} member${activeMembers.length===1?'':'s'}${club.founder_name?' · Founded by '+esc(club.founder_name):''}</p>
      </div>
      <div>${heroAction}</div>
    </div>
  </div>`;

  let body;
  if (A.clubTab==='members') body = clubMembersTab(clubId, activeMembers, canManage);
  else if (A.clubTab==='events') body = `<div class="panel"><div id="clubEventsBody" class="cb-tab-body"><div class="empty">Loading events…</div></div></div>`;
  else if (A.clubTab==='meetings') body = `<div class="panel"><div id="clubMeetingsBody" class="cb-tab-body"><div class="empty">Loading meetings…</div></div></div>`;
  else if (A.clubTab==='gallery') body = `<div class="panel"><div id="clubGalleryBody" class="cb-tab-body"><div class="empty">Loading memories…</div></div></div>`;
  else body = clubOverviewTab(club, isLeader, isStaff, canManage, pendingRequests);

  $('#viewContainer').innerHTML = `<div class="view">${hero}${tabBar}${body}</div>`;
  $('#backClubs').onclick = () => go('clubs');
  document.querySelectorAll('.cb-tab').forEach(b=>b.onclick=()=>{ A.clubTab=b.dataset.tab; clubDetailPage(); });

  if (A.clubTab==='events') loadClubEventsTab(clubId, canManage, club.name);
  if (A.clubTab==='meetings') loadClubMeetingsTab(clubId, canManage);
  if (A.clubTab==='gallery') loadClubGalleryTab(clubId, club.my_membership_status==='active', isLeader, isStaff);
}

function clubOverviewTab(club, isLeader, isStaff, canManage, pendingRequests){
  const pendingHtml = canManage && pendingRequests.length ? `
    <div class="section-title">MEMBERSHIP REQUESTS (${pendingRequests.length})</div>
    <div class="activity-list">${pendingRequests.map(r=>`
      <div class="activity-row" style="align-items:center;">
        <div class="cb-club-mark" style="width:32px;height:32px;font-size:12px;border-radius:50%;">${esc((r.full_name||'?').slice(0,2).toUpperCase())}</div>
        <div style="flex:1;"><strong>${esc(r.full_name)}</strong><span style="font-size:11px;color:var(--muted);display:block;">${esc(r.student_id||'—')} · ${esc(r.branch||'—')}</span></div>
        <button class="small-btn green" onclick="reviewMembership(${club.id},${r.id},'approve')">Approve</button>
        <button class="danger-btn" style="font-size:11px;padding:4px 10px;" onclick="reviewMembership(${club.id},${r.id},'reject')">Reject</button>
      </div>`).join('')}</div>` : '';

  return `<div class="panel">
    <div class="cb-tab-body">
      ${club.description?`<p style="font-size:13px;line-height:1.6;">${esc(club.description)}</p>`:'<p class="empty">No description yet.</p>'}
      <div class="info-grid" style="margin-top:14px;">
        ${club.contact_email?`<div><span>Email</span><strong>${esc(club.contact_email)}</strong></div>`:''}
        ${club.contact_phone?`<div><span>Phone</span><strong>${esc(club.contact_phone)}</strong></div>`:''}
        ${club.meeting_schedule?`<div><span>Usually meets</span><strong>${esc(club.meeting_schedule)}</strong></div>`:''}
        ${club.founder_name?`<div><span>Founded by</span><strong>${esc(club.founder_name)}</strong></div>`:''}
      </div>
      ${isStaff && club.status==='pending_staff' ? `<div style="display:flex;gap:8px;margin-top:20px;padding-top:16px;border-top:1px solid var(--line);">
        <button class="primary-btn" style="flex:1;" onclick="reviewClub(${club.id},'approve')">✓ Approve Club</button>
        <button class="danger-btn" style="flex:1;" onclick="reviewClub(${club.id},'reject')">✕ Reject</button>
      </div>` : ''}
      ${isLeader ? `<div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--line);display:flex;gap:8px;flex-wrap:wrap;">
        <button class="ghost-btn" onclick="openCreateEventModal(${club.id},'${esc(club.name).replace(/'/g,"\\'")}')">＋ Create Event</button>
        <button class="ghost-btn" onclick="A.clubTab='meetings';clubDetailPage()">📅 Schedule a Meeting</button>
        <button class="ghost-btn" onclick="A.clubTab='gallery';clubDetailPage()">🖼 Add a Memory</button>
      </div>` : ''}
      ${pendingHtml}
    </div>
  </div>`;
}

function clubMembersTab(clubId, activeMembers, canManage){
  const rows = activeMembers.length ? activeMembers.map(m=>`
    <div class="activity-row" style="align-items:center;">
      <div class="cb-club-mark" style="width:36px;height:36px;font-size:13px;border-radius:50%;">${esc((m.full_name||'?').slice(0,2).toUpperCase())}</div>
      <div style="flex:1;">
        <strong style="font-size:13px;">${esc(m.full_name)}</strong>
        <span style="font-size:11px;color:var(--muted);display:block;">${esc(m.student_id||'—')} · ${esc(m.branch||'—')} · Year ${esc(m.year||'—')}</span>
      </div>
      <span class="badge ${m.role==='leader'?'blue':m.role==='co-leader'?'green':'gray'}">${esc(m.role)}</span>
      ${canManage && m.role !== 'leader' ? `<button class="small-btn" onclick="openRoleModal(${clubId},${m.id},'${esc(m.full_name)}','${esc(m.role)}')">Edit Role</button>` : ''}
    </div>`).join('') : '<div class="empty">No active members yet.</div>';
  return `<div class="panel"><div class="panel-head"><div><h3>Club Members</h3><p>Everyone currently part of this club, with their assigned title.</p></div></div><div class="activity-list">${rows}</div></div>`;
}

async function loadClubEventsTab(clubId, canManage, clubName){
  let d;
  try { d = await api('/api/clubs/'+clubId+'/events'); } catch(e) { $('#clubEventsBody').innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  const isStaff = A.user.accessRole !== 'student';
  const modeIcon = {online:`${iconImg('system-wifi.png','Online')}`,offline:`${iconImg('system-location.png','Offline')}`,hybrid:`${iconImg('custom-campus-services.png','Hybrid')}`};
  const card = (e, isPast) => {
    let actionBtn = '';
    if (isStaff) actionBtn = `<button class="ghost-btn" style="font-size:11px;padding:4px 10px;" onclick="viewEventRegistrants(${e.id})">View Registrants</button>`;
    else if (!isPast) {
      if (e.my_status==='registered') actionBtn = e.is_paid && e.my_payment_status!=='verified' ? `<span class="badge yellow">Payment ${esc(e.my_payment_status||'pending')}</span>` : '<span class="cb-registered">✓ Registered</span>';
      else actionBtn = `<button class="primary-btn" style="font-size:11px;padding:5px 12px;" onclick="openRegisterFlow(${e.id})">${e.is_paid?`Register · ₹${e.price}`:(e.requires_form?'Apply & Register':'Register')}</button>`;
    } else {
      actionBtn = e.my_status==='registered' ? '<span class="cb-registered">✓ Attended</span>' : '';
    }
    const day=(e.event_date||'').slice(8,10)||'--', mon=(e.event_date||'').slice(5,7)||'';
    return `<article class="cb-event-card">
      <div class="cb-event-date"><strong>${esc(day)}</strong><span>${esc(mon)}</span></div>
      <div class="cb-event-main">
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:4px;">
          <div class="cb-event-tag">${esc(e.type||'EVENT')}</div>
          <span style="font-size:10px;color:var(--muted);"><span class="inline-mode-icon">${modeIcon[e.event_mode]||iconImg('system-location.png','Offline')}</span>${esc(e.event_mode||'offline')}</span>
          ${e.is_paid?`<span class="badge yellow">₹${e.price} · Paid</span>`:''}
        </div>
        <h4>${esc(e.title)}</h4>
        <p>${esc(e.time_start||'Time TBA')} · ${esc(e.location||'Campus')} · ${e.attendee_count||0} attending</p>
        <div class="cb-event-action">${actionBtn}</div>
      </div>
    </article>`;
  };
  $('#clubEventsBody').innerHTML = `
    <div class="panel-head"><div><h3>Upcoming (${d.upcoming.length})</h3><p>Events this club is hosting soon.</p></div>${canManage?`<button class="primary-btn" id="clubNewEventBtn">＋ New Event</button>`:''}</div>
    <div class="cb-event-list" style="padding:12px 16px;">${d.upcoming.map(e=>card(e,false)).join('') || '<div class="empty">No upcoming events for this club.</div>'}</div>
    <div class="panel-head" style="border-top:1px solid var(--line);"><div><h3>Past Events (${d.past.length})</h3><p>What this club has already hosted — check the Memories tab for photos.</p></div></div>
    <div class="cb-event-list" style="padding:12px 16px;">${d.past.map(e=>card(e,true)).join('') || '<div class="empty">No past events yet.</div>'}</div>
  `;
  if (canManage) $('#clubNewEventBtn').onclick = () => openCreateEventModal(clubId, clubName);
}

async function loadClubMeetingsTab(clubId, canManage){
  let d;
  try { d = await api('/api/clubs/'+clubId+'/meetings'); } catch(e) { $('#clubMeetingsBody').innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  const modeIcon = {online:`${iconImg('system-wifi.png','Online')}`,offline:`${iconImg('system-location.png','Offline')}`,hybrid:`${iconImg('custom-campus-services.png','Hybrid')}`};
  const todayStr = new Date().toISOString().slice(0,10);
  const rows = d.meetings.map(m=>{
    const isPast = m.meeting_date < todayStr;
    const rsvpBtns = !isPast ? `
      <button class="small-btn ${m.my_rsvp==='going'?'green':''}" onclick="rsvpMeeting(${m.id},'going',${clubId})">✓ Going</button>
      <button class="small-btn ${m.my_rsvp==='not_going'?'red':''}" onclick="rsvpMeeting(${m.id},'not_going',${clubId})">✕ Can't go</button>` : '';
    return `<div class="cb-meeting-card">
      <div class="cb-meeting-date"><strong>${esc(m.meeting_date.slice(8,10))}</strong><span>${esc(m.meeting_date.slice(5,7))}</span></div>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
          <h4 style="margin:0;font-size:13px;">${esc(m.title)}</h4>
          <span style="font-size:10px;color:var(--muted);"><span class="inline-mode-icon">${modeIcon[m.meeting_mode]||iconImg('system-location.png','Offline')}</span>${esc(m.meeting_mode)}</span>
        </div>
        ${m.agenda?`<p style="font-size:11px;color:var(--muted);margin:4px 0;">${esc(m.agenda)}</p>`:''}
        <p style="font-size:11px;color:var(--muted);margin:2px 0;">${esc(m.start_time||'Time TBA')} · ${esc(m.location||(m.online_link?'Online':'TBA'))} · ${m.going_count} going · hosted by ${esc(m.created_by_name||'—')}</p>
        <div style="display:flex;gap:6px;margin-top:6px;">${rsvpBtns}</div>
      </div>
    </div>`;
  }).join('') || '<div class="empty">No meetings scheduled yet.</div>';

  $('#clubMeetingsBody').innerHTML = `
    <div class="panel-head"><div><h3>Club Meetings</h3><p>Internal meetings for members — RSVP to let leaders know you're coming.</p></div>${canManage?`<button class="primary-btn" id="scheduleMeetingBtn">＋ Schedule Meeting</button>`:''}</div>
    <div class="cb-meeting-list">${rows}</div>
  `;
  if (canManage) $('#scheduleMeetingBtn').onclick = () => openMeetingModal(clubId);
}

window.rsvpMeeting = async (meetingId, status, clubId) => {
  try { await api('/api/meetings/'+meetingId+'/rsvp/'+status, {method:'POST'}); toast('RSVP saved.'); loadClubMeetingsTab(clubId, true); }
  catch(e){ toast(e.message,'error'); }
};

function openMeetingModal(clubId){
  modal(`<div class="modal-head"><h3>Schedule a Meeting</h3><button id="closeM" class="close-btn">✕</button></div>
    <div class="modal-form">
      <div class="form-grid">
        <div><label>MEETING TITLE *</label><input id="mtTitle" required placeholder="e.g. Weekly sync"></div>
        <div><label>MODE</label><select id="mtMode"><option value="offline">📍 Offline</option><option value="online">🌐 Online</option><option value="hybrid">🔀 Hybrid</option></select></div>
      </div>
      <div><label>AGENDA</label><textarea id="mtAgenda" rows="3" placeholder="What will you discuss in this meeting?"></textarea></div>
      <div class="form-grid">
        <div><label>DATE *</label><input id="mtDate" type="date" required></div>
        <div><label>TIME</label><input id="mtTime" type="time" value="17:00"></div>
      </div>
      <div id="mtLocRow"><label>LOCATION</label><input id="mtLoc" placeholder="Room / Hall"></div>
      <div id="mtLinkRow" class="cc-modal-conditional" style="display:none;"><label>ONLINE LINK</label><input id="mtLink" placeholder="https://meet.google.com/..."></div>
    </div>
    <div class="modal-actions">
      <button class="ghost-btn" onclick="closeM()">Cancel</button>
      <button class="primary-btn" id="submitMeetingBtn">Schedule</button>
    </div>`);
  $('#mtMode').onchange = () => { $('#mtLinkRow').style.display = $('#mtMode').value!=='offline'?'block':'none'; };
  $('#submitMeetingBtn').onclick = async () => {
    const title = $('#mtTitle').value.trim(), date = $('#mtDate').value;
    if (!title||!date) { toast('Title and date are required','error'); return; }
    $('#submitMeetingBtn').disabled = true;
    try {
      await api('/api/clubs/'+clubId+'/meetings', {method:'POST', body:JSON.stringify({
        title, agenda:$('#mtAgenda').value.trim(), meetingDate:date, startTime:$('#mtTime').value,
        meetingMode:$('#mtMode').value, location:$('#mtLoc').value.trim(), onlineLink:($('#mtLink')||{}).value||''
      })});
      toast('Meeting scheduled!'); closeM(); loadClubMeetingsTab(clubId, true);
    } catch(e){ toast(e.message,'error'); $('#submitMeetingBtn').disabled=false; }
  };
}

async function loadClubGalleryTab(clubId, isMember, isLeader, isStaff){
  let d;
  try { d = await api('/api/clubs/'+clubId+'/gallery'); } catch(e) { $('#clubGalleryBody').innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  const canAdd = isMember || isStaff;
  const grid = d.photos.map(p=>`
    <div class="cb-memory-card">
      <img src="${p.image}" alt="${esc(p.caption||'Club memory')}" loading="lazy">
      <div class="cb-memory-info">
        <span>${esc(p.caption||'Untitled memory')}</span>
        <small>${esc(p.uploaded_by_name||'Member')}${p.event_title?' · '+esc(p.event_title):''}</small>
        ${(p.uploaded_by===A.user.id || isLeader || isStaff) ? `<button class="danger-btn" style="font-size:9px;padding:3px 8px;margin-top:6px;" onclick="deleteGalleryPhoto(${clubId},${p.id})">Remove</button>` : ''}
      </div>
    </div>`).join('') || '<div class="empty">No memories yet. Be the first to add one!</div>';

  $('#clubGalleryBody').innerHTML = `
    <div class="panel-head"><div><h3>Club Memories</h3><p>Photos from meetups, events, and everyday club life.</p></div>${canAdd?`<button class="primary-btn" id="addMemoryBtn">📷 Add Memory</button>`:''}</div>
    <div class="cb-memory-grid">${grid}</div>
  `;
  if (canAdd) $('#addMemoryBtn').onclick = () => openGalleryUploadModal(clubId);
}

window.deleteGalleryPhoto = async (clubId, photoId) => {
  if (!confirm('Remove this memory?')) return;
  try { await api(`/api/clubs/${clubId}/gallery/${photoId}/delete`,{method:'POST'}); toast('Memory removed.'); loadClubGalleryTab(clubId, true, true, true); }
  catch(e){ toast(e.message,'error'); }
};

function openGalleryUploadModal(clubId){
  modal(`<div class="modal-head"><h3>Add a Memory</h3><button id="closeM" class="close-btn">✕</button></div>
    <div class="modal-form">
      <div><label>PHOTO *</label><input id="gpFile" type="file" accept="image/*"></div>
      <div><label>CAPTION <em>OPTIONAL</em></label><input id="gpCaption" placeholder="What's happening in this photo?"></div>
    </div>
    <div class="modal-actions">
      <button class="ghost-btn" onclick="closeM()">Cancel</button>
      <button class="primary-btn" id="submitGpBtn">Add to Gallery</button>
    </div>`);
  $('#submitGpBtn').onclick = async () => {
    const file = $('#gpFile').files[0];
    if (!file) { toast('Please choose a photo','error'); return; }
    $('#submitGpBtn').disabled = true;
    try {
      const image = await compressPhoto(file);
      await api('/api/clubs/'+clubId+'/gallery', {method:'POST', body:JSON.stringify({image, caption:$('#gpCaption').value.trim()})});
      toast('Memory added!'); closeM(); loadClubGalleryTab(clubId, true, true, true);
    } catch(e){ toast(e.message,'error'); $('#submitGpBtn').disabled=false; }
  };
}

window.reviewClub = async (clubId, action) => {
  let reason = '';
  if (action === 'reject') {
    reason = prompt('Reason for rejection (optional)', 'Club proposal does not meet current requirements.');
    if (reason === null) return;
  }
  try {
    await api('/api/clubs/'+clubId+'/review/'+action, {method:'POST', body:JSON.stringify({reason})});
    toast(action==='approve'?'Club approved!':'Club rejected.');
    if (action==='approve') clubDetailPage(); else go('clubs');
  } catch(e) { toast(e.message,'error'); }
};

window.reviewMembership = async (clubId, memberId, action) => {
  try {
    await api(`/api/clubs/${clubId}/members/${memberId}/${action}`, {method:'POST'});
    toast(action==='approve'?'Membership approved!':'Request rejected.');
    clubDetailPage();
  } catch(e) { toast(e.message,'error'); }
};

window.openRoleModal = (clubId, memberId, name, currentRole) => {
  modal(`<div class="modal-head"><h3>Assign Role</h3><button id="closeM" class="close-btn">✕</button></div>
    <form id="roleForm" class="modal-form">
      <p>Assigning role for <strong>${esc(name)}</strong></p>
      <div><label for="roleInput">ROLE</label><input id="roleInput" value="${esc(currentRole)}" placeholder="e.g. co-leader, pr-leader, treasurer, secretary"></div>
      <div class="section-note">You can type any custom role: leader, co-leader, pr-leader, treasurer, secretary, etc.</div>
      <div class="modal-actions">
      <button type="button" class="ghost-btn" onclick="closeM()">Cancel</button>
        <button type="submit" class="primary-btn" id="saveRoleBtn">Save Role</button>
      </div>
    </form>`);
  $('#roleForm').onsubmit = async (e) => { e.preventDefault();
    const role = $('#roleInput').value.trim().toLowerCase();
    if (!role) { toast('Role cannot be empty','error'); return; }
    try {
      await api(`/api/clubs/${clubId}/members/${memberId}/role`, {method:'POST', body:JSON.stringify({role})});
      toast('Role updated!'); closeM(); clubDetailPage();
    } catch(e) { toast(e.message,'error'); }
  };
};

function openCreateClubModal() {
  modal(`<div class="modal-head"><h3>Propose a New Club</h3><button id="closeM" class="close-btn">✕</button></div>
    <form id="clubProposalForm" class="modal-form">
      <p class="modal-wide-note" style="padding:0;">📋 Your proposal will be sent to staff for review. Once approved, you become the club leader.</p>
      <div id="clubFormMsg" class="form-message" style="display:none;"></div>
      <div class="form-grid">
        <div><label for="cfName">CLUB NAME *</label><input id="cfName" required placeholder="e.g. Photography Club"></div>
        <div><label for="cfCat">CATEGORY *</label><select id="cfCat"><option>Technical</option><option>Cultural</option><option>Sports</option><option>Creative</option><option>Social</option><option>Academic</option><option>Other</option></select></div>
      </div>
      <div><label for="cfDesc">DESCRIPTION *</label><textarea id="cfDesc" rows="3" required placeholder="What is this club about? What activities will you do?"></textarea></div>
      <div class="form-grid">
        <div><label for="cfDept">DEPARTMENT</label><input id="cfDept" placeholder="e.g. CSE, Management"></div>
        <div><label for="cfEmail">CONTACT EMAIL</label><input id="cfEmail" type="email" placeholder="club@college.edu"></div>
      </div>
      <div class="form-grid">
        <div><label for="cfPhone">CONTACT PHONE</label><input id="cfPhone" inputmode="numeric" placeholder="Optional"></div>
        <div><label for="cfSchedule">MEETING SCHEDULE</label><input id="cfSchedule" placeholder="e.g. Every Saturday 4pm"></div>
      </div>
      <div>
        <label for="cfLogo">CLUB IMAGE</label>
        <input id="cfLogo" type="file" accept="image/*">
        <div class="section-note">Optional · This image will appear on the club card.</div>
      </div>
      <div class="modal-actions">
        <button type="button" class="ghost-btn" onclick="closeM()">Cancel</button>
        <button type="submit" class="primary-btn" id="submitClubBtn">Submit Proposal →</button>
      </div>
    </form>`);

  $('#clubProposalForm').onsubmit = async (e) => { e.preventDefault();
    const name = $('#cfName').value.trim();
    const desc = $('#cfDesc').value.trim();
    if (!name || !desc) { toast('Name and description are required','error'); return; }
    $('#submitClubBtn').disabled = true;
    try {
      const logo = $('#cfLogo').files[0] ? await compressPhoto($('#cfLogo').files[0]) : null;
      const r = await api('/api/clubs', {method:'POST', body:JSON.stringify({
        name, description:desc, category:$('#cfCat').value,
        department:$('#cfDept').value.trim(), contactEmail:$('#cfEmail').value.trim(),
        contactPhone:$('#cfPhone').value.trim(), meetingSchedule:$('#cfSchedule').value.trim(), logo
      })});
      toast('Club proposal submitted for staff review!');
      closeM(); clubs();
    } catch(e) {
      const msg = $('#clubFormMsg');
      msg.style.display='block'; msg.className='form-message'; msg.textContent=e.message;
    } finally { $('#submitClubBtn').disabled=false; }
  };
}

window.joinClub = async (id) => {
  try { await api('/api/clubs/'+id+'/join',{method:'POST'}); toast('Membership request sent to club leader!');
    if (A.view==='club-detail') clubDetailPage(); else clubs(); }
  catch(e) { toast(e.message,'error'); }
};
window.leaveClub = async (id) => {
  if (!confirm('Leave this club?')) return;
  try { await api('/api/clubs/'+id+'/leave',{method:'POST'}); toast('Left club.'); go('clubs'); }
  catch(e) { toast(e.message,'error'); }
};



// ══════════════════════════════════════════════════════════
// EVENTS — Full Featured
// ══════════════════════════════════════════════════════════

async function events(){
  const d = await api('/api/events');
  const isStaff = A.user.accessRole !== 'student';
  const modeIcon = {online:`${iconImg('system-wifi.png','Online')}`,offline:`${iconImg('system-location.png','Offline')}`,hybrid:`${iconImg('custom-campus-services.png','Hybrid')}`};

  const eventCard = e => {
    const registered = e.my_status === 'registered';
    let actionBtn = '';
    if (!isStaff) {
      if (registered) {
        actionBtn = (e.is_paid && e.my_payment_status!=='verified')
          ? `<span class="badge yellow">Payment ${esc(e.my_payment_status||'pending')}</span>`
          : '<span class="cb-registered">✓ Registered</span>';
      } else {
        actionBtn = `<button class="primary-btn" style="font-size:11px;padding:5px 12px;" onclick="openRegisterFlow(${e.id})">${e.is_paid?`Register · ₹${e.price}`:(e.requires_form?'Apply & Register':'Register')}</button>`;
      }
    } else {
      actionBtn = `<button class="ghost-btn" style="font-size:11px;padding:4px 10px;" onclick="viewEventRegistrants(${e.id})">View Registrants</button>`;
    }
    const day = (e.event_date||'').slice(8,10)||'--';
    const mon = (e.event_date||'').slice(5,7)||'';
    return `<article class="cb-event-card">
      <div class="cb-event-date"><strong>${esc(day)}</strong><span>${esc(mon)}</span></div>
      <div class="cb-event-main">
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:4px;">
          <div class="cb-event-tag">${esc(e.type||'EVENT')}</div>
          <span style="font-size:10px;color:var(--muted);"><span class="inline-mode-icon">${modeIcon[e.event_mode]||iconImg('system-location.png','Offline')}</span>${esc(e.event_mode||'offline')}</span>
          ${e.requires_form?'<span class="badge blue">Application required</span>':''}
          ${e.is_paid?`<span class="badge yellow">₹${e.price} · Paid entry</span>`:''}
        </div>
        <h4>${esc(e.title)}</h4>
        <p>${esc(e.club_name||'Campus event')} · ${esc(e.time_start||'Time TBA')} · ${esc(e.event_mode==='online'?(e.online_link?'Online':'Virtual'):(e.location||'Campus'))}</p>
        ${e.description?`<p style="font-size:11px;color:var(--muted);margin-top:4px;">${esc(e.description.slice(0,100))}${e.description.length>100?'…':''}</p>`:''}
        <div class="cb-event-action">${actionBtn}</div>
      </div>
    </article>`;
  };

  const createBtn = isStaff ? `<button class="primary-btn" id="createEventBtn">＋ Create Event</button>` : '';

  $('#viewContainer').innerHTML=`<div class="view">
    ${createBtn?`<div class="toolbar">${createBtn}</div>`:''}
    <div class="panel">
      <div class="panel-head"><div><h3>Upcoming Events</h3><p>Register for campus activities — online, offline, and hybrid.</p></div><span class="badge gray">${d.events.length} events</span></div>
      <div class="cb-event-list" style="padding:12px 16px;">${d.events.map(eventCard).join('') || '<div class="empty">No upcoming events yet.</div>'}</div>
    </div>
  </div>`;

  if (isStaff) $('#createEventBtn').onclick = () => openCreateEventModal(null);
}

// ── Unified registration flow: handles plain register, application forms,
//    and paid events (payment QR + proof upload) all from one modal. ──
window.openRegisterFlow = async (eventId) => {
  let d;
  try { d = await api('/api/events/'+eventId); } catch(e) { toast(e.message,'error'); return; }
  const ev = d.event, fields = d.fields || [];

  if (!ev.is_paid && !fields.length) {
    // Simple case — nothing to fill in, just confirm and register.
    try {
      await api('/api/events/'+eventId+'/register', {method:'POST', body:JSON.stringify({answers:{}})});
      toast('Registered for event!'); view();
    } catch(e) { toast(e.message,'error'); }
    return;
  }

  const fieldsHtml = fields.map((f,i) => {
    const req = f.required ? ' *' : '';
    const inputId = `ef_${i}`;
    let inp = '';
    if (f.type === 'textarea') {
      inp = `<textarea id="${inputId}" ${f.required?'required':''} placeholder="${esc(f.label)}" rows="3" style="width:100%;resize:vertical;font-family:inherit;font-size:13px;padding:8px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text);"></textarea>`;
    } else if (f.type === 'select' && f.options) {
      inp = `<select id="${inputId}" ${f.required?'required':''}>${f.options.map(o=>`<option>${esc(o)}</option>`).join('')}</select>`;
    } else {
      inp = `<input id="${inputId}" type="${f.type||'text'}" ${f.required?'required':''} placeholder="${esc(f.label)}">`;
    }
    return `<div><label>${esc(f.label)}${req}</label>${inp}</div>`;
  }).join('');

  const paymentHtml = ev.is_paid ? `
    <div class="cb-payment-box">
      <div class="cb-payment-head"><strong>Entry fee: ₹${ev.price}</strong><span>Scan the QR code below to pay, then upload your payment screenshot. ${ev.club_name?esc(ev.club_name):'The organizers'} will verify it shortly.</span></div>
      ${ev.payment_qr_image?`<img src="${ev.payment_qr_image}" alt="Payment QR code" class="cb-payment-qr">`:'<div class="empty">No QR code was uploaded for this event — contact the organizers.</div>'}
      <label>UPLOAD PAYMENT SCREENSHOT *</label><input id="rgProof" type="file" accept="image/*">
      <label style="margin-top:8px;display:block;">TRANSACTION ID / NOTE (optional)</label><input id="rgNote" placeholder="e.g. UPI ref number">
    </div>` : '';

  modal(`<div class="modal-head"><h3>${ev.is_paid?'Complete Registration':'Apply'}: ${esc(ev.title)}</h3><button id="closeM" class="close-btn">✕</button></div>
    <p style="font-size:12px;color:var(--muted);margin:0 0 12px;">${ev.club_name?esc(ev.club_name)+' · ':''}${esc(ev.event_date||'')} ${esc(ev.start_time||'')}</p>
    ${fieldsHtml?`<div class="modal-form">${fieldsHtml}</div>`:''}
    ${paymentHtml}
    <div class="modal-actions" style="margin-top:16px;">
      <button class="ghost-btn" onclick="closeM()">Cancel</button>
      <button class="primary-btn" id="submitFormBtn">${ev.is_paid?'Submit Payment & Register':'Submit & Register'}</button>
    </div>`);

  $('#submitFormBtn').onclick = async () => {
    const answers = {};
    fields.forEach((f,i) => { answers[f.label] = ($('#ef_'+i)||{}).value || ''; });
    let paymentProof = '';
    if (ev.is_paid) {
      const file = ($('#rgProof')||{}).files?.[0];
      if (!file) { toast('Please upload a payment screenshot','error'); return; }
      paymentProof = await compressPhoto(file);
    }
    $('#submitFormBtn').disabled = true;
    try {
      await api('/api/events/'+eventId+'/register', {method:'POST', body:JSON.stringify({
        answers, paymentProof, paymentNote: ($('#rgNote')||{}).value||''
      })});
      toast(ev.is_paid?'Payment submitted — pending verification.':'Application submitted & registered!');
      closeM(); view();
    } catch(e) { toast(e.message,'error'); $('#submitFormBtn').disabled=false; }
  };
};

window.viewEventRegistrants = async (eventId) => {
  let d;
  try { d = await api('/api/events/'+eventId+'/registrants'); } catch(e) { toast(e.message,'error'); return; }
  const isPaid = !!d.event.is_paid;
  const cols = ['Name','Student ID','Branch','Year',...(isPaid?['Payment']:[]),...(d.formFields.map(f=>f.label)),...(isPaid?['Verify']:[])];
  const payBadge = s => s==='verified'?'<span class="badge green">Verified</span>':s==='rejected'?'<span class="badge red">Rejected</span>':'<span class="badge yellow">Pending</span>';
  const rows = d.registrants.map(r=>{
    const cells = [esc(r.full_name), esc(r.student_id||'—'), esc(r.branch||'—'), esc(r.year||'—')];
    if (isPaid) cells.push(r.payment_proof?`<a href="${r.payment_proof}" target="_blank" rel="noopener">${payBadge(r.payment_status)}</a>`:payBadge(r.payment_status));
    d.formFields.forEach(f=>cells.push(esc(r.answers[f.label]||'—')));
    if (isPaid) cells.push(r.payment_status==='verified'?'—':`<button class="small-btn green" onclick="reviewPayment(${eventId},${r.user_id},'verify')">Verify</button> <button class="danger-btn" style="font-size:9px;padding:4px 8px;" onclick="reviewPayment(${eventId},${r.user_id},'reject')">Reject</button>`);
    return `<tr>${cells.map(v=>`<td>${v}</td>`).join('')}</tr>`;
  }).join('');
  modal(`<div class="modal-head"><h3>Registrants — ${esc(d.event.title)}</h3><button id="closeM" class="close-btn">✕</button></div>
    ${isPaid?`<p style="font-size:12px;color:var(--muted);margin:0 0 10px;">Click a Pending badge's screenshot link to view proof, then Verify or Reject.</p>`:''}
    <div class="table-wrap" style="max-height:400px;overflow:auto;">
      <table><thead><tr>${cols.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead>
      <tbody>${rows||'<tr><td colspan="'+cols.length+'" class="empty">No registrants yet.</td></tr>'}</tbody></table>
    </div>`);
};

window.reviewPayment = async (eventId, userId, action) => {
  try {
    await api(`/api/events/${eventId}/registrants/${userId}/payment/${action}`, {method:'POST'});
    toast(action==='verify'?'Payment verified.':'Payment rejected.');
    viewEventRegistrants(eventId);
  } catch(e) { toast(e.message,'error'); }
};

function openCreateEventModal(clubId, clubName) {
  const todayStr = new Date().toISOString().slice(0,10);
  const clubField = clubId
    ? `<div><label>HOSTED CLUB</label><input value="${esc(clubName||'This club')}" disabled></div>`
    : `<div><label>CLUB (optional)</label><input id="evClubIdText" placeholder="Leave blank for campus-wide event" disabled title="Create campus-wide events from here; club events are created from inside the club."></div>`;

  modal(`<div class="modal-head"><h3>Create Event</h3><button id="closeM" class="close-btn">✕</button></div>
    <form id="eventCreateForm" class="modal-form">
      <div id="evFormMsg" class="form-message" style="display:none;"></div>
    <div class="form-grid">
      <div><label>EVENT NAME *</label><input id="evTitle" required placeholder="e.g. Annual Hack Night"></div>
      <div><label>EVENT TYPE</label><select id="evType"><option>Workshop</option><option>Meetup</option><option>Competition</option><option>Hackathon</option><option>Activity</option><option>Seminar</option><option>General</option></select></div>
    </div>
    <div class="form-grid">${clubField}<div><label>DATE *</label><input id="evDate" type="date" required min="${todayStr}"></div></div>
    <label>DESCRIPTION</label><textarea id="evDesc" rows="2" placeholder="What should students expect?" style="width:100%;resize:vertical;font-family:inherit;font-size:13px;padding:8px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--text);"></textarea>
    <div class="form-grid">
      <div><label>MODE</label><select id="evMode"><option value="offline">📍 Offline</option><option value="online">🌐 Online</option><option value="hybrid">🔀 Hybrid</option></select></div>
      <div><label>CAPACITY (0=unlimited)</label><input id="evCap" type="number" min="0" value="0"></div>
    </div>
    <div class="form-grid">
      <div><label>START TIME</label><input id="evStart" type="time" value="10:00"></div>
      <div><label>END TIME</label><input id="evEnd" type="time" value="16:00"></div>
    </div>
    <div class="form-grid" id="evLocationRow">
      <div><label>LOCATION</label><input id="evLoc" placeholder="Room/Hall/Building"></div>
    </div>
    <div id="evOnlineLinkRow" style="display:none;">
      <label>ONLINE LINK</label><input id="evOnlineLink" placeholder="https://meet.google.com/...">
    </div>

    <div class="cb-toggle-row">
      <label class="cb-toggle"><input type="checkbox" id="evHasForm"> <span>Needs a custom registration form?</span></label>
    </div>
    <div id="evFormBuilder" style="display:none;margin-top:4px;border:1px solid var(--border);border-radius:10px;padding:12px;">
      <div style="font-size:12px;font-weight:700;margin-bottom:8px;">FORM FIELDS</div>
      <div id="evFormFields"></div>
      <button type="button" class="ghost-btn" style="margin-top:8px;font-size:11px;" id="addFieldBtn">＋ Add Field</button>
    </div>

    <div class="cb-toggle-row">
      <label class="cb-toggle"><input type="checkbox" id="evIsPaid"> <span>This is a paid event</span></label>
    </div>
    <div id="evPaidBuilder" style="display:none;margin-top:4px;border:1px solid var(--border);border-radius:10px;padding:12px;">
      <div class="form-grid">
        <div><label>PRICE PER STUDENT (₹) *</label><input id="evPrice" type="number" min="1" step="1" placeholder="e.g. 100"></div>
        <div><label>PAYMENT QR CODE *</label><input id="evQrFile" type="file" accept="image/*"></div>
      </div>
      <p class="section-note" style="font-size:11px;">Upload your UPI / bank payment QR code. Every student who registers will see this same QR to scan and pay — you verify each payment from the club's Events tab afterwards.</p>
      <img id="evQrPreview" style="display:none;max-width:140px;border-radius:10px;margin-top:6px;border:1px solid var(--line);">
    </div>

      <div class="modal-actions">
        <button type="button" class="ghost-btn" onclick="closeM()">Cancel</button>
        <button type="submit" class="primary-btn" id="submitEventBtn">Create Event</button>
      </div>
    </form>`);

  // Show/hide online link based on mode
  $('#evMode').onchange = () => {
    const mode = $('#evMode').value;
    $('#evOnlineLinkRow').style.display = mode !== 'offline' ? 'block' : 'none';
  };

  // Form builder toggle
  let formFields = [];
  $('#evHasForm').onchange = () => {
    $('#evFormBuilder').style.display = $('#evHasForm').checked ? 'block' : 'none';
  };

  const renderFields = () => {
    $('#evFormFields').innerHTML = formFields.map((f,i) => `
      <div style="display:flex;gap:6px;margin-bottom:6px;align-items:center;">
        <input value="${esc(f.label)}" placeholder="Field label" style="flex:2;" onchange="window._evFields[${i}].label=this.value">
        <select onchange="window._evFields[${i}].type=this.value">
          <option value="text" ${f.type==='text'?'selected':''}>Text</option>
          <option value="textarea" ${f.type==='textarea'?'selected':''}>Long text</option>
          <option value="number" ${f.type==='number'?'selected':''}>Number</option>
          <option value="email" ${f.type==='email'?'selected':''}>Email</option>
        </select>
        <label style="font-size:11px;white-space:nowrap;"><input type="checkbox" ${f.required?'checked':''} onchange="window._evFields[${i}].required=this.checked"> Req</label>
        <button type="button" class="danger-btn" style="padding:2px 8px;font-size:11px;" onclick="window._evFields.splice(${i},1);renderEvFields()">✕</button>
      </div>`).join('') || '<div style="font-size:12px;color:var(--muted);">No fields yet. Add a field below.</div>';
  };
  window._evFields = formFields;
  window.renderEvFields = () => { formFields=window._evFields; renderFields(); };
  renderFields();

  $('#addFieldBtn').onclick = () => {
    window._evFields.push({label:'',type:'text',required:false});
    renderFields();
  };

  // Paid-event toggle
  let qrImage = '';
  $('#evIsPaid').onchange = () => {
    $('#evPaidBuilder').style.display = $('#evIsPaid').checked ? 'block' : 'none';
  };
  $('#evQrFile').onchange = async () => {
    const file = $('#evQrFile').files[0];
    if (!file) return;
    qrImage = await compressPhoto(file);
    $('#evQrPreview').src = qrImage; $('#evQrPreview').style.display = 'block';
  };

  $('#eventCreateForm').onsubmit = async (e) => { e.preventDefault();
    const title = $('#evTitle').value.trim();
    const date = $('#evDate').value;
    if (!title||!date) { toast('Event name and date are required','error'); return; }
    if (date < todayStr) { toast('Event date cannot be in the past','error'); return; }
    const isPaid = $('#evIsPaid').checked;
    const price = parseFloat($('#evPrice').value)||0;
    if (isPaid && (!price || price<=0)) { toast('Enter a valid price for the paid event','error'); return; }
    if (isPaid && !qrImage) { toast('Please upload your payment QR code','error'); return; }
    const evClubId = clubId || null;
    const ff = $('#evHasForm').checked ? window._evFields.filter(f=>f.label.trim()) : [];
    $('#submitEventBtn').disabled=true;
    try {
      await api('/api/events', {method:'POST', body:JSON.stringify({
        title, description:$('#evDesc').value.trim(),
        clubId:evClubId, eventDate:date,
        startTime:$('#evStart').value, endTime:$('#evEnd').value,
        location:$('#evLoc').value.trim(), eventMode:$('#evMode').value,
        onlineLink:($('#evOnlineLink')||{}).value||'',
        capacity:parseInt($('#evCap').value)||0,
        eventType:$('#evType').value,
        formFields: ff,
        isPaid, price, paymentQr: isPaid ? qrImage : ''
      })});
      toast('Event created! It is now live on the dashboard for all students.'); closeM(); view();
    } catch(e) {
      const msg=$('#evFormMsg'); msg.style.display='block'; msg.className='form-message'; msg.textContent=e.message;
      $('#submitEventBtn').disabled=false;
    }
  };
}

function normalizeLostFoundDate(value){
  const v=(value||'').trim();
  if(!v) return '';
  const m=v.match(/^(\d{2}|\d{4})[-\/](\d{1,2})[-\/](\d{1,2})$/);
  if(!m) return v;
  let y=m[1]; y=y.length===2 ? `20${y}` : y;
  return `${y}-${String(m[2]).padStart(2,'0')}-${String(m[3]).padStart(2,'0')}`;
}
async function removeLostFound(id){
  if(!confirm('Remove this Lost & Found report?')) return;
  try{await api('/api/lostfound/'+id+'/remove',{method:'POST'});toast('Report removed.');lostfound();}catch(e){toast(e.message,'error')}
}
async function lostfound(){
  const d = await api('/api/lostfound');
  const isStaff = A.user.accessRole !== 'student';
  const statusBadge = s => s==='matched'?'<span class="badge blue">Possible Match</span>':s==='resolved'?'<span class="badge green">Resolved</span>':`<span class="badge gray">${esc(s)}</span>`;
  const items = d.items.map(i => `
    <div class="locker-card ${i.report_type==='lost'?'maintenance':'available'}" style="min-height:auto;${isStaff?'cursor:pointer;':''}" ${isStaff?`onclick="openLostFoundDetail(${i.id})"`:''}>
      <div class="locker-top">
        <strong class="locker-id">${esc(i.item_name)}</strong>
        <span class="badge ${i.report_type==='lost'?'red':'green'}">${esc(i.report_type).toUpperCase()}</span>
      </div>
      <div class="locker-room">${esc(i.location)} • ${esc(i.date_occurred)}${isStaff?' • '+esc(i.reporter_name):''}</div>
      <p style="font-size:10px; color:var(--muted); margin:10px 0;">${esc(i.description)}</p>
      <div class="locker-actions">
        ${statusBadge(i.status)}
        ${isStaff?'<button class="ghost-btn" style="font-size:10px;padding:4px 10px;" onclick="event.stopPropagation();openLostFoundDetail('+i.id+')">View Contact →</button>':'<button class="danger-btn" style="font-size:10px;padding:4px 10px;" onclick="event.stopPropagation();removeLostFound('+i.id+')">Remove</button>'}
      </div>
    </div>
  `).join('');
  
  $('#viewContainer').innerHTML=`
    <div class="view">
      <div class="toolbar">
        <button class="primary-btn" onclick="$('#lfModal').classList.remove('hidden')">＋ Report Lost or Found Item</button>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div><h3>${isStaff?'Lost & Found Directory':'My Lost & Found Reports'}</h3><p>${isStaff?'Every report submitted across campus. Open a card to see the reporter\'s contact details.':'Only you can see your own reports here — we\'ll notify you if a match turns up.'}</p></div>
        </div>
        <div class="locker-grid">
          ${items || '<div class="empty" style="grid-column: 1/-1;">'+(isStaff?'No reported items.':'You haven\'t reported anything yet.')+'</div>'}
        </div>
      </div>
    </div>
    
    <!-- Modal -->
    <div id="lfModal" class="modal-backdrop hidden">
      <div class="modal">
        <div class="modal-head"><h3>Report Item</h3><button class="close-btn" onclick="$('#lfModal').classList.add('hidden')">✕</button></div>
        <form id="lfForm" class="modal-form">
          <div class="form-grid">
            <div><label>TYPE</label><select id="lfType"><option value="lost">I Lost Something</option><option value="found">I Found Something</option></select></div>
            <div><label>ITEM NAME</label><input id="lfName" required placeholder="e.g. Blue Water Bottle"></div>
          </div>
          <label>DESCRIPTION</label><input id="lfDesc" required>
          <div class="form-grid">
            <div><label>LOCATION</label><input id="lfLoc" required></div>
            <div><label>DATE</label><input id="lfDate" required inputmode="numeric" placeholder="YYYY-MM-DD or YY-MM-DD"><small class="form-help">You can enter 26 for 2026. Press Enter to normalize.</small></div>
          </div>
          <div class="modal-actions">
            <button type="button" class="ghost-btn" onclick="$('#lfModal').classList.add('hidden')">Cancel</button>
            <button class="primary-btn">Submit Report</button>
          </div>
        </form>
      </div>
    </div>
  `;
  
  $('#lfDate').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();$('#lfDate').value=normalizeLostFoundDate($('#lfDate').value);}});
  $('#lfForm').onsubmit = async e => {
    e.preventDefault();
    const normalizedDate=normalizeLostFoundDate($('#lfDate').value);
    $('#lfDate').value=normalizedDate;
    if(!/^\d{4}-\d{2}-\d{2}$/.test(normalizedDate)){toast('Use a date like 2026-09-14 or 26-09-14.','error');return}
    try {
      const r = await api('/api/lostfound', {method:'POST', body:JSON.stringify({
        type: $('#lfType').value, name: $('#lfName').value, description: $('#lfDesc').value,
        location: $('#lfLoc').value, date: normalizedDate, category: 'General', time: ''
      })});
      $('#lfModal').classList.add('hidden');
      toast(r.matched ? 'Reported! We found a possible match — check your Notices.' : 'Item reported!');
      lostfound();
    } catch(err) { toast(err.message, 'error'); }
  };
}

window.openLostFoundDetail = async (id) => {
  let d;
  try { d = await api('/api/lostfound/'+id); } catch(e) { toast(e.message,'error'); return; }
  const i = d.item;
  modal(`<div class="modal-head"><h3>${esc(i.item_name)}</h3><button id="closeM" class="close-btn">✕</button></div>
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <span class="badge ${i.report_type==='lost'?'red':'green'}">${esc(i.report_type).toUpperCase()}</span>
      <span class="badge gray">${esc(i.status)}</span>
    </div>
    <p style="font-size:13px;margin:0 0 4px;"><b>Description:</b> ${esc(i.description||'—')}</p>
    <p style="font-size:13px;margin:0 0 4px;"><b>Location:</b> ${esc(i.location||'—')}</p>
    <p style="font-size:13px;margin:0 0 14px;"><b>Date:</b> ${esc(i.date_occurred||'—')}</p>
    <div class="cb-payment-box">
      <div class="cb-payment-head"><strong>Reporter contact</strong><span>Reach out to arrange handover or verification.</span></div>
      <p style="font-size:13px;margin:4px 0;"><b>Name:</b> ${esc(i.reporter_name)}</p>
      <p style="font-size:13px;margin:4px 0;"><b>Student/Staff ID:</b> ${esc(i.reporter_student_id||'—')}</p>
      <p style="font-size:13px;margin:4px 0;"><b>Phone:</b> ${esc(i.reporter_mobile||'—')}</p>
      <p style="font-size:13px;margin:4px 0;"><b>Email:</b> ${esc(i.reporter_email||'—')}</p>
    </div>`);
};

async function problems(){
  const d = await api('/api/problems');
  const rows = d.problems.map(p => `
    <tr>
      <td><b>${esc(p.category)}</b></td>
      <td>${esc(p.location)}</td>
      <td>${esc(p.description)}${p.photo?`<div style="margin-top:6px;"><img src="${p.photo}" alt="Problem photo" style="width:72px;height:52px;object-fit:cover;border-radius:7px;border:1px solid var(--line);"></div>`:''}</td>
      <td><span class="badge ${p.status==='resolved'?'green':p.status==='reported'?'red':'yellow'}">${esc(p.status)}</span>${!p.photo?'<small class="low-priority-label">Low priority · no photo</small>':''}</td>
      <td>${fmt(p.created_at)}</td>
    </tr>
  `).join('');
  
  $('#viewContainer').innerHTML=`
    <div class="view">
      <div class="toolbar">
        <button class="danger-btn" onclick="$('#probModal').classList.remove('hidden')">⚠️ Report Issue</button>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div><h3>Campus Problem Reports</h3><p>Infrastructure, cleanliness, and security issues.</p></div>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>CATEGORY</th><th>LOCATION</th><th>DESCRIPTION</th><th>STATUS</th><th>DATE</th></tr></thead>
            <tbody>${rows || '<tr><td colspan="5" class="empty">No reported problems.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- Modal -->
    <div id="probModal" class="modal-backdrop hidden">
      <div class="modal">
        <div class="modal-head"><h3>Report Problem</h3><button class="close-btn" onclick="$('#probModal').classList.add('hidden')">✕</button></div>
        <form id="probForm" class="modal-form">
          <div class="form-grid">
            <div>
              <label>CATEGORY</label>
              <select id="prCat">
                <option>Electrical</option><option>Water</option><option>Cleanliness</option>
                <option>Furniture</option><option>Wi-Fi</option><option>Security</option>
                <option>Infrastructure</option><option>Other</option>
              </select>
            </div>
            <div><label>LOCATION</label><input id="prLoc" required placeholder="e.g. Room 304"></div>
          </div>
          <label>DESCRIPTION</label><input id="prDesc" required placeholder="What is the issue?"><label style="margin-top:10px;display:block;">PHOTO <em>OPTIONAL</em></label><input id="prPhoto" type="file" accept="image/*"><small class="form-help">Adding a photo helps staff verify the issue. Reports without a photo are considered low priority.</small><div id="prWarning" class="role-notice staff-mode" style="display:none;margin-top:8px;"></div>
          <div class="modal-actions">
            <button type="button" class="ghost-btn" onclick="$('#probModal').classList.add('hidden')">Cancel</button>
            <button class="primary-btn" style="background:var(--redbg); color:var(--red)">Submit Alert</button>
          </div>
        </form>
      </div>
    </div>
  `;
  
  $('#prPhoto').onchange=()=>{if(!$('#prPhoto').files[0]){$('#prWarning').style.display='none';return}$('#prWarning').style.display='none'};
  $('#probForm').onsubmit = async e => {
    e.preventDefault();
    let photo=null;
    if($('#prPhoto').files[0]) photo=await compressPhoto($('#prPhoto').files[0]);
    if(!photo){
      $('#prWarning').style.display='block';
      $('#prWarning').innerHTML='<strong>Low-priority warning</strong><span>No photo was attached. This report will be considered low priority during review. Submit anyway or add a photo.</span>';
      if(!confirm('No photo was attached. This report will be considered low priority. Submit anyway?')) return;
    }
    try {
      const r=await api('/api/problems', {method:'POST', body:JSON.stringify({
        category: $('#prCat').value, location: $('#prLoc').value, description: $('#prDesc').value, photo
      })});
      $('#probModal').classList.add('hidden');
      toast(r.lowPriority?'Problem reported as low priority.':'Problem reported!');
      problems();
    } catch(err) { toast(err.message, 'error'); }
  };
}
