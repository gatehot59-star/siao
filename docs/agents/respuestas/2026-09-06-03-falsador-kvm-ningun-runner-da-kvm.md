# Falsador de KVM: ningun runner de Actions da KVM. La VM es la unica.

**Medido:** 2026-09-06 15:02 UTC, run `34041034375`, los dos jobs **success**
**Instrumento:** `.github/workflows/falsador-kvm-runners.yml`, validado antes de disparar (YAML OK, 1 bloque Python, 0 rojos)

---

## El resultado, verbatim

### `ubuntu-24.04-arm` (aarch64)

```
aarch64
Mem:  7911 total, 6961 disponible
vmx|svm en cpuinfo: 0
{
 "existe": false,
 "VEREDICTO": "SIN_KVM"
}
```

**El nodo `/dev/kvm` NO EXISTE.** No es un problema de permisos: no esta.

### `ubuntu-24.04` (x86_64), el control de instrumento

```
x86_64
vmx|svm en cpuinfo: 2
{
 "existe": true,
 "escribible_por_este_usuario": false,
 "abre_rdwr": "ERR:PermissionError:[Errno 13] Permission denied: '/dev/kvm'",
 "VEREDICTO": "SIN_KVM"
}
```

**El control hizo su trabajo.** Los dos dan `SIN_KVM` pero **por causas distintas**: en arm64 el nodo no existe, en x64 existe y el usuario del runner no tiene permiso. Si mi script estuviera roto, daría el mismo error en los dos. **Discrimina.**

---

## Veredicto: mi hipotesis murio, y era la esperanza

Escribi hace un rato: *"si el runner arm64 expone KVM, Actions gana en las dos dimensiones y la VM no se toca"*. **Falso.** No lo expone.

**Entonces la VM de Abraham es la unica maquina con KVM real de las cuatro**, y su pedido original era el correcto.

| Maquina | `/dev/kvm` | ISA | Veredicto |
|---|---|---|---|
| brain-env | **no existe** | x86_64 | Celeron N4020 @ 1,10 GHz. Descartada |
| **VM del corpus** | **API 12, usable** | x86_64 | **la unica con aceleracion** |
| Actions arm64 | **no existe** | aarch64 | nativo pero sin KVM |
| Actions x64 | existe, **sin permiso** | x86_64 | inutilizable para emular |

## Hallazgo lateral que refuerza la decision

| Runner | Android SDK |
|---|---|
| `ubuntu-24.04` (x64) | **`ANDROID_HOME=/usr/local/lib/android/sdk`**, java 17.0.20.1 |
| `ubuntu-24.04-arm` | **`ANDROID_HOME` vacio**, `sdkmanager` AUSENTE, java 17.0.20 |

El runner x64 **viene con el SDK preinstalado** y el arm64 **no**. Actions arm64 no solo carece de KVM: encima habria que instalarle el SDK entero en cada job.

---

## Consecuencia operativa

**El emulador va en la VM**, y no por preferencia: es la unica de las cuatro con `/dev/kvm` abierto y con el `ioctl` respondiendo. Con las tres condiciones ya declaradas:

1. **Datos separados** del corpus: `/home/ubuntu/siao/`, sin tocar `/var/www/corpus` ni la base.
2. **CPU acotada**: `taskset -c 1`, dejando el nucleo 0 para el buscador.
3. **Falsador obligatorio**: `time curl /buscar` antes y despues. Si el buscador se degrada, el emulador no sirve.

Y el limite que no cambia: el AVD sera **x86_64**, asi que prueba el **Agent Bridge** (binder/AIDL, ABI independiente del ISA) y **no** el userland arm64 ni el GKI.

---

## NO MEDIDO

- **Que API de Android necesita el Agent Bridge.** El ADR-002 apunta a Android 16 / android17-release para `AppFunctions` y `EXECUTE_APP_FUNCTIONS`. Sin ese dato la imagen no se elige.
- Si el Bridge requiere **GMS** para manejar WhatsApp o el banco.
- Si el servicio `adb` del gateway ya tiene AVDs vivos (dijo `No devices attached`, pero no medi si hay AVD creados).
- **Si `sudo usermod -aG kvm runner` en el job x64 destraba el permiso.** Es una via que NO probe y podria revivir Actions x64 como opcion.
