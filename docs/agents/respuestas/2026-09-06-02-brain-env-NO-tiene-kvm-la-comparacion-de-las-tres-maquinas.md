# ¿Mejor brain-env? **No.** Las tres máquinas, medidas

**Medido:** 2026-09-06 · pregunta de Abraham tras el peritaje de la VM
**Respuesta corta:** brain-env es **la peor de las tres** para un emulador, y el motivo es un hecho, no una preferencia.

---

## La medición que cierra la pregunta

```
$ uname -m         -> x86_64
$ nproc            -> 2
$ model name       -> Intel(R) Celeron(R) N4020 CPU @ 1.10GHz
$ ls -la /dev/kvm  -> No such file or directory
$ grep -c 'vmx|svm' /proc/cpuinfo -> 2
```

**El CPU tiene las extensiones de virtualización (2), pero el container NO tiene el device `/dev/kvm`.** Sin ese nodo no hay aceleración posible: un emulador ahí cae a software puro, en un **Celeron N4020 a 1,10 GHz**.

Y ese Celeron ya tiene antecedentes medidos en este proyecto: **más de 25 minutos en extraer UN tomo de PDF** que Actions cerró en 90 segundos junto a otros nueve.

---

## Las tres máquinas

| | **brain-env** | **VM del corpus** | **Actions arm64** |
|---|---|---|---|
| Arquitectura | x86_64 | x86_64 | **arm64 NATIVO** |
| Núcleos | 2 | 2 | 2 |
| CPU | Celeron N4020 @ 1,10 GHz | (no medido el modelo) | (hosted) |
| `/dev/kvm` | **NO EXISTE** | **SÍ, API 12** | **NO MEDIDO** |
| Disco libre | 119 GB | 35 GB | efímero por job |
| Persistencia | sí (`/workspace`) | sí | **no**: muere con el job |
| Riesgo | ninguno | **comparte CPU con el corpus en producción** | ninguno |
| Costo | incluido | **factura por hora encendida** | gratis (privado: come cuota) |

**Ninguna es la máquina ideal**, y conviene decirlo así en vez de elegir la menos mala y llamarla buena:

- **brain-env**: sin KVM y el CPU más lento. Sirve para leer, compilar cosas chicas y medir. **No para emular.**
- **VM**: la única con KVM real, pero es **x86_64** (no acelera el arm64 de SIAO) y **comparte 2 núcleos con el buscador del bufete**.
- **Actions arm64**: la única **nativa arm64**, que es la arquitectura de SIAO. Es donde salió toda la evidencia del proyecto. Su contra: cada job arranca de cero, así que un AVD hay que rearmarlo o cachearlo.

---

## Qué significa para el reparto de SIAO

| Trabajo | Máquina | Por qué |
|---|---|---|
| Userland openKylin arm64, GKI, `.ko`, rootfs | **Actions arm64** | es arm64 nativo y ya probó que funciona |
| **Agent Bridge** (binder, AIDL, AppFunctions) sobre un AVD | **VM** | la única con KVM; la ABI de binder no depende del ISA |
| Leer repos, medir índices, correr scripts chicos, sondear la web | **brain-env** | persistente y ya tiene el acceso montado |

**NO MEDIDO, y es la pregunta que puede cambiar todo esto:** si los runners `ubuntu-24.04-arm` de GitHub exponen `/dev/kvm`. Si lo exponen, **Actions arm64 gana en las dos dimensiones a la vez** (arquitectura nativa **y** aceleración) y la VM deja de ser necesaria para el emulador. Se mide con un job de tres líneas y **no lo hice todavía**.

Eso es lo que yo mediría antes de instalar un solo paquete en la VM.
