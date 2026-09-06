# 2026-09-06 · Audité el origen: 57 de `-proposed`, y mi auditor tiene un defecto medido

## 1. Pedido literal

> "pues audita el origen"

Hecho. Promoví el camino que funciona (`main` + `huanghe-proposed`) a **sujeto** y lo
audité paquete por paquete en `ubuntu-24.04-arm` (aarch64 nativo, `runner_id
1000002028`, 69,5 s).

## 2. El número que pedías

Rootfs de **175 paquetes, 357.535.564 B (341 MiB)**:

| | paquetes |
|---|---|
| **SOLO de `huanghe-proposed`** | **57** (~102 MiB instalados) |
| idénticos en `main` y `-proposed` (indistinguibles) | 89 |
| solo de `main` | 18 |
| en **ningún** índice | 11 |

**Y no son periféricos.** Los que vienen de `-proposed` son el núcleo:

```plain
systemd            259.5-ok1.2   (main tenia 255.2-ok2.8)   15.737 KB
libsystemd-shared  259.5-ok1.2                              10.160 KB
udev               259.5-ok1.2                              11.023 KB
libssl3t64         3.5.5-ok6     (main tenia 3.2.1-ok5)       9.366 KB
libpam-modules     1.7.0-ok2     (main tenia 1.5.3-ok8)       3.226 KB
passwd             1:4.17.4-ok1  (main tenia 1:4.14.3-ok3.5)  5.374 KB
libselinux1  3.9-ok3 | libsepol2 3.9-ok1 | libgcrypt20 1.12.1-ok1
tar | sed | tzdata 2026a | man-db | nano | vim-tiny | rsyslog | nftables
login.defs 1:4.17.4-ok1  y  openssl-provider-legacy 3.5.5-ok6  -> NO EXISTEN en main
```

**El rootfs que funciona es mayormente `-proposed` en sus piezas centrales, no `main`
con tres parches.** Eso es un dato de producto y no lo puedo suavizar: la base que
hoy compila es, de hecho, la rama sin QA de openKylin.

### `apt-cache policy` dentro del chroot, verbatim

```plain
Package files:
 100 /var/lib/dpkg/status
     release a=now
 500 .../openkylin huanghe-proposed/main arm64 Packages
     release v=3.0,o=openKylin,a=huanghe-proposed,n=huanghe,l=openKylin,c=main,b=arm64
 500 .../openkylin huanghe/main arm64 Packages
     release v=3.0,o=openKylin,a=huanghe,n=huanghe,l=openKylin,c=main,b=arm64
Pinned packages:
```

Las dos suites a **500** y **cero pins**, que es exactamente el escenario que se
midió. Y de paso el propio `apt` re-confirma con su instrumento lo que yo había
leído a mano: **`n=huanghe` en las dos**, así que pinear por `n=` era imposible.

---

## 3. Y aun así el veredicto es NO MEDIDO, porque mis controles no pasaron

### C3 CRUZADO: un falso positivo, y la causa es mi lector

```plain
C3_cruzado_solo_main:
  paquetes: 60 | atribuidos_a_proposed: 1 | discrimina: false
  lista: [["init-system-helpers", "1.66-ok1"]]
```

En un rootfs armado **solo con `main`**, mi auditor atribuyó un paquete a
`-proposed`. Eso no puede pasar, y la causa la medí:

```plain
huanghe/main/binary-arm64        11.837 paquetes | con MAS DE UNA version: 750
   init-system-helpers  ['1.57-ok2', '1.66-ok1']
huanghe-proposed/main/binary-arm64  11.370 paquetes | con MAS DE UNA version: 567
   init-system-helpers  ['1.66-ok1']
```

**`main` lista DOS versiones del mismo paquete y mi lector usaba `setdefault`**, o
sea que se quedaba con la primera y descartaba la otra. **No es un caso raro: 750 de
11.837 paquetes de `main` (6,3%) tienen más de una versión.** Mi instrumento estaba
mal para el 6% del repo.

### C1 POSITIVO: falló por una suposición mía

`C1_positivo_libdevmapper_de_proposed: false`. Esperaba ver `libdevmapper1.02.1` en
la lista, y **no está porque el `systemd 259.5` de `-proposed` no lo arrastra**
(`libcryptsetup12` tampoco aparece entre los 175). O sea que mi "control positivo"
no medía el instrumento: medía que yo hubiera adivinado bien qué se instala. **Un
control que depende de una suposición propia no es un control.**

---

## 4. Consecuencia honesta

**El 57 es una cota, no un número cerrado.** Con el bug del lector, los paquetes
multi-versión pueden estar mal clasificados **en las dos direcciones**: alguno de
los 57 podría existir también en `main`, y alguno de los 89 "indistinguibles"
podría ser en realidad solo de `-proposed`.

**Lo que SÍ se sostiene sin depender del bug**, porque sale de comparar contra la
versión que `apt` eligió y no de mi índice:

- `systemd` instalado es **259.5-ok1.2** y en `main` la que hay es **255.2-ok2.8**.
  Esa diferencia está en las dos lecturas y no depende de multi-versión.
- `login.defs` y `openssl-provider-legacy` **no existen en `main`** en ninguna
  versión, así que salieron de `-proposed` con certeza.
- Las dos suites entraron a **500 sin pins**, medido por `apt-cache policy`.

**Lo arreglo comparando contra el CONJUNTO de versiones de cada suite**, no contra
una, y reemplazando C1 por un control que no dependa de adivinar (por ejemplo,
inyectar en el índice un paquete inexistente y verificar que el auditor lo marque).

## 5. NO MEDIDO

- **El conteo exacto**, hasta arreglar el lector multi-versión.
- **Si los 11 paquetes sin índice** salieron de una versión retirada del mirror o de
  otro componente. No los perseguí.
- **Las firmas:** sigo con `[trusted=yes]` y `NO_PUBKEY 8B313CEAFF592D96`.
- **Si `-proposed` como base es aceptable.** Eso es decisión de Abraham y el script
  lo declaró **antes** de correr: no dice "aprobado", reporta el número.

## 6. Contrato de cierre

- **Instrumento:** `tools/f002_auditar_origen.py` (rama `titan/f-002-rootfs`)
- **Evidencia cruda del runner:** `mediciones/f-002/F-002-v4-origen.json`,
  `mediciones/f-002/F-002-v4-salida-cruda.txt`, `mediciones/f-002/F-002-v4-origen.md`
- **Este archivo:** `docs/agents/respuestas/2026-09-06-02-audite-el-origen-57-de-proposed-y-mi-auditor-tiene-un-defecto-medido.md`

--- METODO PROMETEO ---
**Máquina:** GitHub Actions **arm64** (aarch64 nativo, `nproc 2`, `runner_id
1000002028`, 69,5 s) como sujeto, más `brain-env` por el gateway para el censo de
multi-versión de los índices. **Cero QEMU, cero kernel.**
**Artefacto 2 (ClickUp):** Doc del turno con el número y el defecto del auditor.
