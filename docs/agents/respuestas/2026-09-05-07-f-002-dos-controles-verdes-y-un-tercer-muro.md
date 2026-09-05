# 2026-09-05 · F-002: los dos controles discriminan, y aparece un tercer muro

## 1. Pedido literal

> "Relanzá F-002 con usr-is-merged y el pin"

Corrió en `ubuntu-24.04-arm` (aarch64 nativo, `runner_id 1000002026`). **Pero el
`usr-is-merged` que vos me pediste salió de una propuesta mía que era falsa, y lo
medí antes de gastar el runner** (§5).

## 2. Veredicto

| | Resultado |
|---|---|
| **N1** · sin pin, con hook | **falló como predije** → el control discrimina |
| **N2** · con pin, sin hook | **falló como predije** → el control discrimina |
| **SUJETO** · con pin y con hook | **pasó los dos muros**, chocó con un **tercero** |
| **F-002** | **ROJO**, y el rojo es del repo de openKylin |

---

## 3. Los dos controles, verbatim, y por primera vez confirman mis diagnósticos

### N1: sin pin → la dependencia rota, con la firma exacta

```plain
The following packages have unmet dependencies:
 libcryptsetup12 : Depends: libdevmapper1.02.1 (>= 2:1.02.197)
                   but it is not going to be installed
E: Unable to correct problems, you have held broken packages.
```

### N2: sin el hook de merged-usr → el ENOENT, con la firma exacta

```plain
--- PIN ESCRITO EN EL TARGET ---
/usr/bin/dpkg --status-fd 9 --no-triggers --configure dpkg:arm64
chroot: failed to run command 'dpkg': No such file or directory
```

**Los dos controles fallan con la firma que predije y ninguno instala, así que
discriminan.** Consecuencia: **el pin era la causa del ROJO 2** y **los symlinks
de merged-usr eran la causa del cuarto ENOENT**. Es la primera vez en toda la
jornada que dos diagnósticos míos quedan confirmados por un control que podía
decir lo contrario.

---

## 4. El sujeto pasó los dos muros y apareció un tercero

```plain
E: Package 'login.defs' has no installation candidate
```

No hay error de `libdevmapper` y no hay `ENOENT`: **los dos fixes funcionaron.** Y
la causa del tercero está medida:

```plain
huanghe/main/binary-arm64      -> paquete 'login.defs' NO EXISTE
huanghe/main/binary-amd64      -> NO EXISTE
huanghe-proposed/binary-arm64  -> EXISTE, y ademas:
   passwd Depends: base-passwd (>= 3.6.4), libpam-modules, login.defs, libacl1, ...
```

**En `-proposed`, openKylin partió `login.defs` afuera de `passwd`; en `main` ese
paquete no existe.** Así que `main` y `-proposed` **no son un conjunto
consistente**: mezclarlos no es un problema de prioridades, es un problema de
**conjunto**. Mi pin de tres paquetes no puede arreglar eso, porque el defecto no
está en qué versión gana sino en que los dos componentes describen dos universos
distintos de paquetes.

### Consecuencia: gana el auditor, y ahora con medición

Su §2.2 decía que sumar `-proposed` arrastra todo `-proposed` y que **SIAO necesita
un overlay apt propio desde el día 1**. Yo lo acepté como higiene y respondí con
"un paquete pineado". **La medición dice que su versión fuerte era la correcta:**
la vía no es pinear, es **no agregar `-proposed` como fuente nunca**, bajar los
`.deb` que necesitamos y servirlos desde un repo propio con `sha256` registrado.

**Eso es un hallazgo de arquitectura, no de plomería:** el overlay de SIAO deja de
ser una comodidad y pasa a ser un componente obligatorio del producto.

---

## 5. Dos defectos míos cazados ANTES de gastar el runner

### 5.1 Mi propio fix del ADR-003 era falso

En el ADR-003 propuse `--include=usr-is-merged`. **Lo medí y es falso:**

```plain
usr-is-merged 35-ok1 (2868 B)
  control: ['./control', './md5sums', './preinst']
  preinst: is_merged() { for dir in /bin /sbin /lib; do
             [ "$(readlink -f $DPKG_ROOT$dir)" = "$DPKG_ROOT/usr$dir" ] || return 1
  data.tar: solo changelog.Debian.gz y copyright
```

Es un paquete **transicional**: sólo **verifica** que el sistema ya esté merged y
**falla si no lo está**. No crea un solo symlink. **Incluirlo habría hecho fallar
el build antes, no arreglarlo**, y yo habría leído ese fallo como "el repo sigue
roto". El que convierte es `usrmerge`, que depende de `perl` y corre en
`postinst`: demasiado tarde.

**La vía correcta, y es la que usé:** un `--setup-hook` que crea `/bin`, `/sbin`,
`/lib` y `/lib64` como symlinks en el árbol **vacío**, antes del primer paquete.
Y el control N2 prueba que era necesario.

### 5.2 El pin lo escribí con el campo equivocado

```plain
huanghe          -> Suite: huanghe          Codename: huanghe
huanghe-proposed -> Suite: huanghe-proposed Codename: huanghe
```

Escribí `Pin: release n=huanghe-proposed`. **`n=` es Codename y los dos dicen
`huanghe`**, así que el pin **no habría matcheado nunca**: `-proposed` entraba con
prioridad 500 y el criterio (b) daba rojo **por mi culpa**, y yo iba a culpar al
repo. El campo correcto es **`a=` (Suite)**. El auditor lo había escrito bien y yo
lo copié mal.

---

## 6. NO MEDIDO

- **El criterio (b) nunca se evaluó**: sin rootfs no hay qué auditar por origen.
- **Si el overlay propio cierra la cadena.** Es la conclusión de §4, no una
  medición: hay que bajar los tres `.deb` de `-proposed`, armar el repo local y
  correrlo.
- **Si `login.defs` tiene más hermanos** de este tipo entre `main` y `-proposed`.
  Medí uno porque uno frenó el build; no censé el resto.
- **El tamaño real del rootfs** y su `p_align` a escala.
- Los `dpkg: warning: ignoring pre-dependency problem!` que aparecen en masa: son
  esperables en un bootstrap, pero **no los verifiqué uno por uno**.

## 7. Contrato de cierre

- **Instrumento:** `tools/f002_rootfs_con_pin.py` (rama `titan/f-002-rootfs`)
- **Workflow:** `.github/workflows/f-002-rootfs.yml`
- **Evidencia cruda, commiteada por el runner:**
  `mediciones/f-002/F-002-salida-cruda.txt`, `mediciones/f-002/F-002.json`
- **Este archivo:** `docs/agents/respuestas/2026-09-05-07-f-002-dos-controles-verdes-y-un-tercer-muro.md`

--- METODO PROMETEO ---
**Máquina:** GitHub Actions **arm64** (aarch64 nativo, `nproc 2`, `runner_id
1000002026`) como sujeto, y `brain-env` por el gateway para el cruce de índices
`apt`. **Cero QEMU, cero kernel:** este falsador es de empaquetado.
**Artefacto 2 (ClickUp):** Doc del turno con los dos controles y el tercer muro.
