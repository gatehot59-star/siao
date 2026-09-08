# MAPA DE LA EVIDENCIA · dónde está cada medición de SIAO

**Última verificación contra el repo:** 2026-09-07 22:35 (America/Buenos_Aires) · `main` = `522defdc`  
**Para quién:** cualquiera que audite este repo, humano o agente.

---

## 0 · Por qué existe este archivo

Porque su ausencia ya produjo un error medido, y no de un descuidado: TITÁN Tao auditó SIAO el 2026-09-07 leyendo `main` en vivo, con método y declarando sus límites, y concluyó que **F-004d en android14-6.1 estaba `NO MEDIDO`**. Está **VERDE y medido** desde las 14:26 UTC de ese mismo día.

**No fue su culpa. Fue la del repo, o sea mía.** Tres causas encadenadas:

1. El verde vive **solo** en la rama `titan/f-004-kmi`, y **`main` no la referencia por ningún lado**.
2. El archivo más nuevo de `docs/agents/respuestas/` en `main` es del 09-07 y todavía reporta el problema **abierto**: quedó viejo el mismo día.
3. `AGENTS.md` obliga a leer `CONTEXTO-SIAO.md`, que dice *"no hay kernel compilado"* cuando hay ocho builds y un `vmlinux` de 354 MB.

Así que el auditor hizo todo bien y el repo lo mandó al lugar equivocado. **Este archivo es el índice que faltaba: dice en qué rama, en qué SHA y en qué archivo exacto está cada veredicto.**

### La regla que lo hace útil

> **Si este mapa y `CONTEXTO-SIAO.md` se contradicen, gana este mapa**, porque cada línea de acá se verifica contra un SHA y un archivo, y el contexto se escribe a mano.  
> **Y si este mapa y el repo se contradicen, gana el repo.** Este archivo también se escribe a mano: es una foto con fecha, no un contrato.

### Lo que este mapa NO arregla, declarado

Anotar el SHA de una rama **no protege sus objetos**. Si alguien borra `titan/f-004-kmi`, el recolector de basura de git se lleva la evidencia igual y este mapa solo va a servir para saber **qué** se perdió. Resuelve el problema de **descubrimiento**, no el de **durabilidad**. Lo segundo necesita traer la evidencia a `main` o proteger las ramas, y sigue pendiente.

---

## 1 · El mapa, por falsador

| Falsador | Veredicto | Rama | SHA de la rama | Archivo que hay que ABRIR |
|---|---|---|---|---|
| **FALSADOR-001** userland openKylin arm64 fuera de su ISO | **A VERDE, B VERDE** | `titan/falsador-userland-arm64` | `139b8637` | `mediciones/falsador-001/arm64/` y `/x64/` |
| **F-001** userland sobre GKI | ver el `.md` | `titan/f-001-userland-sobre-gki` | `98dc52ef` | `mediciones/f-001/F-001.md` + `F-001-salida-cruda.txt` |
| **F-002** rootfs `siao-base-s1` (9 versiones) | **CERRADO** en la v9 | `titan/f-002-rootfs` | `4a862d16` | `mediciones/f-002/F-002-v9.md` (+ `v3`…`v8` para la serie) |
| **F-001-S1** GKI de Google en QEMU | **VERDE**, arrancó | `titan/f-004-kmi` | `2b877236` | `mediciones/f-001-s1/f001s1-aarch64-boot.txt` |
| **F-004** el fragmento rompe el KMI | **ROJO**, causa `SYSVIPC` | `titan/f-004-kmi` | `2b877236` | `mediciones/f-004/` y `mediciones/f-004-v3/` |
| **F-004b** padding KABI | perdí la predicción; apareció el 2º rompedor | `titan/f-004-kmi` | `2b877236` | `mediciones/f-004b/F-004b-VEREDICTO.txt` |
| **F-004c** nueve símbolos sin `CGROUP_PIDS` | **VERDE** (495 B, 0 offsets, 0 CRC) | `titan/f-004-kmi` | `2b877236` | `mediciones/f-004c/F-004c-VEREDICTO.txt` |
| **F-004d** ocho símbolos @ android15-6.6 | **VERDE** (68 B) | `titan/f-004-kmi` | `2b877236` | `mediciones/f-004d/` |
| **F-004d @ android14-6.1** ← *el que ordena el proyecto* | **VERDE, sin parche al ACK** | `titan/f-004-kmi` | `2b877236` | **`mediciones/f-004d-61/F-004d-61-VEREDICTO.txt`** |
| **F-007a / F-007b** vendors y `.ko` real de Pixel | ver los recibos | `main` | — | `docs/agents/respuestas/2026-09-06-13-*` y `-14-*` |
| Falsadores de KVM en runners | ver los recibos | `main` | — | `docs/agents/respuestas/2026-09-06-03-*` y `-04-*` |

**Instrumentos:** los **15** scripts de Python que produjeron todo lo de arriba viven en `tools/` de `titan/f-004-kmi` (`f001s1_arnes.py`, `f004_kmi_v3.py`, `f004b_kabi.py`, `f004c_stg.py`, `f004d61_build.py`, `f004d61_stg.py`, y nueve más). **`main` no tiene `tools/`.**

---

## 2 · El veredicto que más se busca, transcripto acá

Para que nadie tenga que cambiar de rama para saber el estado del camino crítico. Verbatim de `mediciones/f-004d-61/F-004d-61-VEREDICTO.txt`:

```
== F-004d en la generacion android14-6.1 ==
  maquina x86_64 | fecha UTC 2026-09-07T14:26:07Z
  R-17: baseline PROPIO de 6.1. No se cita nada de 6.6.
  baseline  .stg 10699061 B | sha256 c91ed3a1963a261b290c624d251f081b
  ocho      .stg 10699333 B | sha256 047141d8822061e9a61a3865f236dae0
=== pasada SIN CRC ===
  rc=4 | 68 B | CRC x0 | added x1 | byte-size x0 | offset x0
  structs tocadas: NINGUNA
  --- reporte ENTERO ---
   | function symbol 'void put_pid_ns(struct pid_namespace*)' was added

================ VEREDICTO ================
    F-004d @ android15-6.6 : SIN CRC     68 B | offsets 0 | CRC 0   (medido ayer)
    F-004d @ android14-6.1 : SIN CRC     68 B | offsets 0 | CRC 0
  VERDE: fragmento de OCHO ABI-compatible en android14-6.1, sin parche al ACK
  R-13: esto dice ABI-compatible. Que un .ko real CARGUE es F-007c.
```

Y el arnés, de `mediciones/f-004d-61/v3-ocho.json`: `rc_archscripts: 0`, `error_126_serial: false`, `error_126_paralelo: false`, `rc_build: 0`, `parche_al_ack: false`.

**Ojo con el alcance, que el propio veredicto declara (R-13):** esto dice **ABI-compatible**, no dice que un módulo real cargue. Eso es F-007c y **sigue NO MEDIDO**.

---

## 3 · Dos correcciones a archivos que hoy mienten

No las aplico acá porque son archivos canónicos y editarlos de paso, en medio de otra entrega, es cómo se sobrescribe trabajo ajeno. Quedan declaradas y esperando el OK de Abraham:

| Archivo | Dice | Es |
|---|---|---|
| `CONTEXTO-SIAO.md` §3 | *"existe `.github/workflows/falsador-userland-arm64.yml`"* | **falso en `main`**: hay dos archivos y son `falsador-kvm-runners.yml` y `falsador-kvm-usermod.yml` |
| `CONTEXTO-SIAO.md` §3 | *"no hay kernel compilado"* | **falso**: ocho builds, `vmlinux` de 354.673.168 B y `Module.symvers` de 16.036 líneas |
| `README.md` | *"nada de este repo corrió todavía en ninguna máquina"* | **falso**: rootfs construido, GKI arrancado en QEMU en 2,2 s, ocho builds. *"Cero dispositivo"* **sí** sigue siendo cierto |
| `mediciones/INDICE.md` (en la rama) | tiene **dos** filas para F-004d@6.1: una `NO MEDIDO` y otra `VERDE` | la vieja no se borró al cerrar. Quien lea la primera fila se lleva el dato viejo |

---

## 4 · Cómo leer una rama sin clonarla

Para un agente con la API de GitHub, el parámetro `ref` acepta el nombre de rama directo. No hace falta checkout:

```
GET /repos/gatehot59-star/siao/contents/mediciones/f-004d-61/F-004d-61-VEREDICTO.txt?ref=titan/f-004-kmi
```

**Y la advertencia que cuesta un hallazgo mal:** listar un directorio devuelve **nombres y tamaños**, no contenido. Un `ls` de `mediciones/f-004d-61/` muestra 46 archivos y **no dice qué dice ninguno**. Concluir un estado desde el listado es medir el sujeto equivocado: el veredicto está **adentro** del archivo que se llama `VEREDICTO`.

---

## 5 · Mantenimiento

Este archivo se actualiza **en el mismo turno** en que una medición nueva cierra, junto con el recibo. Si su fecha de verificación es anterior al último archivo de `docs/agents/respuestas/`, **está desactualizado por definición** y hay que re-verificarlo contra el repo antes de citarlo.

**NO MEDIDO en esta versión:** no abrí el contenido de los 15 instrumentos de `tools/`, así que **no puedo afirmar que midan lo que sus nombres dicen medir**. Esa es una auditoría de instrumentos y es la más cara de todas. Tampoco enumeré archivo por archivo `mediciones/f-004/`, `f-004-v3/` ni `f-004d/`: confirmé que existen y de dónde salen, no su contenido completo.
