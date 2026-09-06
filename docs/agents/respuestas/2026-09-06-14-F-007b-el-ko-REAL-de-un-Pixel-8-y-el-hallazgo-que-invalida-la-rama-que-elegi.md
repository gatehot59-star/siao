# F-007b: el `.ko` real de un Pixel, y el hallazgo que invalida la rama que elegí

**Fecha:** 2026-09-06 · **Máquina:** **`brain-env`** por el gateway (servicio `build`, tool `run`) + servicio **`playwright`**. **Cero Actions, cero compilación.**

**Autorización:** Abraham aceptó los términos de Google y me lo dijo explícitamente. Con eso el botón "Reconozco" se apretó en el navegador del gateway.

**Evidencia cruda en el taller:** `/workspace/F-007b-paso1.txt`, `-paso3.txt`, `-paso4.txt`, `-paso6.txt`, `-paso9.txt`, más `f7-outer.json`, `f7-inner.json`, `f7-devices.json`, `f7-cruce.json`, `f7-ko-*.json` y `vendor_dlkm.img` (25.591.808 B, sha256 `3b16903dc74597e883925ff5cd893377a03992ec409a466334e517747b0f10fb`).

---

## 1 · La técnica: 6,4 MB de un zip de 3,72 GiB, sin bajar el zip

```plain
dl.google.com -> Accept-Ranges: bytes | Content-Range: bytes 0-255/3998432633
zip externo: 3.998.432.633 B (3,72 GiB), 10 entradas
  image-shiba-cp2a.260805.005.zip  comp=0 (STORED)  3.945.077.653 B
zip ANIDADO: leido POR RANGO desde el offset 191, 32 entradas
  vendor_dlkm.img  comp=8  csz=6.447.287  usz=25.591.808
bajados: 6.447.287 B -> inflados a 25.591.808 B, coincide con usz: True
```

**Se bajaron 6,4 MB de 3,72 GiB: el 0,16%.** El zip anidado está **STORED**, así que se puede entrar a su central directory por rango y sacar una sola entrada. No hizo falta `unzip` (ausente en el taller): `zlib` de Python alcanza.

---

## 2 · EL HALLAZGO: ningún Pixel usa `android15-6.6`

El auditor lo pidió explícitamente: *"verificar con `strings`, no asumir modelo"*. **Lo verifiqué, y me refutó la elección de rama entera:**

```plain
shiba  (Pixel 8)        build mas nuevo -> vermagic=6.1.157-android14-11-ge4470993d947-ab15260412
comet  (Pixel 9 ProFold) build mas nuevo -> vermagic=6.1.157-android14-11-ge4470993d947-ab15260412
tegu   (Pixel 9a)        build mas nuevo -> vermagic=6.1.157-android14-11-ge4470993d947-ab15260412
```

**Los tres, en su build de agosto de 2026, corren `6.1` de la generación `android14`.** No 6.6, no android15.

**Consecuencia directa, y es la más dura de la jornada: toda la serie F-004 → F-004d está medida sobre `android15-6.6`, que es una generación de KMI que NINGÚN Pixel corre.** Elegí esa rama porque en `android16-6.12` el directorio `android/` daba 404 y en `android15-6.6` existía: un criterio de **disponibilidad del instrumento**, no de **dispositivo objetivo**. Es el error E-01 en su forma más costosa: experimento impecable, sujeto equivocado.

**Y la salida es barata, medida hoy:** `android14-6.1` también publica sus listas (**37**, contra 38 de `android15-6.6`), así que todo el arnés de F-004 se puede reapuntar cambiando una variable de entorno.

---

## 3 · Los `.ko` reales, leídos de verdad

```plain
vendor_dlkm.img: 25.591.808 B | ext4 (magic 0x53EF @1080), NO sparse, NO EROFS
cabeceras ELF halladas          : 67
de esas, ET_REL + aarch64 (modulos): 67
modulos con .modinfo Y __versions  : 55
nombres de .ko referenciados       : 121
```

Ejemplo real, `aoc_alsa_dev`:

```plain
name     : aoc_alsa_dev
vermagic : 6.1.157-android14-11-ge4470993d947-ab15260412 SMP preempt mod_unload modversions aarch64
license  : Dual BSD/GPL
55 simbolos exigidos, entre ellos:
   __arch_copy_to_user           0x9a85eebb
   __mutex_init                  0xa571f6b0
   __platform_driver_register    0x894c433a
   _printk                       0x92997ed8
```

**Control interno que podía dar rojo y dio verde:** de los 1.101 símbolos distintos que exigen los 55 módulos, **cero tienen CRC contradictorio entre módulos**. Si mi parser estuviera leyendo basura, dos módulos habrían reportado CRC distintos para el mismo símbolo.

---

## 4 · El cruce, y el número que cuantifica "el KMI tiene generación"

```plain
exigidos por los 55 modulos reales del Pixel 8 : 1.101
presentes en mi kernel (6.6-android15)         :   828
AUSENTES de mi kernel                          :   273
con CRC IDENTICO                               :   275  (33,2%)
con CRC DISTINTO                               :   553
```

Ejemplos:

```plain
IGUAL  ___ratelimit          0x1d24c881
IGUAL  __check_object_size   0x88db9f48
DIST   __alloc_pages         pixel 0x7870d49b  vs  mio 0xa184bb4e
DIST   __arch_copy_to_user   pixel 0x9a85eebb  vs  mio 0x6cbbfc54
```

**Esto NO es un rojo del fragmento de SIAO: es un rojo de la GENERACIÓN.** Los dos brazos son kernels **de stock sin parchar**, uno 6.1 y otro 6.6. **El auditor tenía razón en su punto 2, y ahora tiene tamaño:** un DLKM de un dispositivo real solo carga en un kernel de **su** generación de KMI. 33,2% de coincidencia entre generaciones vecinas.

**Y hay un dato fino que refuerza el método:** 275 símbolos **sí** conservan su CRC entre 6.1 y 6.6. O sea que el CRC no cambia por versión sino **por cambio real de firma o de tipos**. Es el mismo mecanismo que midió F-004c, visto desde afuera.

---

## 5 · Un defecto mío, cazado leyendo la salida

El primer parser usó stride **72** (8 + `MODULE_NAME_LEN` que creí 64) y produjo basura verificable:

```plain
  pt_client_enable   0x3206d402
  o                  0x7665645f      <- 0x7665645f es ASCII '_dev'
```

**Estaba leyendo bytes del nombre como si fueran CRC.** El kernel define `MODULE_NAME_LEN = 64 - sizeof(unsigned long)` = **56**, o sea stride **64**. El control aritmético lo confirma: `3776 / 64 = 59` exacto; `3776 / 72 = 52,4`. **Lo cacé porque la salida cruda estaba a la vista** (R-08), no porque revisara el código.

---

## 6 · Lo que esto le hace al plan

1. **F-004 → F-004d se reapuntan a `android14-6.1`** si el objetivo es un Pixel. El arnés ya existe y `F004_RAMA` es una variable de entorno.
2. **Y hay que decidir el dispositivo objetivo ANTES de seguir**, porque define la rama. Eso es una decisión de producto, no técnica: Pixel → `android14-6.1`; un chino con MTK reciente → puede ser 6.6.
3. **Lo que NO se cae:** el mecanismo del padding KABI es independiente de la generación. `ANDROID_KABI_RESERVE` existe en las dos ramas, y `SYSVIPC` agrega los mismos 24 B. Habría que re-medirlo, no re-pensarlo.
4. **Y el método de F-007b es reusable:** con la URL de cualquier factory image, 6 MB de descarga dan el `vermagic` y los CRC exigidos. Sirve para **elegir** el dispositivo con datos.

---

## NO MEDIDO, declarado

- **Si un `.ko` del Pixel carga en un kernel 6.1 propio.** No compilé `android14-6.1` todavía. Eso es F-007c.
- **Si los 62 dispositivos del índice** incluyen alguno en 6.6: probé **tres**.
- **Los 12 módulos** de los 67 ELF que no tienen `.modinfo` + `__versions` parseables.
- **`komodo` falló** con `IndexError` en mi parser de central directory; no lo diagnostiqué.
- **El `.ko` carveado no se validó contra el archivo real del ext4:** lo saqué por búsqueda de magic ELF, no leyendo los inodos. Los CRC son consistentes entre módulos, lo que es evidencia fuerte, no prueba de integridad.
- **La licencia de los módulos** dice `GPL`, `GPL v2` y `Dual BSD/GPL`, o sea que su fuente **debería** estar disponible. No lo verifiqué.

--- METODO PROMETEO ---
Máquina: `brain-env` vía gateway (servicio `build`) + servicio `playwright`. Cero Actions.
Artefacto en git: este archivo.
Artefacto en ClickUp: Doc espejo enlazado en el cierre.
Instrumentos: `/workspace/f7e.py`, `f7f.py`, `f7g.py`, `f7h.py`, `f7i.py`, `f7j.py`.
