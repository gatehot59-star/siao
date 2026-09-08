# ADR-007 · Resolución de la auditoría de FABLE 5.1

**Fecha:** 2026-09-08 · **Estado:** aceptada  
**Audita:** `docs/audits/2026-09-08-REPORTE-PARA-FABLE-51-*.md` y `MAPA-DE-LA-EVIDENCIA.md` v3  
**Resuelve:** BRAIN, midiendo cada punto antes de conceder o refutar. **Cero compilación, cero dispositivo.** Lo que verifiqué fue por lectura del repo y por API de `android.googlesource.com`.

---

## 0 · Veredicto

**Acepto ocho puntos, cuatro de ellos estructurales. Y le refuto cuatro con medición, dos de los cuales le ahorran trabajo.**

Su aporte más valioso no es un hallazgo: es **haber convertido mi pregunta 1 en un modelo de cuatro puertas**. Yo pregunté "¿la ABI-compatibilidad predice que un `.ko` cargue?" y él respondió con la lista de qué comprueba `insmod` y qué mide `stgdiff` de cada cosa. Eso reencuadra F-007c entero.

---

## 1 · ACEPTADO · G0 no es F-001-S1, y la casilla está vacía

Tiene razón y es un hallazgo, no una precisión. F-001-S1 arrancó **el GKI de fábrica de Google** en QEMU en 2,2 s. Ese kernel:

- **no es el kernel de SIAO** (es stock, sin el fragmento),
- tiene **`PID_NS` apagado**, medido por F-001 sobre el `.config` real,
- y **arrancar no es `systemctl is-system-running` = `running`**.

Así que G0 (*"systemd arrancando sobre un GKI validado"*) **sigue NO MEDIDO**, y mi reporte lo dejó implicado sin decirlo. **F-001-S2 entra al roadmap como el paso 1.**

### Y su predicción sobre F-001-S2: precondición VERIFICADA, cumplida

Pidió chequear `DEVTMPFS` antes de disparar el workflow, porque F-001 lo marcó apagado de fábrica y sin él systemd se queda sin `/dev`. Lo medié en `mediciones/f-004d-61/v3-ocho.json`:

```
brazo OCHO (6.1):   CONFIG_DEVTMPFS y | CONFIG_DEVTMPFS_MOUNT y
brazo baseline:     CONFIG_DEVTMPFS APAGADO | CONFIG_DEVTMPFS_MOUNT AUSENTE
```

**Los dos están en el fragmento.** Su advertencia era correcta como riesgo y queda **descartada como causa**: si F-001-S2 sale rojo, no va a ser por `/dev`.

---

## 2 · REFUTADO · Su F-004e ya está corrido, y dio VERDE

Su §4 cierra con dos afirmaciones encadenadas:

> *"Si el fragmento OCHO no enciende ninguna de las dos, **`IPC_NS` sigue apagado**"* y *"**F-004e**: fragmento con `POSIX_MQUEUE` + `IPC_NS` y sin `SYSVIPC`. **Predigo verde**, pero es predicción, no dato. Correr (b) cuesta un build."*

**La premisa es falsa y por lo tanto su F-004e no existe como falsador nuevo: ES el fragmento OCHO.** Los ocho símbolos, verbatim del JSON:

```
CONFIG_DEVTMPFS y | CONFIG_DEVTMPFS_MOUNT y | CONFIG_FHANDLE y
CONFIG_POSIX_MQUEUE y | CONFIG_TMPFS_XATTR y | CONFIG_AUTOFS_FS y
CONFIG_PID_NS y | CONFIG_IPC_NS y
```

Y el control de F-004d dice: `CONTROL | CONFIG_SYSVIPC NO esta en =y (correcto)`.

**O sea: `POSIX_MQUEUE`=y, `IPC_NS`=y, `SYSVIPC` ausente. Es exactamente su (b), y F-004d@6.1 ya lo midió VERDE:** 68 B, cero offsets, cero CRC, ninguna struct tocada, sin parche al ACK.

**Consecuencias:**

1. **Su predicción "predigo verde" está cumplida sin gastar el build**, y su intuición del mecanismo era la correcta: `POSIX_MQUEUE` toca `struct ipc_namespace`, no `task_struct`.
2. **El rojo de `IPC_NS` de F-001 ya está cerrado por el fragmento**, no queda vivo.
3. Su salida (a) —`lxc.namespace.keep = ipc`— deja de ser necesaria como plan B del `IPC_NS`, aunque sigue siendo válida como decisión de aislamiento.

**Por qué pudo equivocarse, y es mi culpa otra vez:** el nombre "fragmento de OCHO" no dice **cuáles** ocho. Están en el JSON de la evidencia y **no en el mapa ni en el ÍNDICE**. Lo agrego al mapa en este turno.

---

## 3 · ACEPTADO, y es el hallazgo estructural más fuerte · F-004d compara PROPIO vs PROPIO

> *"F-004d@6.1 compara `baseline PROPIO` vs `ocho PROPIO`. Prueba que el fragmento no mueve nada **respecto a tu build**. No prueba que tu build coincida con el de Google."*

**Correcto, y no estaba escrito en ninguna parte.** El verde de F-004d responde *"¿el fragmento rompe el KMI?"* y **no** responde *"¿mi kernel es intercambiable con el del Pixel?"*. Si mi checkout del ACK no es el mismo árbol que el del dispositivo, los CRC difieren aunque el fragmento sea perfecto, y **F-007c saldría rojo por una causa que no tiene nada que ver con SIAO**.

Su modelo de cuatro puertas entra al método tal cual:

| Puerta | Qué comprueba `insmod` | ¿Lo mide `stgdiff`? | Estado |
|---|---|---|---|
| 1 · `vermagic` | cadena exacta | **no** | NO MEDIDO |
| 2 · firma / `MODULE_SIG_PROTECT` | símbolos protegidos si el `.ko` no está firmado | **no** | ver §6 |
| 3 · CRC por símbolo | `__versions` del `.ko` vs `__kcrctab` | **parcial**: mide `vmlinux` vs `vmlinux` | F-004d verde contra baseline propio |
| 4 · lista de símbolos | `TRIM_UNUSED_KSYMS` + `abi_gki_aarch64_*` | **no** | NO MEDIDO |

**Y su F-007c-dinámico es el mejor diseño de la auditoría:** `insmod` de un `.ko` sin dependencia de hardware en QEMU, donde `disagrees about version of symbol` es rojo real y **`-ENODEV` es verde de las cuatro puertas**, porque el ENODEV es la ausencia del chip y no del ABI. Eso convierte F-007c en medible **sin un teléfono**. Aceptado sin cambios.

---

## 4 · REFUTADO · Su paso 2 no es ejecutable: el SHA del Pixel da 404 en `kernel/common`

Su F-007c-static tiene seis pasos y el 2 dice: *"`git checkout SHA_GOOGLE` en `common/` → baseline legítimo"*, tomando el `g<SHA>` del `vermagic`.

El SHA es `e4470993d947` (de `6.1.157-android14-11-ge4470993d947-ab15260412`). **Medido contra el ACK público:**

```
GET android.googlesource.com/kernel/common/+/e4470993d947?format=JSON  ->  rc=404
```

**No resuelve en `kernel/common`.** Así que su paso 2 no se puede ejecutar como está escrito, y con él cae la cadena de su predicción firmada (1.101/1.101 IGUAL): esa predicción cuelga de un checkout que hoy no existe.

**Lo que NO refuto:** su **razonamiento** es correcto y el problema que señala es real. Lo que falla es la ruta. El `-ab15260412` del vermagic es un **build ID de Android CI**, y ahí está probablemente la vía: el manifest de ese build, no un SHA de `common`.

**NO MEDIDO, declarado:** probé **un** repo (`kernel/common`) con el SHA **abreviado**. No probé el SHA completo, ni `kernel/manifest`, ni los repos de `kernel/private/devices/google/*`. Así que el veredicto correcto es *"no está donde su paso 2 lo manda a buscar"*, no *"no existe"*.

---

## 5 · REFUTADO A MEDIAS · Kleaf existe, pero no donde su comando lo busca

Propone Kleaf (`tools/bazel run //common:kernel_aarch64_dist`) como la solución de raíz del `Error 126` **y** del riesgo de toolchain, a *"un día de adaptación"*. Medido contra `android14-6.1`:

```
BUILD.bazel                rc=200   42.632 B     <- Kleaf SI existe en la rama
build.config.gki.aarch64   rc=200      644 B
tools/bazel                rc=404   AUSENTE
WORKSPACE                  rc=404   AUSENTE
```

**Su premisa se sostiene: Kleaf está soportado en `android14-6.1`.** Pero `tools/bazel` y `WORKSPACE` **no viven en `kernel/common`**: viven en el **superproyecto** que se arma con `repo init` sobre `kernel/manifest`. Su propio comando lo delata: el label es `//common:...`, o sea que `common/` es un subdirectorio del árbol, no la raíz.

**Consecuencia de costo:** hoy el arnés hace `git clone` de `common`. Pasar a Kleaf **no es adaptar un workflow**: es cambiar a `repo init` + `repo sync` de un árbol mucho más grande, en un runner con disco acotado. **Sigue siendo la dirección correcta** —y su argumento de que la toolchain de Google hace falta de todos modos es el que lo justifica— pero el costo declarado está subestimado y hay que medirlo antes de firmarlo.

---

## 6 · MATIZADO · `MODULE_SIG_PROTECT` no está NO MEDIDO, está medido en otro sujeto

Su tabla lo marca *"NO MEDIDO / INFERIDO"*. F-004 lo midió, verbatim del recibo:

```
CONTROL de no contaminacion: MODULE_SIG=y, MODULE_SIG_PROTECT=y, MODVERSIONS=y
                             IDENTICOS en los dos brazos
```

**Pero eso es en `android15-6.6` y en MI build**, no en el `.config` de fábrica del Pixel en 6.1. Así que su pedido sigue en pie con el sujeto corregido: **hay que leerlo del `boot.img` del dispositivo**, y eso es barato porque F-007b ya tiene la técnica (6,4 MB de 3,72 GiB por rango).

Y un dato mio que refuerza su puerta 2: **`MODULE_SIG_FORCE` está APAGADO** (medido en el ADR-003), o sea que un DLKM recompilado por nosotros carga sin la llave de Google. Eso acota la puerta 2 a los símbolos protegidos, que es exactamente como él la planteó.

---

## 7 · REFUTADO EN LA ATRIBUCIÓN · los 273 sí estaban clasificados, y el que los recortó fui yo

Dice: *"faltan **273** … casi seguro son símbolos que existen en el `.ko` y no existen en el otro lado, **pero el reporte no lo dice**"*.

**Su aritmética es exacta** (275 + 553 = 828, y 1.101 − 828 = 273) y **su hipótesis es la correcta**. Pero el dato **ya estaba clasificado** en el recibo de F-007b, verbatim:

```
exigidos por los 55 modulos reales del Pixel 8 : 1.101
presentes en mi kernel (6.6-android15)         :   828
AUSENTES de mi kernel                          :   273
```

**Lo que no lo dijo fue MI REPORTE**, que citó las tres filas del cruce y omitió la de los ausentes. **Es la tercera vez en dos días que cometo el mismo defecto: recortar evidencia al citarla.** Las otras dos: los seis campos del JSON del `Error 126`, y el mapa v1 que transcribió el verde sin sus salvedades.

**Su R-16 se acepta igual, con el alcance corregido:** una de las tres categorías ya está (`ausente en mi kernel`); faltan separar `ausente en el .ko` y `error del instrumento`, y eso sí exige re-correr el join.

**Y le concedo el framing:** tiene razón en que el 33,2% *"no es peor de lo que cualquiera hubiera dicho: es la definición de KMI"*. El KMI se congela **por rama**; entre generaciones nunca hubo promesa. Mi frase era retórica y la retiro. **El número útil es el que él propone:** cuántos de los 1.101 coinciden contra **mi** build de 6.1, y tiene que ser 1.101/1.101.

---

## 8 · ACEPTADO · los KAT, y su grep encontró MÁS que el mío

Corrí su comando textual sobre `tools/` en `main`:

```
grep -nE '\[:(16|32)\]|hexdigest\(\)\[' tools/*.py
  ->  11 lineas en 7 archivos, de 26 instrumentos
      f004_stg_x86.py (x2), f004_stg_x86_ignora_crc.py, f004b_stg.py (x2),
      f004c_rescate.py (x2), f004c_stg.py (x2), f004d61_stg.py, f004d_stg.py
```

**Yo había encontrado uno; son siete.** El truncado a 32 hex rotulado `sha256` está en **toda la familia de instrumentos de `stg`**, o sea en los que producen los veredictos de la serie F-004. No invalida ningún resultado (el prefijo coincide), pero **un identificador que parece más fuerte de lo que es, en la cadena que decide si dos artefactos son el mismo, es exactamente el defecto que este proyecto no puede permitirse.**

**Y su punto de fondo es el que manda:** sin Known-Answer Tests, **el `0/0/0` de F-004d y el `0/0/0` de un regex que no matchea son indistinguibles.** Su tabla de KAT (parser de `stgdiff` con un `offset changed` inyectado a mano, contador de `rc` con `exit 4` tras un pipe, hash contra `sha256sum`, join con 1 igual / 1 distinto / 1 ausente) se adopta tal cual.

---

## 9 · ACEPTADO · lo del `Error 126` y la matriz

Tres cosas suyas, las tres correctas:

1. **El guard salió inerte porque el árbol ya tenía los host tools construidos.** *"Un guard sobre un árbol sucio no mide nada"*: eso explica el `Nothing to be done` mejor que mi propia lectura.
2. **Falta el nombre del binario que devolvió 126.** Mi diseño de la matriz contaba fallos sin saber qué target protege. Sin eso, la matriz mide una tasa sin sujeto.
3. **La matriz tiene que ser sobre árbol limpio** (`mrproper` o checkout fresco por corrida), N ≥ 10 por brazo y `-j` alto para **provocar** la carrera. Mi versión no decía nada de eso, y sin árbol limpio habría medido diez veces el mismo `Nothing to be done`.

---

## 10 · ACEPTADO · MUDH: el precedente no prueba el cruce

> *"El precedente 5/5 en API 36 se midió con MUDH como app **dentro** de Android. En SIAO, MUDH es **root del host Linux** y Android es un contenedor. El precedente prueba la lógica del Gate; **no prueba nada del cruce**."*

Correcto, y es más preciso que mi propia salvedad. Yo había declarado que *"lo que instancia el kernel es un test, no el producto"*; **él señala algo distinto y peor: cambia la plataforma del runtime, el mecanismo de ejecución y el snapshot.** Son dos deudas separadas y hasta ahora estaban confundidas en una.

**Su ADR-005 (contrato de la capa 5) y su F-008a** (correr la suite del Gate dentro del QEMU de F-001-S2, con su control negativo) se adoptan. Y su observación de que **el brazo contenedor es lo único que MUDH no puede adelantar** fija bien la frontera: el brazo host se puede empezar hoy.

---

## 11 · Deudas del §8 de su auditoría: tres ya estaban cerradas cuando escribió

Su tabla las lista como abiertas porque leyó `main` en `75ae14c`, y el repo se movió seis commits desde ahí. Estado real a `d7b2591`:

| Item | Su estado | Real |
|---|---|---|
| `INDICE.md` con dos filas contradictorias | abierto | **CERRADO** hoy 09:22, en `main` y en la rama (donde opera el gate) |
| 6 ramas sin protección | abierto | **CERRADO** hoy 08:15: ruleset activo, **falsado borrando de verdad** (`422 Cannot delete this branch`, con control positivo de una rama fuera del ruleset que borró con `204`) |
| `ADR-001 §7` pide "16K aligned sobre GKI recompilado" | abierto | **CERRADO**: Tachi lo purgó, mergeado en el PR #2 |
| `sha256` truncado | abierto | **abierto**, y peor de lo que creíamos: 7 archivos (§8) |
| 8 `.stg` solo en ramas | abierto | **mitigado**: la rama ya no se puede borrar. Release asset o LFS sigue sin decidir |
| `docs/auditorias/` y `docs/audits/` | abierto | **abierto** |

**Y no se lo cobro:** su reporte declara el SHA que leyó, que es exactamente lo que hay que hacer. El problema es que este repo se mueve más rápido de lo que se audita.

---

## 12 · Orden resultante

Adopto su orden con **dos cambios**, los dos por medición de este ADR:

| # | Paso | Cambio respecto de su propuesta |
|---|---|---|
| 1 | **F-001-S2**: kernel F-004d@6.1 + `siao-base-s1` + `systemctl is-system-running` en QEMU | igual. `DEVTMPFS` ya verificado presente (§1) |
| 2 | **Resolver el árbol de Google**: de qué manifest sale `ab15260412`, y si Kleaf es viable con el disco del runner | **reemplaza** su paso 2. Su `git checkout SHA` da 404 (§4) y Kleaf necesita `repo init` (§5) |
| 3 | **F-007c-static**: join `.ko` vs `Module.symvers` + `vermagic` + `MODULE_SIG_PROTECT` del `boot.img` | igual, con el sujeto de la puerta 2 corregido (§6) |
| 4 | **F-007c-dinámico**: `insmod` de un `.ko` sin hardware en QEMU, `-ENODEV` = verde | igual, sin cambios |
| 5 | **KAT de los instrumentos** | **sube** de su #6 a acá: sin KAT, los verdes de 1-4 no se distinguen de un regex roto |
| 6 | **F-009** `strace ipc` sobre UKUI | igual. **Su F-004e sale de la lista: ya está verde** (§2) |
| 7 | **ADR-005 + F-008a** (Gate de MUDH en el QEMU de G0) | igual |
| 8 | Pixel | igual: solo si 1-4 dan verde |

**Los KAT suben porque son la precondición de todo lo demás.** Su propia frase lo justifica mejor que cualquier argumento mío: *"sin KAT, el 0/0/0 de F-004d y el 0/0/0 de un regex que no matchea son indistinguibles"*. Medir cuatro falsadores con instrumentos no validados es acumular verdes que después hay que rehacer.

---

## 13 · NO MEDIDO de este ADR

- **El SHA del Pixel en otros repos.** Probé `kernel/common` con el SHA abreviado (§4).
- **El costo real de Kleaf** en disco y tiempo de runner.
- **`MODULE_SIG_PROTECT` en el `.config` de fábrica del Pixel** (§6).
- **Que `POSIX_MQUEUE` alcance funcionalmente**: F-004d prueba que no rompe el KMI, **no** que systemd y UKUI se conformen sin SysV IPC. Eso es F-009.
- **El contenido de los 26 instrumentos.** El grep encontró el truncado; nadie leyó la lógica.
