# El Doc de KVM destraba F-001-S1, y el GKI de Google **arrancó** en QEMU

**Fecha:** 2026-09-06 · **Máquinas:** Actions **arm64** y **x64** en matriz, cero KVM usado. Árbol de trabajo: `titan/f-004-kmi`.

**Pedido:** Abraham me pasó su Doc *"SÍ DESTRABA: las TRES vías dan KVM usable en el runner x64"* con un *"esto te puede servir"*.

**Sirvió, y de una forma que su propio titular no anticipa.**

---

## 1 · Lo que el Doc aporta, y la consecuencia que no saca

Su medición, que re-verifiqué de forma independiente:

```plain
Actions x64   -> /dev/kvm USABLE   (mi guard: abre O_RDWR sin error)
Actions arm64 -> /dev/kvm NO_EXISTE (el nodo no esta en el filesystem)
```

**Las dos coinciden con lo que él midió. Pero la conclusión para SIAO es la inversa de la que su título sugiere:**

**KVM solo acelera cuando huésped y anfitrión comparten ISA.** El kernel de SIAO es **aarch64**:

| Máquina | `/dev/kvm` | ISA del huésped | ¿KVM sirve? |
|---|---|---|---|
| Actions **x64** | **USABLE** | arm64 sobre x86_64 | **NO: la ISA no coincide** |
| Actions **arm64** | **NO_EXISTE** | arm64 sobre aarch64 | **NO: no hay nodo** |

**Conclusión: F-001-S1 va por TCG (emulación pura) en las dos máquinas.** El valor real del Doc es **haberme ahorrado buscar una aceleración que para este caso no existe**, y el propio kernel lo confirmó en su arranque: `KVM is not available. Ignoring kvm-arm.mode`.

**Y de paso su lección de método entró al instrumento.** Él cuenta que un veredicto `SIN_KVM` colapsó tres estados (no existe / sin permiso / roto) y produjo una conclusión falsa sobre una salida correcta. Mi chequeo devuelve **los tres separados**, y ninguno se llama igual que otro.

---

## 2 · Y lo grande: el kernel ARRANCÓ

```plain
qemu-system-aarch64 8.2.2 | rc=0 en 2,2 s | 15.217 B de salida

[    0.000000] Booting Linux on physical CPU 0x0000000000 [0x411fd070]
[    0.000000] Linux version 6.6.58-android15-8-g217cec2d0381-ab12874290-4k
               (kleaf@build-host) (Android (11368308, +pgo, +bolt, +lto, +mlgo...
[    0.000000] KASLR enabled
[    0.000000] Machine model: linux,dummy-virt
[    0.000000] KVM is not available. Ignoring kvm-arm.mode
[    0.000000] psci: PSCIv1.1 detected in firmware.
[    0.000000] Dentry cache hash table entries: 262144
```

**El GKI certificado de Google, el mismo `boot.img` del que salí a leer el `.config` en F-001, EJECUTA en QEMU.** Banner leído, memoria mapeada, PSCI detectado, cachés inicializadas.

**Eso convierte el arnés de F-001-S1 de "pendiente" a VERDE MEDIDO.** Lo que falta ahora no es la máquina ni la herramienta: es **el kernel de SIAO + el rootfs**, que es exactamente el paso siguiente.

**Y el instrumento puede dar rojo, probado:** el control positivo con un `-kernel` inexistente **falla**, así que un "verde" acá no es el default del script.

---

## 3 · Tres defectos míos en tres corridas, todos cazados por la salida cruda

| Intento | Error | Qué clase de defecto |
|---|---|---|
| 15:17 | el zip trae `boot-6.6.img` y mi filtro pedía `endswith("boot.img")` | **guard demasiado estrecho: no falló, se salteó, con rc=0 y sin veredicto** |
| 15:23 | `failed to find romfile "efi-virtio.rom"`, rc=1 en 0,1 s | la máquina `virt` agrega una NIC virtio y su ROM PXE viene en `ipxe-qemu`. **Ni el kernel ni QEMU: mi invocación** |
| 15:30 | — | **VERDE** |

**El primero es el peor de los tres**, y es el patrón que este proyecto ya tiene nombrado: un chequeo que se saltea silenciosamente y sale con `rc=0`. El `exit code` no lo delató; **lo delató leer la salida**, que es literalmente lo que R-08 existe para forzar.

El segundo se arregló con `-nic none` (para arrancar sin rootfs la red no hace falta) **más** el paquete, o sea las dos vías y no una.

---

## 4 · Lo que queda por delante, ahora con el arnés medido

**F-001-S1 real** necesita tres piezas y las tres ya existen o son un build:

1. **El `Image` del kernel de SIAO.** F-004c dejó `vmlinux` y los `.ko`, **no** el `Image` arrancable. Hay que agregarlo al empaquetado. Un build.
2. **El rootfs.** F-002 lo construyó (177 paquetes, 248 MiB) pero **no quedó commiteado como tarball**. Hay que reconstruirlo o guardarlo. Un build.
3. **La consola.** El GKI arranca con `console=ttynull` en su cmdline embebido; para ver `systemd` hay que forzar `console=ttyAMA0` y armar el disco virtio.

**Y el dato de diseño que cambia por F-007b:** si el objetivo es un Pixel, el kernel va compilado de `android14-6.1`, no de `android15-6.6`. El arnés recién medido sirve igual para las dos generaciones.

---

## NO MEDIDO, declarado

- **`llego_a_init` salió `false`.** El kernel arrancó pero no llegó al pánico por falta de init en los 200 renglones que capturé: su cmdline embebido trae `console=ttynull`, así que probablemente siguió booteando en silencio. **Mi predicción decía "banner + pánico" y solo se cumplió la primera mitad.**
- **Cuánto tarda un boot completo en TCG.** El banner salió en 2,2 s; un `systemd` entero no está medido.
- **Si `systemd` levanta.** Es F-001-S1 propiamente dicho, y sigue pendiente.
- **El brazo x64** de esta corrida: leí el `.json` de arm64. El de x64 está commiteado y no lo abrí.
- **`emulator -accel-check`** del Doc de Abraham: no lo toqué, no hace falta para QEMU.

--- METODO PROMETEO ---
Máquinas: Actions arm64 y x64 en matriz. Cero KVM usado (medido irrelevante para este caso).
Artefacto en git: este archivo. Evidencia cruda: `mediciones/f-001-s1/` en `titan/f-004-kmi`
(`f001s1-aarch64.json`, `f001s1-aarch64-boot.txt`, `f001s1-aarch64-bitacora.txt` y sus pares de x64).
Instrumento: `tools/f001s1_arnes.py`.
Artefacto en ClickUp: Doc espejo enlazado en el cierre.
