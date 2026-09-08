# Indice de mediciones (R-15)

Un run sin linea aca esta **NO LEIDO** y bloquea el siguiente falsador.

> **Dos correcciones del 2026-09-08, y las dejo escritas en vez de borrarlas:**
>
> 1. **Había DOS filas para F-004d@android14-6.1**, misma generación y misma
>    carpeta, con veredictos opuestos: una `NO MEDIDO` y otra `VERDE`. La vieja no
>    se borró al cerrar la medición. **Un gate que se contradice no gatea**, y
>    quien leyera la primera fila se llevaba el dato viejo con autoridad de
>    índice. Es H-12 de la segunda auditoría de Tao.
> 2. **Tenía una sola medición de siete.** Un índice con una entrada tampoco
>    gatea: si su regla dice que un run sin línea está NO LEIDO, entonces seis
>    falsadores cerrados figuraban como no leídos. Las seis filas nuevas salen de
>    `docs/agents/MAPA-DE-LA-EVIDENCIA.md`, verificadas contra sus veredictos.

| falsador | generacion | veredicto | evidencia |
|---|---|---|---|
| FALSADOR-001 | — (userland arm64) | **A VERDE, B VERDE**: 146 ELF con `p_align 65536`, y `bash 5.3.9 aarch64` corriendo en chroot | `mediciones/falsador-001/` |
| F-001 | — (userland sobre GKI) | ver el `.md` | `mediciones/f-001/F-001.md` |
| F-002 | — (rootfs) | **CERRADO** en la v9: `siao-base-s1`, 177 paquetes, 248 MiB, `rc=0` | `mediciones/f-002/F-002-v9.md` |
| F-001-S1 | android15-6.6 | **VERDE**: el GKI de Google arrancó en QEMU aarch64 en 2,2 s | `mediciones/f-001-s1/f001s1-aarch64-boot.txt` |
| F-004 | android15-6.6 | **ROJO**: el fragmento rompe el KMI, causa `SYSVIPC` en `task_struct` | `mediciones/f-004/`, `mediciones/f-004-v3/` |
| F-004b | android15-6.6 | predicción perdida; el padding KABI funcionó y apareció el 2º rompedor (`CGROUP_PIDS`) | `mediciones/f-004b/F-004b-VEREDICTO.txt` |
| F-004c | android15-6.6 | **VERDE**: nueve símbolos sin `CGROUP_PIDS`, 495 B, 0 offsets, 0 CRC | `mediciones/f-004c/F-004c-VEREDICTO.txt` |
| F-004d | android15-6.6 | **VERDE**: ocho símbolos, 68 B, 0 offsets, 0 CRC | `mediciones/f-004d/` |
| **F-004d** | **android14-6.1** | **VERDE en ABI**, sin parche al ACK: 68 B, 0 offsets, 0 CRC, ninguna struct tocada · **ver las DOS salvedades de abajo** | `mediciones/f-004d-61/F-004d-61-VEREDICTO.txt` |
| F-007c | android14-6.1 | **NO MEDIDO** — y es lo que hoy bloquea el proyecto | no existe todavía |

## Las dos salvedades de F-004d@6.1, que el veredicto solo no alcanza a decir

**(a) Alcance (R-13, declarado por el propio veredicto):** dice **ABI-compatible**.
**No** dice que un módulo real cargue. Eso es **F-007c** y sigue NO MEDIDO.

**(b) El `Error 126` NO está eliminado.** El guard serial salió **inerte en los dos
brazos**: `segundos_archscripts: 0.02`, `archscripts_hizo_trabajo: false`, y `make`
dijo `Nothing to be done for 'archscripts'` **con el `HOSTCFLAGS` ya aplicado**. El
falsador que el proyecto declaró antes de correr decía: *"si vuelve a dar 0,0 s, el
arreglo no se aplicó y no hay que interpretar nada más"*. Así que el 126 no apareció
en esa corrida **con el guard sin hacer trabajo**: es **una carrera ganada, no
cerrada**, y el 126 está medido como intermitente.

**Para cerrarlo hace falta una matriz de N corridas** del mismo brazo contando
fallos. Es `needs-runtime` y no existe. Hasta entonces, el 126 está **dormido, no
muerto**, y cualquier build futuro del kernel puede volver a caer por esa causa.

## Regla de uso

**Una fila por falsador y por generación.** Cuando una medición cierra, se
**reemplaza** su fila, no se agrega otra al lado: eso fue exactamente el defecto que
convirtió este archivo en un gate contradictorio.

Si este índice y `docs/agents/MAPA-DE-LA-EVIDENCIA.md` se contradicen, **gana el
archivo de veredicto** que los dos citan: ninguno de estos dos índices es la
medición, los dos son punteros escritos a mano.
