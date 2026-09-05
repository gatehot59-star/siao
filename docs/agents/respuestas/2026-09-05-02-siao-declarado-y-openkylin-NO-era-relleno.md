# 2026-09-05 · SIAO declarado, y openKylin NO era un nombre de relleno

## 1. Pedido literal

Abraham declaró el alcance: **SIAO = Sistema de Inteligencia Artificial Operativo**, un
OS móvil donde la IA es dueña del sistema y Android corre de inquilino en un
contenedor. Y adjuntó el documento de diseño completo (titulado "AURA OS", v0.9),
pidiendo que el nombre pase a SIAO.

Dentro del mismo mensaje venía una hipótesis suelta: que **openKylin** también podía
ser un nombre de relleno arrastrado "de algún paper técnico asiático".

## 2. Qué se hizo

1. Se **perdió una apuesta en público** (ver §5) y se registró.
2. Se verificaron **en vivo** las dos piezas que sostienen el diseño entero, antes de
   commitear una línea de alcance: openKylin 3.0 y la API AppFunctions de Android.
3. Se declaró la sección 1 del contexto vivo, que estaba en `NO DECLARADO`.
4. Se escribió el **ADR-001** con la decisión de arquitectura y las **cinco
   correcciones** al documento fuente.

## 3. Evidencia cruda, verbatim

### 3.1 openKylin 3.0 existe (refuta H-003)

De `openkylin.top/news/4099-en.html`, publicado **2026-08-28**:

```plain
"OpenAtom openKylin version 3.0 is officially released! In this version upgrade,
openKylin has upgraded the system kernel across generations to Linux 7.0, completing
the comprehensive iteration of more than 180 core components; building an open
foundation for intelligent agents, enabling AI to run through the entire system
chain; ... scenario coverage extends from smart desktops to mobile devices, servers
and other full scenarios."

"openKylin 3.0 upgrades the system kernel directly from Linux 6.6 to Linux 7.0.
GCC 15, glibc 2.42, LLVM 22, JDK 25"
```

De `opensourceforu.com`, 2026-09-01, citando a Wu Qingbo, presidente del comité
técnico de openKylin:

```plain
"The shift from 'AI as an application' to 'AI as an operating system' is not simply a
feature upgrade, but a transformation of the underlying architecture."
```

De la nota china (`qudong.com`), sobre la capa de agentes:

```plain
"KylinBot、WorkBuddy、OpenClaw、Raccoon Work等智能体可在openKylin 3.0上运行。
智能体通过MCP协议直接调用桌面能力，无需模拟点击"
("los agentes invocan las capacidades del escritorio directamente por protocolo MCP,
sin necesidad de simular clicks")
```

**Veredicto: H-003 es FALSA.** openKylin no es relleno: es un OS que ya hizo la mitad
de arriba del trabajo de SIAO. Sacarlo obliga a reescribir userland multiarquitectura,
host MCP y SDK de IA.

### 3.2 El índice de releases (refuta la premisa de "tallar el ISO de escritorio")

De `releases.openkylin.top/3.0/`, verbatim:

```plain
openKylin-Desktop-V3.0-20260827-arm64.iso          28-Aug-2026 01:02   6748999680
openKylin-Embedded-V3.0-Beta-202608281407-ARM64..> 28-Aug-2026 09:35   2296999936
openKylin-Embedded-V3.0-Release-spacemit-k3-ris..> 27-Aug-2026 12:08   5184213396
openKylin-Server-V3.0-2026.8.27-3-arm64.iso        27-Aug-2026 14:20   1748994048
```

**2.296.999.936 B contra 6.748.999.680 B.** El embedded ARM64 es 2,9× más chico y es
el punto de partida correcto para una partición `system` de teléfono. Sigue en
**Beta**, y así queda declarado.

Y el ISO se llama `20260827`, o sea que **la fecha 31/08 del documento fuente es la
prensa, no el release**.

### 3.3 AppFunctions es real, pero pide privilegio de sistema

De `developer.android.com/ai/appfunctions`:

```plain
"AppFunctions is an Android platform API with an accompanying Jetpack library to
simplify Android MCP integration. It empowers your apps to behave like on device MCP
servers... Callers must have the EXECUTE_APP_FUNCTIONS permission to discover and
execute AppFunctions"

"AppFunctions is available on devices running Android 16 or higher."

"As of May 2026, AppFunctions integration with Gemini is in a private preview with
trusted testers."
```

Del `package-summary` de `android.app.appfunctions`:

```plain
"An app function is a discrete piece of functionality within an application that is
made available for execution by trusted, system-privileged applications (referred to
as 'agents')."
```

Y de la referencia de `androidx`, el detalle de versiones que el documento no tenía:

```plain
@RequiresApi(value = 37) ... anyOf = ["android.permission.EXECUTE_APP_FUNCTIONS",
"android.permission.DISCOVER_APP_FUNCTIONS", "android.permission.EXECUTE_APP_FUNCTIONS_SYSTEM"]
```

**Veredicto: la API existe y hace lo que el documento decía, pero el llamador tiene
que ser system-privileged.** Y eso, en SIAO, **no es un obstáculo sino una pieza de
diseño**: el `system` del contenedor de apps es nuestro, así que el Agent Bridge va
firmado por nosotros y en `priv-app`. El permiso deja de mendigarse.

## 4. Lo que NO se hizo, y por qué

- **No se ejecutó nada.** Cero compilación, cero dispositivo, cero rootfs arrancado.
  Todo este turno es lectura verificada más escritura de documentos.
- **No se verificó** la deprecación de NNAPI, ni el estado de QNN/NeuroPilot, ni un
  solo número de HarmonyOS/HyperOS/BlueOS. Van al ADR marcados como **hallazgos
  ajenos**, no como mediciones propias.
- **No se creó `.github/workflows/`.** El falsador de la §7 del ADR (arrancar el
  userland arm64 en Actions) es el próximo paso natural, pero es una corrida y este
  turno no la hizo: declararla hecha sería inventarla.

## 5. Me refuto: perdí una apuesta que yo mismo propuse

Ante "esto te va a gustar, ¿apostamos?", aposté **antes** de escuchar, para poder ser
refutado: *"la I es de inferencia activa, no de inteligente"*. **Falso.** Es
**Inteligencia Artificial**, y el proyecto es un OS móvil, no el de Friston en
microcontrolador. Queda como H-002 en el cementerio de hipótesis, porque una apuesta
pública perdida es exactamente el tipo de registro que este método pide y el tipo que
es tentador no escribir.

Y hay un patrón propio en el error: predije desde el contexto que ya tenía en la
cabeza (los ~10 proyectos de Abraham, el más avanzado es Friston) en vez de esperar el
dato. **Es responder de memoria, con forma de intuición.**

## 6. Estado: bien / mal / NO MEDIDO

- **Bien:** alcance declarado, ADR-001 escrito, cinco correcciones al documento fuente
  con evidencia cruda de fuente primaria.
- **Mal:** la apuesta (H-002).
- **NO MEDIDO:** absolutamente todo lo ejecutable del proyecto.

## 7. Contrato de cierre

- **Archivos commiteados:**
  - `docs/adr/2026-09-05-01-arquitectura-siao-openkylin-sobre-treble.md`
  - `docs/agents/CONTEXTO-SIAO.md` (sección 1 declarada, H-002 y H-003 al cementerio)
  - `README.md`
  - este archivo
- **Repo:** <https://github.com/gatehot59-star/siao>

--- METODO PROMETEO ---
**Máquina:** ninguna. Verificación web contra fuentes primarias y escritura por API de
GitHub. Cero cómputo, y por eso no se reporta ninguna medición de entorno.
**Artefacto 2 (ClickUp):** Doc "SIAO declarado, y openKylin NO era relleno", en el Space.
