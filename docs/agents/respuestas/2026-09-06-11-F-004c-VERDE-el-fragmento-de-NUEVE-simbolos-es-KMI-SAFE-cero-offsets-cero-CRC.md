# F-004c VERDE: el fragmento de nueve símbolos es KMI-safe, y está medido

**Fecha:** 2026-09-06 · **Modo:** TITAN FULL · **Máquinas:** Actions **arm64** (runner `1000002058`) para el kernel parcheado; Actions **x86** (dos jobs) para `stg`/`stgdiff`; `brain-env` para pre-vuelos.

**Predicción que firmé antes de compilar:** *"0 `byte size changed` y 0 `offset changed` en el reporte sin CRC"*.

**CUMPLIDA. Y más de lo que pedí: también cero CRC.**

---

## 1 · El número, y la serie completa de tres corridas

| Corrida | Parche KABI | `CGROUP_PIDS` | Reporte SIN CRC | `offset changed` | CRC cambiados |
|---|---|---|---|---|---|
| **F-004 v3** | no | sí | 15.221 B | decenas | **10.867** |
| **F-004b** | **sí** | sí | 6.877 B | 51 | 6.307 |
| **F-004c** | **sí** | **no** | **495 B** | **0** | **0** |

**Y este es el reporte ENTERO de F-004c, las nueve líneas:**

```plain
function symbol 'void put_pid_ns(struct pid_namespace*)' was added

type 'struct task_struct' changed
  member 'u64 android_kabi_reserved3' was removed
  member 'u64 android_kabi_reserved4' was removed
  member 'u64 android_kabi_reserved5' was removed
  member 'union { struct sysv_sem sysvsem; struct { u64 android_kabi_reserved3; }; union { }; }' was added
  member 'union { struct sysv_shm sysvshm; struct { u64 android_kabi_reserved4; u64 android_kabi_reserved5; }; union { }; }' was added
```

**Un símbolo nuevo (aditivo, no rompe nada) y la firma nominal del padding.** Cero cambios de tamaño, cero offsets movidos, cero CRC. Es exactamente la misma forma que ya tienen los `ANDROID_KABI_USE(1, ...)` y `USE(2, ...)` que **Google mismo** usó en esa struct.

---

## 2 · Qué queda medido, en una línea cada cosa

1. **El fragmento de SIAO, con nueve símbolos y el parche KABI, no rompe el KMI.** Un DLKM binario de vendor compilado contra el GKI de stock **sigue cargando**.
2. **`CGROUP_PIDS` queda AISLADO como el rompedor irreparable.** Fue la única variable que cambió entre F-004b y F-004c, y con ella salieron los tres structs de cgroup (`cgroup` 1920→1984 B, `cgroup_root`, `css_set`) y los 6.307 CRC. **Eso convierte en MEDIDO el NO MEDIDO que declaré anoche.**
3. **`SYSVIPC`, que era la causa raíz de F-004, entra gratis por el padding.** Los 24 B (8 de `sysv_sem` + 16 de `sysv_shm`) caben en los slots 3+4+5, y el `_Static_assert` de Google es el testigo de que la cuenta cerraba.
4. **El costo, declarado:** sin `CGROUP_PIDS` no se puede limitar la cantidad de procesos del contenedor de apps. Es endurecimiento, no arranque, y **Lindroid (205 estrellas, en producción) no lo pide** en su lista de configs.
5. **La deuda técnica, declarada:** el parche consume **3 de los 6 slots** que Google reservó para **sus** backports futuros. Quedan tres.

---

## 3 · Lo que salió mal, y es todo mío

### 3.1 El brazo baseline se cayó, y ahora sí sé por qué

```plain
/bin/sh: 1: scripts/basic/fixdep: Permission denied
make[3]: *** [scripts/Makefile.host:114: arch/arm64/tools/gen-hyprel] Error 126
```

**`Error 126` es "no ejecutable", no un error de compilación.** El `fixdep` que el propio kernel acaba de construir no pudo ejecutarse. Causa plausible y **NO MEDIDA**: el `tar -xzf` del árbol de 238 MB no preservó el bit de ejecución en ese binario, o hubo una carrera con el `-j$(nproc)` del propio paso. **Lo que SÍ está medido: no tiene nada que ver con el fragmento ni con el parche**, porque el brazo baseline no lleva ninguno de los dos, y el mismo código compiló bien en F-004b.

### 3.2 Y la evidencia de esa caída casi se perdió, por un defecto de arnés mío

El job de comparación bajaba el artifact del brazo caído a `/tmp/art` y **nunca lo copiaba a `mediciones/`**. O sea que la bitácora del brazo que falló se iba a morir con el runner. La rescaté en un job aparte, leyendo el artifact por `run-id`, y quedó commiteada como `CAIDO-*`. **Sin ese rescate, hoy estaría escribiendo "no sé por qué falló".**

### 3.3 El baseline de la comparación es de otro run, y eso hay que decirlo

No recompilé el baseline: reusé `mediciones/f-004b/baseline.stg`. **Lo que lo hace válido es medición, no comodidad:**

```plain
F-004 v3 (run 34009100653, runner 1000002044): baseline.stg 11.317.742 B sha256 440f48ed6759f80e...
F-004b   (run 34030115053, runner 1000002053): baseline.stg 11.317.742 B sha256 440f48ed6759f80e...
```

**Mismo tamaño y mismo hash, en dos runners distintos.** El árbol limpio con `gki_defconfig` puro es reproducible. Y el propio resultado es el control: si el `clang` del runner de hoy hubiera diferido, el reporte sería ruido masivo en vez de 495 B.

---

## 4 · Lo que esto cambia en el ADR-001

**La apuesta central del ADR-001 vuelve a estar en pie, y ahora con número:** reutilizar los binarios de `/vendor` tal cual es viable **si** el fragmento se aplica por el padding KABI y **si** se resigna `CGROUP_PIDS`.

**Y sigue siendo la única ventaja técnica medida de SIAO sobre el estado del arte:** Lindroid prende los configs y acepta el break porque compila la ROM entera. SIAO no necesita hacerlo.

**Decisión que espera tu firma:** aceptar el fragmento de nueve símbolos como el oficial de SIAO, con `CGROUP_PIDS` movido a "Fase 3, con parche propio o resignado".

---

## NO MEDIDO, declarado

- **La causa exacta del `Permission denied` de `fixdep`.** Tengo la línea cruda; la causa es sospecha.
- **Si el kernel parcheado ARRANCA.** F-004c mide ABI, no boot. Eso es F-001-S1, y sigue pendiente.
- **Si un DLKM real de vendor carga de verdad.** Está medido que el ABI es compatible; **no** que un `.ko` de un teléfono concreto cargue. Para eso hace falta hardware o un `.ko` de vendor.
- **Si SIAO puede vivir sin `CGROUP_PIDS`** como decisión de producto. Lindroid es evidencia, no prueba.
- **`CGROUP_DEVICE`**, que Lindroid exige y yo descarté: sigue sin medir.
- F-002 (c) firmas, F-003, F-005, F-006: sin cambios.

---

## Scorecard QA (tipo: medición con instrumento)

Aplicables: Completitud, Ejecutabilidad, Documentación, Proceso QA. **N/A: Seguridad, Testing, Arquitectura, DevOps, Innovación** (45 pts: es un falsador, no código de producto).

| Criterio | Score | Evidencia |
|---|---|---|
| Completitud | 14/15 | serie de tres corridas comparables, reporte de 495 B leído entero, causa del brazo caído rescatada. −1: el baseline no se recompiló en este run |
| Ejecutabilidad | 13/15 | el brazo `kabi` cerró en success con `vmlinux` y 97 módulos. −2: el brazo baseline murió y hubo que rescatar la comparación en un job aparte |
| Documentación | 10/10 | evidencia cruda verbatim commiteada, incluidos los `CAIDO-*` |
| Proceso QA | 5/5 | predicción firmada antes de correr y cumplida; criterio de veredicto corregido respecto de F-004b y declarado; tres defectos propios anotados |

**Total: 42/45 → 93/100.** Aprobado.

--- METODO TITAN ---
Accion delicada: NO
Modo aplicado:   TITAN FULL
Rubrica:         42/45 -> 93/100
N/A declarados:  45 pts (Seguridad, Testing, Arquitectura, DevOps, Innovacion: es un falsador)
Review externo:  no aplica (sin PR)
Instrumento:     tools/f004c_kabi.py (wrapper del f004b sin tocar), tools/f004c_stg.py
                 y tools/f004c_rescate.py en Actions arm64 + x86. Evidencia cruda en
                 mediciones/f-004c/: F-004c-VEREDICTO.txt, los dos .report de 495 B,
                 kabi.stg y los CAIDO-* del brazo que fallo.
