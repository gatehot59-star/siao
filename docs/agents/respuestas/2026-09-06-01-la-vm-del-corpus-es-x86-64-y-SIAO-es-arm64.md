# La VM del corpus es x86_64 y SIAO es arm64: qué se puede probar ahí y qué no

**Medido:** 2026-09-06 · VM de Abacus (la del corpus legal), vía túnel Cloudflare
**Pedido de Abraham:** instalar un emulador de Android en esa VM para probar SIAO
**Veredicto corto:** sirve para **una** de las seis capas de SIAO, y **no es la que está bloqueada**.

---

## El hecho que decide, y va primero

| Sujeto | Arquitectura |
|---|---|
| **SIAO** | **arm64** (openKylin arm64, GKI arm64, `.ko` de Pixel 8, `p_align 65536`) |
| **La VM del corpus** | **x86_64** (`uname -m` = `x86_64`) |

**KVM solo acelera guests de la misma arquitectura que el host.** Medí que KVM funciona en esa VM (`ioctl(KVM_GET_API_VERSION)` = **12**), pero eso acelera **x86_64**. Un AVD **arm64** ahí correría por emulación TCG de QEMU, sin aceleración, **en 2 núcleos**.

**No estoy midiendo cuánto más lento**: eso es NO MEDIDO y no lo voy a estimar con un número inventado. Lo que sí es un hecho es que la aceleración no aplica.

## Y la máquina que SÍ es arm64 nativa ya está en uso

Del `CONTEXTO-SIAO.md`, medido el 2026-09-05: **GitHub Actions arm64** (`ubuntu-24.04-arm`, `runner_id 1000002018`), **aarch64 nativo, 2 vCPU**, y **seis jobs con runner real aunque el repo sea privado** (H-005 murió ahí). Toda la evidencia de SIAO hasta hoy salió de esa máquina.

O sea: **para lo arm64 ya hay una máquina nativa y gratis.** La VM x86_64 no la mejora, la empeora.

---

## Qué de SIAO se puede probar en esa VM, capa por capa

| Capa de SIAO | ¿Se prueba en la VM x86_64? | Por qué |
|---|---|---|
| Userland openKylin arm64 (rootfs, systemd) | **NO** | es arm64; y ya se construye en Actions arm64 |
| Kernel GKI con `PID_NS`/`USER_NS`/`IPC_NS` | **NO** | GKI es arm64, y el kernel no se prueba en un emulador ajeno |
| Los `.ko` / DLKM del Pixel 8 (`vermagic 6.1.157-android14-11`) | **NO** | arm64, y necesitan el device o su GKI |
| Contenedor LXC de Android sin `vendor` | **PARCIAL** | LXC corre acá, pero sin los HALs del SoC no es el sujeto real |
| **El Agent Bridge: binder, AIDL, AppFunctions, `EXECUTE_APP_FUNCTIONS`** | **SÍ** | es Java/Kotlin sobre AOSP: **la ABI de binder no depende del ISA** |
| La app de titiritero (meter la mano en el corralito) | **SÍ** | UI automation sobre un AVD x86_64 sirve igual |

**La única capa donde la VM aporta de verdad es el Agent Bridge**, que hoy está en **cero código**. Y para eso un AVD **x86_64 con KVM** es rápido y honesto: se prueba el contrato, no el fierro.

---

## Inventario medido de la VM (para esto)

| Recurso | Valor |
|---|---|
| Arquitectura | `x86_64` |
| Núcleos | **2** |
| RAM disponible | 6.334 MB de 7.957 |
| Swap | **ninguna** |
| Disco libre | **35 GB** de 48 |
| `/dev/kvm` | **API 12**, y `ubuntu` ya en el grupo `kvm` (lo destrabé el 2026-09-06) |
| `Xvfb` / `xvfb-run` | **ya instalados** |
| `docker` | presente, `ubuntu` en el grupo |
| `binfmt_misc` | montado, **sin ningún handler registrado** (solo `register` y `status`) |
| `qemu-aarch64-static`, `systemd-nspawn` | **ausentes** |

**Disponible en apt** (medido, no supuesto):

```
qemu-user-static   1:8.2.2+ds-0ubuntu1.18
qemu-system-arm    1:8.2.2+ds-0ubuntu1.18
lxc                1:5.0.3-2ubuntu7.2
mmdebstrap         1.4.3-6
openjdk-17-jdk-headless  17.0.20+8-1~24.04
```

**Ausentes y necesarios para un AVD:** `java`, `adb`, `sdkmanager`, `avdmanager`, `emulator`. No existe `~/Android` ni `ANDROID_HOME`.

### Trampa de medición cazada en esta corrida

Un bucle `for p in ...; do apt-cache policy $p; done` devolvió **`SIN_CANDIDATO` siete veces**. Era **falso**: el shell del gateway pre-expande `$`, así que `$p` viajó vacío y `apt-cache` no consultó nada. Lo cacé porque `openjdk-17-jdk-headless` ya lo había medido **con candidato** minutos antes. Sin ese dato previo habría publicado que la VM no puede instalar nada.

**Un cero producido por una variable vacía se ve igual que una ausencia real.** Rehecho sin bucle.

---

## El riesgo, y no es técnico

**Esa VM sirve el corpus legal en producción.** `corpus-api` está `active` y usa **24,8 MB** de RAM, así que la memoria no es el problema: **son los 2 núcleos.** Un emulador arranca a full CPU 30-120 s y eso compite con el buscador que el bufete va a usar.

Y la VM **factura por tiempo encendido**: un emulador olvidado prendido es plata de Abraham. **El costo por hora es NO MEDIDO por mí.**

Abraham pidió explícitamente que esto vaya **separado del corpus**. La separación real es:

- **Datos:** el SDK y el AVD en `/home/ubuntu/siao/`, nunca en `/var/www/corpus` ni tocando `rag-abogacia-v7.db`.
- **CPU:** el emulador acotado a **1 núcleo** (`taskset -c 1`), dejando el 0 para el corpus.
- **Falsador obligatorio:** `time curl /buscar?q=vendimia` **antes y después** de bootear. Si el buscador se degrada, el emulador no sirve.

---

## Lo que hay que decidir antes de instalar nada

1. **¿Ya existe un emulador?** El servicio `adb` del gateway (el de la campaña de MUDH-Mobile) responde `"No devices attached"`, pero **no medí si todavía tiene AVDs**. Si los tiene, montar un segundo **duplica una capacidad existente** y encima la pone a competir con producción.
2. **¿Qué versión de Android necesita el Agent Bridge?** `AppFunctions` y `EXECUTE_APP_FUNCTIONS` son de **Android 16 / android17-release** según el ADR-002. Un AVD de API 34 **no puede probar eso**. Es el dato que decide la imagen y **nadie me lo dio**.
3. **¿Play services?** Si el titiritero tiene que manejar WhatsApp o el banco, la imagen tiene que traer GMS, y eso cambia el `sdkmanager` y el tamaño.

---

## Mi recomendación, con su contra-argumento

**Instalar en la VM un AVD x86_64 de la API que exija AppFunctions, acotado a 1 núcleo, solo para el Agent Bridge.** Todo lo arm64 sigue en Actions arm64, que es nativo y gratis.

**Por qué puede estar mal:** si el Agent Bridge depende de algo del `/vendor` real o del binder del SoC, el AVD lo va a dar verde y el device rojo. Sería un instrumento que **no puede dar rojo** donde importa, que es el patrón que este proyecto persigue. Antes de escribir código contra el AVD hay que declarar qué parte del Bridge **no** queda probada ahí.

---

## NO MEDIDO

- Cuánto más lento es un AVD arm64 emulado en esa VM (no lo estimo).
- Si el servicio `adb` del gateway tiene AVDs vivos.
- El costo en créditos por hora de la VM.
- Cuánto degrada el buscador un emulador en 2 núcleos.
- Qué API de Android necesita el Agent Bridge, y si requiere GMS.
- Si el AVD x86_64 puede probar `EXECUTE_APP_FUNCTIONS` de verdad o solo compilarlo.
