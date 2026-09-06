# Reporte para auditoría: las últimas CINCO entregas de SIAO

**Fecha:** 2026-09-06 · **Pedido literal:** *"haz un reporte de todo lo que hiciste en estas últimas 5 entregas, para que audite"*.

**Criterio de selección, declarado:** las cinco últimas entregas **que produjeron una medición o una decisión**. Los acks y los resúmenes en criollo no cuentan como entrega. Van de la auditoría de origen de F-002 hasta F-004.

**Máquinas usadas en las cinco:** GitHub Actions **arm64** (`ubuntu-24.04-arm`, aarch64 nativo) para todo lo que compila o construye rootfs; `brain-env` por el gateway para lecturas, índices apt y pre-vuelos. **Cero QEMU ejecutado en las cinco. Cero hardware.**

---

## Tabla de las cinco

| # | Entrega | Veredicto | Quién quedó refutado |
|---|---|---|---|
| E-1 | Auditoría de origen del rootfs (57 de `-proposed`) | Parcial + defecto propio medido | Yo (mi parser de índices) |
| E-2 | F-002 v5: pre-vuelo | Rojo del arnés | El auditor en un punto, y yo en otro |
| E-3 | F-002 v6: la hipótesis del layout flat | **FALSA**, y el control por fin discriminó | Yo |
| E-4 | **F-002 CERRADO**: `siao-base-s1` = `main` + 3 paquetes | **VERDE (a) y (b)**, ROJO declarado en (c) | Mis seis diagnósticos previos |
| E-5 | F-004 KMI por `Module.symvers` | **NO MEDIDO**, con causa ya medida | Yo, dos veces |

---

## E-1 · Auditoría de origen: 57 paquetes de `-proposed`, y mi auditor tenía un defecto

**Pedido:** *"pues audita el origen"*.

**Medido:** el rootfs que se construía traía **57 paquetes de `huanghe-proposed`**, o sea que el snapshot no era "main + 3" como yo quería creer. **Y el propio auditor tenía un defecto medido:** mi parser de índices usaba `setdefault`, así que se quedaba con la **primera** versión que veía; **750 de 11.837 paquetes de `main` tienen más de una versión**, y esos quedaban mal clasificados. Por eso la auditoría definitiva no la hizo mi parser sino **`apt-cache policy` desde adentro del chroot**.

**Archivo:** `docs/agents/respuestas/2026-09-06-02-audite-el-origen-57-de-proposed-y-mi-auditor-tiene-un-defecto-medido.md`

**Error propio:** escribí un instrumento nuevo cuando el sistema ya traía el instrumento correcto. Es el patrón de "la respuesta estaba en el archivo, no en una corrida".

---

## E-2 · F-002 v5: el pre-vuelo refuta al auditor, y el runner me refuta a mí

**Medido en pre-vuelo, antes de gastar runner:** dos de las piezas que se daban por buenas no lo eran. Después el runner **me refutó a mí**: mi fix propuesto no produjo el rootfs.

**Archivo:** `docs/agents/respuestas/2026-09-06-03-f-002-v5-el-pre-vuelo-refuta-al-auditor-y-el-runner-me-refuta-a-mi.md`

**Valor real de esta entrega:** cacé defectos **antes** de la máquina. Es la única de las cinco donde el ahorro es medible en minutos de cuota.

---

## E-3 · F-002 v6: mi sospecha del layout flat era FALSA

**Medido:** el repo overlay **no** fallaba por ser flat ni por faltarle `Release`. Las dos eran mis hipótesis y las dos cayeron. Lo importante de esta entrega es lo otro: **el control empezó a discriminar**, o sea que dejó de auto-aprobarse.

**Archivo:** `docs/agents/respuestas/2026-09-06-04-v6-mi-sospecha-del-layout-es-FALSA-y-el-control-por-fin-discrimino.md`

---

## E-4 · F-002 CERRADO: el rootfs existe y la base es `main` + TRES paquetes

**Medido en Actions arm64 (`runner_id 1000002033`, 79,8 s):**

```plain
rc=0 · 177 paquetes · 248 MiB
ORIGEN por apt-cache policy DENTRO del chroot:
   huanghe/main       174
   OVERLAY-SIAO         3
   huanghe-proposed     0      <-- CERO
systemd 255.2-ok2.8 de huanghe/main (el del release oficial, no el 259.5 sin QA)
```

**`siao-base-s1` = `main` + 3 paquetes:** `libdevmapper1.02.1 2:1.02.205-ok1`, `libgcrypt20 1.12.1-ok1`, `libgpg-error0 1.59-ok1`. De 57 a 3.

**La causa era UNA palabra, y el control discrimina:**

```plain
copy://  -> instalo=True,  rc=0
file://  -> instalo=False, rc=25 ("not accessible from chroot directory -- use copy:// instead of file://")
```

Misma orden, mismo overlay, única variable: cuatro letras. **Y `mmdebstrap` tenía escrita la solución en la salida que yo venía recortando con `tail`.**

**Archivo:** `docs/agents/respuestas/2026-09-06-05-F-002-CERRADO-siao-base-s1-es-main-mas-TRES-paquetes.md`

**NO MEDIDO, declarado:** (c) **firmas** sigue ROJO porque todo se construyó con `trusted=yes` y la huella de la llave no se verificó contra una fuente independiente del mismo mirror (R-07). **Si el rootfs ARRANCA** tampoco está medido: F-002 mide que se construye, no que bootea. Eso es F-001-S1.

**Errores propios en esta línea, contados:** seis versiones diagnosticando mal (`main`/`proposed` inconsistentes → falso; falta `Release` → falso; layout flat → falso). Y lo que encontró la causa **no fue una hipótesis mejor: fue dejar de recortar la evidencia antes de leerla.**

---

## E-5 · F-004 (KMI): NO MEDIDO, y ahora la causa está medida

**Pedido:** *"Corré F-004 con el método alternativo"*, y después *"extraé el primer error real del build ARM64"*.

### Por qué el método alternativo, medido en pre-vuelo

```plain
abi_gki_aarch64.stg de android15-6.6  -> EXISTE, 8.014.732 B decodificado, empieza version: 0x00000002
stgdiff: 5 vias probadas, 5 fallaron (google/stg 404, /tags 404, prebuilts 404 x2,
         paquete 'stg' ausente en ubuntu-ports arm64)
```

La **referencia** está; la **herramienta** no. Así que `stgdiff` queda **NO MEDIDO por falta de instrumento**, declarado, y el sustituto mide la misma pregunta con el enforcer real que ya había medido en el `.config` del GKI: **`CONFIG_MODVERSIONS=y`**, o sea que un cambio de layout no da un diff, da **un módulo que no carga** porque el CRC no coincide. Los CRC viven en `Module.symvers`.

### Qué corrió, con números

Dos jobs paralelos en `ubuntu-24.04-arm` sobre `android15-6.6` (`VERSION 6 PATCHLEVEL 6 SUBLEVEL 142`), árbol bajado por `+archive` (238.722.440 B, sha256 `3dac554d...`), mismo `clang 18.1.3` en los dos brazos.

```plain
baseline: gki_defconfig puro -> los 10 simbolos del fragmento APAGADOS o AUSENTES
siao    : gki_defconfig + fragmento -> merge_config rc=0, los 10 en =y
build baseline: rc=2 en 276,3 s · Module.symvers presente: False
build siao   : rc=2        · Module.symvers presente: False
```

### La causa REAL del `rc=2`, verbatim del runner

```plain
  CC      certs/system_keyring.o
  HOSTCC  certs/extract-cert
/tmp/f004/ack/certs/extract-cert.c:152:7: error: use of undeclared identifier 'key_pass'
  152 |                 if (key_pass)
      |                     ^
/tmp/f004/ack/certs/extract-cert.c:153:42: error: use of undeclared identifier 'key_pass'
  153 |                         ERR(!ENGINE_ctrl_cmd_string(e, "PIN", key_pass, 0), "Set PKCS#11 PIN");
2 errors generated.
make[4]: *** [scripts/Makefile.host:114: certs/extract-cert] Error 1
make[3]: *** [scripts/Makefile.build:480: certs] Error 2
```

**Lectura, marcada como conclusión y no como medición:** el que no compila **no es el kernel, es una herramienta de host** (`HOSTCC certs/extract-cert`), y revienta contra el `libssl-dev` de Ubuntu 24.04 por el bloque `ENGINE`/PKCS#11. **No tiene relación con el fragmento de SIAO:** apareció **idéntico en los dos brazos**, incluido el baseline sin tocar. O sea: **esto no dice nada, ni bueno ni malo, sobre el KMI.**

**Archivos commiteados (rama `titan/f-004-kmi`):** `mediciones/f-004/F-004-PRIMER-ERROR.txt`, `mediciones/f-004/f004-baseline-build.txt` (106.406 B, log completo), `f004-baseline-bitacora.txt`, `f004-baseline-defconfig.txt`, `f004-siao-merge.txt`, `F-004.json`, `F-004.md`, más `tools/f004_kmi.py` y `.github/workflows/f-004-kmi.yml` y `.github/workflows/f-004-primer-error.yml`.

### Mis dos errores de esta entrega, medidos

1. **Volví a recortar la evidencia.** El instrumento corría el build con `2>&1 | tail -40`, así que las **2.501 líneas** anteriores al error se tiraban y el resumen mostraba un `make Error 2` sin causa. **Es el mismo defecto que en F-002 me costó seis versiones, cometido al día siguiente de escribir la lección.** Ese pipe además hacía que `rc` fuera el de `tail`, no el del build: en la primera corrida el archivo dice `rc=0` sobre un build que falló.
2. **El brazo `siao` del relanzamiento no se volvió a medir.** Su log commiteado sigue siendo el viejo de 1.467 B con `tail`, o sea que **el `rc=2` del brazo con fragmento es del intento anterior, no del corregido.** Lo declaro NO MEDIDO en vez de presentar los dos brazos como si fueran de la misma corrida.

### Lo que sigue, y por qué

La vía barata es **desactivar la firma de módulos en LOS DOS brazos por igual** (`CONFIG_MODULE_SIG=n`), porque `extract-cert` solo existe para firmar y **los CRC de `Module.symvers` no dependen de la firma**: la comparación sigue siendo válida si la variable se aplica a los dos. Alternativa si eso mueve algún símbolo: usar el `clang` prebuilt de Google en vez del del runner. **Ninguna de las dos está medida todavía.**

---

## Cómo auditarme, concretamente

1. **El log completo de F-004 está commiteado**, no resumido: `mediciones/f-004/f004-baseline-build.txt`, 106.406 B, con el error en la línea 2.501. Si mi lectura de "herramienta de host, no kernel" es falsa, el archivo la desmiente.
2. **El origen del rootfs es recomputable**: `apt-cache policy` dentro del chroot, no mi parser.
3. **Lo que NO tiene evidencia y lo digo yo primero:** el brazo `siao` de F-004 corregido, las firmas de `siao-base-s1`, el boot del rootfs, F-003 (16K), F-005 (AppFunctions) y F-006 (LSM/KMI).
4. **Incumplimiento de método que declaro:** F-004 no tenía archivo de respuesta en `main` hasta este reporte; su evidencia vivía solo en la rama.

--- METODO PROMETEO ---
Máquinas: GitHub Actions arm64 (`ubuntu-24.04-arm`) y `brain-env` vía gateway.
Artefacto en git: este archivo.
Artefacto en ClickUp: Doc espejo enlazado en el cierre del chat.
