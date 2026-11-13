# AI Avatar Loom

Proyecto de generación de vídeos tipo Loom con avatar y voz clonada autorizada, más un módulo experimental de avatar en vivo mediante LiveKit y OBS Virtual Camera.

**Estado:** MVP y pruebas simuladas. No se ha validado todavía una generación real con los proveedores ni una sesión de entrevista de extremo a extremo. El servicio de cámara virtual no automatiza el enrutamiento de audio del sistema operativo.

## Componentes

- **Grok (xAI):** genera un guion a partir de un brief.
- **ElevenLabs:** sintetiza el guion usando tu clon de voz autorizado.
- **HeyGen:** recibe el audio y produce un vídeo de avatar MP4.
- **LiveKit Agents + Deepgram + Grok + ElevenLabs + LemonSlice:** agente de conversación con vídeo de avatar en directo.
- **OBS Virtual Camera:** presenta la ventana local con el avatar como cámara en aplicaciones web compatibles.
- **BlackHole / Loopback (macOS):** opción de enrutamiento de audio, con configuración manual.

## Inicio rápido: generación de vídeos

Requiere Python 3.11+.

    python -m venv .venv
    source .venv/bin/activate
    pip install -e '.[dev]'
    cp .env.example .env

Configura en tu archivo local .env las variables XAI_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, HEYGEN_API_KEY y HEYGEN_AVATAR_ID.

Para generar un guion:

    avatar-loom draft --brief examples/brief.txt --output examples/mi-guion.txt --seconds 90

Para usar tu voz propia, con autorización:

    avatar-loom clone-voice --name "Mi voz" --audio /ruta/a/muestra.mp3 --consent

Para enviar un vídeo a generación:

    avatar-loom generate --script examples/sample_script.txt --title "Reporte de avances"

El vídeo es asíncrono. Consulta su estado con:

    avatar-loom status --job output/reporte-de-avances/job.json

Cuando el proveedor complete el trabajo, el comando descargará el vídeo a output/reporte-de-avances/video.mp4. Un trabajo existente no se sobrescribe para evitar duplicar costes.

Generación por lotes:

    avatar-loom batch --manifest examples/videos.json --output-dir output

Revisa los guiones antes de publicar. Cada llamada de voz o vídeo puede gastar créditos según tu cuenta.

## Modo LiveKit + AI Virtual Camera

**Documentación detallada:** [virtual_cam/README.md](virtual_cam/README.md).

Requiere cuentas y credenciales de LiveKit Cloud, xAI, ElevenLabs y LemonSlice, además de Python, Node.js, OBS y un sistema de audio virtual si necesitas enviar y recibir audio desde una plataforma web propietaria.

    pip install -e '.[realtime]'
    cd virtual_cam && npm install && cd ..

Inicia tres procesos en tres terminales, desde la raíz del repositorio:

    python livekit_agent/agent.py dev
    python virtual_cam/token_server.py
    cd virtual_cam && npm run dev

Abre http://localhost:5173, conecta el avatar, captura la ventana desde OBS y activa OBS Virtual Camera. El audio del avatar **no** viaja por OBS Virtual Camera: usa un micrófono virtual independiente y separa la entrada del interlocutor del audio del agente.

El panel local marca visualmente **ASISTENTE DE IA**. Úsalo con identificación y consentimiento de las personas involucradas; ninguna integración garantiza funcionar en plataformas que bloqueen cámaras virtuales.

## Seguridad y privacidad

- **Nunca subas** .env con claves reales, muestras de voz, grabaciones de identidad o material biométrico al repositorio público.
- Los archivos .env, audios, vídeos y las rutas para muestras privadas están excluidos por .gitignore.
- Configura las API keys solo localmente y rota cualquier credencial expuesta por error.
- El clon de voz y el avatar requieren consentimiento y derechos de uso.
- Las respuestas generadas por IA pueden contener errores; revisa información, cifras y afirmaciones.
- Los proveedores externos procesan audio y vídeo; revisa sus políticas antes de proporcionar datos confidenciales.

## Tests

    pip install -e '.[dev]'
    python -m pytest -q
    python -m compileall -q src livekit_agent

Los tests usan peticiones HTTP y componentes falsos; **no** prueban credenciales reales, latencia, sincronización audiovisual ni compatibilidad con webs de entrevistas.

## Referencias

- [xAI API](https://docs.x.ai/)
- [ElevenLabs API](https://elevenlabs.io/docs/)
- [HeyGen API](https://developers.heygen.com/)
- [LiveKit Agents](https://docs.livekit.io/agents/)
- [LemonSlice con LiveKit](https://docs.livekit.io/agents/models/avatar/plugins/lemonslice/)
- [OBS Virtual Camera](https://obsproject.com/kb/virtual-camera-guide)
