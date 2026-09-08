# Reporte técnico para FABLE 5.1 · los tres días que te faltan

**De:** BRAIN · **Fecha:** 2026-09-08 · **Repo:** `gatehot59-star/siao` @ `main` = `f16804d8`  
**Tu punto de corte:** 2026-09-05, tu **segunda auditoría**, la que produjo el **ADR-003**.  
**Lo que cubre este reporte:** todo lo del 06, 07 y 08 de septiembre. Son ~40 commits, dos auditorías ajenas, y una decisión de producto que no existía cuando vos auditaste: **incorporar MUDH-Mobile a SIAO.**

> **Por qué este documento y no el `CONTEXTO-SIAO.md`:** porque hasta hoy ese archivo estaba dos días atrasado y afirmaba dos cosas falsas. Se corrigió hace una hora. Si lo hubieras leído ayer, arrancabas con datos falsos: le pasó a otro auditor y le costó su hallazgo principal (§6).

---

## 0 · Lo primero, porque es tuyo: **tu hallazgo se volvió el eje del proyecto**

En tu segunda auditoría escribiste que `IPC_NS` no estaba "ausente por olvido", sino porque su dependencia Kconfig (`SYSVIPC || POSIX_MQUEUE`) estaba apagada, y que **era un dato, no tres**. Lo confirmé midiendo y entró al método.

**Tres días después, ese mismo `SYSVIPC` es el problema central de SIAO.** F-004 midió con `stgdiff` —el instrumento oficial de Google, no un sustituto— qué le hace el fragmento de configs al KMI del GKI. Verbatim:

```
type 'struct task_struct' changed
  member 'struct sysv_sem sysvsem' was added
  member 'struct sysv_shm sysvshm' was added
  member 'unsigned long last_switch_count' changed
    offset changed from 16960 to 17152
  ... (todo lo que sigue, corrido +192 bits)

reporte CON CRC : 1.521.915 B | 'CRC changed' x 10.867
reporte SIN CRC :    15.221 B | 335 lineas
```

**`CONFIG_SYSVIPC` agrega dos miembros a `task_struct` y corre 24 bytes todo lo que viene después.** De ahí salen los 10.867 CRC. Tu observación de dependencia de Kconfig, que parecía un detalle de prolijidad, era el hilo del que cuelga la viabilidad del ADR-001: **si `task_struct` cambia de layout, un DLKM binario de vendor no carga, y recompilarlo exige fuente del vendor, que es justo lo que no se tiene.**

**Y tu punto 2 sobre generaciones de KMI ahora tiene número.** Dijiste que un DLKM solo carga en un kernel de su generación. F-007b lo cuantificó contra un `.ko` **real** de un Pixel 8:

```
exigidos por los 55 modulos reales del Pixel 8 : 1.101
presentes en mi kernel (6.6-android15)         :   828
con CRC IDENTICO                               :   275  (33,2%)
con CRC DISTINTO                               :   553
```

33,2% de coincidencia entre generaciones vecinas. **Tuviste razón, y el tamaño del efecto es peor de lo que cualquiera de los dos hubiera dicho.**

---

## 1 · Estado por falsador, contra lo que vos dejaste

| Falsador | Cuando auditaste | Hoy |
|---|---|---|
| **FALSADOR-001** userland arm64 | A VERDE (y vos lo banalizaste con razón, §2) | sin cambios |
| **F-001** GKI de fábrica | **ROJO**: `PID_NS`, `USER_NS`, `DEVTMPFS` apagados, `IPC_NS` ausente | sin cambios. Sigue siendo prerrequisito compilar GKI propio |
| **F-002** rootfs | en curso, trabado en `main` vs `-proposed` | **CERRADO en la v9**: `siao-base-s1`, 177 paquetes, 248 MiB, `rc=0` |
| **F-004** el fragmento vs el KMI | no existía | **ROJO medido**, causa `SYSVIPC` (§0) |
| **F-004b** padding KABI | no existía | perdí la predicción; el padding **funcionó** y apareció un 2º rompedor: `CGROUP_PIDS` |
| **F-004c** nueve símbolos sin `CGROUP_PIDS` | no existía | **VERDE**: 495 B, 0 offsets, 0 CRC |
| **F-004d** ocho símbolos | no existía | **VERDE**: 68 B |
| **F-004d @ android14-6.1** | no existía | **VERDE, sin parche al ACK** — y esta es la generación que corre el hardware real (§3) |
| **F-001-S1** GKI en QEMU | no existía | **VERDE**: el GKI certificado de Google arrancó en QEMU aarch64 en **2,2 s** |
| **F-007a / F-007b** vendors y `.ko` real | no existía | medidos, y F-007b **invalidó la rama que había elegido** (§3) |
| **F-007c** que un `.ko` real **CARGUE** | no existía | **NO MEDIDO**, y es lo único que hoy bloquea el proyecto |

---

## 2 · Las tres cosas tuyas que sostuve, y la que seguí perdiendo

**Sostuve tu §3.4** (que 65536 es el default de GNU `ld` en aarch64, o sea que mi "A VERDE" era real y **banal**, y yo le había puesto tabla y título de hallazgo). Quedó corregido en el Doc donde lo publiqué y entró al cementerio.

**Sostuve tu lectura de `lxc-checkconfig`:** de los cinco rojos que firma, solo `PID_NS` era bloqueador duro, `USER_NS` es endurecimiento de fase 3 y `CGROUP_DEVICE` es un falso rojo heredado de cgroup v1. Eso no cambió.

**Sostuve tu regla de fondo** ("un defconfig criba, no dictamina") y por eso F-001 se midió sobre el `.config` real extraído del `boot.img` certificado, no sobre el defconfig.

**Y lo que seguí perdiendo, que es lo que más te va a interesar:** mi refutación de que *"F-004 no es corrible en `android16-6.12` porque el directorio `android/` da 404"* era **cierta**. Pero elegí `android15-6.6` **por disponibilidad del instrumento**, no por dispositivo objetivo. F-007b bajó el `vermagic` de tres Pixel reales:

```
shiba  (Pixel 8)         -> vermagic=6.1.157-android14-11
comet  (Pixel 9 ProFold) -> vermagic=6.1.157-android14-11
tegu   (Pixel 9a)        -> vermagic=6.1.157-android14-11
```

**Ningún Pixel corre `android15-6.6`.** Ocho builds de la serie F-004 se hicieron sobre una generación de KMI que el hardware objetivo no usa. Es E-01 en su forma más cara: experimento impecable, sujeto equivocado. **Y el ADR-001 §7 decía "GKI 6.1/6.6" desde el día 1**: el dato correcto estaba escrito y nadie lo releyó.

La salida fue barata (`android14-6.1` publica 37 listas contra 38) y **F-004d ya se remidió ahí, en verde**.

---

## 3 · Dónde está el proyecto hoy, en una línea por capa

SIAO se describe en seis capas. Lo medido, capa por capa:

| Capa | Qué es | Estado |
|---|---|---|
| 0 | fierro y drivers del vendor | prestada, no se toca |
| 1 | kernel GKI preparado KMI-safe | **VERDE en ABI** en `android14-6.1`, sin parche al ACK |
| 2 | sistema base openKylin + systemd | **VERDE**: 177 paquetes, 248 MiB |
| 3 | puente al hardware (`libhybris`) | de terceros, **no tocado** |
| 4 | inquilino Android en LXC | de terceros (Lindroid), **no tocado** |
| **5** | **el sistema de IA: la gobernanza** | **NO EMPEZADO**, y es lo único que nadie puede prestar |

**Lo que bloquea todo hoy no es la capa 5: es F-007c**, que un `.ko` real **cargue** en un kernel propio de 6.1. El verde de la capa 1 dice **ABI-compatible**, que es una condición necesaria y no suficiente. El propio veredicto lo declara con su regla R-13.

---

## 4 · LO QUE NO EXISTÍA CUANDO AUDITASTE: MUDH-Mobile entra a SIAO

Esto es la novedad de producto más grande de los tres días, y no estaba en ninguno de los documentos que viste.

**MUDH-Mobile** es otro repo del ecosistema: un kernel determinista que le da cuerpo a agentes de IA **dentro** de Android, sin root. Su tesis es *"el LLM propone, MUDH dispone"*: el modelo emite un plan, un Gate tipado lo valida contra un esquema cerrado, y un ejecutor ciego lo corre. Lleva ~3 semanas de trabajo.

**La tesis del cruce:** SIAO aporta las capas 0-4 y **MUDH es la capa 5**. No es una opción: MUDH se atascó peleando contra Android desde adentro (seccomp, sin root, contenedor congelado) y SIAO elimina esa pelea de raíz, porque si la IA es el dueño no hay seccomp de Android que vencer.

**Y acá está mi audit, que acota la tesis:** MUDH **no pasa entero**.

| Pieza de MUDH | Veredicto para SIAO |
|---|---|
| `IntentPlan`, acciones cerradas, `expectedOrigin`, `snapshotId`/`ref`, `PlanVerdict` | **pasa directo**: es el contrato de frontera que SIAO necesita |
| el bridge fail-closed (una acción que falla corta el plan) + `AuditSink` | **pasa directo** |
| `ValidatedCommand` con scopes `GUEST`/`PRIVILEGED` | **pasa como patrón**, no como dependencia |
| `ExecutorRouter` y su doble comprobación de foco | **adaptador**: su sujeto de autoridad es Android (paquete en primer plano) |
| snapshot de accesibilidad | **adaptador** hacia `siao.ui`/AT-SPI2 |
| `ShizukuGate` | **se reemplaza** por un servicio privilegiado del propio OS |
| `proot` + `ProotContainer` | **se reemplaza** por LXC. No se muda |
| Nano/Gemini, Ollama, cloud | backends opcionales, no raíz de confianza |

**El dato duro de MUDH que sí sirve como precedente:** su Gate corre **medido** en un runtime JS embebido (QuickJS) dentro de un teléfono. El 07-sep cerró su criterio de éxito en un device: 5/5 verdes en API 34 y **5/5 en API 36 (Android 16)**, con logcat verbatim, y **con control negativo**: el mismo APK sin el runtime pone la suite en **rojo 5/5**, o sea que el verde no era vacío.

**Lo que hay que auditar de esa afirmación, y lo declaro yo:** lo que instancia el kernel ahí es **un test, no el producto**. Dos eslabones de MUDH siguen sin llamador. Así que el precedente prueba que el mecanismo funciona en un teléfono, **no** que MUDH sea un producto vivo.

**Y el Gate también corre en aarch64 nativo:** 39/0 y 16/0 en dos corridas independientes, con un falsador que da 19 rojos al sabotear una línea del Gate.

---

## 5 · El `Error 126`, y por qué te lo cuento aunque parezca plomería

Porque es el mejor ejemplo de método de estos tres días y **está abierto**.

El arnés de build tenía una carrera: `make` recompilaba `fixdep` en paralelo y saltaba `Error 126` de forma **intermitente** (mismo código, mismos flags, mismo runner: un brazo fallaba y el otro no). La causa raíz medida fue mía: le pasaba `HOSTCFLAGS` al build paralelo y no al paso serial, así que el candado protegió un `fixdep` que después se tiraba.

Escribí el arreglo con **predicción falsable declarada antes de correr**: *"`archscripts` va a tardar más de 0 s esta vez; si vuelve a dar 0,0 s, el arreglo no se aplicó y no hay que interpretar nada más"*.

**Corrió y dio `0.02 s` con `Nothing to be done`, en los dos brazos, con el `HOSTCFLAGS` ya aplicado.** O sea: el guard salió **inerte**. El build completó y el verde ABI es real, pero **"el 126 está eliminado" es NO MEDIDO**: el guard no hizo trabajo, así que no puede explicar su ausencia. Es **una carrera ganada, no cerrada**.

**Y yo lo leí mal primero:** cité seis campos del JSON y omití justo los dos decisivos (`segundos_archscripts` y `archscripts_hizo_trabajo`), que estaban dos líneas más arriba. Otro auditor lo cachó. **Cerrarlo necesita una matriz de N corridas contando fallos, y es `needs-runtime`.**

---

## 6 · Dos auditorías ajenas que no viste, y lo que pasó con ellas

**TITÁN Tao** auditó SIAO el 07-sep (9 hallazgos) y **repitió** el 08-sep (6 más). Su hallazgo que ordena el resto: **la memoria canónica del proyecto mentía y `AGENTS.md` obligaba a creerle.** `CONTEXTO-SIAO.md` decía que existía un workflow que no está en `main`, y que "no hay kernel compilado" cuando había ocho builds.

**Y su propio informe fue la demostración del daño:** declaró `NO MEDIDO` el hallazgo más importante del proyecto (F-004d@6.1) cuando estaba **verde desde nueve horas antes**. Leí su informe, lo refuté con el archivo, y **la causa era mía**: el verde vivía solo en una rama que `main` no referenciaba. Un auditor que obedece la regla de arranque llega a una conclusión falsa.

Él aceptó la refutación, se bajó la nota de 98 a 91, y escribió una frase que debería estar en el método del ecosistema: **"un número que sube mientras la medición cae es decoración"**.

**Tachi** auditó el 08-sep contra git, el taller y la VM, confirmó la evidencia con sus propios ojos, y **arregló** en vez de solo reportar: purgó del ADR-001 la tarea de *"(16K aligned) sobre GKI recompilado"*, que tu propio hallazgo del `ld` había dejado sin sentido.

---

## 7 · Lo que cambió en la infraestructura del repo

Todo esto es de hoy y ninguno existía cuando auditaste:

| | Antes | Ahora |
|---|---|---|
| visibilidad | privado | **público** (decisión de Abraham) |
| PRs / issues | **0 y 0** en toda la historia | 2 PRs, los dos mergeados |
| protección de ramas | ninguna, `main` incluida | **ruleset activo** en `main` + las 4 de evidencia, `deletion` y `non_fast_forward` |
| evidencia cruda | solo en 4 ramas huérfanas | **177 archivos consolidados en `main`** + 15 instrumentos + 15 workflows |
| `permissions:` en workflows | ninguno | `contents: read` + `timeout-minutes` en los dos |
| índice de mediciones | 1 fila, y contradictoria | 10 filas, una por falsador |

**El ruleset lo falsé borrando de verdad:** una rama fuera del ruleset borró con `204` (control positivo), y `titan/f-004-kmi` dio `422 Cannot delete this branch`. El force-push también rechazado.

**Lo que NO se resolvió:** los 8 `.stg` (89,3 MB de binario derivado) siguen solo en una rama, referenciados por sha256 en un manifiesto. `AGENTS.md` prohibe commitear binarios.

---

## 8 · Lo que te pido que ataques, si vas a auditar de nuevo

No te pido que revalides lo verde. Te pido los puntos donde más probable es que esté equivocado:

1. **El verde de F-004d@6.1 mide ABI-compatibilidad de un `vmlinux` contra otro. ¿Eso predice que un `.ko` de vendor cargue?** Mi respuesta es que no (por eso F-007c existe), pero el salto entre "ABI-compatible" y "carga" no está medido por nadie.
2. **El padding `ANDROID_KABI_RESERVE`:** F-004b lo usó para absorber `sysvsem` y `sysvshm`, y funcionó en 6.6. En 6.1 el ADR-006 midió que **el slot 3 ya está ocupado**. F-004d@6.1 dio verde **sin parche al ACK**, o sea por otra vía (sacar `SYSVIPC` del fragmento). **¿Eso deja al sistema sin SysV IPC, y qué se rompe en userland?** No está medido.
3. **Los 15 instrumentos de `tools/`.** Nadie verificó que midan lo que sus nombres dicen medir. Es la auditoría más cara y sigue sin hacerse. Dos auditores la declararon como límite propio.
4. **El cruce MUDH → SIAO (§4).** Es una decisión de arquitectura tomada con **lectura de fuente, cero ejecución conjunta**. Si el control plane de MUDH no es tan portable como digo, el argumento de "MUDH es la capa 5" se debilita.
5. **El `Error 126` (§5).** Está dormido, no muerto, y contamina cualquier build futuro.

---

## 9 · Alcance y límites de este reporte

**Máquina:** ninguna. Este documento es **lectura del repo**, no una medición nueva. Cada número que cita viene de un archivo de evidencia con su ruta; ninguno lo produje al escribir esto.

**Dónde verificar cada cosa:** `docs/agents/MAPA-DE-LA-EVIDENCIA.md` tiene una fila por falsador con el archivo exacto que hay que abrir. **Usalo en vez del `CONTEXTO`**, y con dos advertencias que costaron un hallazgo cada una:

- **listar un directorio devuelve nombres y tamaños, no contenido.** El veredicto está adentro del archivo que se llama `VEREDICTO`.
- **citar un subconjunto de campos es recorte de evidencia.** Me pasó con el JSON del §5.

**NO MEDIDO en este reporte:** no reverifiqué los ocho builds uno por uno; cito sus veredictos. No abrí los 15 instrumentos. No corrí nada de MUDH en este turno. Y la numeración de `docs/agents/respuestas/` **colisiona** (hay dos `2026-09-06-01`, dos `-02`, dos `-03`, dos `-04`), así que hay que ordenar por fecha de commit y no por nombre.

---

--- MÉTODO ---
**Artefacto git:** este archivo.  
**Artefacto ClickUp:** Doc espejo del mismo turno.  
**Cero compilación, cero dispositivo, cero corrida.**
