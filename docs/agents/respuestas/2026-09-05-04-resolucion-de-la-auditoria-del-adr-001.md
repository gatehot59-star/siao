# 2026-09-05 · La auditoría del ADR-001, resuelta midiendo

## 1. Pedido literal

Una auditoría externa del ADR-001, afirmación por afirmación, con tres puntos
marcados como no sostenibles, un riesgo omitido (H1), una objeción al falsador
(H2) y correcciones de redacción concretas.

**Contestado primero eso, en el ADR-002:**
`docs/adr/2026-09-05-02-resolucion-auditoria-adr-001.md`

## 2. Marcador

| Punto | Resultado |
|---|---|
| A2 (la fecha) | **Él tenía razón. Yo introduje el error** corrigiendo un dato que estaba bien |
| A6, A7, H5 | **Aceptados.** El ADR-001 se corrige en su redacción |
| H1 (allowlist de Android 17) | **Confirmado en AOSP**, con dos matices que mejoran la posición |
| H4 (contenedor de apps) | **Confirmado y PEOR**: para arm64 no hay imagen Android 16 |
| H3 (rootfs por `mmdebstrap`, no por ISO) | **Aceptado**, y es lo que el falsador ya hizo a escala chica |
| A3 (índice no verificable) | **Refutado**: responde 200, y acá está la URL |
| A9/H2 (el falsador mide lo incorrecto) | **Premisa refutada**: no leyó el ISO y la respuesta no es 4K |
| "repo público es prerrequisito del runner arm64" | **Refutado, medido**: privado, seis jobs con runner real |
| H2 como próximo paso | **Le doy la razón, y le traigo un sospechoso**: `CONFIG_PID_NS` |

## 3. Evidencia cruda, verbatim

### A2 · la fecha (contra mí)

```plain
GET 200 165188 https://www.openkylin.top/news/4099-en.html
   TIMESTAMP: 2026-08-31 17:05:48
GET 200 163436 https://www.openkylin.top/news/4099-cn.html
   TIMESTAMP: 2026-08-31 17:05:48
```

Mi "28-ago" venía de un **extracto de buscador**. La página dice 31.

### A3 · el índice, con URL

<https://releases.openkylin.top/3.0/>

```plain
GET 200 len 2082
   openKylin-Desktop-V3.0-20260827-arm64.iso          28-Aug-2026 01:02   6748999680
   openKylin-Embedded-V3.0-202608281407-ARM64.iso     28-Aug-2026 09:35   2296999936
   openKylin-Server-V3.0-2026.8.27-3-arm64.iso        27-Aug-2026 14:20   1748994048
```

El nombre **ya no dice `Beta`**: mi propio caveat tampoco estaba respaldado.

### El sospechoso de F-001

```plain
RAMA android16-6.12 | gki_defconfig leido: 22133 bytes
  CONFIG_PID_NS   =NOT SET     <-- explicito, en las TRES ramas
  CONFIG_USER_NS  AUSENTE del defconfig
  CONFIG_NAMESPACES=y  CONFIG_CGROUPS=y  CONFIG_CGROUP_BPF=y  CONFIG_MEMCG=y
  CONFIG_ANDROID_BINDERFS=y  CONFIG_BLK_DEV_LOOP=y  CONFIG_OVERLAY_FS=y  CONFIG_VETH=y
RAMA android15-6.6 -> identico | RAMA android14-6.1 -> identico
```

Leído de `android.googlesource.com/kernel/common/+/refs/heads/<rama>/arch/arm64/configs/gki_defconfig`.

## 4. Lo que este turno NO hizo

- **Cero compilación, cero QEMU, cero kernel.** F-001 no se corrió.
- **No verifiqué** NNAPI, QNN ni NeuroPilot.
- **No medí el `.config`** del GKI construido: un `defconfig` solo criba.

## 5. Tres defectos propios de este turno

1. **A2**: afirmé una fecha desde un extracto de buscador y encima corrigí a
   quien la tenía bien.
2. **El "sigue siendo Beta"** del Embedded: tampoco respaldado.
3. **`CONFIG_BRIDE` por `CONFIG_BRIDGE`** en mi propio cribado. Un símbolo mal
   tipeado **siempre** da ausente: es el mismo cero disfrazado de medición que
   `grep -c` y que `ps`. Declarado, no re-corrido en silencio.

## 6. Contrato de cierre

- **Archivos commiteados:**
  - `docs/adr/2026-09-05-02-resolucion-auditoria-adr-001.md`
  - `docs/agents/CONTEXTO-SIAO.md` (H-007 a H-010 al cementerio)
  - este archivo
- **Repo:** <https://github.com/gatehot59-star/siao>

--- METODO PROMETEO ---
**Máquina:** `brain-env` (gateway, servicio `build`, tool `run`) para las lecturas
HTTP verificadas, más búsqueda web contra fuente primaria. **Cero cómputo de
compilación.**
**Artefacto 2 (ClickUp):** Doc del turno con el marcador de la auditoría.
