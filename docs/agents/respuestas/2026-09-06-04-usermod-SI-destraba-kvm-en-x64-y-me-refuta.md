# `usermod` SÍ destraba KVM en x64, y eso me refuta

**Medido:** 2026-09-06 15:09 UTC · run `34041396776`, **success**
**Instrumento:** `.github/workflows/falsador-kvm-usermod.yml`

---

## El resultado: las TRES vías funcionan

| Vía | `api_version` | `create_vm` | Veredicto |
|---|---|---|---|
| **V3** `sudo` directo | **12** | **4** | **KVM_USABLE** |
| **V1** `usermod -aG kvm` + `sg kvm` | **12** | **4** | **KVM_USABLE** |
| **V2** `chmod 666 /dev/kvm` | **12** | **4** | **KVM_USABLE** |

Y el módulo está cargado de verdad:

```
kvm_amd    237568  0
ccp        159744  1 kvm_amd
kvm       1404928  1 kvm_amd
crw-rw---- 1 root kvm 10, 232 /dev/kvm
kvm:x:993:
```

El `create_vm: 4` es lo que cierra el caso: **no es que el nodo abra, es que se creó una VM de verdad**. Es el mismo nivel de prueba que corrí en la VM de Abraham.

## ME REFUTO

Hace 20 minutos publiqué que el runner x64 daba **`SIN_KVM`** y lo puse en una tabla junto a brain-env como "inutilizable para emular". **Falso.** Era un **problema de permisos**, no de ausencia, y mi propio falsador tenía el dato en la salida:

```
"existe": true,
"abre_rdwr": "ERR:PermissionError:[Errno 13] Permission denied"
```

`PermissionError` **no es** `FileNotFoundError`. Yo mismo escribí en ese informe que los dos jobs fallaban "por causas distintas", y **aun así rotulé las dos con la misma etiqueta**. El instrumento discriminó y **el que no discriminó fui yo al leerlo**.

El mecanismo, para no repetirlo: mi `VEREDICTO` colapsaba tres estados distintos (`no existe`, `sin permiso`, `KVM roto`) en una sola palabra. **Un veredicto que borra la causa que su propio dato registró es un instrumento a medias.**

## La prueba más dura que SÍ había diseñado: `emulator -accel-check`

No se pudo correr:

```
ANDROID_HOME=/usr/local/lib/android/sdk
emulator AUSENTE en /usr/local/lib/android/sdk/emulator/emulator
build-tools  cmake  cmdline-tools  extras  licenses  ndk  platform-tools  platforms
```

El SDK del runner trae `cmdline-tools`, `platform-tools`, `ndk` y `build-tools`, **pero no el paquete `emulator`**. Se instala con `sdkmanager "emulator"`, y eso **queda NO MEDIDO**: la aceleración está probada por `ioctl`, no por su consumidor real.

---

## El cuadro corregido

| Máquina | `/dev/kvm` | ISA | SDK | Riesgo para el corpus |
|---|---|---|---|---|
| brain-env | **no existe** | x86_64 | no | ninguno. Celeron @ 1,10 GHz |
| VM del corpus | usable (API 12) | x86_64 | no | **comparte 2 núcleos con producción** |
| Actions arm64 | **no existe** | aarch64 | **no** | ninguno |
| **Actions x64** | **usable con `usermod`** | x86_64 | **sí** (falta `emulator`) | **ninguno** |

**Cambia la recomendación, y a favor de Abraham:** el AVD del Agent Bridge conviene en **Actions x64**, no en la VM.

- KVM real, medido con `CREATE_VM`.
- **Cero riesgo** para el buscador del bufete.
- **Cero costo** de VM encendida.
- SDK ya casi completo.

La VM queda como estaba: **sirviendo el corpus**, que es lo que Abraham pidió ("luego solo será usado por corpus").

**El contra, y es real:** cada job arranca de cero, así que el AVD hay que crearlo o cachearlo en cada corrida, y no hay sesión interactiva para mirar la pantalla. Para desarrollo iterativo eso incomoda; para un banco de pruebas reproducible, **es mejor**.

---

## NO MEDIDO

- **`emulator -accel-check`**: hay que instalar el paquete `emulator` primero.
- Que un AVD **bootee** en ese runner, y cuánto tarda en frío.
- Si el AVD sobrevive el límite de 6 h por job.
- Si `actions/cache` sirve para no rearmar el AVD (el `.avd` pesa varios GB).
- **Qué API necesita el Agent Bridge**: sigue siendo el dato que falta, y sin él no se elige la imagen.
