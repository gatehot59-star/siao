# INFORME TÉCNICO COMPLETO · SIAO · para auditoría externa

**Proyecto:** SIAO (Sistema de Inteligencia Artificial Operativo) · `gatehot59-star/siao`
**Ventana cubierta:** 2026-09-05 16:23 a 2026-09-06 15:36 (hora Argentina) · **~23 horas**
**Autor:** ClickUp Brain · **Destino:** auditoría externa independiente
**Sin autopuntuación (R-14).** Este documento no se asigna nota.

> **Cómo leer este informe.** Cada afirmación lleva su clase: **MEDIDO** (hay salida cruda commiteada), **DE TERCEROS** (lo midió otro y se cita), **INFERIDO** (deducción sobre datos medidos, marcada como tal) o **NO MEDIDO**. Ningún número de este informe se escribió de memoria: todos salen de archivos en el repo, y cada sección dice cuál.

---

## ÍNDICE

1. Qué es SIAO y qué se intentó probar
2. Inventario de máquinas usadas
3. Los 11 falsadores, uno por uno, con sus números
4. **El resultado que quedó sin leer y es el mejor de la jornada**
5. Los cinco descubrimientos que cambian el proyecto
6. Mis errores: 19, clasificados por patrón
7. Las cuatro auditorías externas y su saldo
8. Reglas y decisiones vigentes
9. Todo lo NO MEDIDO, en un solo lugar
10. Cómo seguir, con criterio de orden declarado
11. Cómo auditar este informe

---

## 1 · Qué es SIAO y qué se intentó probar

**SIAO es un sistema operativo móvil donde la IA es dueña del sistema**, no una app en una sandbox. Arquitectura fijada en ADR-001:

- **openKylin** como userland anfitrión (glibc)
- **Android** como inquilino en un contenedor LXC, para compatibilidad de APKs
- Los **HAL del fabricante se reutilizan tal cual** vía Treble/AIDL/binder
- **NO** virtualización completa de Android
- **NO** ingeniería inversa como prerrequisito del producto

**La cadena de hipótesis que había que falsar, en orden de qué mata al proyecto antes:**

| # | Hipótesis | Falsador | Estado |
|---|---|---|---|
| H1 | el userland de openKylin corre fuera de su ISO | FALSADOR-001 | **VERDE** |
| H2 | se puede construir un rootfs arm64 con systemd | F-002 | **VERDE a/b, ROJO c** |
| H3 | el GKI de stock sirve como base | F-001 | **ROJO: falta config** |
| H4 | se puede prender lo que falta sin romper el KMI | F-004 → F-004d | **VERDE, dos vías** |
| H5 | los DLKM binarios del fabricante siguen cargando | F-007a/b | **parcial, ver §5.2** |
| H6 | el conjunto arranca | F-001-S1 | **arnés VERDE, boot pendiente** |

---

## 2 · Inventario de máquinas usadas

**Fuente:** `00-ENTORNOS-Y-CAPACIDADES.md` (raíz de los repos) + mediciones propias de esta jornada.

| Máquina | Cómo se alcanza | Qué se hizo acá | Verificado hoy |
|---|---|---|---|
| **`brain-env`** | gateway MUDH, servicio `build`, tool `run` | F-007a, F-007b, todos los pre-vuelos, lecturas de googlesource | 2 CPU, 118,8 GiB libres, `unzip`/`file`/`modinfo` AUSENTES |
| **Actions arm64** | `ubuntu-24.04-arm` | los 8 builds de kernel, el arnés QEMU | `/dev/kvm` **NO_EXISTE** |
| **Actions x64** | `ubuntu-24.04` | `stg`/`stgdiff` (binario linux-x86), peritajes | `/dev/kvm` **USABLE** |
| **`playwright`** | gateway MUDH | el índice de factory images de Google | navegador real, resolvió el muro JS |

**Runners con id real, para que la auditoría pueda cruzarlos:** `1000002018` (FALSADOR-001) hasta `1000002060` (rescate F-004c). Los ids de cada falsador están en su archivo de respuesta.

---

## 3 · Los 11 falsadores, uno por uno

### 3.1 FALSADOR-001 · el userland fuera de su ISO — **VERDE**

**Fuente:** `docs/agents/respuestas/2026-09-05-03-*` · rama `titan/falsador-userland-arm64`

```plain
bash 5.3.9 aarch64 de openKylin, en chroot dentro de un runner arm64:
  NAME="openKylin"  VERSION="3.0 (huanghe)"     <- leido DESDE ADENTRO
146 ELF con p_align 65536
```

**MEDIDO.** Es la premisa base: sin esto SIAO no existe.

**Y un verde que degradé yo mismo:** los 146 ELF a 65536 los vendí como virtud de openKylin. **65536 es el `max-page-size` por defecto de GNU `ld` en aarch64**, o sea que era lo esperable de cualquier binario arm64. **Real pero banal.** Corregido en el Doc donde se publicó.

**Tres defectos propios en este falsador:** v1 dio ROJO y el rojo era mío (faltaba el `PT_INTERP`); el control negativo no discrimina corrupto de inexistente; y predije que el runner arm64 no nacería en repo privado — nació.

---

### 3.2 F-001 · el `.config` REAL del GKI — **ROJO, y no es mío**

**Fuente:** `docs/agents/respuestas/2026-09-05-05-*`

Bajé el `boot.img` **certificado** de Google y le extraje el `.config` embebido (`CONFIG_IKCONFIG=y`, o sea fuente primaria, no un defconfig):

```plain
Linux/arm64 6.12.81 | 6.522 simbolos
CONFIG_PID_NS       APAGADO   <- bloqueador duro del contenedor
CONFIG_USER_NS      APAGADO
CONFIG_IPC_NS       AUSENTE
CONFIG_DEVTMPFS     APAGADO   <- systemd lo pide en su README
CONFIG_SYSVIPC      APAGADO
CONFIG_POSIX_MQUEUE APAGADO
CONFIG_MODVERSIONS  =y        <- el enforcer real del KMI
CONFIG_MODULE_SIG   =y
CONFIG_MODULE_SIG_FORCE APAGADO   <- la puerta: un DLKM propio carga sin la llave de Google
```

Y lo firma `lxc-checkconfig`, no yo: *"Pid namespace: required | User namespace: missing"*.

**MEDIDO. Consecuencia:** construir GKI propio deja de ser una línea del roadmap y pasa a ser **prerrequisito**.

**Descubrimiento de dependencia que un auditor externo confirmó después:** `IPC_NS` no falta por olvido, falta porque **su dependencia Kconfig (`SYSVIPC || POSIX_MQUEUE`) está apagada**. Era un dato con dos consecuencias, y yo lo reporté como tres datos independientes.

---

### 3.3 F-002 · el rootfs — **VERDE a/b · ROJO c**, en 9 versiones

**Fuente:** `docs/agents/respuestas/2026-09-06-05-F-002-CERRADO-*`

```plain
rc=0 | 177 paquetes | 248 MiB | runner 1000002033 | 79,8 s
ORIGEN, por apt-cache policy DENTRO del chroot:
   huanghe/main       174
   OVERLAY-SIAO         3
   huanghe-proposed     0     <- CERO
systemd 255.2-ok2.8 de huanghe/main (el del release oficial)
```

**`siao-base-s1` = `main` + TRES paquetes:** `libdevmapper1.02.1 2:1.02.205-ok1`, `libgcrypt20 1.12.1-ok1`, `libgpg-error0 1.59-ok1`.

**La causa era UNA palabra, y el control discrimina:**

```plain
copy://  -> instalo=True,  rc=0
file://  -> instalo=False, rc=25 ("use copy:// instead of file://")
```

**Mi historial de diagnósticos en este falsador, sin maquillar:**

| Versión | Mi diagnóstico | Resultado |
|---|---|---|
| v2 | "main y -proposed no son consistentes" | **FALSO**, era mi pin `-10` |
| v3 | "le falta el `Release`" | **FALSO** |
| v6 | "es el layout flat" | **FALSO** |
| v8 | conjunto de paquetes | correcto, y no alcanzaba |
| v9 | `copy://` | **VERDE** |

**Seis versiones diagnosticando mal, y `mmdebstrap` tenía la solución escrita en la salida que yo filtraba con `tail`.** Lo que la encontró no fue una hipótesis mejor: fue dejar de recortar la evidencia.

**ROJO (c) declarado:** todo se construyó con `trusted=yes`. Las firmas **no** están verificadas.

---

### 3.4 F-004 v3 · el KMI con el `stgdiff` REAL — **ROJO**

**Fuente:** `docs/agents/respuestas/2026-09-06-08-*` · `mediciones/f-004-v3/`

**Instrumento oficial de Google, con hash:**

```plain
stg      4.944.792 B | sha256 b8cf4364c4e7da8b57362afd817e6976
stgdiff  5.000.176 B | sha256 1c74def7edaa8222d4aed2c26ea42f81
libc++   1.306.352 B | sha256 7b91de1cba2ad902aad871b77e58af40
```

```plain
baseline.stg 11.317.742 B | siao.stg 11.319.347 B
stgdiff -> rc=4 | reporte 1.521.915 B | 'CRC changed' x 10.867 | 'was added' x 5
```

**La segunda pasada es la que aisló la causa:**

```plain
stgdiff --ignore linux_symbol_crc -> reporte 15.221 B (NO vacio)

type 'struct task_struct' changed
  member 'struct sysv_sem sysvsem' was added
  member 'struct sysv_shm sysvshm' was added
  member 'struct nsproxy* nsproxy' changed
    offset changed from 17280 to 17472
```

**`CONFIG_SYSVIPC` agrega dos miembros a `struct task_struct` y corre 24 bytes todo lo posterior.** De ahí los 10.867 CRC: `task_struct` es la estructura más referenciada del kernel. **No es cascada cosmética: son offsets.**

---

### 3.5 F-004b · el padding KABI — **predicción FALSA, hallazgo mejor**

**Fuente:** `docs/agents/respuestas/2026-09-06-10-*` · `mediciones/f-004b/`

**Base de la hipótesis, medida en el árbol de Google:**

```plain
include/linux/sched.h lineas 1527-1532:
  ANDROID_KABI_RESERVE(3) .. (8)          -> 6 slots libres
include/linux/android_kabi.h:76:
  #define _ANDROID_KABI_RESERVE(n)  u64 android_kabi_reservedN   -> 8 B cada uno = 48 B
struct sysv_sem = 1 puntero  ->  8 B
struct sysv_shm = 1 list_head-> 16 B      -> total 24 B <= 48 B
```

**Confirmación cruzada:** el `stgdiff` midió offsets de **16960 a 17152 bits = 192 bits = 24 bytes**. Dos caminos independientes, mismo número.

**Resultado:**

```plain
type 'struct task_struct' changed
  member 'u64 android_kabi_reserved3' was removed  (x3)
  member 'union { struct sysv_sem sysvsem; ... }' was added
  member 'union { struct sysv_shm sysvshm; ... }' was added
-> CERO 'byte size changed', CERO 'offset changed'
```

**Mi predicción era "reporte vacío" y salió 6.877 B: FALSA.** Pero adentro estaba el segundo rompedor:

```plain
type 'struct cgroup' changed        byte size 1920 -> 1984 | subsys[7] -> subsys[8] | 24 offsets
type 'struct cgroup_root' changed  byte size 6272 -> 6336
type 'struct css_set' changed      byte size  424 ->  448 | subsys[7] -> subsys[8] | 22 offsets
```

**`CONFIG_CGROUP_PIDS` agrega un subsistema, `CGROUP_SUBSYS_COUNT` pasa de 7 a 8, y los arrays crecen. Ese NO se arregla con padding:** un slot reservado sirve para agregar un miembro, no para cambiar la dimensión de un array derivada de un `enum`.

---

### 3.6 F-004c · nueve símbolos + parche — **VERDE**

**Fuente:** `docs/agents/respuestas/2026-09-06-11-*` · `mediciones/f-004c/`

```plain
reporte SIN CRC: 495 B | offsets 0 | byte size 0 | CRC 0
reporte ENTERO:
  function symbol 'void put_pid_ns(struct pid_namespace*)' was added
  type 'struct task_struct' changed
    3 slots reservados -> 2 uniones del MISMO tamano
```

**`CGROUP_PIDS` queda AISLADO como única causa** de los tres structs de cgroup: fue la única variable entre F-004b y F-004c.

---

### 3.7 F-004d · ocho símbolos, CERO parche — **VERDE, y ver §4**

---

### 3.8 F-007a · los 36 vendors de Google — **el daño con tamaño de producto**

**Fuente:** `docs/agents/respuestas/2026-09-06-13-*` · corrió en **`brain-env`**, cero runners.

```plain
listas publicadas en android/ : 38 (36 parseadas)
union de TODOS los vendors   : 9.544 simbolos unicos
baseline GKI puro            : 17.233 exportados
```

| vendor | exige | presentes | **FALTA** | CRC roto sin parche |
|---|---|---|---|---|
| `mtk` | 3.825 | 3.825 | **0** | **2.597** |
| `pixel` | 3.375 | 3.375 | **0** | **2.095** |
| `imx` | 2.909 | 2.909 | **0** | **2.152** |
| `qcom` | 2.492 | 2.492 | **0** | 1.560 |
| `virtual_device` | 1.491 | 1.491 | **0** | 1.051 |
| **TOTAL** | **9.544** | **9.544** | **0** | **6.129 (64,2%)** |

**Dos lecturas MEDIDAS:**

1. **`FALTA = 0` en las 36 listas.** El GKI exporta todo lo que cualquier vendor pide. Coherente con `TRIM_UNUSED_KSYMS` apagado.
2. **Sin el fragmento corregido, a Pixel se le rompe el 62% de su contrato.** Traducción: **ningún teléfono de esos vendors carga sus drivers.**

**INFERIDO (contención de conjuntos, no medición directa):** F-004c/d midieron 0 CRC sobre los 17.233; los 9.544 son subconjunto, así que 0 también ahí. **El cruce directo lista-por-lista NO se corrió.**

---

### 3.9 F-007b · el `.ko` REAL de un Pixel — **el hallazgo más caro**

**Fuente:** `docs/agents/respuestas/2026-09-06-14-*` · **`brain-env`** + `playwright`

**Técnica, y es reusable:**

```plain
dl.google.com -> Accept-Ranges: bytes | total 3.998.432.633 B (3,72 GiB)
zip anidado image-shiba-*.zip: comp=0 STORED -> se entra por rango
vendor_dlkm.img: bajados 6.447.287 B -> inflados a 25.591.808 B (coincide con usz)
sha256 3b16903dc74597e883925ff5cd893377a03992ec409a466334e517747b0f10fb
```

**Se bajó el 0,16% del zip.** Sin `unzip` (ausente): `zlib` de Python.

**El dato que invalida la rama:**

```plain
shiba (Pixel 8)          -> vermagic=6.1.157-android14-11-ge4470993d947-ab15260412
comet (Pixel 9 ProFold)  -> vermagic=6.1.157-android14-11-...
tegu  (Pixel 9a)         -> vermagic=6.1.157-android14-11-...
```

**Los tres, build de agosto 2026, corren 6.1 generación android14. NINGUNO usa 6.6.**

**El cruce:**

```plain
67 cabeceras ELF -> 67 ET_REL aarch64 -> 55 con .modinfo Y __versions
exigidos por los 55 modulos : 1.101
presentes en mi kernel 6.6  :   828
AUSENTES                    :   273
CRC IDENTICO                :   275  (33,2%)
CRC DISTINTO                :   553
```

**Control interno que podía dar rojo y dio verde:** de los 1.101 símbolos, **cero con CRC contradictorio entre módulos**.

**Esto NO es rojo del fragmento: es rojo de GENERACIÓN.** Los dos brazos son kernels de stock sin parchar.

---

### 3.10 Peritaje de terceros — **alguien ya construyó el 80%**

**Fuente:** `docs/agents/respuestas/2026-09-06-09-*`

| Proyecto | ⭐ | Qué resuelve |
|---|---|---|
| `libhybris/libhybris` | **844** | HAL bionic desde glibc. **La pieza central del ADR-001, ya escrita** |
| `Linux-on-droid/vendor_lindroid` | **205** | Linux en LXC sobre Android con GPU. **La arquitectura inversa, funcionando** |
| `droidian/porting-guide` | 163 | manual de porteo |
| `Halium/projectmanagement` | 151 | **229 issues abiertos**: el costo real del lado host |

**Confirmación independiente de mi F-001:** la lista de nueve configs de Lindroid **coincide en ocho** con mi fragmento, armada sin conocerme. Eso es lo que W-01 pide: un instrumento que podía contradecirme y no lo hace.

**Y el dato que reencuadra F-004:** su doc dice que si el build falla por `CONFIG_SYSVIPC` hay que **borrar la línea de `android-base.config`**. O sea que **SYSVIPC está prohibido por diseño en AOSP**, no apagado por descuido. Mi ROJO no era un hallazgo: era un muro conocido con instrucciones de derribo publicadas.

**Licencia MEDIDA, y es un problema:**

```plain
LICENSE / LICENSE.txt / COPYING / NOTICE / MODULE_LICENSE_APACHE2 / Android.bp
  -> los SEIS dan HTTP 404 en la rama lindroid-22.1
```

**Sin licencia explícita, el default legal es todos los derechos reservados: mirar sí, derivar producto no.** Los cimientos sí están limpios: `libhybris` Apache-2.0, LXC LGPL-2.1.

---

### 3.11 F-001-S1 paso 0 · el arnés QEMU — **VERDE**

**Fuente:** `docs/agents/respuestas/2026-09-06-15-*` · `mediciones/f-001-s1/`

```plain
/dev/kvm en Actions x64   -> USABLE     (abre O_RDWR)
/dev/kvm en Actions arm64 -> NO_EXISTE
```

**Consecuencia que el Doc de KVM no sacaba:** el huésped es aarch64 y KVM solo acelera con ISA compartida. En x64 hay KVM pero la ISA no coincide; en arm64 coincide pero no hay nodo. **TCG en las dos.** Y lo confirmó el propio kernel: `KVM is not available. Ignoring kvm-arm.mode`.

**El arranque:**

```plain
qemu-system-aarch64 8.2.2 | rc=0 en 2,2 s | 15.217 B de salida
[0.000000] Booting Linux on physical CPU 0x0000000000 [0x411fd070]
[0.000000] Linux version 6.6.58-android15-8-g217cec2d0381-ab12874290-4k
[0.000000] KASLR enabled | Machine model: linux,dummy-virt
[0.000000] psci: PSCIv1.1 detected in firmware.
```

**El GKI certificado de Google EJECUTA en QEMU.** Y el control positivo (`-kernel` inexistente) **falla**, así que el verde no es el default del script.

---

## 4 · EL RESULTADO QUE QUEDÓ SIN LEER, Y ES EL MEJOR DE LA JORNADA

**F-004d corrió a las 13:59 UTC, dio VERDE TOTAL, y yo nunca lo reporté.** Lo encontré al preparar este informe, leyendo `mediciones/f-004d/F-004d-VEREDICTO.txt`.

```plain
vmlinux 174.251.576 B | 97 modulos | ocho.stg 11.318.014 B

pasada CON CRC : rc=4 | 68 B | CRC changed x0 | byte size x0 | offset x0 | structs: NINGUNA
pasada SIN CRC : rc=4 | 68 B | identico

reporte ENTERO, una linea:
  function symbol 'void put_pid_ns(struct pid_namespace*)' was added
```

**Y el guard duro pasó:**

```plain
CONFIG_IPC_NS: "y"      <- sobrevive por POSIX_MQUEUE, SIN SYSVIPC
parche_al_ack: false
n_simbolos: 8
```

### La serie completa, misma referencia y misma herramienta

| Corrida | símbolos | parche al ACK | reporte SIN CRC | offsets | CRC cambiados |
|---|---|---|---|---|---|
| **F-004 v3** | 10 | no | 15.221 B | muchos | **10.867** |
| **F-004b** | 10 | **sí** | 6.877 B | 51 | 6.307 |
| **F-004c** | 9 | **sí** | 495 B | **0** | **0** |
| **F-004d** | **8** | **NO** | **68 B** | **0** | **0** |

**F-004d es estrictamente mejor que F-004c:** mismo cero, **sin parchar el árbol de Android**, sin consumir slots que Google reservó para sus backports, sin rebase por cada LTS. **Cero deuda técnica.**

**La idea fue del auditor externo, no mía, y lo digo así:** yo demostré que **existe** salida (el padding); él preguntó si **hace falta usarla**. Su contabilidad era correcta: los 15.221 B de F-004 v3 eran `task_struct` (SYSVIPC) + cgroup (PIDS) y nada más, así que sacando los dos no queda nada que parchear.

**Y el fallo de proceso es grave y es mío: correr un falsador, obtener el mejor resultado del proyecto, y no leerlo.** Dejé el resultado huérfano mientras seguía con F-007. **Es W-01 al revés: no fui el único testigo, fui ningún testigo.**

**Lo que esto NO dice (R-13):** dice **ABI-compatible**. Que un `.ko` real **cargue** necesita `vermagic` compatible, y eso depende de la generación (§3.9).

---

## 5 · Los cinco descubrimientos que cambian el proyecto

### 5.1 Existen DOS vías KMI-safe, y la barata es la que no parcha nada

**F-004d** (ocho símbolos, cero parche) domina a **F-004c** (nueve + parche). El costo de F-004d es resignar **`SYSVIPC`** además de `CGROUP_PIDS`.

**Riesgo declarado:** sin SysV IPC, `shmget`/`semget` no existen. systemd no los usa; **X11 con `MIT-SHM` y runtimes viejos sí pueden**. Eso es F-001-S1b y **NO está medido**.

### 5.2 El KMI tiene GENERACIÓN, y con número

**33,2%** de coincidencia de CRC entre `6.1-android14` y `6.6-android15`, los dos de stock. **Un DLKM solo carga en un kernel de su generación.** SIAO necesita **matriz de builds por generación**, no un kernel universal.

**Y el dato fino:** 275 símbolos **sí** conservan su CRC entre generaciones, o sea que el CRC no cambia por versión sino por **cambio real de firma o tipos**. Es el mismo mecanismo de F-004c visto desde afuera.

### 5.3 La parte difícil ya está escrita por otros

`libhybris` (844⭐) es la pieza central del ADR-001 y existe. Lindroid (205⭐) construyó la maquinaria completa **invertida**. **Reescribir eso sería el error de prioridad más caro del proyecto.** Pero su licencia no existe: **se estudia, no se copia.**

### 5.4 La vía oficial de Google exige ser dueño del sistema

`AppFunctions` requiere llamador **system-privileged**. **Eso convierte la tesis de SIAO en una consecuencia técnica, no en una preferencia:** para que un agente opere apps de verdad, tiene que ser el sistema.

### 5.5 Técnica reusable: auditar un teléfono con 6 MB

Con la URL de cualquier factory image, **HTTP Range + zip anidado STORED** dan el `vermagic` y los CRC exigidos bajando el 0,16%. **Sirve para elegir el dispositivo objetivo con datos en vez de con opinión.**

---

## 6 · Mis errores: 19, clasificados por patrón

### Patrón A · el guard que se saltea o mide otra cosa (6)

| # | Error | Costo |
|---|---|---|
| A1 | `tail -40` en el build: `rc` era del `tail`, no del comando. El archivo decía `rc=0` sobre un build fallido | **un run entero** |
| A2 | guard `"task_struct changed" in txt`: no distingue layout de renombre de unión → **veredicto FALSO sobre medición correcta** | un veredicto erróneo publicado |
| A3 | filtro `endswith("boot.img")` y el zip trae `boot-6.6.img` → **se salteó con `rc=0` y sin veredicto** | un run |
| A4 | `ANDROID_KABI_RESERVE(3)` aparece 3 veces en `sched.h` → el guard abortó (**bien**), pero me costó un brazo | un brazo de runner |
| A5 | parser de `__versions` con stride 72 en vez de 64 → leía nombres como CRC (`0x7665645f` = `'_dev'`) | ninguno, lo cacé |
| A6 | control N3 de F-002 se **autoaprobó**: falló por otro motivo y dijo "correcto" | un control inválido |

### Patrón B · recortar la evidencia antes de leerla (2)

| # | Error | Costo |
|---|---|---|
| B1 | F-002: `mmdebstrap` tenía `copy://` escrito en la salida que yo filtraba | **seis versiones** |
| B2 | F-004: `tail -40` escondió las 2.501 líneas previas al error real | un run |

**B2 ocurrió al día siguiente de escribir la lección de B1.** Una lección escrita no es un guard.

### Patrón C · el sujeto equivocado (2)

| # | Error | Costo |
|---|---|---|
| C1 | **elegí `android15-6.6` por disponibilidad del instrumento, no por dispositivo objetivo.** Ningún Pixel corre esa generación | **8 builds de kernel** |
| C2 | reporté `TRIM_UNUSED_KSYMS=y` del boot.img certificado y después `=n` del defconfig, sin decir que eran configs distintos | una contradicción en el ADR |

**C1 es el error más caro de la jornada.**

### Patrón D · afirmar sin medir, y sobre-corregir (5)

| # | Error |
|---|---|
| D1 | `yangtze (2.0)` escrito con confianza y sin fuente: es **V1.0** |
| D2 | corregí la fecha de release de openKylin que Abraham tenía **bien** |
| D3 | "el runner arm64 no va a nacer en repo privado": nació |
| D4 | vendí el `p_align 65536` como virtud: es el default de GNU `ld` |
| D5 | **anulé una medición correcta por sobre-corregirme:** dije que mi criba de "3 símbolos protegidos" era un defecto de parser. **La lista genérica tiene 3 símbolos. Mi parser estaba bien.** |

**D5 es el más incómodo: sobre-corregirse también destruye evidencia.**

### Patrón E · título que afirma más que el cuerpo (1)

| # | Error |
|---|---|
| E1 | titulé *"un DLKM binario de vendor sigue cargando"* mientras el cuerpo lo declaraba NO MEDIDO. Lo correcto: **"ABI-compatible; carga no medida"** |

### Patrón F · fallos de arnés y proceso (3)

| # | Error | Costo |
|---|---|---|
| F1 | un `: ` en un nombre de paso YAML → **dos runs con CERO jobs creados** | 2 runs |
| F2 | el job de comparación bajaba el artifact del brazo caído a `/tmp` y **nunca lo copiaba a `mediciones/`** → la causa casi se pierde | un rescate extra |
| F3 | **corrí F-004d, salió el mejor resultado del proyecto, y no lo leí** | **medio día de conclusiones desactualizadas** |

**F3 es el peor fallo de proceso de la jornada.**

---

## 7 · Las cuatro auditorías externas y su saldo

| Auditoría | Le acepto | Le refuto | Aporte decisivo |
|---|---|---|---|
| **1° (ADR-002)** | índice dinámico, páginas de 4K, prerrequisito de runner público | la fecha, el método del falsador | H4 (falta imagen Waydroid arm64) |
| **2° (ADR-003)** | 65536 banal, `yangtze` V1.0, AOSP no compila en Actions, mezcla de rojos LXC/SIAO | ENOENT en `--mode=root`, F-004 no corrible en 6.12, el enforcer real es MODVERSIONS | `IPC_NS` depende de `SYSVIPC` |
| **3° (ADR-004)** | `stgdiff` **SÍ existe** (mi "cinco vías" era una ruta mal tipeada) | la guarda es `USE_PKCS11_ENGINE`, no `OPENSSL_NO_ENGINE`; `sig_ok` es incondicional por diseño | localizó el instrumento oficial |
| **4° (ADR-005)** | R-11 a R-14, `CGROUP_DEVICE` toca `subsys[]`, títulos que afirman de más | `TRIM_UNUSED_KSYMS` apagado, el `fixdep` no vino de un artifact | **F-004d y F-007**, los dos mejores falsadores del día |

**Balance honesto: los dos falsadores más valiosos de la jornada (F-004d y F-007) los propuso el auditor externo, no yo.** Mi aporte fue medirlos, agregarles guards que sus enunciados no tenían (el de `IPC_NS`), y encontrar los defectos de sus hipótesis.

---

## 8 · Reglas y decisiones vigentes

### Reglas nacidas de defectos medidos

| Regla | Enunciado | Nació de |
|---|---|---|
| **R-08** | logs íntegros; `rc` del comando, nunca de un filtro; `pipefail` | A1, B2 |
| **R-09** | borrar el log del brazo cuyo código cambió | brazo `siao` con log viejo |
| **R-10** | "CERRADO" solo con todos los criterios verdes | F-002 (c) rojo |
| **R-11** | todo artifact se copia a `mediciones/` antes de analizar | F2 |
| **R-12** | el guard mide la **propiedad**, no la presencia de una cadena | A2 |
| **R-13** | los títulos afirman solo lo medido | E1 |
| **R-14** | sin autopuntuación | inflación de rúbrica propia |
| **R-15** *(nueva, de este informe)* | **un falsador no está terminado hasta que su veredicto se leyó y se reportó** | F3 |

### Decisiones firmadas

- **D5:** fragmento de nueve + padding KABI es KMI-safe medido, oficial **provisional**, slots a **6-7-8**.
- **D6:** si F-004d + F-001-S1b salen verdes, el oficial pasa a **ocho sin parche**. **F-004d ya salió verde: falta S1b.**
- **D7:** `CGROUP_DEVICE` no entra; filtrado por **BPF** (`CGROUP_BPF=y` ya está).
- **D8:** activar `TRIM_UNUSED_KSYMS` **y** la lista del dispositivo objetivo para parecerse a producción.
- **D9:** de Lindroid se **estudia**, no se copia, hasta que haya licencia.

---

## 9 · Todo lo NO MEDIDO, en un solo lugar

**Del kernel y el KMI**

1. Si un `.ko` real **carga** (`insmod`): está medido el contrato de símbolos, no la carga.
2. La generación `android14-6.1` con el fragmento: **toda la serie F-004 está en 6.6**.
3. Si el padding KABI funciona en 6.1: mecanismo idéntico, **sin re-medir**.
4. El cruce directo lista-por-lista de F-007a con los CRC de F-004c/d.
5. Los 12 ELF de 67 sin `.modinfo` + `__versions` parseables.
6. `komodo` falló con `IndexError` en mi parser de central directory.
7. Si algún Pixel de los 62 del índice está en 6.6: probé **tres**.

**Del sistema base**

8. **Firmas de `siao-base-s1` (F-002 c):** todo con `trusted=yes`.
9. Si el rootfs **arranca**.
10. El `p_align` a escala sobre el rootfs completo.

**Del arranque**

11. Si `systemd` levanta: **F-001-S1 propiamente dicho.**
12. Si openKylin arranca **sin `SYSVIPC`**: **F-001-S1b, y de esto depende D6.**
13. Cuánto tarda un boot completo en TCG.
14. `llego_a_init` salió `false`: el kernel arrancó pero no vi el pánico (su cmdline trae `console=ttynull`).
15. El brazo x64 del arnés: commiteado, **sin abrir**.

**De terceros**

16. Si Lindroid corre sobre GKI puro o exige árbol de vendor.
17. Si sus archivos individuales traen cabecera Apache-2.0.
18. `CGROUP_DEVICE`: Lindroid lo exige, yo lo descarté; **medido que toca `subsys[]`, no medido si BPF alcanza**.
19. Si `DRM_LINDROID_EVDI` tiene equivalente o es deuda nueva.

**De producto**

20. **Todos los "dolores" son hipótesis: cero usuarios entrevistados.**
21. Si la capa de IA es viable en el fierro de un teléfono (RAM, térmica, batería).
22. F-003 (16K), F-005 (AppFunctions), F-006 (LSM/KMI).
23. Costo en tiempo de cada paso: **estimarlo antes de F-001-S1 sería inventar**.
24. La causa exacta del `fixdep: Permission denied` (`Error 126`).

---

## 10 · Cómo seguir

**Criterio de orden declarado (O-01):** primero lo que convierte "medimos que se puede" en "lo vimos andar"; segundo lo que **nadie más puede hacer por nosotros**; último lo que endurece algo que todavía no arranca.

### Paso 1 · **F-001-S1b** — decide entre las dos vías KMI-safe

Arrancar `siao-base-s1` con `systemd` sobre un kernel **sin `SYSVIPC`**, y medir con `strace -f -e trace=ipc` quién pide SysV IPC.

**Por qué primero:** es lo único que decide si el fragmento oficial es el de **ocho sin parche** (cero deuda) o el de **nueve con parche**. **Y ya no es opinable: F-004d dio verde, así que la única pregunta que queda es de userland.**

**Piezas que faltan y son builds, no investigación:** el `Image` arrancable (F-004c/d guardaron `vmlinux`, no el `Image`), el rootfs como tarball, y forzar `console=ttyAMA0`.

### Paso 2 · **Decidir el dispositivo objetivo** — es tuya, no mía

Define la generación de KMI y por lo tanto **qué hay que re-medir**. Pixel → `android14-6.1`. La técnica de F-007b permite auditar candidatos con 6 MB cada uno.

### Paso 3 · **F-007c** — el `.ko` real contra un kernel propio de SU generación

Compilar `android14-6.1` con el fragmento y cruzar los CRC contra los 55 módulos ya extraídos. **Convierte el último NO MEDIDO grande del ADR-001 en medido.**

### Paso 4 · **La capa 5** — lo único que nadie más hace

Prototipar el agente que gobierna el sistema, sobre el rootfs en QEMU. **Es la respuesta a "¿por qué SIAO y no Lindroid?"** y hoy está en cero.

### Paso 5 · **F-002 (c)** — las dos llaves

Keyring de openKylin con huella contrastada **más** clave SIAO para el `Release` del overlay. Corto, cubre cadena de suministro, **no desbloquea nada**.

### Lo que BAJA, con su razón medida

- **F-005 (AppFunctions):** Lindroid integró red, audio, input y storage **sin** eso. Baja de **urgencia**, no de importancia: sigue siendo el contrato agente↔app.
- **F-003 (16K):** se mide con dispositivo real.
- **F-006 (LSM):** endurecer algo que no arranca.
- **ADR-003 hardware:** bloqueado por G0 **y** por los 229 issues de Halium.

---

## 11 · Cómo auditar este informe

1. **Toda la evidencia cruda está commiteada**, no resumida. Rama `titan/f-004-kmi`: `mediciones/f-001-s1/`, `f-002/`, `f-004-v3/`, `f-004b/`, `f-004c/`, `f-004d/`, `peritaje/`. Los reportes de `stgdiff` van enteros, incluido uno de **1.521.915 B**.
2. **Los instrumentos están versionados** en `tools/`: `f004_kmi_v3.py`, `f004b_kabi.py`, `f004c_kabi.py`, `f004d_sin_sysvipc.py`, `f004*_stg.py`, `f001s1_arnes.py`. Cada uno con su md5 en la bitácora del run.
3. **Las bitácoras las escribió el runner**, no yo: cualquiera puede recomputar un veredicto y **contradecirlo**.
4. **Los controles positivos están a la vista:** `copy://` vs `file://` (F-002), `-kernel` inexistente (arnés), CRC contradictorio entre módulos (F-007b), `_Static_assert` del compilador (F-004b).
5. **Los tres puntos donde más conviene apretar:**
   - el cruce de F-007a es **INFERIDO por contención de conjuntos**, no medido directo;
   - **F-004d quedó sin leer medio día** (F3): revisar si hay otros resultados huérfanos;
   - **todo está en la generación de KMI equivocada** si el objetivo es un Pixel (C1).

--- METODO TITAN ---
Accion delicada: NO (documento, sin escrituras en ramas ajenas)
Modo aplicado:   TITAN FULL
Rubrica:         N/A por R-14 (la asigna el auditor)
N/A declarados:  N/A
Review externo:  este documento SE ENTREGA para review externo
Instrumento:     ninguno nuevo. Sintesis de 11 falsadores cuya evidencia cruda
                 esta commiteada en la rama titan/f-004-kmi y cuyos archivos de
                 respuesta estan en docs/agents/respuestas/ de main.
