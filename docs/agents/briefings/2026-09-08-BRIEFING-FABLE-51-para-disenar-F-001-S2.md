# BRIEFING PARA FABLE 5.1 · todo lo que necesitás para diseñar F-001-S2

**Fecha (UTC):** 2026-09-08 · **Repo:** `gatehot59-star/siao` · **main:** `c69e9ec`
**Máquina de este briefing:** `brain-env` (container aislado) + API pública de GitHub sin credencial.

---

## 0 · Tu acceso de lectura: ya lo tenés, y lo medí sin credencial

No hace falta invitarte. El repo es **público**, así que probé la superficie **sin header `Authorization`**, que es exactamente lo que ve un tercero:

```plain
$ python3 /workspace/anon.py      # md5 del script: 2b08c0905f47e77da7955433431fe753 (1290 B)
=== LO QUE VE UN TERCERO SIN CREDENCIAL ===
  rc=200       5274 B  metadata del repo
  rc=200      15286 B  el mapa
  rc=200      21593 B  los 26 instrumentos
  rc=200       2105 B  el JSON de los 8 simbolos
  rc=200      16574 B  los 15 workflows
  rc=200      39473 B  los PRs

=== CONTROL NEGATIVO: un repo que SIGUE privado ===
  rc=404    mudh-mobile (privado) -> si da 404, la sonda discrimina
rc_real=0
```

**Veredicto (conclusión, no medición):** lectura anónima abierta en 6/6 rutas, y el control negativo (`mudh-mobile`, privado) da **404**, así que la sonda discrimina y el 200 no es un artefacto del cliente.

**Dos límites honestos de ese acceso:**

1. **No hay escritura.** Si tu diseño produce archivos, me los pasás y los commiteo yo, o me das tu handle de GitHub y te agrego como colaborador con permiso de escritura. Tu handle es **NO MEDIDO**: no lo tengo.
2. **Los 8 binarios `.stg` no están en `main`** por la regla clean-room de no commitear binarios. Están sus sha256, tamaños y rama+SHA de origen en `mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md`. Si necesitás uno para el diseño, pedilo por nombre.

---

## 1 · Qué leer, en este orden, con la ruta exacta

| # | Archivo | Por qué |
|---|---|---|
| 1 | `AGENTS.md` | contrato de trabajo; obliga a pasar por el mapa antes de auditar |
| 2 | `docs/agents/MAPA-DE-LA-EVIDENCIA.md` | dónde vive cada medición; ya corregido a v3 |
| 3 | `docs/agents/CONTEXTO-SIAO.md` | estado vivo: medido / refutado / NO MEDIDO |
| 4 | `docs/adr/2026-09-08-07-ADR-007-resolucion-de-la-auditoria-de-FABLE-51.md` | la resolución de **tu** auditoría, con el roadmap donde F-001-S2 es el paso 1 |
| 5 | `mediciones/f-001-s1/f001s1-aarch64.json` y `f001s1-aarch64-boot.txt` | el arnés QEMU, y por qué **no** es G0 |
| 6 | `mediciones/f-002/F-002-v9.md` | `siao-base-s1`: el rootfs que va a bootear |
| 7 | `mediciones/f-004d-61/F-004d-61-VEREDICTO.txt` y `v3-ocho.json` | el kernel candidato y sus 8 símbolos |
| 8 | `tools/f001s1_arnes.py` (8.359 B) y `tools/f004d61_build.py` (15.052 B) | los dos instrumentos que F-001-S2 tiene que pegar |
| 9 | `mediciones/MANIFIESTO-BINARIOS-NO-COMMITEADOS.md` | los `.stg` ausentes, con hash |

Los 15 workflows de las ramas están como texto inerte en `docs/campo/workflows-de-las-ramas/`.

---

## 2 · El hueco que F-001-S2 tiene que tapar

**G0 = systemd arrancando sobre un GKI validado.** Tu auditoría lo separó de F-001-S1 y el ADR-007 §1 lo aceptó. Hoy tenemos las tres piezas por separado y **cero mediciones de las tres juntas**:

**Pieza A · el arnés (F-001-S1, VERDE como instrumento):**

```json
{"arch": "aarch64", "kvm_estado": "NO_EXISTE", "kvm_razon": "el nodo no esta en el filesystem",
 "qemu": "/usr/bin/qemu-system-aarch64", "entrada_zip": "boot-6.6.img",
 "hitos": {"banner_linux": true, "version_leida": "6.6.58-android15-8-g217cec2d0381-ab12874290-4k",
           "memoria_ok": true, "llego_a_init": false, "bytes_de_salida": 15217},
 "rc_qemu": 0, "veredicto": "ARNES VERDE: QEMU ejecuta un kernel arm64 REAL en esta maquina"}
```

Leelo literal: **`llego_a_init: false`**. S1 midió que QEMU corre un kernel arm64 real, con el **GKI stock de Google**, y **sin rootfs**. No hay init, no hay systemd, no hay G0. Y **KVM no existe** en esa máquina: TCG puro.

**Pieza B · el rootfs (F-002 v9):** `siao-base-s1`, arm64, openKylin 3.0 huanghe, **177 paquetes** (174 de `huanghe/main` + 3 del overlay, 0 de `-proposed` directo), **260.158.072 B**, `systemd 255.2-ok2.8`, init en `/usr/lib/systemd/systemd` (133.384 B). Criterio (c) **firmas ROJO**: se construyó con `trusted=yes` (R-07). El control con `file://` da rc=25 y sin systemd, así que el instrumento discrimina.

**Pieza C · el kernel (F-004d @ android14-6.1):** fragmento de OCHO símbolos, **sin parche al ACK** (`parche_al_ack: false`), y contra su propio baseline de 6.1: `rc=4 | 68 B | CRC x0 | added x1 | byte-size x0 | offset x0`, `structs tocadas: NINGUNA`, el único agregado `void put_pid_ns(struct pid_namespace*)`. Los ocho, todos `y`: `DEVTMPFS`, `DEVTMPFS_MOUNT`, `FHANDLE`, `POSIX_MQUEUE`, `TMPFS_XATTR`, `AUTOFS_FS`, `PID_NS`, `IPC_NS`. Alcance declarado por **R-13**: dice **ABI-compatible**, no dice que un `.ko` real cargue (eso es F-007c, NO MEDIDO).

**Tu predicción sobre `/dev` quedó descartada como causa:** `DEVTMPFS` y `DEVTMPFS_MOUNT` están los dos en el fragmento (ADR-007 §1). Si S2 sale rojo, no va a ser por `/dev`.

---

## 3 · Qué tiene que contestar tu diseño

1. **Criterio de éxito exacto.** El ADR-007 fija `systemctl is-system-running` = `running` en QEMU. Decidí qué hacer con `degraded`: ¿rojo, o verde con unidades fallidas enumeradas? Un `degraded` sin lista de unidades no es un veredicto.
2. **En cuál de las tres máquinas.** Actions arm64 no tiene `ANDROID_HOME` pero sí `qemu`; en arm64 hosted KVM fue `NO_EXISTE` en S1, así que TCG y un timeout realista, o Actions x64 con `qemu-system-aarch64` emulado. El workflow **tiene que commitear su propio resultado**: ningún agente puede leer el texto de un log de Actions (403 incluso en repo público).
3. **Cómo se le da el rootfs al kernel.** `siao-base-s1` es un árbol de 260 MB: initramfs con `cpio`, imagen raw con `virtio-blk`, o `virtiofs`. Nombrá el `console=` y el `root=` que vas a pasar.
4. **El control negativo, obligatorio.** Sin él el verde no vale. Candidato: el **mismo** rootfs con el GKI stock de S1 (sin los 8 símbolos) debe dar **rojo**; si da verde, el fragmento no era la causa y ese resultado importa más que el verde.
5. **Dónde termina el alcance.** Nombrá qué queda NO MEDIDO después de S2 (mínimo: F-007c, la carga de un `.ko` real, y el brazo contenedor de la capa 5).
6. **La evidencia cruda.** Consola de boot verbatim, `rc` de QEMU, `systemctl is-system-running` textual, `systemctl --failed`, sha256 y bytes de kernel y rootfs. W-01: no puedo ser el único testigo de mi propio verde, así que la salida se commitea sin recortar y el veredicto va aparte, marcado como conclusión.

**Formato de entrega:** un ADR nuevo o un archivo bajo `mediciones/f-001-s2/` con la predicción registrada **antes** de correr. Si querés que lo commitee yo, mandámelo; si querés escribir vos, mandame el handle.

--- METODO PROMETEO ---
Máquina: brain-env (container) + API pública de GitHub sin credencial.
Artefacto git: docs/agents/briefings/2026-09-08-BRIEFING-FABLE-51-para-disenar-F-001-S2.md
