# 2026-09-06 · F-002 v5: el pre-vuelo refuta al auditor, y el runner me refuta a mí

## 1. Pedido

F-002 v5, autorizado por el acta: `main` + overlay de 3 `.deb` **con `Release`**, tres
criterios. Predicción del auditor escrita antes: **ROJO por dependencias**.

## 2. Dos refutaciones en la misma corrida

### 2.1 La predicción del auditor es FALSA, y lo dijo el pre-vuelo antes del runner

Apliqué R-05: dry-run en `brain-env` con **`apt-get -s`**, que es el resolvedor
canónico (R-04). Salida cruda:

```plain
apt-cache policy:
  500 file:/tmp/pre2/overlay ./ Packages
      release v=3.0,o=SIAO,a=huanghe,n=huanghe,l=SIAO overlay
  500 .../openkylin huanghe/main arm64 Packages
      release v=3.0,o=openKylin,a=huanghe,n=huanghe,l=openKylin,c=main,b=arm64

apt-get install -s rc=0   ->  68 paquetes
  Inst libdevmapper1.02.1  2:1.02.205-ok1   SIAO overlay:3.0/huanghe [arm64]
  Inst libcryptsetup12     2:2.8.4-1ok10    openKylin:3.0/huanghe [arm64]
  Inst libsystemd0         255.2-ok2.8      openKylin:3.0/huanghe [arm64]
  Inst systemd             255.2-ok2.8      openKylin:3.0/huanghe [arm64]
  Inst systemd-sysv        255.2-ok2.8      openKylin:3.0/huanghe [arm64]
  Inst libpam-systemd      255.2-ok2.8      openKylin:3.0/huanghe [arm64]
```

**No arrastra nada más.** `libcryptsetup12 2.8.4` de `main` declara `libblkid1`,
`libc6`, `libdevmapper1.02.1`, `libjson-c5`, `libssl3t64` y `libuuid1`, y el único que
`main` no satisfacía era `libdevmapper`. **De los 3 `.deb` del overlay sólo UNO se
instala.**

**Consecuencia para D1 del acta:** `siao-base-s1` puede ser **`main` + 1 paquete**, con
`systemd 255.2` de `main` en vez de `259.5` de `-proposed`. Es la base más chica, la más
cercana al release oficial, y baja de **57 paquetes de `-proposed` a 1**.

### 2.2 Pero MI diagnóstico del v3 también es falso

En el v3 dije que al overlay le faltaba el `Release` para entrar en el `narrow` de
mmdebstrap. Le puse un `Release` completo, con `Date` y con los `SHA256` del `Packages`
(los dos defectos que el pre-vuelo delató), y **mmdebstrap falló igual**:

```plain
SUJETO (con Release):  rc=25
  ?narrow(?or(?archive(^huanghe$),?codename(^huanghe$)),?architecture(arm64),...)
N2 (sin Release):      rc=25, el mismo error
```

**Mi N2 no discrimina:** da el mismo resultado que el sujeto, así que **no separa "con
Release" de "sin Release"**. Es el mismo defecto del N3 del v3, **dos turnos
seguidos**: un control que no distingue el sujeto de su negación no es un control.

## 3. Entonces (a) tiene dos respuestas, de dos instrumentos

| Instrumento | Qué mide | Veredicto |
|---|---|---|
| **`apt-get -s`** (resolvedor canónico) | ¿la cadena de dependencias cierra? | **VERDE** |
| **mmdebstrap** (constructor) | ¿se materializa el rootfs? | **ROJO**, y la causa **no** es el `Release` |

**La pregunta de F-002 era si la cadena cierra, y cierra.** Lo que no funciona es
mmdebstrap con un repo flat local, y eso es un **límite del arnés** que hay que aislar
aparte. **El auditor acertó el color y falló la causa**, y eso importa: si aceptamos el
ROJO sin mirar la causa, `siao-base-s1` queda con 57 paquetes de `-proposed` cuando
podría tener 1.

## 4. Criterio (c): hay pieza concreta, pero es circular

```plain
openkylin-keyring 6288 B, sha256 verificado contra el indice, y contiene:
  ./usr/share/keyrings/openkylin-archive-keyring.gpg   2290 B
  ./usr/share/keyrings/deb-sign/openkylin.gpg          2262 B
  ./etc/apt/trusted.gpg.d/openkylin-archive-keyring.gpg
```

**El keyring existe y se puede obtener.** Pero verificarlo con el índice del **mismo
mirror** es circular. **(c) queda PARCIAL**: falta el fingerprint desde fuente primaria
fuera del mirror. R-07 se sostiene: nada de lo construido hoy cuenta como medición de
producto.

## 5. Criterio (b): NO MEDIDO

Sin rootfs materializado no hay nada que auditar por `apt-cache policy`. **Pero el
instrumento ya está escrito y sin lector propio** (R-04 respetado), así que cuando el
arnés funcione, (b) sale en la misma corrida.

## 6. Los dos controles que SÍ discriminaron

```plain
N1 solo main -> rc=25, causa_detectada=True
  libcryptsetup12 : Depends: libdevmapper1.02.1 (>= 2:1.02.197)
                    but it is not going to be installed
```

Ese control mira la causa (R-02) y la encontró. El otro, no.

## 7. NO MEDIDO

- **Por qué mmdebstrap rechaza el repo flat local**, con `Release` y todo. Sospecha no
  probada: el `c=` vacío de un repo flat (visible en el `apt-cache policy` del
  pre-vuelo) contra el `?narrow`. **Sospecha, no medición.**
- **(b)** hasta que el arnés produzca un rootfs.
- **(c)** hasta tener el fingerprint fuera del mirror.
- Si un overlay **no flat** (con `dists/huanghe/main/binary-arm64/`) entra en el
  `narrow`. Es la próxima prueba obvia y es corta.

## 8. Contrato de cierre

- **Instrumento:** `tools/f002_v5.py` (rama `titan/f-002-rootfs`)
- **Evidencia cruda:** `mediciones/f-002/F-002-v5.json`,
  `mediciones/f-002/F-002-v5-salida-cruda.txt`
- **Este archivo:** `docs/agents/respuestas/2026-09-06-03-f-002-v5-el-pre-vuelo-refuta-al-auditor-y-el-runner-me-refuta-a-mi.md`

--- METODO PROMETEO ---
**Máquina:** `brain-env` para el pre-vuelo R-05 (el que dio el resultado que importa) y
GitHub Actions **arm64** (`runner_id 1000002029`, 55,6 s) para el sujeto. **Cero QEMU,
cero kernel.**
**Artefacto 2 (ClickUp):** Doc del turno con las dos refutaciones.
