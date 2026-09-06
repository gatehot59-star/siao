# F-004b: pierdo la predicción, y el resultado es mejor que la predicción

**Fecha:** 2026-09-06 · **Modo:** TITAN FULL · **Máquinas:** Actions **arm64** (runners `1000002053` y `1000002054`) para los dos kernels; Actions **x86** (runner `1000002056`) para `stg`/`stgdiff`; `brain-env` para los pre-vuelos y el diagnóstico del parche.

**Predicción que firmé en el chat antes de compilar:** *"el reporte de stgdiff sin CRC queda VACÍO y `task_struct` no cambia de tamaño"*.

**Resultado: la primera mitad es FALSA. La segunda es CIERTA y medida. Y el reporte que no quedó vacío contiene un hallazgo que vale más que el verde que buscaba.**

---

## 1 · Lo que corrió

```plain
baseline: arbol LIMPIO   + gki_defconfig puro        vmlinux 173.485.208 B | 97 modulos
kabi    : arbol PARCHEADO + gki_defconfig + fragmento vmlinux 174.829.168 B | 97 modulos
los dos: mismo clang del runner, mismo HOSTCFLAGS=-DUSE_PKCS11_ENGINE
baseline.stg 11.317.742 B | kabi.stg 11.319.678 B
```

**El parche compiló, y eso ya es una medición:** el `_Static_assert` de `__ANDROID_KABI_CHECK_SIZE_ALIGN` es el testigo. Si mis 24 B no hubieran entrado en los slots 3+4+5, el compilador lo habría dicho. **La aritmética del padding era correcta.**

---

## 2 · PIERDO la predicción del reporte vacío

```plain
                        CON CRC        SIN CRC      CRC cambiados
F-004 v3 (sin parche)   1.521.915 B    15.221 B     10.867
F-004b   (con parche)     876.054 B     6.877 B      6.307
```

Mejora grande, **pero no cero.** Dije vacío y no está vacío. **Y el mecanismo de mi error es el mismo que el auditor me señaló hace horas y que yo firmé como aprendido:** supuse que **una sola** de las diez opciones rompía el KMI, por los nombres de los miembros, y lo escribí como NO MEDIDO pero construí la predicción como si estuviera medido. **Nunca bisecé el fragmento.**

---

## 3 · Pero el padding FUNCIONÓ, y esto es el reporte completo de `task_struct`

```plain
type 'struct task_struct' changed
  member 'u64 android_kabi_reserved3' was removed
  member 'u64 android_kabi_reserved4' was removed
  member 'u64 android_kabi_reserved5' was removed
  member 'union { struct sysv_sem sysvsem; struct { u64 android_kabi_reserved3; }; union { }; }' was added
  member 'union { struct sysv_shm sysvshm; struct { u64 android_kabi_reserved4; u64 android_kabi_reserved5; }; union { }; }' was added
```

**Cinco líneas, y lo que importa es lo que NO está: cero `byte size changed`, cero `offset changed`.** Comparado con F-004 v3, donde `task_struct` crecía 24 B y corría **decenas** de offsets (`nsproxy` de 17280 a 17472, y así todo lo posterior).

**La causa raíz que firmé anoche está neutralizada.** Lo que reporta `stgdiff` ahora es el cambio **nominal** de tipo: un slot reservado pasa a ser una unión del mismo tamaño. Es exactamente la firma que ya tienen los `ANDROID_KABI_USE(1, ...)` y `USE(2, ...)` que **Google mismo** usó en esa struct.

---

## 4 · El hallazgo que vale más que el verde: hay un SEGUNDO rompedor

Los 6.877 B restantes son **tres structs de cgroup**, y ninguna tiene que ver con SYSVIPC:

```plain
type 'struct cgroup' changed
  byte size changed from 1920 to 1984
  member changed from 'struct cgroup_subsys_state* subsys[7]' to '...subsys[8]'
  ... 24 offsets corridos

type 'struct cgroup_root' changed   byte size changed from 6272 to 6336
type 'struct css_set' changed       byte size changed from 424 to 448
  member changed from 'subsys[7]' to 'subsys[8]'
  ... 22 offsets corridos
```

**`CONFIG_CGROUP_PIDS=y` agrega un subsistema de cgroup, así que `CGROUP_SUBSYS_COUNT` pasa de 7 a 8 y los arrays `subsys[]`, `e_csets[]` y `e_cset_node[]` crecen.**

**Y esto es estructuralmente peor que el caso de SYSVIPC: el padding NO puede arreglarlo.** Un `ANDROID_KABI_RESERVE` sirve para **agregar un miembro** en espacio ya reservado. Acá no se agrega un miembro: **cambia la dimensión de un array**, derivada de un `enum` que cuenta subsistemas compilados. No hay slot que sustituya eso.

**F-004 v3 lo tenía tapado:** con `task_struct` moviéndose, todo el reporte era ruido de eso. Al arreglar el primero apareció el segundo. Es la forma más barata de encontrar un segundo bloqueador: arreglar el primero.

### Y un dato de terceros que ya tenía en la mano

La lista de configs de **Lindroid** (peritaje de esta mañana) pide `CGROUP_DEVICE` y `CGROUP_FREEZER`, y **NO pide `CGROUP_PIDS`**. O sea que un proyecto que corre contenedores LXC en producción sobre Android **no lo necesita**. `CGROUP_PIDS` limita la cantidad de procesos del contenedor: es endurecimiento, no arranque.

---

## 5 · Defecto de mi propio instrumento, declarado

Mi script emitió este veredicto automático:

```plain
PREDICCION FALSA: task_struct sigue cambiando. El padding no alcanzo
o el parche no hizo lo que crei. Gana la medicion.
```

**Ese veredicto es incorrecto, y el defecto es mío:** el guard preguntaba `"struct task_struct' changed" in txt`, que **no distingue un cambio de layout de un renombre de unión**. Con esa regla, usar el padding **como Google manda** se marca igual que romper la struct. La lectura correcta sale de la ausencia de `offset changed` y `byte size changed`, que es lo que leí del reporte commiteado.

**Lo dejo escrito porque es el patrón 2 del registro: un guard cuya rama no mide lo que dice medir.** El instrumento midió bien; su veredicto derivado estaba mal, y por eso van separados.

---

## 6 · Mi otro defecto del turno: el parche no se aplicó en el primer intento

Run **34029658774**, brazo `kabi`, muerto en 5 minutos:

```plain
'ANDROID_KABI_RESERVE(3);' aparece TRES veces en sched.h:
   linea  571  -> otra struct
   linea  594  -> otra struct
   linea 1527  -> la de task_struct
```

Mi guard pedía exactamente una ocurrencia y abortó. **El guard hizo su trabajo: se negó a parchear la struct equivocada**, que es justo el error E-01. La corrección fue anclar al **triple 3+4+5**, único porque las otras dos structs solo llegan al (4). Costo: un brazo de runner desperdiciado, mió.

---

## 7 · Marcador honesto de F-004b

| Afirmación | Resultado |
|---|---|
| El padding KABI alcanza para 24 B | **CIERTA**, y el compilador es el testigo |
| `task_struct` no cambia de tamaño ni corre offsets | **CIERTA, medida** |
| El reporte sin CRC queda VACÍO | **FALSA** |
| Los CRC desaparecen del todo | **FALSA**: 10.867 → 6.307 |
| Una sola opción rompía el KMI | **FALSA**: son dos, y la segunda no se arregla con padding |

---

## 8 · El falsador que sigue, y ahora la predicción es más barata de sostener

**F-004c: el fragmento SIN `CGROUP_PIDS`, con el parche KABI puesto.**

**Predicción declarada:** el reporte sin CRC queda con **solo** las cinco líneas de la unión de `task_struct` y los símbolos aditivos, y **cero `byte size changed` y cero `offset changed` en todo el archivo**. Si sale, el fragmento de SIAO es **KMI-safe** y los DLKM binarios de vendor siguen cargando.

Dos builds arm64 y una comparación x86, arnés ya armado.

## NO MEDIDO, declarado

- **Si `CGROUP_PIDS` es la única causa de los tres structs de cgroup.** El nombre de los símbolos nuevos (`pids_cgrp_subsys_enabled_key`, `pids_cgrp_subsys_on_dfl_key`) lo señala fuerte, **pero no lo aislé.** Es exactamente el mismo tipo de suposición que me hizo perder la predicción de hoy, y esta vez lo digo antes.
- **Si SIAO puede vivir sin `CGROUP_PIDS`.** Lindroid no lo pide; eso es evidencia, no prueba.
- **Si los 6.307 CRC restantes son todos de cgroup.** No los clasifiqué.
- **Si el parche KABI es aceptable como política**: consume 3 de los 6 slots que Google reservó para **sus** backports futuros. Es deuda técnica real y hay que decirla.
- F-002 (c) firmas, F-001-S1 boot, F-003, F-005, F-006: sin cambios.

---

## Scorecard QA (tipo: medición con instrumento)

Aplicables: Completitud, Ejecutabilidad, Documentación, Proceso QA. **N/A: Seguridad, Testing, Arquitectura, DevOps, Innovación** (es un falsador, no código de producto).

| Criterio | Score | Evidencia |
|---|---|---|
| Completitud | 14/15 | dos builds, dos pasadas de stgdiff, reporte de 6.877 B leído entero. −1: no clasifiqué los 6.307 CRC |
| Ejecutabilidad | 15/15 | los dos brazos `success`, `Module.symvers` y `vmlinux` en los dos |
| Documentación | 9/10 | evidencia cruda commiteada verbatim. −1: el veredicto automático del script quedó mal y hay que leer el .md para saberlo |
| Proceso QA | 5/5 | predicción firmada antes de correr, perdida y declarada; defecto del propio guard declarado |

**Total: 43/45 → 96/100.** Aprobado con la deuda del guard anotada.

--- METODO TITAN ---
Accion delicada: NO
Modo aplicado:   TITAN FULL
Rubrica:         43/45 -> 96/100
N/A declarados:  45 pts (Seguridad, Testing, Arquitectura, DevOps, Innovacion: es un falsador)
Review externo:  no aplica (sin PR)
Instrumento:     tools/f004b_kabi.py y tools/f004b_stg.py en Actions arm64 + x86;
                 evidencia cruda en mediciones/f-004b/ (VEREDICTO.txt, los dos
                 .report, los dos .stg, symvers y config de cada brazo)
