# 2026-09-05 · FALSADOR-001: la premisa base de SIAO es VERDE, y mi instrumento falló dos veces

## 1. Pedido literal

> "Corré el falsador del userland en Actions arm64"

Hecho. Corrió en **aarch64 nativo** de GitHub Actions, tres veces (v1, v2, v3), con
un job x64 en paralelo como control de instrumento.

## 2. Veredicto

| Pregunta | Veredicto | Número |
|---|---|---|
| **A** · ¿los binarios arm64 de openKylin 3.0 alinean a páginas de 16 KB? | **VERDE** | `p_align = 65536` en los 146 ELF, sin excepción |
| **B** · ¿ese userland ejecuta en un aarch64 ajeno, fuera de su ISO? | **VERDE** | `bash 5.3.9 aarch64` en chroot leyendo su propio `os-release` |

**A importa porque 65536 es múltiplo de 16384.** Un binario alineado a 64 KB carga
en kernels de páginas de 4 KB, 16 KB y 64 KB. O sea: **no hay que recompilar el
userland** para los dispositivos Android 15+ de páginas grandes, que era el riesgo
que el ADR-001 declaraba en su tabla y que costaba una variante entera de la distro.

**B importa porque es la premisa de la que cuelga el proyecto.** Si el userland de
openKylin solo viviera adentro de su ISO, la opción C del ADR-001 no existía.

## 3. Evidencia cruda, verbatim (arm64, run 33988392695)

```plain
maquina: {"arch": "aarch64", "nproc": 2, "kernel": "6.17.0-1022-azure", "pagesize": 4096,
          "runner_os": "Linux", "runner_arch": "ARM64", "github_run_id": "33988392695"}
ELF medidos: 146 | arquitecturas: ['aarch64']
ALINEACIONES CRUDAS observadas (p_align de PT_LOAD): [65536]
  ejemplos con el minimo: ['lib/aarch64-linux-gnu/libselinux.so.1',
   'usr/lib/aarch64-linux-gnu/libBrokenLocale.so.1', 'usr/lib/aarch64-linux-gnu/libdl.so.2',
   'usr/lib/aarch64-linux-gnu/libgcc_s.so.1', 'usr/lib/aarch64-linux-gnu/libpcre2-8.so.0.11.2']
A: VERDE - todo PT_LOAD alinea a >= 16384 (minimo observado 65536)

GUARD DE PRECONDICION: pasa, interprete y librerias estan
CONTROL POSITIVO rc=0 out='CONTROL_POSITIVO_OK' err=''
CHROOT openKylin ['/usr/bin/bash', '-c', 'echo OPENKYLIN_USERLAND_VIVO'] rc=0 out='OPENKYLIN_USERLAND_VIVO' err=''
CHROOT openKylin ['/usr/bin/bash', '--version'] rc=0 out='GNU bash, version 5.3.9(1)-release (aarch64-unknown-linux-gnu)\nCopyright (C) 2025 Free Software Foundation, Inc. ...'
CHROOT openKylin ['/usr/bin/env', 'true'] rc=0 out='' err=''
CHROOT openKylin ['/usr/bin/bash', '-c', 'cat /etc/os-release ...'] rc=0 out='NAME="openKylin"\nFULL_NAME="openKylin"\nVERSION="3.0 (huanghe)"\nVERSION_US="3.0 (huanghe)"'
B: VERDE - el userland arm64 de openKylin EJECUTA en un aarch64 ajeno
```

Los doce `.deb` bajaron con **sha256 verificado contra el índice oficial**, doce de
doce: `base-files 14-ok3`, `libc6 2.43-ok2`, `libgcc-s1 15.2.0-16ok8`, `bash 5.3-ok1`,
`dash 0.5.12-ok1`, `coreutils 9.4-ok4`, `libtinfo6`, `libselinux1`, `libpcre2-8-0`,
`libacl1`, `libattr1`, `libgmp10`. El sufijo `-okN` es la firma de openKylin: son
sus paquetes, no los de Debian.

### El cruce de instrumento: mismo script, dos arquitecturas

El lector de ELF está escrito a mano en Python (sin `readelf` ni `ldd`, que no
sirven cross-arch), así que A tiene que dar el **mismo** número en x64. Dio
`[65536]` en las dos máquinas con el mismo md5 de instrumento. **Si hubiera
diferido, la diferencia era del lector y no de los binarios.**

## 4. TRES COSAS QUE VAN CONTRA MÍ

### 4.1 El v1 dio B=ROJO, y el ROJO era mío

Las cuatro pruebas fallaron idéntico:

```plain
chroot: failed to run command '/bin/bash': No such file or directory
B: ROJO - el userland arm64 de openKylin NO EJECUTA en un aarch64 ajeno
```

Ese `ENOENT` **no era del binario: era del intérprete ausente**. El rootfs tenía
solo `bash`, `coreutils` y `libc6`, sin `base-files` (los symlinks de merged-usr) ni
`libtinfo6` (que `bash` pide por `DT_NEEDED`). Sin `/lib`, el `PT_INTERP`
`/lib/ld-linux-aarch64.so.1` no resuelve y el kernel contesta `ENOENT`, que se lee
exactamente igual que "el binario no existe".

**Si publicaba ese ROJO, mandaba a descartar la arquitectura entera de SIAO por un
defecto de mi extractor.** Es el patrón medido de este proyecto: instalar paquetes
no es `untar`, y `dpkg` resuelve lo que mi tar no.

### 4.2 Mi control negativo NO discrimina, y eso acota lo que este falsador puede afirmar

```plain
CONTROL NEGATIVO 1 (ELF corrupto)     rc=127 err='chroot: failed to run command '/bin/roto': No such file or directory'
CONTROL NEGATIVO 2 (ruta inexistente) rc=127 err='chroot: failed to run command '/bin/no-existe-nunca': No such file or directory'
CONTROL NEGATIVO discrimina corrupto de inexistente: False (firmas iguales: True)
```

Las dos firmas son la misma. **Consecuencia declarada, y es una limitación real del
instrumento: sirve para sostener un VERDE y NO sirve para atribuir un ROJO.** El
VERDE se sostiene porque la prueba devolvió la cadena exacta esperada y el
`os-release` correcto, y eso la basura no lo puede producir. Un ROJO, en cambio,
no podría distinguirse de una pieza faltante mía. Por eso el v3 tiene el guard de
precondición: si falta algo, el veredicto es **NO MEDIDO**, no ROJO.

### 4.3 `/usr/bin/uname` dio 127, y tampoco es de openKylin

```plain
CHROOT openKylin ['/usr/bin/uname', '-m'] rc=127 err='chroot: failed to run command '/usr/bin/uname': No such file or directory'
```

En el mismo chroot, `/usr/bin/env` dio `rc=0`. O sea que el `coreutils` de openKylin
pone `uname` en otra ruta (probablemente `/bin`, que acá es un **directorio real** y
no el symlink de merged-usr). **Queda NO MEDIDO, no defecto ajeno.** Adivinar la
ruta y reportar el 127 como falla de openKylin sería el mismo error que 4.1.

## 5. ME REFUTO: predije que el runner arm64 no iba a nacer

El inventario tiene medido que en el otro repo privado **696 de 696 jobs hosted
quedaron con `runner_id 0`**, y que los runners arm64 gratis son de repo público.
Con eso predije que en `siao` (privado) el job iba a quedar sin runner.

**Nació:**

```plain
JOB arm64-nativo | status completed | concl success | runner_id 1000002018
  | runner_name GitHub Actions 1000002018 | labels ['ubuntu-24.04-arm']
```

Tres corridas, seis jobs, seis con runner real. **El inventario es una foto y se
re-mide, no se recuerda**: apliqué un hallazgo de otro repo y de otra semana como si
fuera una propiedad de la cuenta. Si me hubiera quedado en la predicción, pedía
pasar el repo a público sin necesidad.

## 6. NO MEDIDO

- **El comportamiento bajo un kernel de páginas de 16 KB.** El runner reporta
  `pagesize: 4096`. Lo medido es que la **alineación** es compatible (65536), no que
  cargue en un kernel de 16 KB: eso necesita el dispositivo.
- **El userland completo.** Son 12 paquetes y un shell, no `systemd`, ni UKUI, ni
  Wayland, ni el AI SDK, ni KylinBot.
- **El `chroot` no es un teléfono:** mismo kernel del runner, sin `/vendor`, sin
  binder, sin GKI. Lo que quedó descartado es "el userland no sale de su ISO".
- **El ISO Embedded ARM64 (2,29 GiB) sigue sin tocarse.** Esto se midió contra el
  repo `apt`, que es otro sujeto.
- **La ruta real de `uname`** en el coreutils de openKylin.

## 7. Qué cambia en el proyecto

1. **La Fase 0 del ADR-001 ya no cuelga de una premisa sin medir.** Comprar el
   teléfono dejó de ser el primer paso obligado para saber si esto era posible.
2. **Sale un riesgo de la tabla:** "compilar la variante ARM64 con alineación 16K
   desde el día 1" era una tarea del roadmap. Los binarios **ya vienen** a 64 KB.
3. **Actions arm64 sirve para SIAO estando el repo privado**, y eso es la fábrica
   entera disponible sin publicar nada todavía.

## 8. Contrato de cierre

- **Instrumento:** `tools/falsador_userland_arm64.py` (rama `titan/falsador-userland-arm64`)
- **Workflow:** `.github/workflows/falsador-userland-arm64.yml`
- **Evidencia cruda commiteada por el propio runner:**
  `mediciones/falsador-001/arm64/` y `mediciones/falsador-001/x64/`
- **Este archivo:** `docs/agents/respuestas/2026-09-05-03-falsador-001-la-premisa-base-de-siao-es-VERDE.md`

--- METODO PROMETEO ---
**Máquina:** GitHub Actions **arm64** (aarch64 nativo, 2 vCPU, `runner_id 1000002018`)
como sujeto, Actions x64 como control de instrumento, y `brain-env` para leer los
runs por API. El texto de los logs no se leyó por API (403 por diseño): **cada job
commiteó su propia salida cruda**, que es de dónde salen todos los números de arriba.
**Artefacto 2 (ClickUp):** Doc del turno con el veredicto y los dos defectos propios.
