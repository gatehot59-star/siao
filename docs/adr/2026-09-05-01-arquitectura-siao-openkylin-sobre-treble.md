# ADR-001 · Arquitectura de SIAO: userland openKylin sobre el contrato Treble

**Fecha:** 2026-09-05 · **Estado:** aceptada · **Versión del diseño:** 0.9
**Autor de la idea madre:** Jorge Abraham Mendieta · **Redacción y verificación:** BRAIN

---

## 1. Contexto

SIAO (Sistema de Inteligencia Artificial Operativo) necesita un sistema base sobre el
cual la IA sea el dueño del sistema y Android quede como inquilino. El debate previo
llegó a tres candidatos de arquitectura y a un documento de diseño titulado "AURA OS"
que este ADR absorbe, renombra y **corrige en cuatro puntos medidos**.

## 2. Decisión

**Opción C: openKylin como userland nativo + HALs del vendor por binder + contenedor
LXC de apps sin vendor propio.** Ni virtualización ni ingeniería inversa de drivers.

### Las tres opciones, comparadas

| Criterio | A) Host + Android guest (KVM/pKVM) | B) Android en LXC completo con vendor propio | **C) Host nativo + HALs por binder + LXC de apps sin vendor** |
|---|---|---|---|
| GPU desde el host | ❌ Sin passthrough usable en SoC móvil | ⚠️ Conflicto por hwcomposer | ✅ El host es dueño de hwcomposer/gralloc |
| Módem, cámara, sensores | ❌ Solo desde el guest | ⚠️ Solo desde el contenedor | ✅ Host directo (ofono-binder, camera AIDL) |
| RAM extra | 1,5–2,5 GB | 0,8–1,2 GB | **0,3–0,5 GB**, y solo al usar apps Android |
| Latencia agente → hardware | 2 saltos | 1 salto | **0 saltos** (binder directo) |
| Batería en idle | Mala (dos schedulers, dos suspend) | Regular | Buena (un kernel, un suspend) |
| Precedente en producción | **ninguno en móvil** | Waydroid sobre Halium | **Sailfish OS (12 años, comercial), Ubuntu Touch, Droidian** |

**La "delegación inversa"** (passthrough de cámara/módem al guest y retorno por
`v4l2loopback`/`veth`) queda **descartada como arquitectura principal** y degradada a
*mecanismo de fallback* para HALs que no logremos hablar directo en la PoC.

## 3. Por qué esto NO es ingeniería inversa

Project Treble (Android 8+) impuso un contrato: `/system` y `/vendor` se comunican
**exclusivamente** por interfaces HIDL/AIDL estables sobre binder. Ese contrato lo
diseñó Google para poder reemplazar `/system` sin tocar `/vendor`. **Nosotros hacemos
exactamente lo mismo, solo que nuestro `/system` es openKylin.**

```plain
┌─────────────────────────────────────────┐
│  openKylin userland (glibc, systemd)    │  ← "nuestro /system"
│  libgbinder → /dev/hwbinder, /dev/binder│
└──────────────┬──────────────────────────┘
               │ AIDL/HIDL (contrato Treble, ABI estable, VINTF)
┌──────────────▼──────────────────────────┐
│  Contenedor "vendor" (LXC, bionic)      │  ← binarios del OEM, intactos
└──────────────┬──────────────────────────┘
               │ ioctl / sysfs
┌──────────────▼──────────────────────────┐
│  Kernel GKI (android15-6.6 / 16-6.12)   │
│  + DLKM del vendor                      │
└─────────────────────────────────────────┘
```

Los blobs de `/vendor` se redistribuyen como hace LineageOS/Sailfish: el usuario los
extrae de su propio dispositivo o se flashean con el firmware OEM. **No se decompila
nada.** La ingeniería inversa entra como línea de largo plazo (mainline + Mesa
freedreno/panthor), no como requisito del producto.

## 4. CORRECCIONES MEDIDAS EN VIVO al documento fuente

Las cuatro se midieron el 2026-09-05 con búsqueda web contra fuentes primarias. La
evidencia cruda está en `docs/agents/respuestas/2026-09-05-02-*`.

### C-1 · openKylin NO es un nombre de relleno. Y es la pieza que sostiene todo

La hipótesis era que el análisis previo había arrastrado el nombre "de algún paper
técnico asiático o lo usó como nombre de relleno". **Es falsa.** openKylin es una
distro real (OpenAtom, base Debian, escritorio UKUI, origen China), y su **3.0 salió
el 2026-08-28** con exactamente lo que SIAO necesita en la capa de arriba:

- Linux **7.0** (salto directo desde 6.6), **GCC 15, glibc 2.42, LLVM 22, JDK 25**.
- **Agentes en la capa del OS:** KylinBot nativo, más WorkBuddy, OpenClaw y Raccoon
  Work soportados, invocando capacidades del escritorio **por MCP, sin simular
  clicks**. Cita del presidente del comité técnico, Wu Qingbo: *"el paso de la IA
  como aplicación a la IA como sistema operativo no es una mejora de features, es una
  transformación de la arquitectura de base"*.
- **Multiarquitectura de una sola fuente:** x86, ARM, RISC-V (RVA23) y LoongArch.
- **El propio release dice que el alcance se extiende del escritorio al móvil.**
- PQC NIST (ML-KEM, ML-DSA, SLH-DSA) por openHiTLS, y cadena de arranque con TPM.

**Consecuencia:** si se saca openKylin, SIAO pierde de golpe el userland
multiarquitectura, el host MCP, el SDK de IA y la neutralidad de silicio, y hay que
reescribir todo eso. **Renombrar AURA → SIAO es gratis; cambiar la base no lo es.**
Las dos cosas se habían mezclado en una sola frase.

### C-2 · La fecha del release es 2026-08-28, no el 31/08

El anuncio oficial en `openkylin.top` es del **2026-08-28** y los ISO son
`...V3.0-20260827...`. El 31/08 es la prensa (GlobeNewswire y medios chinos). Dato
chico, pero era un dato afirmado.

### C-3 · AppFunctions exige un llamador SYSTEM-PRIVILEGED, y eso cambia el diseño

El documento presentaba `AppFunctionManager` (Android 16) como el enchufe limpio para
que el agente invoque apps sin scraping de UI. **La API existe y es real**, y la doc
oficial la describe como *"el equivalente móvil de los tools de MCP"*, con las apps
actuando de *"servidores MCP on-device"*. Pero la letra chica que faltaba:

- El llamador necesita el permiso **`EXECUTE_APP_FUNCTIONS`** y la doc habla de
  **"trusted, system-privileged applications"**. No es una API para una app común.
- Disponible en **Android 16 (API 36) o superior**; en API 37 aparecen
  `DISCOVER_APP_FUNCTIONS` y `EXECUTE_APP_FUNCTIONS_SYSTEM`.
- La integración con Gemini estaba en **private preview con testers** a mayo 2026.

**Y acá la corrección se vuelve ventaja:** el Agent Bridge **puede** ser privilegiado,
porque el `system` del contenedor de apps **es nuestro**. Deja de ser un permiso a
mendigar y pasa a ser un requisito de construcción de la imagen: el bridge va firmado
por nosotros, en `priv-app`, con `EXECUTE_APP_FUNCTIONS` concedido por la plataforma
que nosotros armamos. Eso es exactamente la tesis de Abraham (*SIAO está afuera y por
encima*) aterrizada en un permiso concreto.

### C-4 · Existe openKylin-Embedded V3.0 ARM64, y es mejor punto de partida

El índice de releases lista **`openKylin-Embedded-V3.0-Beta-202608281407-ARM64`, de
2.296.999.936 B (2,29 GiB)**, contra los 6.748.999.680 B (6,29 GiB) del ISO de
escritorio arm64. Nadie lo había mirado en el debate, que asumía tallar el desktop.
Para una partición `system` de ~2,5 GB en un teléfono, **partir del embedded es
empezar del lado correcto**. Sigue siendo **Beta**: eso se declara, no se esconde.

### C-5 · Confirmado: el kernel 7.0 NO es el que va a correr en el teléfono

El documento ya lo decía y la fuente lo sostiene. El userland de openKylin 3.0 pide
kernel ≥ 3.2, así que corre sobre el **GKI del dispositivo** (`android15-6.6` /
`android16-6.12`). **Se pierde Rust for Linux de fábrica** y las features de 7.0. La
premisa "sistema anfitrión universal" queda acotada a lo correcto: **openKylin como
userland universal sobre el kernel GKI del dispositivo.**

## 5. Arquitectura resultante

```plain
 L8  Agentes         KylinBot · OpenClaw · agentes propios · Planner SIAO on-device
 L7  Gobernanza      siao-policyd · siao-capd (MCP servers) · siao-auditd · siao-consentd  [Rust]
 L6  Shell           UKUI-Mobile (Wayland) · Kylin-CUA adaptado · AT-SPI2
 L5  Core OS         openKylin 3.0 ARM64 (systemd, glibc 2.42, apt, PipeWire, ofono,
                     libcamera, NetworkManager, AI SDK, openHiTLS PQC)
 L4  Runtime Android LXC "apps" (AOSP 16 system-only, SIN vendor) + Agent Bridge privilegiado
 L3  Puente HW       libgbinder (AIDL/HIDL) · libhybris (EGL, gralloc, QNN)
                     · LXC "vendor" (init.rc del OEM, hwservicemanager, HALs)
 L2  Kernel          GKI android15-6.6 / android16-6.12 + vendor_dlkm · binderfs · cgroups v2
 L1  Firmware        ABL/XBL, TEE, AVB con claves SIAO
 L0  Silicio         ARM64 (Snapdragon / Dimensity / Tensor) · RISC-V RVA23 (futuro)
```

### El principio rector de la capa de gobernanza

> **El LLM propone; el sistema dispone.** Todo acto del agente pasa por una capa
> determinista tipada en Rust que decide, ejecuta y registra. El modelo nunca toca
> hardware, filesystem ni red directamente.

Dos anillos: el **probabilístico** (planner on-device de 3–8 B, agentes de terceros,
memoria vectorial) solo puede emitir `tool_call` con schema estricto; el
**determinista** (`policyd`, `capd`, `auditd`, `consentd`) evalúa contra política
declarativa, pide consentimiento con dry-run visible y firma un recibo auditable.

**Esto es lo que ninguno de los tres competidores chinos publica:** describen *qué*
hace el agente, no *cómo* se lo restringe.

### Capability Servers del núcleo (MCP)

| Servidor | Tools | Backend |
|---|---|---|
| `siao.telephony` | `call.place`, `sms.send`, `data.toggle` | ofono + binder-radio |
| `siao.camera` | `capture.photo{mode}`, `stream.open` | libcamera / camera AIDL |
| `siao.sensors` | `location.get`, `motion.subscribe` | sensors AIDL + geoclue |
| `siao.files` | `fs.search`, `fs.read{scope}` | portal xdg con sandbox |
| `siao.ui` | `screen.describe`, `ui.act{node}` | AT-SPI2 + Accessibility bridge |
| `siao.apps.android` | `app.launch`, `app.functions.list/call` | AppFunctions vía Agent Bridge privilegiado |
| `siao.memory` | `memory.recall`, `memory.store{ttl}` | SQLite + vector index cifrado |

## 6. Posicionamiento (hallazgos ajenos, no medidos por mí)

| | HarmonyOS NEXT | HyperOS 3 | BlueOS / OriginOS | **SIAO** |
|---|---|---|---|---|
| Kernel | HongMeng propietario | Linux (Android) | abstraction layer / Linux | Linux GKI del dispositivo |
| ¿Corre APKs? | **No** | Sí (es Android) | BlueOS no / OriginOS sí | **Sí, en contenedor sin vendor** |
| Hardware | Solo Kirin | Solo Xiaomi | Solo vivo | **Cualquier Treble desbloqueable** |
| Apertura | Parcial | Cerrado | Kernel abierto | **100% abierto** |

- **Frente a Huawei:** probó que el mercado acepta un OS-agente, pero pagó reescribir
  el ecosistema y solo corre en su silicio. SIAO replica la tesis manteniendo APKs.
- **Frente a Xiaomi:** sus agentes viven *dentro* de la jaula de Android. En SIAO el
  agente **es** el sistema.
- **Frente a vivo:** BlueOS es el más afín en espíritu, pero no lo llevan al
  teléfono. SIAO es el BlueOS que sí corre, porque reutiliza el vendor de Android.

## 7. Roadmap

- **Fase 0 (mes 0–1) · hardware.** Treble ≥ Android 14, bootloader desbloqueable y
  re-lockeable, GKI 6.1/6.6, soporte previo en Halium/Droidian. Candidatos: Pixel 7/8
  (GKI puro, pKVM, kernel abierto), Fairphone 5 (Droidian activo, QCM6490),
  SHIFTphone 8. Un MediaTek secundario para forzar portabilidad.
- **Fase 1 (mes 1–5) · PoC.** Rootfs openKylin ARM64 sobre GKI; contenedor vendor
  con Halium; pantalla, táctil, Wi-Fi, audio, radio.
  **Criterio de salida: llamada de voz real y un `tool_call` MCP → SMS real, sin
  `system_server` de Android corriendo.**
- **Fase 2 (mes 6–12) · Alpha.** Contenedor de apps con bind del vendor, 20 APKs,
  Agent Bridge con AppFunctions, cámara básica, planner en NPU (< 1,5 s primer
  token). Criterio: dogfooding diario y batería ≥ 80 % del firmware OEM en idle.
- **Fase 3 (mes 13–20) · Beta.** OTA A/B firmada, relock, pipeline de cámara con
  libcamera, SDK de Capability Servers, auditoría externa. Criterio: 1.000 usuarios,
  crash < 1/100 h, 3 dispositivos.
- **Fase 4 (mes 21–30) · Producción.** OEM/ODM de referencia con `/vendor` licenciado
  (elimina la extracción de blobs por el usuario), track mainline, track RISC-V.

### El paso que O-01 pone ANTES de la Fase 0

El roadmap arranca comprando un teléfono. **Hay un falsador más barato y va primero:**
arrancar el userland ARM64 de openKylin 3.0 en un **aarch64 nativo de GitHub Actions**
(4 vCPU, 16 GB, gratis en repo público) y medir con `readelf` la alineación de páginas
de 16 KB. Si el userland no sobrevive fuera de su ISO, **eso se sabe hoy y sin
hardware**, y es la premisa de la que cuelga todo lo demás.

## 8. Riesgos

| Riesgo | Prob. | Impacto | Respuesta |
|---|---|---|---|
| HAL de cámara/NPU con extensiones no estándar (`vendor.qti.*`) | Alta | Medio | Fallback en contenedor; pipeline libcamera propio |
| Sin Play Integrity → apps bancarias | Alta | **Alto en Occidente**, bajo en China | Mercados sin GMS, nichos (empresa, gobierno, privacidad). **No hay solución legal completa** |
| Dependencia de blobs vendor | Alta | Medio | Acuerdo OEM (Fase 4) + track mainline |
| Google restringe AppFunctions o binderfs | Media | Medio | Accessibility bridge como plan B; Treble/GKI son contratos con OEMs |
| El planner alucina `tool_calls` | Alta | **Bajo por diseño** | El anillo determinista rechaza fuera de schema |
| openKylin-Embedded ARM64 sigue en **Beta** | — | Medio | Declarado, no escondido: se mide antes de apoyarse |

## 9. Consecuencias

**Aceptamos:** depender de blobs de `/vendor`, no tener certificación GMS, y que el
kernel lo ponga el dispositivo (adiós Linux 7.0 en el teléfono).

**Ganamos:** cero saltos entre el agente y el hardware, un solo kernel y un solo
suspend, neutralidad de silicio, y compatibilidad APK sin heredar `system_server`.

---

--- METODO PROMETEO ---
**Máquina:** ninguna. Verificación por búsqueda web contra fuentes primarias y
escritura por API de GitHub. **Cero compilación y cero dispositivo:** declarado.
**Artefacto 1 (git):** este ADR + `docs/agents/respuestas/2026-09-05-02-siao-declarado-y-openkylin-NO-era-relleno.md`
**Artefacto 2 (ClickUp):** Doc del turno, linkeado en la bitácora.
