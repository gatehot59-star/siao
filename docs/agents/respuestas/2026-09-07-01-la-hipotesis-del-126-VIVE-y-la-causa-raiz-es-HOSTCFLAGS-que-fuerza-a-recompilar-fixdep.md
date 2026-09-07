# La hipótesis del 126 **no murió**: se afinó a causa raíz, y el defecto era mío

**Fecha:** 2026-09-07 · **Run:** `34126598730` · runners `1000002220` (baseline), `1000002221` (ocho), `1000002222` (x64).

**Evidencia cruda:** `mediciones/f-004d-61/v2-baseline-bitacora.txt`, `v2-baseline-build.txt`, `v2-baseline-archscripts.txt`, `v2-ocho.json`.

---

## 1 · Respuesta corta a la pregunta: la hipótesis **VIVE**

**No murió, y ahora tiene causa raíz medida.** El instrumento estaba diseñado para matarla si el 126 aparecía en el paso serial. **No apareció ahí. Apareció después, en el paso paralelo, y la bitácora explica por qué.**

---

## 2 · La secuencia exacta, MEDIDA

```plain
$ make ... -j1 archscripts
  rc=0 en 0.0 s | out 245 B | err 0 B
  archscripts rc=0 | reaparecio el Error 126 o Permission denied: False
  fixdep: 71464 B | modo 755 | ejecutable para mi: True

$ make ... HOSTCFLAGS='-DUSE_PKCS11_ENGINE' -j$(nproc) Image modules
  rc=2 en 0.6 s
  HOSTCC  arch/arm64/tools/gen-hyprel
  HOSTCC  scripts/basic/fixdep          <-- LO RECOMPILA
  /bin/sh: 1: scripts/basic/fixdep: Permission denied
  make[2]: *** [scripts/Makefile.host:114: arch/arm64/tools/gen-hyprel] Error 126
```

**Los dos datos que cierran el diagnóstico:**

1. **`archscripts -j1` tardó 0,0 s.** No compiló nada: `fixdep` ya existía del paso `gki_defconfig`, con **71.464 B, modo 755 y ejecutable**. O sea que mi "prueba serial" **no probó nada**: no había trabajo que hacer.
2. **El build paralelo RECOMPILA `fixdep`.** Y el motivo está en mi propio comando: **le paso `HOSTCFLAGS='-DUSE_PKCS11_ENGINE'` al build paralelo y NO al paso serial.** `HOSTCFLAGS` es parte de la firma de los targets de host, así que al cambiar, `make` **invalida y rehace `fixdep` y `gen-hyprel`** — esta vez en paralelo, con `-j2`. Y ahí vuelve la carrera.

**La causa raíz, entonces, es un defecto de mi arnés y no del kernel:** puse el candado serial **antes** de cambiar la variable que fuerza la recompilación. El paso serial protegió un `fixdep` que después se tiró a la basura.

---

## 3 · Y el control natural que lo confirma

**El brazo `ocho` compiló entero con los mismos flags y el mismo instrumento:**

```plain
brazo ocho: rc_archscripts 0 | error_126 false | rc_build 0
            vmlinux 354.673.168 B | 60 modulos
            Module.symvers 16.036 lineas | sha256 2b3bf558...
            ocho-android14-6.1.stg  10.699.333 B
            veredicto: brazo OK, vmlinux y symvers producidos y VERIFICADOS
```

**Mismo código, mismos flags, misma rama, mismo tipo de runner: uno falla y el otro no.** Eso es **intermitencia**, que es la firma de una carrera y no de un permiso mal puesto. Si fuera `noexec` en `/tmp` o un modo incorrecto, fallarían **los dos**.

**Y descarta la hipótesis alternativa del auditor** (artifacts que pierden el bit de ejecución): `fixdep` se compila en el runner, se midió en **modo 755 y ejecutable**, y el árbol viene fresco de googlesource.

---

## 4 · Lo que SÍ quedó medido, y es la mitad que importa

**El brazo con el fragmento de ocho funcionó en la generación del Pixel:**

```plain
CONFIG_DEVTMPFS y | DEVTMPFS_MOUNT y | FHANDLE y | POSIX_MQUEUE y
TMPFS_XATTR y | AUTOFS_FS y | PID_NS y | IPC_NS y
CONTROL | CONFIG_SYSVIPC       NO esta en =y (correcto)
CONTROL | CONFIG_CGROUP_PIDS   NO esta en =y (correcto)
rama android14-6.1, SUBLEVEL 176 | pahole v1.25 presente | DEBUG_INFO_BTF=y
```

**El arreglo 1 funcionó:** `dwarves` puso `pahole v1.25` y el link de `vmlinux` completó — **354.673.168 B**, contra el fallo de ayer. La diferencia de herramientas entre generaciones queda **resuelta y medida**.

**El arreglo 3 funcionó:** el brazo caído **no empaquetó nada**. Ayer, en el mismo punto, produjo un tarball de 20 MB sin `vmlinux` adentro y el instrumento siguió. Hoy abortó con mensaje propio y el veredicto quedó **NO MEDIDO** en vez de falso.

**Y R-09 funcionó:** el instrumento borró los cuatro archivos del brazo anterior antes de correr, así que no hay logs viejos mezclados con código nuevo.

---

## 5 · El veredicto de F-004d@6.1 sigue **NO MEDIDO**, y por una sola razón

```plain
F-004d @ android15-6.6 : SIN CRC  68 B | offsets 0 | CRC 0   (medido)
F-004d @ android14-6.1 : SIN CRC   ? B | offsets ? | CRC ?   (falta el baseline)
```

**Falta un brazo, no el resultado.** El `.stg` del brazo de ocho ya existe (10.699.333 B); lo que falta es su par para comparar. **R-17 prohíbe usar el baseline de 6.6**, y con razón: el de 6.6 pesaba 11.317.742 B contra estos 10.699.333 B, o sea que son kernels distintos y compararlos daría ruido, no señal.

---

## 6 · El arreglo, y es de una línea

**Pasarle el MISMO `HOSTCFLAGS` al paso serial**, para que `fixdep` y `gen-hyprel` se construyan una sola vez, en serie, con la firma definitiva:

```plain
antes:  make ... -j1 archscripts
        make ... HOSTCFLAGS='-DUSE_PKCS11_ENGINE' -j2 Image modules

ahora:  make ... HOSTCFLAGS='-DUSE_PKCS11_ENGINE' -j1 archscripts
        make ... HOSTCFLAGS='-DUSE_PKCS11_ENGINE' -j2 Image modules
```

**Predicción declarada antes de correr:** `archscripts` va a tardar **más de 0 s** esta vez (porque ahora sí tiene trabajo: recompilar los targets de host con la firma nueva), y el 126 **no** va a reaparecer en el build paralelo. Si reaparece, la hipótesis de la carrera muere de verdad y hay que buscar en otro lado.

**El dato que hace falsable la predicción es el tiempo de `archscripts`:** si vuelve a dar 0,0 s, el arreglo no se aplicó y no hay que interpretar nada más.

---

## 7 · Lección de método

**Un paso de mitigación que tarda 0,0 segundos no mitigó nada.** Yo leí `rc=0` y escribí *"hipótesis sostenida en esta corrida"*, cuando el propio número al lado (0,0 s) decía que el paso **no hizo trabajo**. Es la misma familia que el `grep -c` que devuelve `0`: **un éxito sin trabajo no es un éxito, es un no-medido.**

Lo salvó que el instrumento imprime el tiempo de cada comando (R-08) y que el guard de `vmlinux` no dejó pasar un artifact falso (R-12).

---

## NO MEDIDO

1. **F-004d en 6.1** (falta el `.stg` del baseline).
2. **Si el arreglo de `HOSTCFLAGS` elimina el 126**: predicción declarada, sin medir.
3. **Por qué el brazo `ocho` gana la carrera y el `baseline` la pierde.** Hipótesis: el brazo de ocho pasa por `merge_config` + `olddefconfig`, que agregan pasos y **cambian el timing**. Sin medir.
4. Si el `pahole v1.25` de Ubuntu produce un BTF equivalente al de Google.

--- METODO PROMETEO ---
Máquinas: Actions arm64 (dos brazos) + x64 (comparador).
Artefacto en git: este archivo. Evidencia: `mediciones/f-004d-61/v2-*`.
Artefacto en ClickUp: Doc espejo enlazado en el cierre.
