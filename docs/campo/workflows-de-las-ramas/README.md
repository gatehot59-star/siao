# Los workflows de las ramas, como EVIDENCIA (no ejecutables)

`main` no tiene estos workflows: viven en las ramas `titan/*`. Se traen aca
**con extension `.txt` a proposito**, por dos motivos:

1. **Que no se ejecuten.** Un `.yml` en `.github/workflows/` corre con el token
   del repo. Como evidencia hay que poder leerlos, no dispararlos.
2. **El PAT del taller no tiene scope `workflow`**, asi que no puede escribir en
   `.github/workflows/` ni para copiar. Medido: `refusing to allow a Personal
   Access Token to create or update workflow ... without workflow scope`.

Si alguno hace falta activo, se copia a `.github/workflows/` por la API de
GitHub, que es otra credencial. **Eso es una decision, no un tramite.**

| Workflow | Bytes | Rama de origen |
|---|---|---|
| `f-001-s1-arnes.yml` | 3747 | `titan/f-004-kmi` |
| `f-001-s1b-qemu.yml` | 1982 | `titan/f-004-kmi` |
| `f-001-userland-sobre-gki.yml` | 3160 | `titan/f-001-userland-sobre-gki` |
| `f-002-rootfs.yml` | 1885 | `titan/f-002-rootfs` |
| `f-004-kmi-v3.yml` | 5950 | `titan/f-004-kmi` |
| `f-004-kmi.yml` | 3622 | `titan/f-004-kmi` |
| `f-004-primer-error.yml` | 2135 | `titan/f-004-kmi` |
| `f-004-sin-crc.yml` | 1539 | `titan/f-004-kmi` |
| `f-004-stgdiff-x86.yml` | 3870 | `titan/f-004-kmi` |
| `f-004b-kabi.yml` | 4040 | `titan/f-004-kmi` |
| `f-004c-rescate.yml` | 3027 | `titan/f-004-kmi` |
| `f-004c-sin-cgroup-pids.yml` | 4085 | `titan/f-004-kmi` |
| `f-004d-61.yml` | 5102 | `titan/f-004-kmi` |
| `f-004d.yml` | 7101 | `titan/f-004-kmi` |
| `falsador-userland-arm64.yml` | 2817 | `titan/falsador-userland-arm64` |

Total: **15** workflows.
