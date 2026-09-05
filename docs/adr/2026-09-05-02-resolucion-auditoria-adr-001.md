# ADR-002 · Resolución de la auditoría externa del ADR-001

**Fecha:** 2026-09-05 · **Estado:** aceptada · **Enmienda a:** ADR-001
**Máquina:** `brain-env` (lecturas HTTP verificadas) + búsqueda web contra fuente primaria.
**Cero compilación en este turno.**

---

## 0. Por qué existe

Una auditoría externa revisó el ADR-001 afirmación por afirmación. Su veredicto
general fue que la decisión arquitectónica se sostiene, con tres afirmaciones
refutables, una omisión de riesgo y una objeción al falsador.

**Este ADR resuelve cada punto midiendo, no opinando.** El auditor acertó en seis
de sus puntos, incluido uno que me deja mal parado; tres no se sostienen y se
refutan con números.

---

## 1. ACEPTADO · el auditor tenía razón y yo estaba mal

### A2 · La fecha. Yo introduje el error "corrigiendo" un dato que estaba bien

Medido hoy, en las dos versiones de la nota oficial:

```plain
GET 200 165188 https://www.openkylin.top/news/4099-en.html
   TIMESTAMP: 2026-08-31 17:05:48
GET 200 163436 https://www.openkylin.top/news/4099-cn.html
   TIMESTAMP: 2026-08-31 17:05:48
```

**Mi "2026-08-28" salió de un extracto de buscador, no de la página.** Y sobre eso
afirmé con tono seguro que "el 31/08 es la prensa", corrigiendo al usuario que
tenía el dato correcto.

**Redacción que reemplaza a la del ADR-001:**

> El ISO lleva build `20260827` y el índice de releases lo fecha `28-Aug-2026
> 01:02`. La nota oficial de `openkylin.top` está timestampeada **2026-08-31
> 17:05:48**. DistroWatch publicó el release el 2026-08-28. La fecha exacta de
> publicación queda **NO MEDIDA**: hay build del 27, listado del 28 y anuncio
> oficial del 31, y no sé cuál cuenta como "release".

**Y el auditor nombra el patrón mejor de lo que yo lo había escrito:** A2 es el
mismo error que H-002 del cementerio. Un extracto de buscador **no es** fuente
primaria, y una corrección a otro exige más evidencia que una afirmación propia,
no menos.

### A6 · "Ni virtualización ni ingeniería inversa" sobre-generaliza

Aceptado: el propio diseño conserva pKVM para el Agent Vault y un track mainline
que **sí** es ingeniería inversa comunitaria. **Redacción correcta:**

> **No virtualización como ruta de compatibilidad de Android.** **No ingeniería
> inversa como requisito del producto.** pKVM se usa para aislar el Agent Vault
> del propio host, y la ingeniería inversa entra como track de largo plazo.

### A7 · Rust for Linux

Aceptado el matiz: Rust for Linux existe upstream en 6.12. Lo que se pierde es
**el empaquetado y los drivers Rust que openKylin distribuye para 7.0**, no la
capacidad del kernel.

### H5 · "Titiritero" describe mal el diseño, y es peligroso

Aceptado, y es la mejor observación de redacción de la auditoría: si el contexto
vivo dice "titiritero", alguien lo implementa como scraping de pantalla. **Texto
que queda:**

> SIAO es el dueño de la casa; Android es un **inquilino con contrato** (Treble
> para el hardware, AppFunctions para las apps); el control por UI es la
> **excepción**, no la regla.

### H1 · Android 17 mueve el gate de privilegio a identidad · CONFIRMADO

Existe en AOSP `android17-release`, y no es un rumor de un sample:

- `core/java/android/os/allowlist/AllowlistProviderService.java` en
  `android17-release`.
- Commit de AOSP **"Enforce agent allowlist in AppFunctionAccessService"**
  (`Bug: 413093397`), que toca `AppFunctionManagerServiceImpl`,
  `AppIdAppFunctionAccessPolicy` y `SignedPackageParser`.
- La allowlist es por **`SignedPackage`** (paquete + certificado) y se lee de
  `DeviceConfig`, namespace `machine_learning`, clave
  `allowlisted_app_functions_agents`, persistida en `agent_allowlist.txt`.
- En API 37 aparecen `DISCOVER_APP_FUNCTIONS` y `EXECUTE_APP_FUNCTIONS_SYSTEM`.

**Dos matices medidos que el auditor no puso, y mejoran la posición:**

1. Todo está detrás del flag `android.permission.flags.app_function_access_service_enabled`.
2. El mismo commit **"adds ADB commands to add agents manually, and disable the
   allowlist entirely"**. En AOSP, que es nuestro caso, es configuración nuestra.

**Entra al ADR como requisito de build y como riesgo, tal como pidió:** el Agent
Bridge necesita **dos artefactos**, `privapp-permissions-siao.xml` **más** la
entrada de allowlist con el hash de nuestro certificado. Riesgo abierto: *Google
movió el gate de privilegio a identidad y puede volver a moverlo.*

### H4 · El contenedor de apps · CONFIRMADO, y PEOR de lo que lo planteó

Su hipótesis era "Waydroid sigue en Lineage 20 / Android 13, verificar". Medido:

- `waydro.id` y los docs oficiales **siguen diciendo Android 13**.
- Waydroid **1.6.3** (2026-05-28) trae **"Initial support for Android 16 images"**.
- **Sí existen** builds Android 16: `WayDroid-ATV/waydroid-builds` release
  `20260717`, **LineageOS 23.2 (Android 16 QPR2)**.
- **Pero ese release dice literal: "ARM64 images are NOT available in this
  release"**, y remite a `20260302`, que es `lineage-20.0` (Android 13).
- En SourceForge, `waydroid_arm64` → lo más nuevo es
  `lineage-20.0-20260403-...-waydroid_arm64-system.zip`.

**Conclusión: para arm64, que es la única arquitectura que le importa a SIAO, NO
existe imagen Android 16.** AppFunctions pide API 36 **dentro** del contenedor,
así que **construimos nuestra propia imagen `system` de AOSP 16 arm64**. No estaba
en ninguna fase del roadmap y es la decisión con más costo oculto del documento.

---

## 2. REFUTADO · con medición, no con opinión

### A3 · "El índice es dinámico y el mirror no respondió" · responde, y acá está la URL

**URL exacta, que el ADR-001 debía citar y ahora cita:**
<https://releases.openkylin.top/3.0/>

```plain
GET 200 len 2082
   openKylin-Desktop-V3.0-20260827-arm64.iso          28-Aug-2026 01:02   6748999680
   openKylin-Embedded-V3.0-202608281407-ARM64.iso     28-Aug-2026 09:35   2296999936
   openKylin-Server-V3.0-2026.8.27-3-arm64.iso        27-Aug-2026 14:20   1748994048
```

Es un `autoindex` de nginx en texto plano, **no una página dinámica**. Los
2.296.999.936 B coinciden exactamente con lo que había reportado.

**Y una corrección contra mí que salió de acá:** el nombre del archivo hoy es
`openKylin-Embedded-V3.0-202608281407-ARM64.iso`, **sin `-Beta-`**. Yo lo había
declarado "sigue siendo Beta", y ese caveat tampoco está respaldado por el índice
de hoy. Mismo build stamp, mismo tamaño, mismo minuto: o lo renombraron, o mi
fuente anterior (otro extracto de buscador) estaba vieja. **Queda NO MEDIDO si es
Beta o Release.**

### A9 / H2 · La objeción al falsador parte de una premisa falsa

El auditor escribió: *"`readelf` sobre binarios del ISO responde una pregunta de
compilación, y la respuesta casi segura es **no**, porque un ISO de escritorio
ARM64 se enlaza con 4K por defecto"*.

**Tres cosas medidas contra eso:**

1. **El falsador nunca leyó el ISO.** Bajó **12 `.deb` del repo `apt`**
   (`dists/huanghe/main/binary-arm64`), con **sha256 verificado 12 de 12** contra
   el índice oficial. O sea: exactamente la fuente que su propio **H3** propone
   como la correcta.
2. **La respuesta no es 4096: es 65536.** 146 ELF aarch64, `p_align` idéntico en
   todos, y **65536 es múltiplo de 16384**, así que sirve en kernels de 4 KB,
   16 KB y 64 KB. Su "casi segura" queda refutada por 146 mediciones.
3. **El falsador no se quedó en `readelf`.** Ejecutó: `bash 5.3.9 aarch64` de
   openKylin en `chroot` leyendo su propio `/etc/os-release`.

Eso hace de A9 **el mismo patrón que el auditor identifica correctamente en A2**:
una afirmación confiada que la fuente primaria no respalda. Se dice sin rencor,
porque el que lo señaló primero fue él.

### "Repo público es prerrequisito del runner arm64 gratuito" · FALSO, medido

`gatehot59-star/siao` es **privado**, y:

```plain
JOB arm64-nativo | concl success | runner_id 1000002018 | labels ['ubuntu-24.04-arm']
```

Tres corridas, seis jobs, seis con runner real. **Publicar el repo sigue siendo
una buena idea por cuota y por tamaño de máquina, pero no es un prerrequisito**, y
la diferencia importa porque una es urgente y la otra no.

---

## 3. Y SU H2 IGUAL GANA COMO PRÓXIMO PASO, con un sospechoso ya nombrado

La premisa de H2 estaba mal, pero **su conclusión es correcta**: la pregunta que
puede matar el proyecto no es la alineación, es **si el userland openKylin
(systemd) arranca sobre un kernel GKI con su `defconfig` real**.

**Y hay un número que lo respalda.** Leí el `gki_defconfig` de arm64 directo de
`android.googlesource.com/kernel/common`, en tres ramas:

```plain
RAMA android16-6.12 | gki_defconfig leido: 22133 bytes
  CONFIG_NAMESPACES         =y
  CONFIG_CGROUPS            =y      CONFIG_CGROUP_BPF   =y     CONFIG_MEMCG =y
  CONFIG_ANDROID_BINDERFS   =y      CONFIG_ANDROID_BINDER_IPC  =y
  CONFIG_BLK_DEV_LOOP       =y      CONFIG_OVERLAY_FS   =y     CONFIG_VETH  =y
  CONFIG_PID_NS             =NOT SET      <-- EXPLICITO
  CONFIG_USER_NS            AUSENTE del defconfig
RAMA android15-6.6  -> identico
RAMA android14-6.1  -> identico
```

**El hallazgo duro: `# CONFIG_PID_NS is not set` está EXPLÍCITO en las tres
ramas.** Namespaces de PID apagados es exactamente lo que rompe `systemd` en
contenedor y LXC. Lo bueno del ADR-001 sobrevive (binderfs, cgroups v2, memcg,
loop, overlayfs y veth **ya vienen en `y`**), pero **vamos a tener que construir
nuestra variante de GKI**, y eso arrastra un riesgo que hay que nombrar: un
`CONFIG_*` que toque símbolos del KMI **rompe los DLKM del vendor**.

### El límite de esta medición, dicho antes de que alguien se apoye en ella

**Un `defconfig` NO es un `.config`.** "AUSENTE del defconfig" **no** significa
apagado: muchos símbolos toman el default de Kconfig o los enciende otro por
`select`. Así que esto es un **cribado que nombra sospechosos**, no un veredicto.
El único dato que se sostiene solo es el `# ... is not set` explícito de
`CONFIG_PID_NS`. El veredicto real sale del `.config` del kernel construido, y
es justamente lo que F-001 tiene que producir.

**Y un defecto mío en el instrumento, que está en la salida cruda:** escribí
`CONFIG_BRIDE` en vez de `CONFIG_BRIDGE`, así que ese símbolo salió "AUSENTE"
por un typo mío. **Un símbolo mal tipeado siempre da ausente**, que es el mismo
cero disfrazado de medición que este proyecto ya se cobró con `grep -c` y con
`ps`. Queda declarado en vez de re-corrido en silencio.

---

## 4. Los tres falsadores que reemplazan al plan anterior

Aceptado el orden del auditor, con la corrección de que F-003 **ya está hecho** en
lo esencial:

| # | Qué mide | Dónde | Estado |
|---|---|---|---|
| **F-001** | ¿arranca `systemd` de openKylin sobre GKI con su `defconfig` real? Criterio: llegar a `multi-user.target` y que `lxc-checkconfig` dé verde | Actions arm64 + QEMU `virt` (TCG si no hay KVM) | **pendiente**, y ya tiene sospechoso: `CONFIG_PID_NS` |
| **F-002** | construir el rootfs con `mmdebstrap` contra los repos de openKylin 3.0 y medir tamaño real | Actions arm64 | **pendiente** |
| **F-003** | `p_align` sobre ese rootfs | Actions arm64 | **hecho en miniatura**: 12 paquetes del repo `apt`, 146 ELF, `65536`. Escalar a la lista completa |

**H3 aceptado sin objeción:** ningún ISO es el punto de partida. El rootfs se
construye con `mmdebstrap`/`debootstrap` contra los repos `apt`. Y eso es
justamente lo que el falsador ya hizo a escala chica, así que **F-002 es escalar
un camino que ya funcionó, no abrir uno nuevo**. El Embedded ARM64 sirve como
referencia de qué considera "mínimo" el propio proyecto.

---

## 5. Riesgos que entran al ADR-001

| Riesgo | Prob. | Impacto | Origen |
|---|---|---|---|
| **Sin imagen Waydroid arm64 con Android 16** → hay que construir AOSP 16 arm64 propio | **Medida** | **Alto** (semanas de ingeniería + mantenimiento) | H4, confirmado |
| Android 17 mueve el gate a allowlist por certificado, y puede moverlo otra vez | Media | Medio | H1, confirmado en AOSP |
| El GKI necesita `CONFIG_*` extra y alguno puede tocar el KMI → rompe los DLKM del vendor | **Medida como sospecha** | Alto | §3 |
| Sin Play Integrity → apps bancarias | Alta | Alto en Occidente, **casi nulo en China y en sector público/empresa** | acepto su matiz: debe pesar en la elección del dispositivo de Fase 0 |

---

## 6. NO MEDIDO, ampliado como pidió

- **Si el Embedded ARM64 es Beta o Release** (el nombre cambió; ver §2).
- **La fecha exacta de publicación del release** (build 27, listado 28, anuncio 31).
- **El `.config` real del GKI construido.** El `defconfig` solo criba.
- **Si los `CONFIG_*` que faltan se pueden agregar sin romper el KMI.**
- **Free-tier de runners arm64 hoy:** medido que **funcionan en repo privado**;
  no medido el límite ni el costo en cuota.
- **`CONFIG_BRIDGE`**, que quedó sin medir por mi typo.
- La deprecación de NNAPI y el estado de QNN / NeuroPilot.
- Todos los números de HarmonyOS NEXT, HyperOS y BlueOS: **hallazgos ajenos**.

---

## 7. Espera firma

1. **¿Aceptamos construir imagen AOSP 16 arm64 propia para el contenedor?** Es la
   decisión con más costo oculto de todo el documento (H4).
2. **¿Corro F-001?** Es un job largo (compilar o bajar GKI + `mmdebstrap` + QEMU
   en TCG) y ya tiene un sospechoso concreto que buscar.
3. **Visibilidad:** sigue siendo buena idea publicar, pero **ya no es urgente**.

---

--- METODO PROMETEO ---
**Máquina:** `brain-env` para las lecturas HTTP verificadas (gateway, servicio
`build`, tool `run`) y búsqueda web contra fuente primaria. **Cero compilación y
cero QEMU en este turno:** declarado, no insinuado.
**Artefacto 1 (git):** este ADR + `docs/agents/respuestas/2026-09-05-04-resolucion-de-la-auditoria-del-adr-001.md`
**Artefacto 2 (ClickUp):** Doc del turno.
