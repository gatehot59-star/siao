# ADR-008 · Resolución del diseño de F-001-S2 de FABLE 5.1

**Fecha:** 2026-09-08 · **Estado:** ACEPTADO con correcciones · **main al resolver:** `f213372`
**Antecedente:** ADR-007 (resolución de la primera auditoría de FABLE) y el pedido formal `docs/agents/pedidos/2026-09-08-PEDIDO-FORMAL-A-FABLE-51-disenar-F-001-S2.md`.

Le pedí a FABLE que, si al leer el repo encontraba que una pieza no decía lo que yo decía que decía, escribiera **eso primero**. Lo hizo, y encontró tres. **Los tres están confirmados midiendo.** Le refuto dos puntos menores, también midiendo.

---

## 1 · ACEPTADO · H-1: `llego_a_init: false` es NO MEDIDO

Confirmado, y **peor de lo que él vio**. No es solo el `head -200`: el código pone el campo en `True` **cuando encuentra un mensaje de FALLO de init**, así que el nombre es la negación de lo que calcula y un pánico habría dado `llego_a_init: true`.

Medición completa y corrección: **`mediciones/f-001-s1/CORRECCION-H1-el-campo-llego_a_init-nunca-midio-eso.md`**. La fila del mapa quedó corregida. Los JSON crudos **no se editan** (W-01).

**Lo que no cambia:** F-001-S1 sigue no siendo G0, por dos razones independientes del campo (GKI stock, sin rootfs).

## 2 · ACEPTADO · H-2: el kernel candidato no existe como artefacto arrancable

`tools/f004d61_build.py` compila `Image modules` (línea 270) y empaqueta `vmlinux` más los `.ko` (línea 311). **`arch/arm64/boot/Image` no entra al tar.** Confirmado leyendo el archivo.

Se adopta su plan, con las dos vías y el cruce:

1. **(b) canónico:** corregir el instrumento para que empaquete `Image`, y rebuildear el brazo `ocho`.
2. **(a) control:** recuperar `Image` del `vmlinux` con `llvm-objcopy -O binary -R .note -R .note.gnu.build-id -R .comment -S`.
3. **KAT gratis:** `sha256(objcopy(vmlinux)) == sha256(Image)` tiene que dar idéntico. Si no, algo del build no es lo que creemos.

### 2.1 · REFUTADO (parcial) · el `.config` ya se commitea

Su remedio pedía *"empaquetar `Image` y `.config`"*. El `.config` **ya está**: línea 303 del instrumento lo escribe como `mediciones/f-004d-61/v3-config-ocho.txt`, **205.550 B**, y es el archivo sobre el que corrí sus dos precondiciones (§4). Falta solo `Image`.

### 2.2 · MATIZADO · el `head -400` no cortó nada

Es un riesgo latente real, pero en esta corrida no se materializó. Verbatim del veredicto:

```
  baseline  vmlinux 353840120 B | modulos 60
  ocho      vmlinux 354673168 B | modulos 60
```

**60 módulos, tope 400.** Se declara y se quita, no se presenta como defecto medido.

## 3 · ACEPTADO · H-3: el instrumento de `main` no es el que corrió

`QEMU_BASE` (línea 38-39) lleva `-nic none`. El comando registrado en `f001s1-aarch64-boot.txt` **no** lo lleva. Y la línea 174 del log muestra `pci 0000:00:01.0: [1af4:1000] type 00 class 0x020000`: la NIC virtio, enumerada. Uno de los dos se editó después del otro. **R-15 roto:** el índice apunta al instrumento actual, no al SHA del que produjo la evidencia.

**Nota de familia:** el instrumento de `main` **también** trae el `| head -200` (línea 154). O sea el defecto de H-1 no es solo histórico: está vivo en el archivo presente.

## 4 · Sus dos precondiciones, corridas GRATIS antes de gastar un run

Sobre `mediciones/f-004d-61/v3-config-ocho.txt`, que ya estaba en `main`.

**Precondición 1 · esperaba 16. Dio 16.**

```plain
CONFIG_AUTOFS_FS=y      CONFIG_BLK_DEV_INITRD=y   CONFIG_CGROUPS=y      CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y CONFIG_EPOLL=y            CONFIG_FHANDLE=y      CONFIG_INOTIFY_USER=y
CONFIG_IPC_NS=y         CONFIG_PID_NS=y           CONFIG_POSIX_MQUEUE=y CONFIG_RD_GZIP=y
CONFIG_SIGNALFD=y       CONFIG_TIMERFD=y          CONFIG_TMPFS=y        CONFIG_UNIX=y
--- CUENTA --- 16
```

**Precondición 2 · predijo "vacío o `=m`". Salió MÁS FUERTE: `is not set`.**

```plain
1898:# CONFIG_VIRTIO_BLK is not set
5485:# CONFIG_VIRTIO_PCI is not set
5490:# CONFIG_VIRTIO_MMIO is not set
2140:# CONFIG_VIRTIO_NET is not set
2900:# CONFIG_VIRTIO_CONSOLE is not set
1483:# CONFIG_VIRTIO_VSOCKETS is not set

--- lo VIRTIO que SÍ está en y ---
CONFIG_VIRTIO=y  CONFIG_VIRTIO_ANCHOR=y  CONFIG_VIRTIO_FS=y  CONFIG_VIRTIO_MENU=y  CONFIG_VIRTIO_VSOCKETS_COMMON=y

--- control positivo del grep ---
3832 líneas con 'is not set'  -> el archivo usa esa forma, así que la ausencia es ausencia real
```

**Consecuencias, y las tres refuerzan su diseño:**

1. **El initramfs no es la mejor vía: es la única.** `virtio-blk` no está ni como módulo. Mi opción "imagen raw con `virtio-blk`" del pedido **no existía**, tenía razón él.
2. **`virtiofs` tampoco sirve**, aunque `CONFIG_VIRTIO_FS=y`: su transporte (`VIRTIO_PCI`/`VIRTIO_MMIO`) está apagado.
3. **`console=ttyAMA0` es correcto** y no una preferencia: `VIRTIO_CONSOLE` está apagado, así que la PL011 es la única consola.

### 4.1 · REFUTADO · `BINFMT_MISC` no es candidata de `degraded`

Nombró `systemd-binfmt.service` entre las candidatas *"si `BINFMT_MISC` no está en GKI"*. Sí está:

```plain
920:CONFIG_BINFMT_MISC=y
```

Queda **una candidata menos**. Las otras dos (`console-setup` sin `/dev/tty1`, unidades de red) siguen en pie y no las medimos todavía.

## 5 · Lo que se adopta del diseño, sin cambios

- **P1 · la tabla de veredictos**, incluido `degraded` como VERDE-CONDICIONADO con `systemctl --failed` enumerado y la atribución por errno. Su criterio de "causa de kernel" (`No such device`, `Function not implemented`, `Operation not supported`, `Invalid argument` sobre `mount`/`socket`/`ioctl`, `Failed to mount`) es operativo y se usa tal cual.
- **P1 · la distinción `starting` al vencer el timeout → NO MEDIDO si la consola avanzó en los últimos 120 s.** Es la regla de los tres estados aplicada a un cuelgue, y es mejor que mi "timeout = rojo".
- **P2 · Actions x64, TCG, 900 s por brazo y 45 min de job.** Y el punto de que el terminador esperado **no es el timeout** sino `systemctl poweroff`, con los cuatro terminadores registrados (`poweroff | panic | freeze | timeout`).
- **P3 · el initramfs en tres archivos** (base `cpio.gz` + sonda `cpio` sin comprimir + concatenación), para preservar la identidad del rootfs.
- **P3 · `nod /dev/console 0600 0 0 c 5 1` en la sonda.** Sin él, `Warning: unable to open an initial console` y la sonda escribe al vacío.
- **P3 · `DefaultDependencies=no`** para evitar el ciclo `multi-user.target → Wants → After multi-user`.
- **P3 · `rdinit=` y no `init=`**, y **sin `root=`** para que el rootfs sea tmpfs y `TMPFS_XATTR` aplique.
- **P3 · `-serial file:` en vez de `-nographic | head`.** Es el fix de H-1 metido en el arnés nuevo.
- **P3 · `panic=5` + `-no-reboot`**, y `Freezing execution.` como **terminador** del arnés: sin eso el control se come los 900 s.
- **P3 · las líneas `ns=`, `devtmpfs=`, `cgroup2=`, `mqueue=`, `autofs=`** de la sonda: confirman en **runtime** los ocho símbolos que `stgdiff` solo vio en la ABI. Cuestan cero y valen mucho.
- **P4 · el control negativo con el MISMO `initrd` byte a byte y el GKI stock `android14-6.1`** (no el de 6.6 de S1: misma generación, R-17). Y su criterio de invalidación: **si el control muestra `SIAO-G0|is-system-running=`, el sujeto no midió nada.**
- **P5 · la predicción**, registrada acá **antes** de correr: `running`, terminador `poweroff`, `ns=` con `pid` e `ipc`, `devtmpfs=1 cgroup2=1 mqueue=1 autofs=1`, y el control en `Freezing execution.`
- **P6 · el alcance**, incluido el punto que yo no tenía: el `vermagic` de este kernel **no** coincide con el del Pixel porque se construyó con `make gki_defconfig` y no con Kleaf. Irrelevante para G0, **decisivo para F-007c**.
- **§4 · los 10 hitos y la tabla de rojos con atribución.** Se usan literales.
- **§5 · la identidad del rootfs antes de arrancar:** `dpkg-query -W | wc -l == 177` y `stat -c %s usr/lib/systemd/systemd == 133384`. Si no coinciden, no es `siao-base-s1` y el run no se interpreta.
- **§6 · correr el CONTROL PRIMERO.** Si el control no congela como predice, se para y se escribe: el sujeto no se interpreta sobre un control que no discrimina.

## 6 · Orden de ejecución aprobado

| # | Paso | Costo | Estado |
|---|---|---|---|
| 0 | precondiciones sobre `v3-config-ocho.txt` | **0** | **HECHO** (§4): 16/16 y virtio apagado |
| 1 | corregir `f004d61_build.py` (empaquetar `Image` y `.config`; quitar `head -400`) y rebuildear el brazo `ocho` | **1 run de Actions** | espera OK de Abraham |
| 2 | cruzar `sha256(objcopy(vmlinux))` con el `Image` del rebuild | 0 | tras el paso 1 |
| 3 | bajar el GKI certificado `android14-6.1` para el control | red | tras el paso 1 |
| 4 | reconstruir `siao-base-s1` y verificar identidad (177 / 133.384 B) | ~158 s | tras el paso 1 |
| 5 | correr **control primero**, después sujeto; commitear consolas enteras; veredicto aparte | 2 runs | tras 2-4 |

**Nada del paso 1 en adelante se dispara sin OK**, porque gasta runs y porque el paso 1 toca un instrumento y **ningún script se commitea sin ejecutarlo**.

## 7 · NO MEDIDO después de este ADR

- **F-001-S2 en sí.** Hay diseño aceptado y predicción registrada; no hay corrida.
- **Si los artifacts de Actions con el `vmlinux` del brazo `ocho` siguen vivos** (retención por defecto 90 días). Él lo declaró NO MEDIDO y lo sigue estando: no lo verifiqué.
- **Los otros 12 instrumentos de `tools/`.** FABLE auditó tres. La auditoría más cara del proyecto está empezada, no hecha.
- **F-007c, red, gráficos, disco real (F-004f), LXC y F-009.** Igual que antes.
