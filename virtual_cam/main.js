import {Room, RoomEvent, Track} from 'livekit-client';

const $ = (id) => document.getElementById(id);
const videoStage = $('stage');
const placeholder = $('placeholder');
const status = $('status');
const controls = {
  connect: $('connect'), disconnect: $('disconnect'), mic: $('mic'), refresh: $('refresh'),
  toggleMic: $('toggle-mic'), present: $('present'),
};
let room = null;
let microphoneActive = false;
let selectedVideo = null;
const audioElements = new Map();

function setStatus(message) { status.textContent = message; }
function buttons(connected) {
  controls.connect.disabled = connected;
  controls.disconnect.disabled = !connected;
  controls.toggleMic.disabled = !connected;
}

function attached(track, _publication, participant) {
  if (track.kind === Track.Kind.Video && !selectedVideo) {
    selectedVideo = track.attach();
    selectedVideo.autoplay = true;
    selectedVideo.playsInline = true;
    selectedVideo.style.transform = 'none';
    videoStage.insertBefore(selectedVideo, placeholder);
    placeholder.hidden = true;
    setStatus(`Avatar conectado (${participant.identity})`);
  } else if (track.kind === Track.Kind.Audio) {
    const element = track.attach();
    element.autoplay = true;
    element.style.display = 'none';
    document.body.appendChild(element);
    audioElements.set(track, element);
    element.play().catch(() => setStatus('Clic para permitir reproducción de audio'));
  }
}
function detached(track) {
  for (const el of track.detach()) el.remove();
  if (audioElements.has(track)) audioElements.delete(track);
  if (selectedVideo && !selectedVideo.isConnected) {
    selectedVideo = null;
    placeholder.hidden = false;
  }
}
async function refreshMicrophones() {
  // Browsers may hide device names until permission is granted.
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  stream.getTracks().forEach(t => t.stop());
  const devices = await navigator.mediaDevices.enumerateDevices();
  controls.mic.replaceChildren(new Option('Micrófono del sistema', ''));
  devices.filter(d => d.kind === 'audioinput' && d.deviceId !== 'default')
    .forEach(d => controls.mic.add(new Option(d.label || 'Entrada de audio', d.deviceId)));
}
async function connect() {
  buttons(true); setStatus('Creando sesión...');
  try {
    const response = await fetch('http://127.0.0.1:8765/token', { cache: 'no-store' });
    if (!response.ok) throw new Error('Token server no disponible o sin credenciales');
    const { serverUrl, token } = await response.json();
    const activeRoom = new Room({ adaptiveStream: true, dynacast: true });
    room = activeRoom;
    activeRoom.on(RoomEvent.TrackSubscribed, attached);
    activeRoom.on(RoomEvent.TrackUnsubscribed, detached);
    activeRoom.on(RoomEvent.Disconnected, () => { clean(); setStatus('Desconectado'); });
    await activeRoom.connect(serverUrl, token);
    await activeRoom.startAudio();
    setStatus('Conectado. Iniciando avatar...');
  } catch (e) { clean(); setStatus(`Error: ${e.message}`); }
}
async function toggleMicrophone() {
  if (!room) return;
  try {
    if (microphoneActive) {
      await room.localParticipant.setMicrophoneEnabled(false);
      microphoneActive = false;
    } else {
      const id = controls.mic.value;
      await room.localParticipant.setMicrophoneEnabled(true, {
        ...(id ? { deviceId: { exact: id } } : {}),
        echoCancellation: false, noiseSuppression: false, autoGainControl: false,
      });
      microphoneActive = true;
    }
    controls.toggleMic.textContent = microphoneActive ? 'Silenciar entrada' : 'Activar entrada';
  } catch (e) { setStatus(`Micrófono: ${e.message}`); }
}
function clean() {
  microphoneActive = false;
  controls.toggleMic.textContent = 'Activar entrada';
  if (room) { const old = room; room = null; old.disconnect(); }
  if (selectedVideo) { selectedVideo.remove(); selectedVideo = null; }
  audioElements.forEach(el => el.remove()); audioElements.clear();
  placeholder.hidden = false; buttons(false);
}
controls.connect.addEventListener('click', connect);
controls.disconnect.addEventListener('click', () => { clean(); setStatus('Desconectado'); });
controls.toggleMic.addEventListener('click', toggleMicrophone);
controls.refresh.addEventListener('click', () => refreshMicrophones().catch(e => setStatus(e.message)));
controls.present.addEventListener('click', () => document.body.classList.toggle('present'));
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') document.body.classList.remove('present'); });
