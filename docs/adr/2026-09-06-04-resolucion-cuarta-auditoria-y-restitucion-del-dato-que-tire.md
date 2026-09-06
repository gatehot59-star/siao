# ADR-005 · Resolución de la cuarta auditoría

**Fecha:** 2026-09-06 · **Máquina:** Actions x86 (job `peritaje-cero-builds`, cero compilación) sobre el `.config` y los repos ya commiteados.

**Evidencia cruda:** `mediciones/peritaje/CERO-BUILDS.txt` en la rama `titan/f-004-kmi`.

**Sin rúbrica: R-14 aceptada. La puntuación la pone el auditor o no existe.**

---

## 1 · Acepto sin peros

**R-11** (todo artifact se copia a `mediciones/` antes de analizar nada), **R-12** (el guard mide la propiedad, no la presencia de una cadena), **R-13** (los títulos afirman solo lo medido) y **R-14** (sin autopuntuación). Las cuatro ya están aplicadas en `tools/f004d_stg.py` y en el workflow de F-004d.

**Y acepto la corrección de título, que es la más justa de las cuatro:** escribí *"un DLKM binario de vendor sigue cargando"* en el título mientras el cuerpo lo declaraba NO MEDIDO. **La frase correcta es "ABI-compatible; carga no medida".** Es el patrón de siempre: el cuerpo honesto y el título vendiendo.

**Las tres firmas (D5, D6, D7) quedan asentadas**, con la corrección de slots 3-4-5 → **6-7-8** por el riesgo de colisión con los backports de Google.

---

## 2 · Le refuto DOS, y una es sobre mí mismo

### 2.1 `TRIM_UNUSED_KSYMS` NO está activo en el `gki_defconfig`

Su punto 1 dice: *"la producción GKI usa `TRIM_UNUSED_KSYMS` + lista: si SIAO recorta distinto, puede dejar de exportar algo que el vendor necesita"*. Medido en el `.config` del baseline:

```plain
# CONFIG_TRIM_UNUSED_KSYMS is not set
CONFIG_MODVERSIONS=y
CONFIG_MODULE_SIG=y
CONFIG_MODULE_SIG_PROTECT=y
# CONFIG_MODULE_SIG_FORCE is not set
CONFIG_ANDROID_KABI_RESERVE=y
```

**Está APAGADO.** Así que mi build no recorta nada: exporta el conjunto completo, que es **más** permisivo que el de Google, no menos. Su riesgo se invierte: **no es que SIAO recorte distinto, es que SIAO no recorta.**

**Y acá me refuto a mí mismo, que es lo importante:** en el ADR-003 reporté `CONFIG_TRIM_UNUSED_KSYMS=y` con `UNUSED_KSYMS_WHITELIST="abi_symbollist.raw"`. **Las dos mediciones son ciertas y son de configs distintos:** aquella salió del `.config` embebido en el **boot.img certificado** que publica Google; esta sale del **`gki_defconfig` del árbol**. O sea que **Google lo activa en su build de release (Kleaf), no en el defconfig.** Consecuencia real: para que el kernel de SIAO se parezca al de producción hay que activarlo **y** darle la lista del dispositivo objetivo. Eso valida su recomendación, con el mecanismo corregido.

### 2.2 El `fixdep: Permission denied` NO vino de un artifact

Su hipótesis: *"los artifacts de GitHub Actions se zipean y pierden los bits de ejecución. Si ese árbol se restauró desde artifact/cache, ahí está"*. La bitácora rescatada lo desmiente:

```plain
bajado 238726574 B en 87.7 s | sha256 a5e654aa93cd919f13c12cdd7ae0ae9e60eadb0a698baef76aca4c07cb076bcb
$ tar -xzf /tmp/f004c/ack.tar.gz -C /tmp/f004c/ack
  rc=0 en 7.9 s
$ make ... HOSTCFLAGS='-DUSE_PKCS11_ENGINE' -j$(nproc) Image modules
  rc=2 en 0.7 s
```

**El árbol se bajó fresco de googlesource y se extrajo con `tar`, sin artifact ni cache en el medio.** Y el build murió en **0,7 segundos**. La causa exacta sigue **NO MEDIDA**, y F-004d ya lleva un `stat` del directorio para cazarla si vuelve.

**Dato colateral que le importa a su "reproducibilidad demostrada":** el `tar.gz` que sirve googlesource **NO es byte-idéntico entre runs** (`3dac554d...` en F-004 v3, `a5e654aa...` en F-004c) porque `+archive` regenera el tarball. **Lo que sí se repitió idéntico fue el `.stg`**, que es la propiedad que importa. La reproducibilidad se sostiene, pero por el `.stg`, no por el tarball.

---

## 3 · Su predicción sobre `CGROUP_DEVICE`: CONFIRMADA, y con el número

```plain
# CONFIG_CGROUP_DEVICE is not set        <-- APAGADO, o sea que prenderlo agranda subsys[]
CONFIG_CGROUP_BPF=y                      <-- la via BPF ya esta disponible
CONFIG_CGROUP_FREEZER=y                  <-- de la lista de Lindroid, este sale GRATIS
subsistemas de cgroup en =y: 6
```

**Tenía razón en las dos mitades:** `CGROUP_DEVICE` está apagado, así que prenderlo rompe el KMI **exactamente igual que `CGROUP_PIDS`**; y `CGROUP_BPF` ya está prendido, así que el filtrado de dispositivos por BPF no cuesta nada. **D7 pasa de razonado a medido.**

Y un regalo del mismo grep: de los nueve configs que pide Lindroid, **`CGROUP_FREEZER` ya viene en `y`**. El caro de su lista es uno solo.

---

## 4 · RESTITUYO un dato que anulé por sobre-corrección

En F-004 v3 mi criba dijo *"3 símbolos protegidos por Google, de los tocados 2 están protegidos: `__put_task_struct` y `module_layout`"*. Yo **anulé ese número** declarándolo defecto de mi parser, con el argumento de que "la lista real tiene miles". Medido hoy, la lista genérica **entera**:

```plain
wc -l abi_gki_aarch64 -> 5
[abi_symbol_list]
# commonly used symbols
  module_layout
  __put_task_struct
  utf8_data_table
```

**Tres símbolos. Mi parser estaba bien y yo lo tiré.** Los miles están en las **38 listas por vendor** (`_qcom`, `_pixel`, `_mtk`, `_xiaomi`, `_exynos`, `_virtual_device`…), no en la genérica.

**Y el dato restituido tiene filo:** de los tres símbolos que Google marca como "commonly used", el fragmento de diez tocaba **dos**. `module_layout` es literalmente el que `insmod` compara para decidir si un módulo puede cargar. Eso refuerza, no debilita, todo lo que vino después.

**La lección para mí es la inversa de la habitual:** sobre-corregirse también destruye evidencia. Anulé una medición correcta para parecer prudente.

**Y aparece la lista que F-001-S1 necesita:** `abi_gki_aarch64_virtual_device`, justo para el arnés QEMU.

---

## 5 · La licencia de Lindroid: medida, y es un problema

```plain
LICENSE                 -> HTTP 404
LICENSE.txt             -> HTTP 404
COPYING                 -> HTTP 404
NOTICE                  -> HTTP 404
MODULE_LICENSE_APACHE2  -> HTTP 404
Android.bp              -> HTTP 404
cabecera de lindroid.mk -> sin encabezado de licencia
```

**`vendor_lindroid` (rama `lindroid-22.1`) no publica licencia en su raíz.** Sin licencia explícita, el default legal es **todos los derechos reservados**: mirarlo se puede, **derivar un producto no**.

**Consecuencia de orden, y modifica el plan:** "leer Lindroid" queda partido en dos. **Estudiar su arquitectura y su lista de configs es legítimo y ya dio frutos** (esta misma jornada). **Copiar código no**, hasta que haya licencia o alguien la pida a los autores. Y sus dependencias sí son claras: `libhybris` es Apache-2.0 y LXC es LGPL-2.1, **así que las piezas que importan están limpias.** El bloqueo es sobre el pegamento de Lindroid, no sobre los cimientos.

**NO MEDIDO:** si archivos individuales de sus subdirectorios traen cabecera Apache-2.0 (convención AOSP). Solo miré la raíz y `lindroid.mk`.

---

## 6 · Su F-004d, corriendo, con un guard que su enunciado no tenía

Su idea es mejor que la mía y lo digo así: yo demostré que **existe** salida (el padding); él pregunta si **hace falta**. Está corriendo el fragmento de **ocho**, sin un solo parche al ACK.

**Pero su enunciado se comía un riesgo, y lo agregué como aborto duro:** `CONFIG_IPC_NS` depende de `(SYSVIPC || POSIX_MQUEUE)` en Kconfig — **por eso en F-001 aparecía AUSENTE, no apagado.** Sacar `SYSVIPC` podía apagar `IPC_NS` y dejar al contenedor de apps sin namespace de IPC, que **sí** es bloqueador. El fragmento conserva `POSIX_MQUEUE=y`, así que la predicción es que sobrevive; **si no queda en `y`, el falsador aborta y se declara**, porque un verde de KMI con el contenedor roto no sirve de nada.

---

## 7 · Y un defecto mío del turno, medido

Los dos primeros intentos de F-004d **murieron con CERO jobs creados** y con el nombre del archivo en vez del `name:` del workflow. Esa es la firma de **YAML que no parseó**. Causa: un paso se llamaba `Subir todo (R-11: nada se queda en /tmp)`, y un escalar plano que contiene `: ` lo lee YAML como un mapping. **Un `: ` en un nombre de paso me costó dos runs.** Ya está entre comillas.

---

## 8 · Firmas de este ADR

- **D5 (aceptada, corregida):** el fragmento de nueve con padding KABI es KMI-safe medido y queda **oficial provisional**, con los slots movidos a **6-7-8**. `CGROUP_PIDS` a Fase 3, con `RLIMIT_NPROC` por user namespace como mitigación interina.
- **D6 (aceptada):** si F-004d + F-001-S1b salen verdes, el fragmento oficial pasa a ser el de **ocho sin parche** y el KABI se archiva como plan B **con** su evidencia.
- **D7 (aceptada, ahora MEDIDA):** `CGROUP_DEVICE` no entra. Filtrado de dispositivos por **BPF**, que ya está en `y`.
- **D8 (nueva, mía):** para que el kernel de SIAO se parezca al de producción hay que activar `TRIM_UNUSED_KSYMS` **y** sumar la lista de símbolos del dispositivo objetivo. Hoy no está activo y el build no recorta.
- **D9 (nueva, mía):** de Lindroid **se estudia la arquitectura, no se copia código**, hasta que aparezca una licencia. Los cimientos (`libhybris` Apache-2.0, LXC LGPL-2.1) están limpios.

## Orden vigente

**F-004d** (corriendo) → **F-001-S1 + S1b** (con la lista `abi_gki_aarch64_virtual_device`) → **F-007** (el `.ko` real de Pixel) → **F-002 c** → estudio de Lindroid → **F-005**.

--- METODO TITAN ---
Accion delicada: NO
Modo aplicado:   TITAN FULL
Rubrica:         N/A por R-14 (la asigna el auditor)
N/A declarados:  N/A
Review externo:  esta entrega ES la respuesta a un review externo
Instrumento:     job 'peritaje-cero-builds' en Actions x86, cero compilacion.
                 Evidencia cruda: mediciones/peritaje/CERO-BUILDS.txt y
                 mediciones/f-004c/CAIDO-f004b-baseline-bitacora.txt
