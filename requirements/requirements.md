# Documento de Arquitectura: Asistente Personal de IA Local Distribuido ("Hey Lili")

## 1. Contexto de la Situación
El entorno del sistema es una red de área local (LAN) privada compuesta por tres nodos principales:
1. **MacBook Air (macOS Monterey):** Servidor de escucha continua de micrófono, detección de Wake Word, transcripción (STT), orquestador central (Core API) y retroalimentación auditiva (TTS).
2. **PC CachyOS (Linux):** Entorno de desarrollo primario y nodo de alta capacidad de cómputo ("el cerebro") que aloja y ejecuta el motor Ollama (LLM), además de actuar como cliente ejecutor de acciones locales en Linux (scripts `.sh`, multimedia, etc.).
3. **PC con Windows:** Cliente receptor y ejecutor de tareas específicas de Windows (control multimedia Spotify/YouTube Music, simulación de teclado/ratón vía PyAutoGUI).

Toda la infraestructura opera de forma 100% privada, local y está concebida para ser extensible hacia futuros dispositivos (dispositivos IoT, apps móviles, etc.).

---

## 2. Estructura del Proyecto (Monorepo)

```text
comandos-voz/
├── server/                      # Orquestador central en MacBook Air
│   ├── app.py                   # API Flask (enrutamiento, estado y orquestación)
│   ├── requirements.txt         # Dependencias del servidor de Mac
│   ├── audio/
│   │   ├── wake_word.py         # Escucha activa "Hey Lili" (openWakeWord / Porcupine)
│   │   ├── vad.py               # Detección de fin de voz (Silero VAD)
│   │   ├── stt.py               # Transcripción con faster-whisper
│   │   └── tts.py               # Feedback sonoro y síntesis de voz (say / piper)
│   └── services/
│       ├── registry.py          # Registro y descubrimiento de nodos clientes
│       ├── llm_client.py        # Comunicación con Ollama en CachyOS
│       └── dispatcher.py        # Despacho de órdenes a nodos locales o remotos
├── clients/
│   ├── cachyos/                 # Cliente ejecutor en CachyOS (Linux)
│   │   ├── app.py               # Servidor ligero Flask (puerto configurable)
│   │   ├── skills/              # Scripts de automatización y control Linux (.sh, etc.)
│   │   └── systemd/             # Definición de servicio systemd para autoarranque
│   └── windows/                 # Cliente ejecutor en Windows
│       ├── app.py               # Servidor ligero Flask
│       ├── skills/              # Control multimedia, PyAutoGUI, etc.
│       └── start_client.bat     # Script de inicio automático
├── common/                      # Código y modelos compartidos entre nodos
│   ├── models.py                # Modelos de datos y esquemas Pydantic
│   ├── security.py              # Validación de tokens internos (X-Internal-Token)
│   └── constants.py             # Enums de dispositivos, acciones y estados
├── scripts/
│   └── mac/                     # Instalación y ejecución automatizada en macOS
│       ├── setup_mac.command    # Instalador automático interactivo (doble clic en Finder)
│       ├── run_mac.command      # Lanzador manual de depuración con doble clic
│       └── com.lili.server.plist # Definición de servicio persistente launchd
├── tests/                       # Suite de pruebas automatizadas con pytest
│   ├── test_router.py
│   ├── test_models.py
│   └── test_skills.py
├── rules/
│   └── agent.md                 # Reglas estrictas de desarrollo para agentes y humanos
├── .env.example                 # Plantilla de variables de entorno
└── requirements/
    └── requirements.md          # Especificación de arquitectura y requerimientos
```

---

## 3. Flujo Integral de Ejecución

$$\text{Audio Continuo} \xrightarrow{\text{Wake Word}} \text{Chime de Activación} \xrightarrow{\text{VAD + STT}} \text{Texto} \xrightarrow{\text{Core API}} \text{Ollama (JSON)} \xrightarrow{\text{Dispatcher}} \text{Nodo Destino} \xrightarrow{\text{Respuesta / TTS}}$$

1. **Escucha:** La Mac detecta la frase "Hey Lili".
2. **Feedback Inmediato:** Se reproduce un sonido corto (*chime*) de confirmación.
3. **Captura y VAD:** Se graba el comando del usuario; `Silero VAD` detecta el silencio final para cerrar la grabación sin tiempos muertos.
4. **Transcripción (STT):** `faster-whisper` genera el texto localmente en la Mac.
5. **Inferencia LLM:** El orquestador envía el texto con el catálogo de habilidades a Ollama en CachyOS mediante HTTP.
6. **Validación:** El orquestador valida la respuesta de Ollama contra el modelo Pydantic `CommandIntent`.
7. **Despacho:** Se envía la orden (`POST /api/execute`) al nodo correspondiente (Mac, CachyOS o Windows).
8. **Feedback Final:** El nodo orquestador reproduce una confirmación verbal (TTS) o sonora del resultado.

---

## 4. Requerimientos Detallados del Sistema

### Requerimiento 1: Pipeline de Audio y Detección de Wake Word (MacBook Air)
* **Detección de Palabra Clave:** Módulo continuo de bajo consumo usando `openWakeWord` (o modelo entrenado para "Hey Lili").
* **Voice Activity Detection (VAD):** Integración de `silero-vad` para cortar la grabación automáticamente tras 1.0 - 1.5 segundos de silencio post-comando.
* **Speech-to-Text (STT):** `faster-whisper` corriendo en la Mac (modelo `base` o `small` optimizado para español/inglés).
* **Feedback Auditivo y TTS:** 
  * Chime de activación al detectar la palabra clave.
  * Síntesis de voz para confirmaciones o lectura de respuestas (ej. comando nativo `say` de macOS o `piper-tts`).

### Requerimiento 2: Orquestador Central Core API (Flask en Mac)
* **Endpoints Principales:**
  * `POST /api/command`: Recibe texto transcrito manualmente o por voz para orquestar la intención.
  * `POST /api/nodes/register`: Permite a los nodos clientes reportar su IP, capacidades (skills) y puerto al iniciar.
  * `GET /api/nodes/status`: Retorna el estado en vivo (online/offline) y latencia de cada nodo.
* **Tolerancia a Fallos y Timeouts:** Todas las llamadas hacia nodos externos deben implementar timeouts explícitos (`connect=2s`, `read=8s`). Si un nodo no responde, se reporta error amigable al usuario vía TTS.

### Requerimiento 3: Inteligencia Distribuida (Ollama en CachyOS)
* **Servicio LLM:** CachyOS ejecuta Ollama expuesto a la LAN en su puerto (por defecto `11434`), con modelos ligeros de baja latencia (ej. `llama3.2:3b`, `qwen2.5:7b` o `mistral:7b`).
* **Contrato Estricto de Datos (JSON Schema):** Ollama responderá únicamente con un JSON estructurado acorde al modelo Pydantic:
  ```json
  {
    "intent": "play_music",
    "target_device": "windows",
    "action": "spotify_play",
    "parameters": {
      "query": "Daft Punk",
      "platform": "spotify"
    },
    "speech_response": "Reproduciendo Daft Punk en la PC con Windows."
  }
  ```
* **Resiliencia de Parsing:** Si la respuesta de Ollama contiene texto extra o no valida contra Pydantic, el orquestador ejecutará una pasada de extracción con regex o un reintento automático.

### Requerimiento 4: Servidores Cliente Ejecutores (CachyOS y Windows)
* **Servidor Flask Ligero:** Corriendo en segundo plano en cada nodo ejecutor.
* **Endpoints en Clientes:**
  * `POST /api/execute`: Recibe la acción autorizada y los parámetros validados.
  * `GET /api/health`: Health check rápido para el orquestador.
* **Descubrimiento de Red (Service Discovery):**
  * Mecanismo primario: Al arrancar, el cliente se anuncia a la IP del orquestador definida en la variable de entorno `SERVER_HOST`.
  * Soporte opcional: Resolución de nombres local mediante mDNS (`macbook.local`).
* **Catálogo de Habilidades (Skills):**
  * **macOS:** Alarmas, recordatorios (AppleScript), clima (OpenWeatherMap API), volumen del sistema.
  * **CachyOS:** Control de sesiones multimedia, lanzamiento de aplicaciones, ejecución de scripts bash parametrizados.
  * **Windows:** Control de Spotify / YouTube Music, atajos de teclado y automatización de interfaz vía `PyAutoGUI`.

### Requerimiento 5: Seguridad en la Red Local (LAN)
* **Autenticación Inter-nodo:** Toda petición entre el servidor y los clientes o viceversa debe incluir la cabecera HTTP `X-Internal-Token` validada contra una clave compartida configurada en `.env`.
* **Lista Blanca de Acciones:** Los clientes ejecutarán únicamente acciones registradas en su catálogo de skills local, rechazando comandos arbitrarios o inyecciones de shell.

### Requerimiento 6: Instalación Automatizada, Despliegue y Autoarranque

#### A. Estrategia de Transferencia (CachyOS -> Mac)
El desarrollo y versionado se realiza en CachyOS. Para transferir los componentes hacia la MacBook Air se soportan dos vías:
1. **Vía Git (Recomendada):** Repositorio remoto privado; en la Mac se ejecuta `git clone` y subsecuentes `git pull`.
2. **Vía Red Local Directa (rsync / scp):** Sincronización directa mediante SSH:
   ```bash
   rsync -avz --exclude 'venv' --exclude '__pycache__' ./ usuario_mac@ip_mac:~/comandos-voz/
   ```

#### B. Instalador Automático para macOS (`setup_mac.command`)
Dado que la compilación cruzada de binarios entre Linux y macOS con librerías nativas de audio (`PortAudio`, `ctranslate2`, `ffmpeg`) resulta frágil, se provee un script ejecutable `.command` con soporte de **doble clic directo desde el Finder de macOS Monterey**:
* **Comprobación de Homebrew y herramientas de sistema:** Verifica e instala `ffmpeg` y `portaudio`.
* **Aislamiento de entorno:** Crea automáticamente el entorno virtual `venv` en la Mac.
* **Instalación de dependencias Python:** Ejecuta `pip install -r server/requirements.txt`.
* **Pre-descarga de modelos:** Descarga los pesos de `faster-whisper` y `silero-vad` para garantizar arranque inmediato sin demoras de red.
* **Asistente de configuración `.env`:** Si no existe `.env`, solicita la IP de CachyOS y el token de seguridad interno.
* **Instalación opcional de servicio persistente (`launchd`):** Configura `~/Library/LaunchAgents/com.lili.server.plist` para que el servidor inicie en segundo plano al arrancar la Mac.

#### C. Lanzador Manual (`run_mac.command`)
Script `.command` con doble clic para levantar el servidor y el pipeline de audio en modo interactivo, mostrando registros y errores en una ventana de Terminal para facilitar la depuración.

#### D. Auto-arranque en otros nodos:
* **CachyOS:** Unidad de servicio `systemd` (`lili-client.service`).
* **Windows:** Script `.bat` ejecutable o acceso directo en la carpeta de inicio (`shell:startup`).

---

## 5. Reglas de Desarrollo para Agentes y Desarrolladores

Las políticas de desarrollo, estándares de estilo, convención de commits y prohibiciones se encuentran centralizadas en:
👉 [rules/agent.md](file:///home/chii/Documents/projects/comandos-voz/rules/agent.md)
*(Es de cumplimiento obligatorio consultar y respetar dicho documento antes y durante cualquier cambio en el repositorio).*