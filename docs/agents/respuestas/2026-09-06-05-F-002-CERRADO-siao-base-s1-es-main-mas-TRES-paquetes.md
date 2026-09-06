# 2026-09-06 · F-002 CERRADO: `siao-base-s1` = `main` + TRES paquetes

## 1. El resultado

**`rc=0`. 177 paquetes. 260.158.072 B (248 MiB).** En `ubuntu-24.04-arm` (aarch64
nativo, `runner_id 1000002033`, 79,8 s).

| Criterio | Veredicto | Instrumento |
|---|---|---|
| **(a)** construye systemd | **VERDE** | mmdebstrap, `rc=0`, `/usr/lib/systemd/systemd` existe |
| **(b)** origen auditado | **VERDE** | `apt-cache policy` dentro del chroot (R-04, cero parser propio) |
| **(c)** firmas verificadas | **ROJO declarado** | `[trusted=yes]`, R-07 |

## 2. El criterio (b), que venía NO MEDIDO desde el v3

```plain
ORIGEN, contado por apt-cache policy DENTRO del chroot:
   huanghe/main       174
   OVERLAY-SIAO         3
   huanghe-proposed     0     <-- CERO, y no esta en las fuentes

systemd  255.2-ok2.8  de huanghe/main   (el del release oficial)
gpgv     2.4.9-ok1.2  de huanghe/main
CONTROL de (b): systemd de huanghe y NO de proposed -> True
```

**Cero paquetes de `-proposed` directo**, y `systemd` es el **255.2 del release
oficial**, no el 259.5 de la rama sin QA.

## 3. `siao-base-s1`: el manifiesto medido

| paquete | overlay | en `main` | sha256 |
|---|---|---|---|
| `libdevmapper1.02.1` | `2:1.02.205-ok1` | `2:1.02.196-ok2` | `a609dc7cf06eaec6...` |
| `libgcrypt20` | `1.12.1-ok1` | `1.10.3-ok2` | `77d4659da56e39d7...` |
| `libgpg-error0` | `1.59-ok1` | `1.47-ok1` | `d7f13c7de1981234...` |

**De 57 paquetes de `-proposed` (el camino del v3) a TRES.** Es la base más chica y la
más cercana al release oficial, que era la opción preferible del acta.

## 4. Las dos cadenas que estaban rotas, ahora instaladas

```plain
base-files          14-ok3
gpgv                2.4.9-ok1.2
libcryptsetup12     2:2.8.4-1ok10
libdevmapper1.02.1  2:1.02.205-ok1     <- overlay
libgcrypt20         1.12.1-ok1         <- overlay
libgpg-error0       1.59-ok1           <- overlay
systemd             255.2-ok2.8
```

Y el `os-release` del rootfs: `NAME="openKylin" VERSION="3.0 (huanghe)"`.

## 5. La causa, y el control que por fin discrimina

```plain
copy://  -> instalo=True,  rc=0
file://  -> instalo=False, rc=25
  E: package file .../libgpg-error0_1.59-ok1_arm64.deb not accessible from chroot
     directory -- use copy:// instead of file:// or a bind-mount.
EL CONTROL DISCRIMINA: True
```

**Mismo overlay, mismos paquetes, misma orden. Única variable: el esquema de la URL.**
Con `file://` el `.deb` vive afuera del chroot y `dpkg` corre adentro; `copy://` hace
que mmdebstrap lo copie al target antes de instalar.

**Es la primera vez en toda la serie que un control discrimina de verdad**, y por eso
es la primera causa medida en vez de sospechada.

## 6. El balance honesto de la serie

| Versión | Mi diagnóstico | Resultado |
|---|---|---|
| v2 | "`main` y `-proposed` no son consistentes" | **falso**, era mi pin `-10` |
| v3 | "le falta el `Release`" | **falso**, con `Release` falló igual |
| v5 | "el auditor acertó el color" | sí, y **falló la causa** |
| v6 | "es el layout flat" | **falso**, el no flat falló igual |
| v8 | conjunto de paquetes | **correcto**, y no alcanzaba |
| v9 | **`copy://`** | **VERDE** |

**Seis versiones diagnosticando mal, y la causa estaba escrita con su solución en la
salida que yo venía filtrando.** Lo que la encontró no fue una hipótesis mejor: fue
dejar de recortar la evidencia antes de leerla.

**Y el hallazgo del v7-v8 sigue en pie y es de openKylin, no mío:** hay **dos** cadenas
rotas en `huanghe/main` arm64, no una. La de `libdevmapper` la veía desde el v2; la de
`gpgv` → `libgcrypt20` **no la vi nunca**, porque mis `apt-get -s` pedían solo los 6
paquetes de systemd y `gpgv` entra por el **conjunto esencial**. Mi resolvedor y mi
constructor medían conjuntos distintos: de ahí salía el "apt verde, mmdebstrap rojo".

## 7. NO MEDIDO

- **(c) firmas.** Todo con `[trusted=yes]` y `NO_PUBKEY 8B313CEAFF592D96`. El
  `openkylin-keyring 2022.05.12-ok3` **está instalado en el rootfs** (lo confirma el
  detalle de `apt-cache policy`), pero verificarlo contra el mismo mirror es circular.
- **Si el rootfs ARRANCA.** F-002 mide que se construye, no que bootea. Eso es F-001-S1.
- **El `p_align` a escala** sobre este rootfs.
- **Si `-proposed` mueve esos 3 paquetes mañana.** Por eso el snapshot con `sha256` del
  acta sigue siendo la decisión correcta: ahora congela **3** archivos, no 57.

## 8. Contrato de cierre

- **Instrumento:** `tools/f002_v9_copy.py` (rama `titan/f-002-rootfs`)
- **Evidencia cruda, sin filtro:** `mediciones/f-002/F-002-v9.json`,
  `F-002-v9-salida-cruda.txt`, `v9-sujeto-copy-completo.txt`,
  `v9-control-file-completo.txt`, `v9-policy-completo.txt`
- **Este archivo:** `docs/agents/respuestas/2026-09-06-05-F-002-CERRADO-siao-base-s1-es-main-mas-TRES-paquetes.md`

--- METODO PROMETEO ---
**Máquina:** GitHub Actions **arm64** (aarch64 nativo, `nproc 2`, `runner_id
1000002033`, 79,8 s) para el sujeto y el control, y `brain-env` para el cierre iterativo
de dependencias con `apt-get -s` que dio la lista de 3. **Cero QEMU, cero kernel.**
**Artefacto 2 (ClickUp):** Doc del cierre de F-002.
