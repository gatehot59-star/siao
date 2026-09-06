# F-004d en 6.1 cerró **NO MEDIDO**, y las dos causas son de arnés

**Fecha:** 2026-09-06 · **Run:** `34049301780` · **Máquinas:** Actions arm64 (runners `1000002078` y `1000002079`) + x64 (`1000002080`).

**Evidencia cruda:** `mediciones/f-004d-61/` en `titan/f-004-kmi`.

**Mi predicción era ~68 B, 0 CRC, 0 offsets. NO SE PUDO EVALUAR: ningún brazo entregó su `vmlinux`.** Queda **NO MEDIDO**, no rojo.

---

## 1 · Lo que SÍ quedó medido, y era el riesgo principal del auditor

**MEDIDO**, del `.config` resuelto de `android14-6.1` con el fragmento de ocho:

```plain
CONFIG_DEVTMPFS        y      CONFIG_TMPFS_XATTR   y
CONFIG_DEVTMPFS_MOUNT  y      CONFIG_AUTOFS_FS     y
CONFIG_FHANDLE         y      CONFIG_PID_NS        y
CONFIG_POSIX_MQUEUE    y      CONFIG_IPC_NS        y

CONTROL | CONFIG_SYSVIPC       NO esta en =y (correcto)
CONTROL | CONFIG_CGROUP_PIDS   NO esta en =y (correcto)
GUARD OK: IPC_NS=y sobrevive por POSIX_MQUEUE, sin SYSVIPC.
```

**El guard duro pasó en la generación del Pixel.** Era el único riesgo que podía invalidar el fragmento de ocho por diseño, y no se materializó. La inferencia del ADR-006 ("en 6.1 `POSIX_MQUEUE` ya viene en `y`, así que `IPC_NS` tiene más margen") **pasa de INFERIDO a MEDIDO**.

**Y hay `Module.symvers`:** 16.036 líneas, sha256 `a86d08ccab5fc5b4f46dbdbf9ef53885e743dc2648908481967f036da8539d72`. Commiteado. Contra 17.234 en 6.6: el kernel de 6.1 exporta ~1.200 símbolos menos, **INFERIDO** como diferencia normal de generación.

---

## 2 · Causa 1: el brazo de ocho compiló 1.430 s y murió al linkear `vmlinux`

**MEDIDO**, últimas líneas de `f004d-build.txt` (244.281 B, commiteado entero):

```plain
BTF: .tmp_vmlinux.btf: pahole (pahole) is not available
Failed to generate BTF for vmlinux
Try to disable CONFIG_DEBUG_INFO_BTF
make[2]: *** [scripts/Makefile.vmlinux:34: vmlinux] Error 1
```

**El kernel me dijo la causa y la solución en tres renglones.** `android14-6.1` trae `CONFIG_DEBUG_INFO_BTF=y` y para generar el BTF necesita **`pahole`**, que no instalé.

**Es una diferencia de dependencia de herramientas ENTRE GENERACIONES**, y es exactamente la clase de cosa que R-17 predice: en 6.6 el mismo `apt-get` alcanzaba, en 6.1 no.

**Y la solución ya la tengo medida de antes:** `pahole` **está en el prebuilt de Google** que uso para `stgdiff`. Del listado de `kernel/prebuilts/build-tools/linux-x86/bin` que medí en el peritaje de cero builds:

```plain
100755 blob c9d7f50ef031bae21b0df50b5b74bf61b72d6612  pahole
```

**Dos vías, las dos de un renglón:** `apt-get install dwarves` (que provee `pahole`) en el runner arm64, o bajar el prebuilt — aunque ese es **linux-x86** y el build es arm64, así que la vía correcta acá es `dwarves`. Lo digo porque casi cometo el error de la generación otra vez: **el binario correcto tiene que ser de la arquitectura del anfitrión.**

**Consecuencia positiva no buscada:** el `Module.symvers` **sí** se generó, porque `modpost` corre antes del link final. Así que la **criba** por CRC es posible sin `vmlinux`; lo que necesita `vmlinux` es el `stgdiff`, que es el veredicto real.

---

## 3 · Causa 2: el `fixdep: Permission denied` por TERCERA vez

**MEDIDO**, y ahora tiene patrón:

```plain
/bin/sh: 1: scripts/basic/fixdep: Permission denied
make[2]: *** [scripts/Makefile.host:114: arch/arm64/tools/gen-hyprel] Error 126
```

| Ocurrencia | Falsador | Brazo | Rama |
|---|---|---|---|
| 1° | F-004c | **baseline** | android15-6.6 |
| 2° | F-004c (rescate) | **baseline** | android15-6.6 |
| 3° | F-004d@6.1 | **baseline** | android14-6.1 |

**Tres veces, siempre en el brazo `baseline`, siempre en menos de 1 segundo.** Y en F-004b el mismo código, el mismo runner y la misma rama **funcionaron**.

**Lo que descarto con evidencia:** el auditor propuso *"los artifacts de Actions pierden el bit de ejecución"*. **Ya lo refuté y sigue refutado:** el árbol se baja fresco de googlesource y se extrae con `tar`, sin artifact ni cache. Y `fixdep` **no** viene del tarball: lo compila `HOSTCC` en el mismo paso.

**Mi hipótesis, y la marco como hipótesis:** es una **carrera de `make -j2`**. `gen-hyprel` y `fixdep` se compilan en paralelo, y la receta de `gen-hyprel` invoca a `fixdep` **mientras el linker todavía lo está escribiendo**: un ELF a medio escribir no es ejecutable, y el kernel devuelve `EACCES`, no `ENOENT`. **Eso explica la intermitencia; "noexec en /tmp" no la explicaría.** Con solo 2 vCPU la ventana es angosta y por eso a veces gana la carrera.

**Prueba barata y falsable:** correr `make archscripts` con `-j1` **antes** del build paralelo. Si el 126 desaparece en varias corridas, la hipótesis se sostiene; si vuelve, es falsa y hay que buscar en otro lado. **NO MEDIDO.**

---

## 4 · Lo que NO cambia

**Ninguna de las dos causas tiene relación con el fragmento de SIAO.** El brazo `baseline` es `gki_defconfig` **puro**, sin fragmento y sin parche: si falla, falla el arnés. Y el brazo de ocho falló por una herramienta ausente, no por un símbolo.

**F-004d en 6.6 sigue VERDE MEDIDO** (68 B, cero offsets, cero CRC). Lo que queda pendiente es **transferirlo a 6.1**, que es justo lo que R-17 prohíbe dar por hecho.

---

## 5 · R-15 funcionó, y conviene decirlo

Este run **no quedó huérfano**: escribió su `VEREDICTO.md`, agregó su línea a `mediciones/INDICE.md` con veredicto **NO MEDIDO**, y por eso lo leí dentro de la hora en vez de medio día después. **La regla que nació del peor fallo de proceso de ayer atrapó el resultado de hoy.**

---

## 6 · Lo que sigue, en un solo relanzamiento

**F-004d@6.1 v2**, con tres cambios y ninguno toca el sujeto:

1. **`apt-get install dwarves`** para tener `pahole`. Arregla la causa 1.
2. **`make archscripts -j1`** antes del build paralelo. Prueba la hipótesis de la causa 2 **y** la sortea.
3. **Guard nuevo:** si `vmlinux` no existe después del build, **abortar con mensaje propio** en vez de dejar que `tar` falle silenciosamente. Ese `tar` devolvió `rc=2` con 109 B de stderr y **el instrumento siguió como si nada**, escribiendo un `elf-d.tar.zst` de 20.127.789 B **sin `vmlinux` adentro**. Es el patrón del guard que no mide lo que dice medir (R-12), esta vez en mi propio empaquetado.

**El punto 3 es el hallazgo más útil de este cierre:** el comparador dijo "no llegó el vmlinux" y tenía razón, pero el artifact existía y pesaba 20 MB. **Un artifact que existe no prueba que contenga lo que dice.**

---

## NO MEDIDO

1. **F-004d en 6.1** (el objetivo de este run).
2. **La causa exacta del `fixdep` 126:** tengo hipótesis con mecanismo y prueba barata, no medición.
3. Si `dwarves` del repo de Ubuntu 24.04 sirve para el BTF de 6.1, o si hace falta la versión de Google.
4. Si el `Module.symvers` de 16.036 líneas alcanza para una **criba** de CRC contra los 55 módulos del Pixel: **requiere un baseline de 6.1 y no lo tengo.**

--- METODO PROMETEO ---
Máquinas: Actions arm64 (dos brazos) + x64 (comparador).
Artefacto en git: este archivo. Evidencia: `mediciones/f-004d-61/`.
Artefacto en ClickUp: Doc espejo enlazado en el cierre.
