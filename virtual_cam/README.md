# AI Virtual Camera (macOS y sitios web)

El módulo muestra un avatar de LemonSlice como participante remoto de una sala LiveKit y ofrece una página local para capturar con OBS. Al activar **OBS Virtual Camera**, el vídeo se ofrece como webcam en navegadores compatibles. **OBS Virtual Camera no transporta audio.**

## Estructura

- livekit_agent/agent.py: agente con STT, Grok, ElevenLabs y LemonSlice.
- virtual_cam/token_server.py: genera tokens de corta vida para la sesión; escucha únicamente en 127.0.0.1.
- virtual_cam/index.html y main.js: panel local para conectar, ver el avatar, seleccionar entrada de sonido, activar/silenciar y mostrar vídeo.
- OBS Studio: captura ventana local y crea dispositivo de cámara virtual.
- BlackHole/Loopback (macOS): permiten crear rutas de audio virtuales, pero no se incluyen ni se configuran automáticamente.

## Requisitos

Python 3.11+, Node.js 20+, OBS Studio y credenciales activas de LiveKit, xAI, ElevenLabs y LemonSlice. Para enrutamiento bidireccional de audio en macOS, instala y configura BlackHole o Loopback según tus necesidades.

Desde la raíz:

    pip install -e '.[realtime]'
    cp .env.example .env
    cd virtual_cam && npm install && cd ..

Configura en .env:

- LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
- XAI_API_KEY y XAI_MODEL (un modelo habilitado para la cuenta)
- ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
- LEMONSLICE_API_KEY y exactamente uno entre LEMONSLICE_AGENT_ID y LEMONSLICE_IMAGE_URL
- Opcional: LIVEKIT_AGENT_NAME y LIVEKIT_SYSTEM_PROMPT_FILE

No subas .env, grabaciones ni claves a este repositorio público.

## Iniciar

Ejecuta en tres terminales desde la raíz:

    python livekit_agent/agent.py dev
    python virtual_cam/token_server.py
    cd virtual_cam && npm run dev

Visita http://localhost:5173, pulsa **Conectar avatar** y verifica que el vídeo aparezca. La página conserva la marca **ASISTENTE DE IA** cuando ocultas los controles.

En OBS: crea una fuente de captura de ventana del navegador, ajusta su resolución y pulsa **Start Virtual Camera**. En el sitio de prueba elige **OBS Virtual Camera** como dispositivo de vídeo. La compatibilidad depende de la plataforma web.

## Audio bidireccional (todavía manual)

Separa las señales para evitar bucles de eco:

    Plataforma web: voz del interlocutor -> ruta A -> entrada de audio del frontend LiveKit
    LiveKit: voz del avatar -> ruta B -> micrófono virtual que recibe la plataforma web

La ruta **A** debe contener exclusivamente el audio del interlocutor, nunca el del avatar. La ruta **B** debe contener únicamente el audio del avatar, nunca el del interlocutor. Si las rutas se mezclan, el agente puede responderse a sí mismo, interrumpirse y producir eco.

En macOS puedes usar dispositivos BlackHole independientes (por ejemplo 2ch y 16ch) más un enrutador por aplicación como Loopback. Para ensayar, utiliza navegadores distintos para la plataforma de entrevista y el panel LiveKit. Configura una salida independiente por navegador, escucha con audífonos y comprueba las rutas antes de publicar audio en la llamada.

El enrutamiento por aplicación **no está implementado automáticamente** y requiere pruebas locales.

## Checklist de aceptación

1. Comprueba que el navegador reconoce OBS Virtual Camera en una sesión de prueba consentida.
2. Comprueba que el vídeo incluye la etiqueta ASISTENTE DE IA.
3. Envía una pregunta a la ruta A y confirma la respuesta del agente.
4. Confirma que en B solo aparece la voz del avatar.
5. Desconecta y verifica que no queda una fuente de audio publicando.

## Limitaciones

- No se ha validado esta integración en servicios reales con credenciales.
- Las plataformas propietarias o supervisadas pueden bloquear cámaras virtuales.
- No incluye mecanismos para eludir restricciones de entrevistas ni de proctoring.
- El uso en entrevistas de terceros requiere identificar el avatar como IA y contar con aprobación de la contraparte.

Referencias:
[LiveKit Agents](https://docs.livekit.io/agents/) ·
[LemonSlice](https://docs.livekit.io/agents/models/avatar/plugins/lemonslice/) ·
[OBS](https://obsproject.com/kb/virtual-camera-guide) ·
[BlackHole](https://github.com/ExistentialAudio/BlackHole/wiki/Use-BlackHole-as-a-Virtual-Microphone)
