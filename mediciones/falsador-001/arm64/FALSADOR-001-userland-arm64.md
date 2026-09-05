# FALSADOR-001 - el userland ARM64 de openKylin 3.0 fuera de su ISO

**Fecha (UTC):** 2026-09-05T19:44:31Z
**Maquina:** {"arch": "aarch64", "nproc": 2, "kernel": "6.17.0-1022-azure", "runner_os": "Linux", "runner_arch": "ARM64", "github_run_id": "33988009462"}

| Pregunta | Veredicto |
|---|---|
| A - paginas de 16 KB (`p_align` >= 16384) | **VERDE** |
| B - ejecuta en un aarch64 ajeno (chroot) | **ROJO** |

Controles del instrumento: `{"positivo_chroot_del_runner": true, "negativo_elf_corrupto_no_ejecuta": true}`

NO MEDIDO: nada

## Salida cruda, verbatim

```plain
== FALSADOR-001 ==
maquina: {"arch": "aarch64", "nproc": 2, "kernel": "6.17.0-1022-azure", "runner_os": "Linux", "runner_arch": "ARM64", "github_run_id": "33988009462"}
INDICE ERR https://mirrors.dotsrc.org/mirrors/pub/openkylin/dists/huanghe/main/binary-arm64/Packages.xz <HTTPError 404: 'Not Found'>
INDICE 200 4165259 bytes https://mirrors.dotsrc.org/mirrors/pub/openkylin/dists/huanghe/main/binary-arm64/Packages.gz
INDICE lineas 392521
PAQUETE bash 5.3-ok1 1243548 B
PAQUETE coreutils 9.4-ok4 2755136 B
PAQUETE libc6 2.43-ok2 1616760 B
DEB 200 1243548 B bash sha256_ok=True
  extraido data.tar.xz (xz) 7485440 B
DEB 200 2755136 B coreutils sha256_ok=True
  extraido data.tar.xz (xz) 20060160 B
DEB 200 1616760 B libc6 sha256_ok=True
  extraido data.tar.zst (zst) 4915200 B
ALINEACIONES CRUDAS observadas (p_align de PT_LOAD): [65536]
A: VERDE - todo LOAD alinea a >= 16384 (min 65536)
CONTROL POSITIVO rc=0 out='CONTROL_POSITIVO_OK' err=''
CONTROL NEGATIVO rc=127 err='chroot: failed to run command ‘/bin/roto’: No such file or directory'
CHROOT openKylin ['/bin/bash', '-c', 'echo OPENKYLIN_USERLAND_VIVO'] rc=127 out='' err='chroot: failed to run command ‘/bin/bash’: No such file or directory'
CHROOT openKylin ['/bin/bash', '--version'] rc=127 out='' err='chroot: failed to run command ‘/bin/bash’: No such file or directory'
CHROOT openKylin ['/usr/bin/uname', '-m'] rc=127 out='' err='chroot: failed to run command ‘/usr/bin/uname’: No such file or directory'
CHROOT openKylin ['/usr/bin/env', 'true'] rc=127 out='' err='chroot: failed to run command ‘/usr/bin/env’: No such file or directory'
B: ROJO - el userland arm64 de openKylin NO EJECUTA en un aarch64 ajeno
```
