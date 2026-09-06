# F-004 MEDIDO: el fragmento rompe el KMI, y la causa es UNA sola opción

**Fecha:** 2026-09-06 · **Máquinas:** GitHub Actions **arm64** (`ubuntu-24.04-arm`, runners `1000002044` y `1000002045`) para los dos kernels; **x86** (`ubuntu-24.04`, runner `1000002048`) para `stg`/`stgdiff`. `brain-env` para los pre-vuelos.

**Veredicto: ROJO, y por primera vez con el instrumento oficial de Google, no con un sustituto.**

---

## 1 · Lo que corrió, con números

```plain
rama android15-6.6 (VERSION 6 PATCHLEVEL 6 SUBLEVEL 142)
baseline: gki_defconfig puro          -> los 10 simbolos APAGADOS o AUSENTES
siao    : gki_defconfig + fragmento   -> merge_config rc=0, los 10 en =y
CONTROL de no contaminacion: MODULE_SIG=y, MODULE_SIG_PROTECT=y, MODVERSIONS=y
                             IDENTICOS en los dos brazos
build baseline: OK  vmlinux 173.481.992 B | 97 modulos
build siao    : OK  vmlinux 174.758.944 B | 97 modulos
```

**El fix del arnés funcionó, y era el que yo predije contra el auditor:** `HOSTCFLAGS=-DUSE_PKCS11_ENGINE` compiló los dos brazos. Con `-DOPENSSL_NO_ENGINE` (su vía A) el error habría cambiado de forma, porque la guarda de `key_pass` es la otra. **Predicción declarada antes de correr, cumplida.**

---

## 2 · `stgdiff` real: rc=4, y el reporte pesa 1,5 MB

```plain
stg      4.944.792 B | sha256 b8cf4364c4e7da8b57362afd817e6976
stgdiff  5.000.176 B | sha256 1c74def7edaa8222d4aed2c26ea42f81
libc++   1.306.352 B | sha256 7b91de1cba2ad902aad871b77e58af40

baseline.stg 11.317.742 B | sha256 440f48ed6759f80e7f97eabcc09efc6f
siao.stg     11.319.347 B | sha256 7d91aa2b9f9dc46224958b238be943b7

stgdiff --stg baseline siao --format small  -> rc=4
reporte: 1.521.915 B | 'CRC changed' x 10.867 | 'was added' x 5
```

**Y el primer intento fue NO MEDIDO por una razón que no era el ELF:** `rc=127`, *"error while loading shared libraries: libc++.so"*, en las **tres** formas de invocación. O sea que el binario no arrancaba. La `libc++` vive en el **mismo** prebuilt (`linux-x86/lib64/libc++.so`). El guard reportó NO MEDIDO en vez de "el ELF está mal": tres estados, no dos.

---

## 3 · La segunda pasada es la que decide, y evita el veredicto ambiguo

10.867 CRC cambiados admitían dos lecturas con costos muy distintos: **solo CRC** (el DLKM de stock no carga, pero recompilado sí) o **también tipos** (el layout cambió y recompilar no alcanza). El propio `--help` de `stgdiff` trae la separación, así que la medí:

```plain
stgdiff --ignore linux_symbol_crc  -> rc=4
reporte SIN CRC: 15.221 B | 335 lineas   (contra 1.521.915 B con CRC)
```

**No está vacío. Y esto es la causa raíz, verbatim:**

```plain
type 'struct task_struct' changed
  member 'struct sysv_sem sysvsem' was added
  member 'struct sysv_shm sysvshm' was added
  member 'unsigned long last_switch_count' changed
    offset changed from 16960 to 17152
  member 'struct nsproxy* nsproxy' changed
    offset changed from 17280 to 17472
  ... (todo lo que sigue, corrido +192 bits)
```

**`CONFIG_SYSVIPC` agrega dos miembros a `struct task_struct` y corre 24 bytes TODO lo que viene después.** `task_struct` es la estructura más referenciada del kernel: de ahí salen los 10.867 CRC. **No es una cascada cosmética: son offsets reales.**

Y tres símbolos nuevos, aditivos: `put_pid_ns`, `pids_cgrp_subsys_enabled_key`, `pids_cgrp_subsys_on_dfl_key`.

---

## 4 · Qué significa para SIAO, y es peor que "hay que compilar el kernel"

Ya sabíamos que había que construir GKI propio. **Lo nuevo y medido:** un **DLKM binario de vendor**, compilado contra el GKI de stock, **no es reutilizable** sobre este kernel. No por la firma (`MODULE_SIG_FORCE` está apagado) ni por el CRC (eso se arregla recompilando): **por offsets de `task_struct`**, y recompilar exige **fuente del vendor**, que es exactamente lo que no se tiene.

Eso golpea el corazón del ADR-001, que apuesta a **reutilizar los binarios de `/vendor` tal cual**.

---

## 5 · Las tres salidas, y ninguna está medida todavía

1. **Sacar `SYSVIPC` del fragmento.** Es la única de las 10 opciones que toca `task_struct` (hipótesis, no medida). systemd no requiere SysV IPC; sí lo requiere software de escritorio que use `shmget`/`semget`. Costo: cero para el KMI, riesgo en userland.
2. **Padding estilo Android:** meter los miembros nuevos en el espacio reservado (`ANDROID_KABI_RESERVE`) en vez de dejar que crezca la struct. Es lo que hace Google para no romper su propio KMI. Costo: un parche al ACK, no un fragmento.
3. **Aceptar el rojo** y compilar los DLKM desde fuente. Requiere fuente del vendor: **para la mayoría de los SoC no existe públicamente.**

---

## 6 · El falsador que sigue, y por qué es el barato

**F-004b: bisecar el fragmento.** Diez opciones, y la sospecha medida es que **una sola** mueve `task_struct`. Si se confirma, el fragmento se parte en "KMI-safe" y "KMI-breaking", y la decisión de producto pasa a ser sobre **una** opción en vez de sobre diez. Dos builds arm64, mismo arnés, cero herramientas nuevas.

## NO MEDIDO, declarado

- **Cuál de las 10 opciones mueve `task_struct`.** Sospecho `SYSVIPC` por los nombres de los miembros; **no está aislado.**
- **Los "3 símbolos protegidos por Google"** de la criba son un **defecto de mi parser**, no un dato: el archivo `android/abi_gki_aarch64` no se parsea con mi regla de una-línea-un-símbolo. La lista real tiene miles. Ese número queda anulado.
- Si el padding `ANDROID_KABI_RESERVE` alcanza para `sysv_sem` + `sysv_shm`.
- F-002 (c) firmas, F-001-S1 boot, F-003, F-005, F-006: sin cambios.

--- METODO PROMETEO ---
Máquinas: Actions arm64 (dos kernels) + Actions x86 (stg/stgdiff) + `brain-env`.
Evidencia cruda en la rama `titan/f-004-kmi`: `mediciones/f-004-v3/F-004-STGDIFF.txt`, `F-004-SIN-CRC.txt`, `F-004-abi.report` (1,5 MB), `F-004-abi-sin-crc.report`, `baseline.stg`, `siao.stg`, `F-004-v3.json`, `F-004-v3.md`.
Artefacto en ClickUp: Doc espejo enlazado en el cierre.
