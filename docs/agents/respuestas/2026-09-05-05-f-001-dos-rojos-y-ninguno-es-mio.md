# 2026-09-05 · F-001: dos ROJOS medidos, y ninguno de los dos es mío

## 1. Pedido literal

> "Corré F-001 en Actions arm64"

Corrió. **Tres corridas** en `ubuntu-24.04-arm` (aarch64 nativo, `runner_id`
1000002022, 1000002023, 1000002024), cada una commiteando su propia salida cruda.

## 2. Veredicto

| Brazo | Veredicto | De quién es el rojo |
|---|---|---|
| **C** · el `.config` REAL del GKI | **ROJO** | **del GKI de Google** |
| **F-002** · rootfs con `mmdebstrap` | **ROJO** | **del repo de openKylin** |
| F-003 · alineación a escala | NO MEDIDO | sin rootfs |
| P · control positivo en QEMU | NO MEDIDO | sin rootfs |
| S · el sujeto (GKI) | NO MEDIDO | sin control positivo |

---

## 3. ROJO 1 · el GKI de fábrica NO puede hostear el contenedor de apps

Bajé el `gki-certified-boot-android16-6.12-2026-06_r1.zip` de Google (17.317.996 B,
sha256 `5469126621456bf79c4a8c8114e13e0a8e5173e61b21754cd056ec188953cd5a`), saqué el
`Image` del `boot.img` (`hdr_v4`, `kernel_size=42441216`) y extraje el **`.config`
embebido** por `IKCFG_ST`: **Linux/arm64 6.12.81, 6.522 símbolos, 8.187 líneas**,
commiteado en `mediciones/f-001/gki-android16-6.12.config`.

```plain
CONFIG_PID_NS      APAGADO (# is not set)
CONFIG_USER_NS     APAGADO (# is not set)
CONFIG_IPC_NS      AUSENTE del .config
CONFIG_DEVTMPFS    APAGADO (# is not set)
CONFIG_CGROUP_PIDS APAGADO   CONFIG_CGROUP_DEVICE APAGADO
CONFIG_FANOTIFY    APAGADO   CONFIG_TMPFS_XATTR   APAGADO
CONFIG_AUTOFS_FS   APAGADO   CONFIG_CHECKPOINT_RESTORE APAGADO
```

### El testigo independiente

No lo digo yo, lo dice **`lxc-checkconfig` 5.0.3** corrido contra ese `.config`:

```plain
--- Namespaces ---
Ipc namespace: required
Pid namespace: required
User namespace: missing
--- Control groups ---
Cgroup device: missing
--- Misc ---
Macvlan: missing
--- Checkpoint/Restore ---
checkpoint restore: missing
```

**Esto cierra el caveat que declaré en el ADR-002 y va más lejos que el defconfig:
el `.config` real es PEOR.** El defconfig sólo delataba `PID_NS`; el config real
agrega `USER_NS`, `IPC_NS` y **`DEVTMPFS`**, que es con lo que `systemd` monta
`/dev`.

**Consecuencia para el ADR-001, y no es opcional:** la opción C **exige construir
una variante propia de GKI**. El kernel certificado de Google, tal como viene, no
puede correr ni el contenedor LXC de apps ni un `systemd` normal. Y eso arrastra el
riesgo ya nombrado: todo `CONFIG_*` que toque símbolos del KMI **rompe los DLKM del
vendor**.

### Un dato de diseño del arnés que salió del mismo config

```plain
CONFIG_VIRTIO_BLK     =m MODULO (system_dlkm, NO en el boot.img)
CONFIG_VIRTIO_PCI     =m MODULO
CONFIG_VIRTIO_CONSOLE =m MODULO
CONFIG_BLK_DEV_INITRD =y
```

Por eso el falsador arranca por **initramfs y no por disco**: con un disco virtio el
GKI no podría montar la raíz nunca, y eso sería un límite del **arnés** disfrazado de
ROJO del userland. Con initramfs, P y S usan el mismo método y la única variable es
el kernel.

Y de paso: **`CONFIG_ARM64_4K_PAGES=y`, `ARM64_16K_PAGES` APAGADO.** El GKI
certificado que bajé es de 4 KB: los dispositivos de páginas de 16 KB usan otro
build. Eso **no** contradice al FALSADOR-001 (que midió la **alineación** del
userland, no el tamaño de página del kernel), pero hay que no confundirlos.

---

## 4. ROJO 2 · `systemd` NO es instalable desde `huanghe/main` en arm64

Cuatro vías para construir el rootfs, y dos de ellas llegaron al **mismo** muro:

```plain
The following packages have unmet dependencies:
 libcryptsetup12 : Depends: libdevmapper1.02.1 (>= 2:1.02.197)
                   but it is not going to be installed
E: Unable to correct problems, you have held broken packages.
```

Los números exactos, leídos del índice oficial:

| Paquete | Versión en `huanghe/main` arm64 | Qué pide |
|---|---|---|
| `systemd` | `255.2-ok2.8` | `libcryptsetup12 (>= 2:2.4)` |
| `libcryptsetup12` | `2:2.8.4-1ok10` | **`libdevmapper1.02.1 (>= 2:1.02.197)`** |
| `libdevmapper1.02.1` | **`2:1.02.196-ok2`** | **una versión por debajo** |

**La cadena está rota en el repo de openKylin, no en mi script**, y lo dijeron **dos
resolvedores independientes**: el `apt` que usa `mmdebstrap` y mi propio `apt` con
`status` vacío. Dos instrumentos distintos, el mismo veredicto.

### Y no cerré en el obstáculo: la pieza que falta existe

```plain
huanghe/pty/binary-arm64            libdevmapper: NO ESTA
huanghe/cross/binary-arm64          libdevmapper: NO ESTA
huanghe-updates/main/binary-arm64   libdevmapper: NO ESTA
huanghe-security/main/binary-arm64  libdevmapper: NO ESTA
huanghe-proposed/main/binary-arm64  libdevmapper: ['2:1.02.205-ok1']   <-- SIRVE
yangtze/main/binary-arm64           libdevmapper: ['2:1.02.167-ok3']   (mas viejo)
```

**`huanghe-proposed` tiene `2:1.02.205-ok1`, que satisface el `>= 2:1.02.197`.** O
sea que el rootfs de SIAO necesita **`huanghe` + `huanghe-proposed`**.

**Está LOCALIZADO pero NO PROBADO:** no corrí el build con `-proposed`. Decirlo
como resuelto sería exactamente el verde que este proyecto persigue.

**Y es un hallazgo de producto, no de plomería:** la base de SIAO necesita un
componente `proposed` para instalar `systemd` hoy. Eso es deuda de la distro y hay
que saberlo antes de apoyar un roadmap de 30 meses encima.

---

## 5. DOS DEFECTOS MÍOS, y el cuarto disfraz del mismo ENOENT

1. **Vía 1:** `E: unable to get absolute path of target directory /tmp/f001/rootfs`.
   Hice `rm -rf` del directorio **padre** antes de llamar a `mmdebstrap`. Mío.
2. **Vía 2:** mi comilla dentro de `su -c` se comió el `SUITE`, y `mmdebstrap` se
   puso a esperar `sources.list` por stdin: *"No SUITE specified"*. Mío.
3. **El cuarto ENOENT del intérprete**, ahora en los `postinst` de `dpkg`:

```plain
dpkg (subprocess): unable to execute old mawk package postinst maintainer script
(/var/lib/dpkg/info/mawk.postinst): No such file or directory
```

Un `postinst` es un script de shell: ese `ENOENT` es `/bin/sh` que todavía no
resuelve en el árbol a medio extraer. **Cuatro apariciones del mismo error con
cuatro disfraces distintos en una sola jornada:** el chroot del FALSADOR-001, el
ensamblado del rootfs, el `chroot dpkg` de mmdebstrap y ahora un `postinst`. Ya no
es incidente, es patrón propio y va al cementerio con número.

**Un guard ajeno me salvó de mí mismo**, y merece decirse: mmdebstrap se negó a
correr `--mode=chrootless` como root con *"might damage the host system"*. No fue
un bug: fue un instrumento ajeno protegiendo la máquina.

---

## 6. La predicción sigue sin falsar

El script registró **antes de correr**: *"Predigo que S NO llega a multi-user"*.
**S quedó NO MEDIDO**, así que la predicción no acertó ni falló: sigue abierta. No
la cuento como acierto.

## 7. NO MEDIDO

- **P, S y F-003:** sin rootfs no hay arranque. Cero QEMU ejecutado.
- **Que `huanghe-proposed` cierre la cadena:** la versión alcanza, el build no corrió.
- **Si los `CONFIG_*` faltantes se pueden agregar al GKI sin romper el KMI.**
- **El `.config` de `android15-6.6`:** el loop cortó en la primera rama que anduvo.
- **Si `systemd` de openKylin arranca en un GKI parcheado.** Es la pregunta de
  F-001 y sigue abierta.

## 8. Contrato de cierre

- **Instrumentos:** `tools/f001_userland_sobre_gki.py`, `tools/f001_rootfs.py`
- **Workflow:** `.github/workflows/f-001-userland-sobre-gki.yml`
- **Evidencia cruda, commiteada por los propios runners** (rama
  `titan/f-001-userland-sobre-gki`): `mediciones/f-001/F-001-salida-cruda.txt`,
  `mediciones/f-001/rootfs-construccion.txt`, `mediciones/f-001/gki-android16-6.12.config`
- **Este archivo:** `docs/agents/respuestas/2026-09-05-05-f-001-dos-rojos-y-ninguno-es-mio.md`

--- METODO PROMETEO ---
**Máquina:** GitHub Actions **arm64** (aarch64 nativo, `nproc 2`, `kvm: false`, tres
corridas) como sujeto, y `brain-env` por el gateway para leer los índices `apt`.
**Cero QEMU ejecutado:** declarado.
**Artefacto 2 (ClickUp):** Doc del turno con los dos ROJOS y los dos defectos propios.
