# F-007a: los 36 vendors de Google, 9.544 símbolos, y el 64% roto sin el parche

**Fecha:** 2026-09-06 · **Máquina:** **`brain-env`** por el gateway MUDH, servicio `build`, tool `run`. Más el servicio `playwright` (navegador real) para el índice de Google. **Cero Actions, cero compilación.**

**Evidencia cruda:** `/workspace/F-007a.txt` en el taller, más la tabla completa abajo. Instrumento: `/workspace/f7d.py`, md5 `4422862e963144800881046e8dc59d7c`.

---

## 0 · Leí el inventario antes de abrir la boca, y me cambió la máquina

Abraham me mandó a `00-ENTORNOS-Y-CAPACIDADES.md`. Lo leí, y tenía razón: **118,8 GiB libres en `/workspace`, egress abierto, `pip3` sin restricciones, y un servicio `playwright` con navegador real que no estaba usando.** Este falsador corrió entero en el taller. Cero runners gastados.

Lo que el taller **no** tiene, medido con `shutil.which` y no supuesto: `unzip`, `simg2img`, `debugfs`, `file`, `modinfo`, `xz`. Eso importa para la parte que quedó bloqueada.

---

## 1 · Por qué el `.ko` real no se midió, y no es una excusa técnica

El índice de factory images de Google **no tiene las URLs en el HTML**: `.zip` aparece **0 veces** en 75.132 bytes. Las carga por JS. Así que abrí el navegador real del gateway, y ahí apareció el muro:

```plain
tablas en la pagina : 0
botones             : [... "Reconozco" ...]
texto del acuerdo   : "Reconozco que lei y acepto los terminos y condiciones."
zips en el HTML     : 0
```

**Eso es una declaración legal a nombre tuyo, y no la firmo yo.** Es exactamente el mismo caso que el inventario ya declara para Kaggle: *"Aceptar las reglas de una competencia es acción humana: no hay endpoint y el navegador no tiene sesión"*. **Técnicamente podía hacer el click. Por método, no.**

**F-007b queda bloqueado por un click tuyo**, y cuando lo des el resto ya está pensado: el zip anidado se abre con `zipfile` de Python (no hace falta `unzip`), pero `vendor_dlkm.img` es sparse/EROFS y para eso **la máquina correcta es Actions x64**, que tiene `apt` y puede instalar `android-sdk-libsparse-utils` y `erofs-utils`.

**Y no cerré el problema ahí**, que es lo que el método pide: hay una vía que mide la misma pregunta y **es más fuerte**.

---

## 2 · Por qué esta variante es mejor que un `.ko` suelto

Un `.ko` individual usa **un puñado** de símbolos: mide un caso. Las listas `abi_gki_aarch64_<vendor>` son **el conjunto completo que Google le garantiza a ese vendor**, o sea el contrato entero. Medir contra las 36 listas es medir **todos los módulos posibles de todos los vendors a la vez**.

Y el hueco que deja, declarado: un `.ko` real trae además el **`vermagic`**, que estas listas no tienen. Esa mitad sigue NO MEDIDA.

---

## 3 · Lo medido

```plain
listas publicadas por Google en android/ : 38
listas parseadas                        : 36  (las 2 restantes son el .stg y allowed_breaks)
union de TODOS los vendors              : 9.544 simbolos unicos
baseline (GKI puro)                     : 17.233 simbolos exportados
siao (fragmento de 10, SIN parche)      : 17.236
```

### De lo que cada vendor EXIGE, cuánto le rompe SIAO sin el parche

| vendor | exige | presentes | FALTA | **CRC cambiado** |
|---|---|---|---|---|
| `abi_gki_aarch64_mtk` | 3.825 | 3.825 | **0** | **2.597** |
| `abi_gki_aarch64_pixel` | 3.375 | 3.375 | **0** | **2.095** |
| `abi_gki_aarch64_imx` | 2.909 | 2.909 | **0** | **2.152** |
| `abi_gki_aarch64_xiaomi_xring` | 2.832 | 2.832 | **0** | 1.769 |
| `abi_gki_aarch64_amlogic` | 2.733 | 2.733 | **0** | 1.861 |
| `abi_gki_aarch64_qcom` | 2.492 | 2.492 | **0** | 1.560 |
| `abi_gki_aarch64_exynos` | 2.490 | 2.490 | **0** | 1.621 |
| `abi_gki_aarch64_pixel_watch` | 2.463 | 2.463 | **0** | 1.601 |
| `abi_gki_aarch64_db845c` | 1.949 | 1.949 | **0** | 1.397 |
| `abi_gki_aarch64_siengine` | 1.883 | 1.883 | **0** | 1.251 |
| `abi_gki_aarch64_mtktv` | 1.853 | 1.853 | **0** | 1.251 |
| `abi_gki_aarch64_virtual_device` | 1.491 | 1.491 | **0** | 1.051 |

```plain
TOTAL sobre la union de los 36 vendors:
  exigidos por algun vendor       : 9.544
  presentes en el kernel baseline : 9.544
  AUSENTES del baseline           : 0
  con CRC CAMBIADO por el fragmento de 10 sin parche: 6.129  (64,2%)
```

---

## 4 · Los tres hallazgos

### 4.1 El GKI exporta **todo** lo que los 36 vendors piden: cero ausencias

**`FALTA = 0` en las 36 listas.** Eso responde y **desactiva** el riesgo que el auditor planteó en su punto 1: no hay ningún símbolo que un vendor necesite y el kernel no exporte. Y es coherente con lo medido en el ADR-005: **`TRIM_UNUSED_KSYMS` está apagado en el `gki_defconfig`**, así que no se recorta nada. El riesgo aparecería **al activarlo**, que es justo lo que D8 manda hacer con la lista del dispositivo objetivo.

### 4.2 El daño del fragmento sin parche ahora tiene tamaño de producto, no de reporte

Hasta ahora decía "10.867 CRC cambiados de 17.233 exportados". **Ese número no dice cuánto le importa a un fabricante.** Ahora sí: de los **3.375** símbolos que **Pixel** exige, el fragmento sin parche le rompe **2.095, el 62%**. Y a MediaTek 2.597 de 3.825. **Traducción: sin el parche, ningún teléfono de esos vendors carga sus drivers.**

### 4.3 Y el parche KABI lleva ese número a CERO, por lógica de conjuntos

F-004c midió **0 `CRC changed` en el reporte completo** de `stgdiff`, sobre los 17.233 símbolos. Los 9.544 de los vendors son un **subconjunto** de esos. **Si cero cambiaron en el total, cero cambiaron en el subconjunto.** No es interpolación: es contención de conjuntos.

| configuración | CRC roto de los 9.544 exigidos |
|---|---|
| fragmento de 10, sin parche | **6.129** (64,2%) |
| fragmento de 9 + parche KABI (F-004c) | **0** |

**Eso es lo que el parche compra, dicho en la unidad que importa.**

---

## 5 · Y un dato que cambia cómo se leen mis números viejos

```plain
abi_gki_aarch64  ->  3 simbolos
```

La lista **genérica** tiene tres símbolos; los miles están en las **por vendor**. Eso confirma la restitución del ADR-005 desde otro ángulo: mi criba original que dijo "3 protegidos, 2 tocados" **estaba bien**, y yo la anulé. La cifra honesta para hablar de KMI **no es 3 ni 17.233: es 9.544**, la unión de lo que los vendors reales exigen.

---

## NO MEDIDO, declarado

- **El `vermagic` de un `.ko` real.** Es la mitad que estas listas no cubren, y depende de tu click.
- **La generación de KMI del dispositivo objetivo.** Medí contra `android15-6.6` a la fecha de hoy; un teléfono concreto está en un tag `android15-6.6-YYYY-MM`. Sigue siendo matriz de builds, no bloqueador.
- **Si un `.ko` carga de verdad.** Esto mide **contrato de símbolos**, no `insmod`.
- **Las 2 listas que no parseé** (`.stg` binario y `allowed_breaks`).
- **Los CRC de F-004c no están commiteados** como `Module.symvers`: el cero viene del reporte de `stgdiff`, no de un cruce directo lista-por-lista. El cruce directo es una corrida más.

--- METODO PROMETEO ---
Máquina: `brain-env` vía gateway (servicio `build`) + servicio `playwright`. Cero Actions.
Artefacto en git: este archivo.
Artefacto en ClickUp: Doc espejo enlazado en el cierre.
Instrumento: `/workspace/f7d.py`, md5 `4422862e963144800881046e8dc59d7c`; salida en `/workspace/F-007a.txt`.
