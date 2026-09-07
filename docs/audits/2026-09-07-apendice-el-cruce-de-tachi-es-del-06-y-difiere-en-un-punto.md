# Apéndice al audit MUDH → SIAO: dónde está el documento de Tachi y en qué diferimos

**Fecha:** 2026-09-07  
**Pedido:** buscar un documento de Tachi "de hoy" sobre la relación SIAO ↔ MUDH-Mobile, en el repo de MUDH o en `brain-env`.

## 1. Qué se encontró, y la corrección de fecha

Existe un solo documento de Tachi sobre el cruce: **`docs/base/04-CRUCE-SIAO-MUDH-2026-09-06.md`** en `gatehot59-star/mudh-mobile`, rama `main`, blob `882166b7725f230bd33147e299772c91a7f659d2`.

**No es de hoy: es del 2026-09-06.** Firmado "De: Tachi (auditor) · Fecha: 2026-09-06". Creado en el commit `95b6a58` (2026-09-06 19:37 UTC, 84 líneas) y corregido en `f74cd8d` (19:54 UTC, +72/-51). El propio archivo dice que corrige una versión anterior que había leído SIAO como "un ADR vacío".

## 2. Qué se buscó y no existe

- `docs/agents/` y `docs/base/` de `main`: sin archivo nuevo del 2026-09-07.
- Búsqueda de código por `SIAO` bajo `docs` del repo: sin resultados adicionales indexados.
- `brain-env`, `/workspace`: los únicos `.md` del 2026-09-07 son recibos de BRAIN sobre emulador, APEX, watchdog, KVM y VM (`2026-09-07-01` a `-05`), en el clon local `/workspace/mudh`, no en `main`. Ninguno trata el cruce SIAO-MUDH.
- `/workspace/analisis.md` es del 2026-09-06 y es de BRAIN, no de Tachi.
- Buzón `nexus.db`: los mensajes del 2026-09-07 son el intercambio BRAIN↔Tachi por `/dev/kvm` y `seccomp=unconfined`. Nada de SIAO.

**Conclusión:** el documento pedido existe, pero su fecha es 06-sep. Si Tachi escribió algo hoy, no está en `main` de MUDH ni en `brain-env`; quedaría en una rama sin pushear o fuera de estas dos fuentes. **NO MEDIDO:** ramas remotas distintas de `main` no se barrieron archivo por archivo.

## 3. Lo que coincide con mi audit

Tachi ubica a MUDH como **capa 5** de SIAO (el sistema de IA / la gobernanza) y a SIAO como las capas 0-4 (kernel KMI-safe, base openKylin, `libhybris`, inquilino Android LXC). Eso es compatible con mi veredicto: lo que pasa de MUDH a SIAO es el **control plane**, no el producto entero.

## 4. Donde NO coincidimos, y es el punto que importa

El cruce de Tachi afirma: *"El trabajo de MUDH (Zod Gate, cable, QuickJS) se conserva entero — solo cambia dónde corre"*.

**Mi audit lo acota:** se conserva entero el **contrato y la lógica determinista** (`IntentPlan`, snapshot ligado, fail-closed, `ValidatedCommand`, auditoría). No se conserva entero el **runtime**:

- `ExecutorRouter` y `MudhAccessibilityExecutor` tienen a Android como sujeto de autoridad (paquete en primer plano, `AccessibilityNodeInfo`) y necesitan adaptador hacia `siao.ui`/`capd`.
- `ShizukuGate` sobra en SIAO: su reemplazo es un servicio privilegiado del propio OS.
- `proot` se reemplaza por LXC, no se muda.
- Y el estado consolidado del 2026-09-06 dice que el cable vive en rama huérfana sin PR, 73 commits atrás: "se conserva entero" describe código leído, no integración viva.

O sea: coincidimos en la jerarquía y diferimos en cuánto de MUDH es portable sin tocar. La diferencia no es retórica: decide si SIAO planifica adaptadores desde el día 1 o asume una mudanza.

---

**Máquina:** GitHub API (lectura) + `brain-env` (búsqueda de archivos y consulta a `nexus.db`, solo lectura).  
**Artefacto git:** este archivo, junto a `docs/audits/2026-09-07-auditoria-mudh-a-siao.md`.  
**Artefacto ClickUp:** el Doc del audit del mismo día.