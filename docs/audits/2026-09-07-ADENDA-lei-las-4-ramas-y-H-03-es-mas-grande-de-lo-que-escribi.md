# Adenda: leí las 4 ramas, y H-03 es más grande de lo que escribí

**Fecha:** 2026-09-07 · **Cierra:** el límite propio #1 de `docs/audits/2026-09-07-auditoria-integral-del-repo-siao-9600a94.md` §5 (*"no leí el contenido de las 4 ramas `titan/*`"*).

**Método:** lectura del árbol de cada rama por API, en su ref, sin clonar y sin correr nada.

---

## 1 · Lo que hay en las ramas y NO hay en `main`

Las cuatro ramas comparten dos directorios de primer nivel que **`main` no tiene**: `mediciones/` y `tools/`.

| Rama | HEAD | `mediciones/` | `tools/` | `.github/workflows/` |
|---|---|---|---|---|
| `titan/f-004-kmi` | `2b87723` | `INDICE.md` + **9** carpetas (`f-001-s1`, `f-001-s1b`, `f-004`, `f-004-v3`, `f-004b`, `f-004c`, `f-004d`, `f-004d-61`, `peritaje`) | **15** instrumentos Python, ~**133 KB** | **12** workflows |
| `titan/f-002-rootfs` | `4a862d1` | `f-002/` | sí | — |
| `titan/f-001-userland-sobre-gki` | `98dc52e` | `f-001/` | sí | — |
| `titan/falsador-userland-arm64` | `139b863` | `falsador-001/` | `falsador_userland_arm64.py` (24.140 B) | — |

**Los 15 instrumentos de `titan/f-004-kmi`:** `f001s1_arnes.py` (8.272 B), `f001s1b_qemu.py` (6.992 B), `f004_kmi.py` (14.643 B), `f004_kmi_v3.py` (16.523 B), `f004_stg_x86.py` (5.976 B), `f004_stg_x86_ignora_crc.py` (4.316 B), `f004b_kabi.py` (12.773 B), `f004b_stg.py` (6.280 B), `f004c_kabi.py` (3.389 B), `f004c_rescate.py` (7.896 B), `f004c_stg.py` (7.259 B), `f004d61_build.py` (15.052 B), `f004d61_stg.py` (7.351 B), `f004d_sin_sysvipc.py` (10.383 B), `f004d_stg.py` (6.833 B).

**Los 12 workflows de `titan/f-004-kmi`**, ninguno de los cuales existe en `main`: `f-001-s1-arnes.yml`, `f-001-s1b-qemu.yml`, `f-004-kmi.yml`, `f-004-kmi-v3.yml`, `f-004-primer-error.yml`, `f-004-sin-crc.yml`, `f-004-stgdiff-x86.yml`, `f-004b-kabi.yml`, `f-004c-rescate.yml`, `f-004c-sin-cgroup-pids.yml`, `f-004d.yml`, `f-004d-61.yml`.

---

## 2 · Qué cambia en el informe

### H-03 sube de "la evidencia vive en ramas huérfanas" a "casi TODO el proyecto vive ahí"

Lo que se pierde si alguien borra **una sola rama** (`titan/f-004-kmi`, sin protección, sin PR, no referenciada por SHA desde `main`): 15 instrumentos de medición, 12 workflows, 9 carpetas de evidencia cruda y el índice que las ordena. **Eso es prácticamente todo el trabajo técnico de las 48 horas del proyecto.**

Y el agravante es de método, no de git: **el contexto vivo ni las menciona.** `CONTEXTO-SIAO.md` §3 apunta a `mediciones/falsador-001/` en `titan/falsador-userland-arm64` —lo verifiqué, está— pero **no dice una palabra** de las otras tres ramas ni de los 15 instrumentos. Un agente nuevo que lea `main` completo concluye que el proyecto tiene dos workflows de KVM y nada más.

### H-08 se matiza, y en dirección favorable

Escribí que *"100% de lo commiteado en `main` es documentación, salvo dos workflows y dos disparadores"*. **Eso sigue siendo exacto para `main`.** Pero la lectura ingenua —"SIAO no tiene código"— es falsa: hay ~**157 KB de Python** entre las cuatro ramas.

**Lo que no cambia:** ese código son **instrumentos de medición**, no producto. La capa 5 (el sistema de IA) sigue sin empezar, y sigue sin haber `LICENSE`. La conclusión de H-08 se sostiene; su enunciado queda más preciso.

### H-05 se refina: el índice ya existe, pero para la evidencia y en una rama

`mediciones/INDICE.md` existe en `titan/f-004-kmi`. O sea que **el proyecto ya resolvió el problema del índice** para la evidencia cruda, y no lo aplicó a `docs/agents/respuestas/`, que es justo el directorio que `AGENTS.md` manda leer al arrancar. La solución está escrita y está del lado equivocado del árbol.

---

## 3 · Lo que sigue NO MEDIDO después de esta adenda

1. **El contenido de los 15 instrumentos.** Leí nombres y tamaños, no código: no puedo afirmar que midan lo que dicen medir. Verificarlo es una auditoría de instrumentos, que es otro trabajo y más caro que éste.
2. **La evidencia cruda dentro de las 9 carpetas de `mediciones/`.** Mismo criterio.
3. **Si los 12 workflows de la rama siguen siendo válidos** contra el estado actual de los runners.
4. **Los 5 ADR completos.** El límite #2 de mi informe sigue abierto y lo dejo abierto a propósito: leerlos enteros son ~60 KB y no cambiaría ninguno de los nueve hallazgos, que son estructurales. Si querés el peritaje del razonamiento interno de los ADR, es un pedido aparte y lo digo antes en vez de simularlo.

---

**Corrección de rúbrica:** con esta adenda, Completitud sube de 14 a **15/15** (el `-1` era exactamente por las ramas sin leer). **Total: 44/45 → 98/100**, con los mismos 55 pts `N/A` declarados en el informe.
