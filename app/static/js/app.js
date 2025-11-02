let map = L.map('map').setView([50.4501, 30.5234], 13); // Київ
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19}).addTo(map);

let myPos = map.getCenter();
map.on('moveend', () => { myPos = map.getCenter(); });

let markers = [];
let geoMarker = null;      
let geoAccuracy = null;
let activeTripId = null;
let activeTrip = null;
let tripTicker = null;
let activeScooterMarker = null;


function log(msg){
  const el=document.getElementById('log');
  const d=document.createElement('div'); d.textContent=msg; el.prepend(d);
}

async function api(path, method='GET', body=null){
  try{
    const res = await fetch(path, {
      method,
      headers: {"Content-Type":"application/json"},
      body: body ? JSON.stringify(body) : null
    });
    const ct = res.headers.get('content-type') || '';
    const isJson = ct.includes('application/json');
    const data = isJson ? await res.json() : { ok:false, error: (await res.text()).slice(0,500) };

    if (!res.ok && isJson && data && data.ok !== true) return data;

    if (!res.ok && !isJson) return { ok:false, error:`HTTP ${res.status}. ${data.error || 'No JSON'}` };

    return data;
  }catch(e){
    return { ok:false, error:'network_error: ' + e.message };
  }
}

async function register(){
  const email=document.getElementById('reg_email').value;
  const password=document.getElementById('reg_pwd').value;
  const r=await api('/api/register','POST',{email,password});
  if(r.ok){ log('Реєстрація успішна'); await me(); }
  else{ log('Помилка: '+r.error); }
}
async function login(){
  const email=document.getElementById('login_email').value;
  const password=document.getElementById('login_pwd').value;
  const r=await api('/api/login','POST',{email,password});
  if(r.ok){ log('Вхід успішний'); await me(); }
  else{ log('Помилка: '+r.error); }
}
async function logout(){ await api('/api/logout','POST'); showAuth(false); log('Вихід'); }
async function topup(){
  const sum=parseInt(document.getElementById('topup_sum').value||'0'); if(sum<=0) return;
  const r=await api('/api/topup','POST',{amount_uah:sum});
  if(r.ok){ log('Баланс поповнено'); await me(); }
}

async function me(){
  const r=await api('/api/me');
  if(r.ok){
    document.getElementById('me_email').textContent=r.user.email;
    document.getElementById('me_balance').textContent=r.user.balance_uah;

    if(r.active_trip){
      activeTrip = r.active_trip;
      activeTripId = activeTrip.id;
      document.getElementById('end_btn').style.display='inline-block';
      startTripTicker();
    } else {
      activeTrip = null;
      activeTripId = null;
      stopTripTicker();
      document.getElementById('trip_info').textContent='немає';
      document.getElementById('trip_stats').textContent='';
      document.getElementById('end_btn').style.display='none';
    }
    showAuth(true);
  }else{
    activeTrip = null;
    stopTripTicker();
    showAuth(false);
  }
}

function showAuth(logged){
  document.getElementById('auth').style.display = logged ? 'none':'block';
  document.getElementById('me').style.display = logged ? 'block':'none';
}

function showAll(){
  const radiusInput = document.getElementById('radius');
  if (radiusInput) radiusInput.value = 0;
  findScooters();
}
window.showAll = showAll;

function clearMarkers(){ markers.forEach(m=>map.removeLayer(m)); markers=[]; }

async function findScooters()
{
  clearMarkers();

  const radius = parseFloat(document.getElementById('radius').value || '1');
  const r = await api(`/api/scooters?lat=${myPos.lat}&lng=${myPos.lng}&radius_km=${radius}`);

  if (!r.ok){
    log('Помилка завантаження самокатів: ' + (r.error || 'невідома'));
    return;
  }

  r.items.forEach(s => {
    const st = s.status;
    const sty = styleForStatus(st);
    const m = L.circleMarker([s.lat, s.lng], sty).addTo(map);
    m.__status = st;

    const canReserve = (st === 'available');
    const canStart   = (st === 'available' || st === 'reserved_me');
    let actions = '';
    actions += canReserve ? `<button onclick="reserve(${s.id})">Зарезервувати</button>` : '';
    actions += canStart   ? `<button onclick="startTrip(${s.id})">Почати поїздку</button>` : '';

    const reservedInfo = s.reserved_until && st === 'reserved_me'
      ? `<div>⏳ Резерв до: <b>${formatUADate(s.reserved_until)}</b></div>` : '';

    m.bindPopup(
      `<b>${s.code}</b><br>${labelForStatus(st)}<br>🔋 ${s.battery}%<br>${reservedInfo}${actions || '<small class="hint">Недоступний для дій</small>'}`
    );

    markers.push(m);
  });

  if (markers.length){
    const group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.2));
  }

  drawMe();
  highlightActiveOnMap();
  log(`Знайдено самокатів: ${r.items.length}`);
}

async function reserve(id){
  const r=await api('/api/reserve','POST',{scooter_id:id});
  if(r.ok){
    const nice = formatUADate(r.reserved_until);
    log('Резерв до: ' + nice);
    await findScooters();
  } else {
    log('Не вдалось зарезервувати: '+r.error);
  }
}


function formatUADate(iso){
  if(!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('uk-UA', {
    day: '2-digit', month: 'long',
    hour: '2-digit', minute: '2-digit'
  });
}

function startTripTicker(){
  stopTripTicker();
  if(!activeTrip) return;
  tripTicker = setInterval(()=>{
    const started = new Date(activeTrip.started_at);
    const nowD = new Date();
    const sec = Math.max(0, Math.floor((nowD - started) / 1000));
    const mm = Math.floor(sec/60).toString().padStart(2,'0');
    const ss = (sec%60).toString().padStart(2,'0');
    const km = haversineKm(activeTrip.start_lat, activeTrip.start_lng, myPos.lat, myPos.lng).toFixed(3);

    document.getElementById('trip_info').innerHTML =
      `🛴 <b>${activeTrip.scooter_code}</b> · ⏱ ${mm}:${ss}`;
    document.getElementById('trip_stats').textContent =
      `Старт: ${formatUADate(activeTrip.started_at)} · Дистанція ~ ${km} км`;
  }, 1000);
}
function stopTripTicker(){
  if(tripTicker){ clearInterval(tripTicker); tripTicker=null; }
}

function highlightActiveOnMap()
{
  if (!markers.length || !activeTrip) return;
  for (const m of markers){
    if (m.__status === 'in_trip_me'){
      activeScooterMarker = m;
      m.openPopup();

      map.panTo(m.getLatLng());
      break;
    }
  }
}

async function startTrip(id){
  const r=await api('/api/start_trip','POST',{scooter_id:id, lat: myPos.lat, lng: myPos.lng});
  if(r.ok){
    activeTripId=r.trip_id;
    await me();
    await findScooters();
    log('Поїздка почалась');
  } else {
    log('Старт неможливий: '+r.error);
  }
}


async function endTrip(){
  if(!activeTripId) return;
  const r=await api('/api/end_trip','POST',{trip_id:activeTripId, lat: myPos.lat, lng: myPos.lng});
  if(r.ok){
    stopTripTicker();
    activeTrip=null; activeTripId=null;
    document.getElementById('end_btn').style.display='none';
    document.getElementById('trip_info').textContent='немає';
    document.getElementById('trip_stats').textContent='';
    log(`Завершено: ${r.receipt.duration_sec}s, ${r.receipt.distance_km}км, ${r.receipt.price_uah} грн`);
    await me();
    await findScooters();
  }else{
    log('Завершити не вдалось: '+r.error);
  }
}


function styleForStatus(status)
{
  switch(status){
    case 'available':      return { radius: 8, color:'#1f9d55', fillColor:'#1f9d55', weight:2, fillOpacity:0.8 }; // зелений
    case 'reserved_me':    return { radius: 9, color:'#d97706', fillColor:'#f59e0b', weight:3, fillOpacity:0.9 }; // помаранчевий (мій)
    case 'reserved_other': return { radius: 8, color:'#f59e0b', fillColor:'#f59e0b', weight:1, fillOpacity:0.3 }; // блідий помаранчевий
    case 'in_trip_me':     return { radius: 10, color:'#2563eb', fillColor:'#3b82f6', weight:4, fillOpacity:0.9 }; // синій (мій)
    case 'in_trip_other':  return { radius: 8, color:'#dc2626', fillColor:'#ef4444', weight:2, fillOpacity:0.8 }; // червоний
    default:               return { radius: 8, color:'#6b7280', fillColor:'#9ca3af', weight:1, fillOpacity:0.6 };
  }
}

function labelForStatus(status){
  return {
    'available':      'Вільний',
    'reserved_me':    'Зарезервовано (мною)',
    'reserved_other': 'Зарезервовано (іншим)',
    'in_trip_me':     'Моя поїздка',
    'in_trip_other':  'У поїздці (інший користувач)'
  }[status] || status;
}

function haversineKm(lat1, lon1, lat2, lon2){
  const R = 6371.0, toRad = x => x*Math.PI/180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLon/2)**2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function setGeoMarker(lat, lng, accuracyMeters){
  const pos = L.latLng(lat, lng);

  if (!geoMarker) {
    geoMarker = L.circleMarker(pos, {
      radius: 8, color:'#2563eb', fillColor:'#3b82f6', weight:3, fillOpacity:0.9
    }).addTo(map).bindPopup('Ви тут');
  } else {
    geoMarker.setLatLng(pos);
  }

  if (accuracyMeters) {
    if (!geoAccuracy) {
      geoAccuracy = L.circle(pos, { radius: accuracyMeters, weight:1, fillOpacity:0.1 }).addTo(map);
    } else {
      geoAccuracy.setLatLng(pos);
      geoAccuracy.setRadius(accuracyMeters);
    }
  }
}

function useGeo(){
  if(!navigator.geolocation){
    log('Геолокація не підтримується браузером');
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude, accuracy } = pos.coords;
      myPos = L.latLng(latitude, longitude);
      setGeoMarker(latitude, longitude, accuracy);
      map.setView(myPos, 14);

      findScooters();
    },
    (err) => log('Не вдалося отримати геолокацію: ' + err.message),
    { enableHighAccuracy: true, timeout: 7000 }
  );
}

window.useGeo = useGeo;


me
