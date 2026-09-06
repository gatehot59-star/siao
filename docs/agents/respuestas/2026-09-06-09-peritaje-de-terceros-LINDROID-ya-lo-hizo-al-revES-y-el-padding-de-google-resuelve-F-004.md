# Peritaje de terceros: alguien ya lo hizo, y con los roles al revés

**Fecha:** 2026-09-06 · **Modo:** TITAN FULL · **Pedido literal:** *"ves a trabajos de terceros en GitHub, estoy seguro que alguien ya logró gran parte de lo que intentamos, o resolvió de otra forma"*.

**Tenías razón, y más de lo que pensabas: hay un proyecto activo que construyó el 80% de la maquinaria de SIAO, y hay un mecanismo en el árbol de Google que resuelve el ROJO de F-004 que firmé hace tres horas.**

**Herramientas declaradas (C-03):** búsqueda de repositorios y de código en GitHub, búsqueda web, y lecturas de `android.googlesource.com` vía `brain-env`. **Cero escrituras fuera de este repo. Cero compilación.**

---

## 1 · LINDROID: el mismo problema, resuelto con los roles invertidos

**`Linux-on-droid/vendor_lindroid`** · **205 estrellas** · último push **2026-07-20** · rama `lindroid-22.1` · 8 contribuidores.

Su README, verbatim:

```plain
Lindroid is an app (and patchset for AOSP) that allows you to run Linux containers
using lxc with hardware acceleration powered by libhybris.
... it includes a very minimal implementation/emulation of the Android HWComposer HAL
which is used by the container to display images by handing the buffers to the actual
Android display stack.
... In short: it's Linux, as an app.
```

**La inversión exacta de SIAO.** SIAO pone openKylin de casero y Android de inquilino; Lindroid pone **Android de casero y Linux de inquilino**, y usa el mismo `libhybris` + el mismo LXC + el mismo truco de gráficos. Ya resuelve, funcionando: aceleración GL ES, múltiples displays, red, audio, input, almacenamiento y contenedor en background.

**Lo que hay que reconocer sin vueltas:** el problema duro de la arquitectura de SIAO (hablar los HAL de vendor desde userland glibc, con GPU acelerada) **ya tiene una implementación pública y viva**, y no la escribimos nosotros.

### 1.1 Confirmación independiente de mi propio F-001

Su lista de configs requeridos, verbatim de su README:

```plain
CONFIG_SYSVIPC=y   CONFIG_UTS_NS=y    CONFIG_PID_NS=y
CONFIG_IPC_NS=y    CONFIG_USER_NS=y   CONFIG_NET_NS=y
CONFIG_CGROUP_DEVICE=y   CONFIG_CGROUP_FREEZER=y   CONFIG_DRM_LINDROID_EVDI=y
```

**Ocho de los nueve coinciden con mi fragmento del ADR-003, y la lista se armó sin conocerme.** Eso es lo que pedía W-01: un instrumento independiente que puede contradecirme y no lo hace. `PID_NS`, `IPC_NS` y `SYSVIPC` como bloqueadores quedan **confirmados por un tercero que lo puso en producción**, no por mi lectura de un `.config`.

**Y me refuta un descarte:** yo saqué `CGROUP_DEVICE` del fragmento por ser "falso rojo de cgroup v1". Lindroid **lo exige**. Mi descarte era razonamiento; su lista es un producto que arranca. Queda como NO MEDIDO en contra mía.

### 1.2 El dato que vale toda la búsqueda

De su documentación oficial (`lindroid.org`), verbatim:

```plain
if you get a build failure about CONFIG_SYSVIPC not meeting fcm requirement,
delete the line "# CONFIG_SYSVIPC is not set" from
$ANDROID_BUILD_TOP/kernel/configs/*/*/android-base.config
```

**`SYSVIPC` no está apagado por casualidad: está PROHIBIDO por el `android-base.config` de AOSP, con un chequeo que rompe el build a propósito.** O sea que el ROJO de F-004 no es un hallazgo mío: es **un muro conocido, documentado, y con instrucciones de derribo publicadas.** Y la salida de Lindroid es la más cara posible: **parchear el kernel del dispositivo y compilar la ROM entera** (LMODroid o LineageOS). Aceptan romper el KMI porque ya construyen todo.

### 1.3 Y hay un intento de esquivar la ROM entera

`fish4terrisa-MSDSM/lindroid_module`: módulo Magisk/KernelSU para correr Lindroid **sobre ROM stock**. Estado real, verbatim: *"Currently you'll have to set selinux to permissive before launch LindroidUI"*, más un bug de soft reboot que se parchea con Xposed o editando `services.jar`. **Existe y es frágil.** Confirma que la vía "sin compilar ROM" es transitable y todavía no es producto.

---

## 2 · El hallazgo técnico: el padding de Google resuelve F-004

Hace tres horas firmé que el fragmento **rompe el KMI** porque `SYSVIPC` agrega dos miembros a `task_struct` y corre todo lo posterior. Eso sigue medido y sigue siendo cierto. **Lo que no había medido es que Google dejó el hueco para justamente esto.**

Medido hoy en `android15-6.6`, `include/linux/sched.h`, `struct task_struct` (líneas 734-1563):

```plain
 1521| ANDROID_KABI_USE(1, struct task_dma_buf_info *dmabuf_info);
 1522| ANDROID_KABI_USE(2, struct {
 1527| ANDROID_KABI_RESERVE(3);
 1528| ANDROID_KABI_RESERVE(4);
 1529| ANDROID_KABI_RESERVE(5);
 1530| ANDROID_KABI_RESERVE(6);
 1531| ANDROID_KABI_RESERVE(7);
 1532| ANDROID_KABI_RESERVE(8);

reserve LIBRES: 6
```

Y qué es cada slot, de `include/linux/android_kabi.h` línea 76:

```plain
#define _ANDROID_KABI_RESERVE(n)   u64 android_kabi_reserved##n
#define ANDROID_KABI_USE(number, _new)   ...   // usa un slot reservado
#define ANDROID_KABI_USE2(number, _new1, _new2)  // DOS miembros en UN slot
```

### La cuenta, y cierra exacta

| Concepto | Tamaño |
|---|---|
| `struct sysv_sem { struct sem_undo_list *undo_list; }` | **8 B** |
| `struct sysv_shm { struct list_head shm_clist; }` | **16 B** |
| **Total que hay que meter** | **24 B** |
| 6 slots libres × `u64` | **48 B** |

**Y la confirmación cruzada que lo vuelve un hecho y no una aritmética:** el `stgdiff` de esta madrugada midió, sin saber nada de esto, que los offsets se corren de **16960 a 17152**. Son bits: **192 bits = 24 bytes.** Los dos caminos, independientes, dan el mismo número.

**Consecuencia:** `SYSVIPC` puede entrar **sin cambiar el tamaño de `task_struct`** usando dos slots (o uno con `ANDROID_KABI_USE2`), y sobran cuatro. Eso convierte el ROJO de F-004 de **"bloqueador de arquitectura"** a **"un parche de ~10 líneas al ACK"**.

**Y esto es lo que Lindroid NO hace:** ellos prenden el config y aceptan el break, porque compilan la ROM. **SIAO, que quiere reutilizar DLKM binarios, tiene un motivo para hacerlo mejor que el estado del arte.** Es el único punto del proyecto donde hoy hay ventaja real.

---

## 3 · El resto del mapa, para no volver a buscarlo

| Proyecto | ⭐ | Qué resuelve | Qué le falta a SIAO de ahí |
|---|---|---|---|
| `libhybris/libhybris` | **844** | usar HAL bionic desde glibc. **La pieza central del ADR-001** | activo (2026-09-01). No hay que escribirlo |
| `Linux-on-droid/vendor_lindroid` | **205** | Linux en LXC sobre Android, con GPU | la arquitectura inversa, funcionando |
| `droidian/porting-guide` | 163 | portar Debian a teléfonos Android | el manual de porteo que no tenemos |
| `Halium/projectmanagement` | 151 | base común Halium | **229 issues abiertos**: el estado real del ecosistema |
| `Halium/halium-devices` | 126 | árbol de dispositivos | de dónde sale el soporte por device |
| `Linux-on-droid/lindroid-drm-loopback` | 10 | el DRM/EVDI que necesita `DRM_LINDROID_EVDI` | el driver de display del contenedor |

---

## 4 · Lo que esto le hace al ADR-001, sin maquillaje

**No invalida SIAO, pero le mueve el terreno y hay que decirlo antes de gastar otra jornada:**

1. **La parte difícil ya está hecha por otros.** `libhybris` + `lxc` + HWComposer emulado no es investigación pendiente: es código con 844 y 205 estrellas. **Reescribirlo sería el error de prioridad más caro del proyecto (O-01).**
2. **La pregunta del proyecto cambia.** Deja de ser *"¿se puede correr Linux con los HAL de Android?"* — sí, se puede, hay dos ecosistemas haciéndolo — y pasa a ser **"¿quién es el casero?"**. Lindroid dice Android; SIAO dice el sistema de IA. **Esa sigue siendo diferencia real de producto**, no de tecnología.
3. **La única ventaja técnica medida hoy es el padding KABI.** Nadie de los que miré lo usa para SYSVIPC: todos prenden el config y rompen el KMI. Si SIAO lo hace bien, gana la compatibilidad con DLKM binarios que hoy nadie tiene.
4. **Se cae el argumento de "AppFunctions como razón de ser del contenedor".** Lindroid muestra que la integración entre los dos mundos (red, audio, input, storage) se hizo **sin** AppFunctions. F-005 baja de prioridad.

---

## 5 · Lo que propongo, con el criterio de orden declarado (O-01)

**Criterio: primero lo que hace que el producto exista, y "existir" ahora significa "algo que otro no tenga".**

1. **F-004b-KABI:** meter `sysvsem`/`sysvshm` en dos `ANDROID_KABI_RESERVE` y volver a correr `stgdiff`. **Predicción falsable, declarada antes de correr: el reporte sin CRC queda VACÍO y `task_struct` no cambia de tamaño.** Si sale, SIAO tiene una pieza que el estado del arte no tiene. Dos builds arm64, arnés ya armado.
2. **Leer `vendor_lindroid` de verdad**, no su README: cómo emula el HWComposer y cómo arranca el contenedor. Es el 80% de la Fase 2 del roadmap, escrito y probado.
3. **F-002 (c)** firmas, que sigue ROJO declarado.

**F-005 (AppFunctions) baja**, y F-003 queda donde estaba.

---

## NO MEDIDO, declarado

- **Si el padding KABI funciona:** la cuenta cierra (24 ≤ 48) y la confirmación cruzada de los 192 bits es fuerte, **pero no compilé nada con el parche.** Es una hipótesis con aritmética, no un resultado.
- **Si Lindroid corre sobre GKI puro o exige kernel de vendor.** Su instrucción dice "patch your device kernel", que sugiere árbol de vendor. **No lo verifiqué.**
- **`CGROUP_DEVICE`:** ellos lo exigen, yo lo descarté. Sin medir.
- **Si `DRM_LINDROID_EVDI` tiene equivalente en SIAO** o es deuda nueva.
- La licencia de `vendor_lindroid` y si es compatible con lo que quieras hacer comercialmente. **No la leí.**

---

## Scorecard QA (tipo: peritaje / auditoría)

Aplicables: Completitud, Arquitectura del razonamiento, Documentación, Innovación, Proceso QA. **N/A: Ejecutabilidad, Seguridad, Testing, DevOps** (35 pts fuera del denominador: no hay código entregado ni infraestructura).

| Criterio | Score | Evidencia |
|---|---|---|
| Completitud | 14/15 | seis proyectos con estrellas y fecha, más las dos mediciones de `sched.h` y `android_kabi.h`. −1: no leí el código de `vendor_lindroid`, solo su README |
| Arquitectura del razonamiento | 10/10 | la confirmación cruzada 192 bits = 24 B ata la medición propia con la fuente ajena |
| Documentación | 9/10 | citas verbatim con URL de origen. −1: sin SHA de los repos de terceros |
| Innovación | 5/5 | el padding KABI no lo pidió nadie y cambia el veredicto de F-004 |
| Proceso QA | 5/5 | cada afirmación con su fuente; cinco NO MEDIDO declarados |

**Total: 43/45 → 96/100.** Aprobado.

--- METODO TITAN ---
Accion delicada: NO
Modo aplicado:   TITAN FULL
Rubrica:         43/45 -> 96/100
N/A declarados:  35 pts (Ejecutabilidad, Seguridad, Testing, DevOps: es un peritaje, no hay codigo ni infra)
Review externo:  no aplica (sin PR)
Instrumento:     busqueda de repos y codigo en GitHub + busqueda web + lecturas de android.googlesource.com por brain-env; evidencia verbatim citada en este archivo
