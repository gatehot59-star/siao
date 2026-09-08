# MAPA DE LA EVIDENCIA · dónde está cada medición de SIAO

**Última verificación contra el repo:** 2026-09-08 01:50 (America/Buenos_Aires) · `main` = `13775db3`  
**Versión:** 2 · la v1 transcribía el verde de F-004d@6.1 **sin la salvedad del §2.1**, o sea que heredó el defecto que venía a arreglar (H-10/H-11 de TITÁN Tao).  
**Para quién:** cualquiera que audite este repo, humano o agente.

---

## 0 · Por qué existe este archivo

Porque su ausencia ya produjo un error medido, y no de un descuidado: TITÁN Tao auditó SIAO el 2026-09-07 leyendo `main` en vivo, con método y declarando sus límites, y concluyó que **F-004d en android14-6.1 estaba `NO MEDIDO`**. El veredicto ABI está **VERDE y medido** desde las 14:26 UTC de ese mismo día.

**Tres causas encadenadas, y las tres son del repo:**

1. El verde vive **solo** en la rama `titan/f-004-kmi`, y **`main` no la referencia por ningún lado**.
2. El archivo más nuevo de `docs/agents/respuestas/` en `main` es del 09-07 y todavía reporta el problema **abierto**: quedó viejo el mismo día.
3. `AGENTS.md` obliga a leer `CONTEXTO-SIAO.md`, que dice *"no hay kernel compilado"* cuando hay ocho builds y un `vmlinux` de 354 MB.

**Este archivo es el índice que faltaba: dice en qué rama, en qué SHA y en qué archivo exacto está cada veredicto.**

### La regla que lo hace útil

> **Si este mapa y `CONTEXTO-SIAO.md` se contradicen, gana este mapa**, porque cada línea de acá se verifica contra un SHA y un archivo, y el contexto se escribe a mano.  
> **Y si este mapa y el repo se contradicen, gana el repo.** Este archivo también se escribe a mano: es una foto con fecha, no un contrato.

### Lo que este mapa NO arregla, declarado

Anotar el SHA de una rama **no protege sus objetos**. Si alguien borra `titan/f-004-kmi`, el recolector de basura de git se lleva la evidencia igual y este mapa solo va a servir para saber **qué** se perdió. Resuelve **descubrimiento**, no **durabilidad**. Lo segundo necesita traer la evidencia a `main` o proteger las ramas, y sigue pendiente.

**Y una segunda cosa que no arregla, aprendida de la v1:** un mapa que dice dónde está el archivo correcto **todavía puede hacer leer un alcance más grande que el medido**, si transcribe el veredicto sin sus salvedades. Por eso el §2 ahora tiene dos.

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
| **F-004d @ android14-6.1** ← *el que ordena el proyecto* | **VERDE en ABI**, sin parche al ACK · **el `Error 126` sigue ABIERTO, ver §2.1** | `titan/f-004-kmi` | `2b877236` | **`mediciones/f-004d-61/F-004d-61-VEREDICTO.txt`** + **`v3-ocho.json`** + **`v3-ocho-archscripts.txt`** |
| **F-007a / F-007b** vendors y `.ko` real de Pixel | ver los recibos | `main` | — | `docs/agents/respuestas/2026-09-06-13-*` y `-14-*` |
| Falsadores de KVM en runners | ver los recibos | `main` | — | `docs/agents/respuestas/2026-09-06-03-*` y `-04-*` |
| **F-007c** · que un `.ko` real CARGUE | **NO MEDIDO** | — | — | no existe todavía |

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

### 2.1 · DOS salvedades, y las dos hay que leer antes de citar este verde

**(a) Alcance del verde, declarado por el propio veredicto (R-13):** dice **ABI-compatible**, **no** dice que un módulo real cargue. Eso es **F-007c** y sigue **NO MEDIDO**.

**(b) El `Error 126` NO está eliminado.** El guard serial que iba a cerrarlo salió **inerte en los dos brazos**. El JSON tiene **ocho** campos relevantes y hay que citarlos completos, porque los dos últimos son los decisivos:

```json
"rc_archscripts": 0,
"segundos_archscripts": 0.02,          <-- decisivo
"archscripts_hizo_trabajo": false,     <-- decisivo
"error_126_serial": false,
"error_126_paralelo": false,
"rc_build": 0,
"pahole": "/usr/bin/pahole",
"parche_al_ack": false
```

Y la salida cruda de `v3-ocho-archscripts.txt` muestra el arreglo **presente en el comando** y el paso sin trabajo:

```
make ... HOSTCFLAGS='-DUSE_PKCS11_ENGINE' -j1 archscripts
rc = 0 | segundos = 0.02
make[1]: Nothing to be done for 'archscripts'.
```

El falsador que el proyecto declaró **antes** de correr, en `respuestas/2026-09-07-01-*` §6: *"si vuelve a dar 0,0 s, el arreglo no se aplicó y no hay que interpretar nada más"*. **Dio 0,02 s.**

**Traducción:** el 126 no apareció en esta corrida **con el guard sin hacer trabajo**, así que el guard no puede explicar su ausencia. Es **una carrera ganada, no cerrada**, y el 126 está medido como **intermitente** por este mismo proyecto. Cerrarlo necesita **una matriz de N corridas del mismo brazo contando fallos**: es `needs-runtime` y no existe todavía.

---

## 3 · Archivos que hoy mienten, y siguen sin corregirse

No los edito acá porque son canónicos y tocarlos de paso es cómo se sobrescribe trabajo ajeno. **Pero que lleven dos días así es el señalamiento más incómodo de la segunda auditoría de Tao, y tiene razón:** son cuatro líneas, son lo más barato del repo, y en vez de corregirlas se escribieron dos documentos nuevos para explicar por qué mienten.

| Archivo | Dice | Es |
|---|---|---|
| `CONTEXTO-SIAO.md` §3 | *"existe `.github/workflows/falsador-userland-arm64.yml`"* | **falso en `main`**: hay dos y son `falsador-kvm-runners.yml` y `falsador-kvm-usermod.yml` |
| `CONTEXTO-SIAO.md` §3 | *"no hay kernel compilado"* | **falso**: ocho builds, `vmlinux` de 354.673.168 B, `Module.symvers` de 16.036 líneas |
| `README.md` | *"nada de este repo corrió todavía en ninguna máquina"* | **falso**: rootfs construido, GKI arrancado en QEMU en 2,2 s, ocho builds. *"Cero dispositivo"* **sí** sigue siendo cierto |
| `README.md` | Android tiene *"una sola función en la vida: que sigan andando WhatsApp, **el banco**"* | el **ADR-001 §8** declara *"sin Play Integrity → apps bancarias · **no hay solución legal completa**"*. La promesa de portada es justo lo que el ADR sabe que no se entrega |
| `mediciones/INDICE.md` (en la rama) | **dos** filas para F-004d@6.1: una `NO MEDIDO` y otra `VERDE` | la vieja no se borró. Y su encabezado lo declara **gate** del falsador siguiente: un gate que se contradice no gatea |
| `ADR-001` §7 Fase 1 | pide *"(16K aligned) sobre GKI recompilado"* | FALSADOR-001 lo mató (H-006 del cementerio): los 146 ELF ya vienen con `p_align 65536` |

---

## 4 · Cómo leer una rama sin clonarla

La API de GitHub acepta el nombre de rama en `ref`. No hace falta checkout:

```
GET /repos/gatehot59-star/siao/contents/mediciones/f-004d-61/F-004d-61-VEREDICTO.txt?ref=titan/f-004-kmi
```

**Dos advertencias, cada una con su error ya cometido:**

1. **Listar un directorio devuelve nombres y tamaños, no contenido.** Un `ls` de `mediciones/f-004d-61/` muestra 46 archivos y no dice qué dice ninguno. El veredicto está **adentro** del archivo que se llama `VEREDICTO`. *(Costado: un auditor concluyó `NO MEDIDO` sobre un verde.)*
2. **Citar un subconjunto de campos es recorte de evidencia.** Cité seis de los ocho campos de `v3-ocho.json` y omití justo los dos que el falsador del proyecto vuelve decisivos. *(Costado: el `Error 126` quedó leído como resuelto cuando sigue abierto.)*

Son el mismo defecto con distinto radio: **no leer el archivo, y leerlo y recortarlo.**

---

## 5 · Mantenimiento

Se actualiza **en el mismo turno** en que una medición cierra, junto con el recibo. Si su fecha de verificación es anterior al último archivo de `docs/agents/respuestas/`, **está desactualizado por definición**.

**NO MEDIDO en esta versión:** el contenido de los 15 instrumentos de `tools/` (así que **no puedo afirmar que midan lo que sus nombres dicen medir**; es la auditoría más cara y sigue sin hacerse); el contenido completo de `mediciones/f-004/`, `f-004-v3/`, `f-004b/` y `f-004d/`; y los ADR 002, 003 y 004.
