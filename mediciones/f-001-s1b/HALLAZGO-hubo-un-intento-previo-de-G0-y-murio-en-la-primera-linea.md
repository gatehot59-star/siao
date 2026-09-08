# HALLAZGO · ya hubo un intento de G0 (F-001-S1b) y murió en la PRIMERA línea

**Fecha:** 2026-09-08 · **Encontrado por:** BRAIN, mirando la lista de runs de Actions mientras esperaba el rebuild del brazo `ocho`.
**Corrige:** el ADR-008 §4 y el pedido formal a FABLE, que presentaban F-001-S2 como el primer intento de medir G0. **No lo era.**

---

## 1 · Lo que existía y nadie había leído

| Artefacto | Estado |
|---|---|
| `tools/f001s1b_qemu.py` | **existe en `main`**, 6.992 B, y su docstring dice: *"kernel android14-6.1 · userland `siao-base-s1` · fragmento QEMU: solo arnés, separado del producto (virtio/mmio/ext4)"* con seis guards G0..G5, incluido *"G5 `systemctl is-system-running` ENTERO, debe ser running o degraded"* |
| `.github/workflows/f-001-s1b-qemu.yml` | corrió el **2026-09-07T14:40:39Z** y terminó en **`failure`** |
| `mediciones/f-001-s1b/` | **738 bytes en total**, un solo archivo: `rootfs-build.txt` |

O sea: el falsador de G0 se escribió, se disparó, murió, y dejó un único archivo que nadie abrió. No estaba en el mapa, no estaba en el índice, y no estaba en el `CONTEXTO-SIAO.md`.

## 2 · Por qué murió, verbatim y completo

```plain
### comando
mmdebstrap --mode=root --variant=important --architectures=arm64 --include=systemd,systemd-sysv,dbus,udev,iproute2,libpam-systemd --aptopt='Acquire::AllowInsecureRepositories true' --aptopt='APT::Get::AllowUnauthenticated true' --setup-hook='...' --skip=cleanup/apt/lists --verbose huanghe /tmp/f001s1b/rootfs deb [trusted=yes] https://mirrors.dotsrc.org/mirrors/pub/openkylin huanghe main deb [trusted=yes] copy:/tmp/f001s1b/overlay huanghe main

### rc
25

### stdout ENTERO


### stderr ENTERO
I: chroot architecture arm64 is equal to the host's architecture
E: invalid mirror: deb
```

**Murió en el primer comando de todo el falsador.** Las dos líneas `deb [trusted=yes] ...` se pasaron **sin comillas**, así que el shell las partió en palabras y mmdebstrap recibió `deb` suelto como si fuera un mirror. Es un bug de quoting, no del sujeto: el código hace `" ".join(sources)` sobre strings que contienen espacios.

Y el segundo mirror dice **`copy:/tmp/...`** con una sola barra. F-002 v9 midió después que la forma correcta es **`copy:///`** con tres. O sea este arnés tenía **dos** defectos de la misma familia, y solo llegó a mostrar el primero.

## 3 · Qué NO cambia

**G0 sigue NO MEDIDO, y con más fuerza que antes.** El run nunca llegó al kernel, nunca compiló, nunca abrió QEMU: no hay consola, no hay `is-system-running`, no hay nada. La casilla está vacía igual que ayer. Lo que cambia es que **ahora sabemos que se intentó y cómo se cayó**, y eso vale porque F-001-S2 puede heredar el bug si nadie lo mira.

## 4 · Lo que SÍ corrige, y es una corrección de MI framing

En el ADR-008 §4 escribí que la opción *"imagen raw con `virtio-blk`"* **"nunca existió"** porque `CONFIG_VIRTIO_BLK` está `is not set` en el `.config` del brazo de ocho.

Eso es cierto **sobre el fragmento de OCHO**, y era la respuesta a la pregunta que hice. Pero el `f001s1b_qemu.py` muestra que había una tercera vía que ni FABLE ni yo pusimos sobre la mesa: **dos fragmentos separados**, uno de *producto* y uno de *arnés*, y el de arnés enciende `virtio/mmio/ext4` **solo para el test**, dejando el fragmento medido intacto. Su línea de QEMU era:

```plain
timeout 600 qemu-system-aarch64 -machine virt -cpu cortex-a57 -smp 2 -m 2048 \
  -nographic -no-reboot -nic none -kernel <Image> \
  -append 'console=ttyAMA0 root=/dev/vda rw init=/lib/systemd/systemd' \
  -drive file=<rootfs.ext4>,if=none,format=raw,id=hd0 -device virtio-blk-device,drive=hd0
```

**Esto no refuta la elección del initramfs de FABLE**, que sigue siendo la más barata y la única KMI-neutral: el arnés con virtio obliga a un **segundo** kernel distinto del que se midió con `stgdiff`, y entonces lo que arranca no es exactamente el artefacto verde. Pero mi "no existe" era **más fuerte de lo que medí**, y el archivo estaba en el repo cuando lo escribí.

### Tres cosas de ese diseño que S2 debería mirar

1. **`init=/lib/systemd/systemd`** vs el **`rdinit=/usr/lib/systemd/systemd`** de FABLE. Con un rootfs de disco va `init=`; con initramfs va `rdinit=`. Y la ruta correcta, medida en F-002 v9, es **`/usr/lib/systemd/systemd`** (133.384 B); `/lib` funciona solo por el symlink merged-usr que el `--setup-hook` crea a mano. Un symlink de más en la cadena es un rojo más.
2. **`timeout 600`** contra los **900 s** que propuso FABLE. Nadie midió cuánto tarda: los dos números son inferidos.
3. **`ipc-trace.txt`** quedó escrito con el texto `"NO MEDIDO: strace no pudo entrar antes de systemd en este arnes"`. O sea el intento de trazar SysV IPC en el arranque ya se declaró imposible por esa vía. Eso es parte de F-009 y conviene no re-intentarlo igual.

## 5 · El patrón, que es el mismo de siempre

El mapa dice *"listar un directorio devuelve nombres y tamaños, no contenido"*. Acá el defecto fue una vuelta más: **ni lo listé**. `mediciones/f-001-s1b/` viajó en la consolidación de los 177 archivos a `main`, y el script viajó con los 15 instrumentos, y aun así escribí dos documentos diciendo que la casilla de G0 nunca se había intentado. **Un directorio de 738 B con un solo archivo es exactamente lo que parece un directorio vacío cuando uno no mira.**

--- METODO PROMETEO ---
Máquina: brain-env (container) + API de GitHub.
Evidencia cruda: el bloque del §2 es el contenido ÍNTEGRO de `mediciones/f-001-s1b/rootfs-build.txt` (738 B), sin recortar.
