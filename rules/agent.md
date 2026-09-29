# agent.md - Instrucciones y Reglas de Ejecución para Agentes de IA

Este archivo define los límites y estándares obligatorios para cualquier agente de IA, asistente de código (como Antigravity) o script de automatización que opere sobre el código fuente de este proyecto.

## 🛑 Prohibiciones Estrictas (DON'Ts)
- NUNCA incluyas API keys, tokens, credenciales o direcciones IP fijas de la red local directamente en el código fuente. Utiliza exclusivamente variables de entorno gestionadas vía archivos `.env`.
- NO instales nuevas dependencias (ej. vía `pip`) ni modifiques los archivos de dependencias (`requirements.txt`, `pyproject.toml`) sin solicitar aprobación previa del usuario.
- NO ejecutes comandos destructivos en el sistema operativo, no borres bases de datos locales y NO modifiques archivos fuera de los directorios de trabajo asignados del proyecto (`/server`, `/clients/cachyos`, `/clients/windows`, `/common`, `/tests`, `/scripts`).
- NO des por completada una tarea ni asegures que una integración funciona si las pruebas automatizadas fallan o no han sido ejecutadas de forma comprobable.
- NO modifiques el System Prompt central de Ollama de forma que rompa la restricción de responder exclusivamente con objetos JSON válidos bajo el esquema formal establecido.
- NO realices llamadas de red HTTP sin definir explícitamente timeouts (`timeout=(connect_timeout, read_timeout)`).

## ⚙️ Reglas de Desarrollo (DOs)
- Corre la suite de pruebas (`pytest`) antes de proponer o entregar cualquier cambio en la lógica de negocio o en los endpoints de las APIs.
- Sigue fielmente la arquitectura, el diseño de red y la estructura de carpetas descrita en el documento de requerimientos principal (`requirements/requirements.md`).
- Emplea modelos **Pydantic** para validar y tipar estrictamente todos los payloads JSON que entran o salen de cualquier nodo y de Ollama.
- Asegura todos los endpoints entre nodos utilizando autenticación interna mediante cabecera (ej. `X-Internal-Token`) leída desde el archivo `.env`.
- Aplica las convenciones de estilo PEP8 para Python y tipado estático (`type hints`) en todo el código generado.
- Utiliza la sintaxis de **Better Comments** en absolutamente todo el código fuente para categorizar las anotaciones:
  - `# *` para información importante o explicaciones clave de arquitectura y flujo.
  - `# !` para advertencias, código deprecado, alertas de seguridad o timeouts críticos.
  - `# ?` para dudas, preguntas lógicas o áreas que requieran revisión humana.
  - `# TODO:` para tareas pendientes o futuras implementaciones (ej. nuevos nodos o skills).
- Registra mensajes de commit usando estrictamente el formato convencional (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`).
- Documenta cualquier nueva *Skill* añadida al catálogo (nativa o remota) especificando claramente su modelo Pydantic y el payload JSON esperado.
- Implementa manejo de excepciones explícito en las llamadas de red (`requests` / `httpx`) con políticas de fallback y logging adecuado para evitar caídas en cascada si un nodo cliente está fuera de línea.