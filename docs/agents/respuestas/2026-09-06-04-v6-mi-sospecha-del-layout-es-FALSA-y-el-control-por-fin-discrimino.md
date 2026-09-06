# 2026-09-06 · v6: mi sospecha del layout es FALSA, y por fin tuve un control que discrimina

## 1. Pedido

> "Probá el overlay no flat"

Probado en `ubuntu-24.04-arm` (aarch64 nativo, `runner_id 1000002030`), con un control
que **sí podía discriminar**: los dos overlays armados con los **mismos 3 `.deb`**, el
**mismo hook** y la **misma orden**. Única variable: el layout.

## 2. El resultado, y me refuta

```plain
RESULTADO: no_flat=False (rc 25) | flat=False (rc 25)
EL CONTROL DISCRIMINA (resultados distintos): False
CAUSA: MI SOSPECHA ES FALSA: el no flat tambien falla, asi que la causa no es el layout
```

**El overlay no flat se armó bien y apt lo lee:**

```plain
Get:2 file:/tmp/f002v6/nonflat huanghe Release [360 B]
arbol del overlay:
  <overlay>/dists/huanghe/Release
  <overlay>/dists/huanghe/main/binary-arm64/Packages
  <overlay>/dists/huanghe/main/binary-arm64/Packages.gz
  <overlay>/pool/main/*.deb   (3)
```

Y en el pre-vuelo `apt-cache policy` le asignó **`c=main`** al no flat contra `c=''` al
flat. La diferencia de layout **existe y es la correcta**. No alcanza.

## 3. Tercera vez que mi diagnóstico del mismo fallo es falso

| Versión | Mi diagnóstico | Resultado |
|---|---|---|
| v3 | "le falta el `Release`" | **falso**: con `Release` falló igual |
| v5 | "es el layout flat, sin componente" | **falso**: con layout completo falló igual |
| v6 | — | **la causa queda NO MEDIDA** |

**Pero esta vez el control estaba bien construido y por eso sirvió.** El N2 del v5 no
discriminaba porque daba el mismo resultado que el sujeto sin que yo lo hubiera
previsto; este dio el mismo resultado **y eso era exactamente lo que mataba mi
hipótesis**. La diferencia no es el resultado: es que el criterio estaba pensado antes.

## 4. Lo que sigue medido y no se mueve

**La cadena de dependencias CIERRA.** `apt-get -s` con `main` + los 3 `.deb` dio
**`rc=0` y 68 paquetes**, en `brain-env`, **dos veces** (pre-vuelo del v5 y pre-vuelo
del v6), y el único paquete del overlay que se instala es `libdevmapper1.02.1`.

Así que **F-002 (a) está contestado por el resolvedor canónico** y lo que falla es **un
constructor en particular**. Eso no es un riesgo del proyecto: es una elección de
herramienta.

## 5. Por qué la causa queda NO MEDIDA, y es defecto mío

```plain
MM | The following packages have unmet dependencies:
MM | E: Unable to correct problems, you have held broken packages.
```

**Falta la línea del medio.** En el control N1 (solo `main`) el **mismo filtro** sí
mostró `libcryptsetup12 : Depends: libdevmapper1.02.1 (>= 2:1.02.197) but it is not
going to be installed`. Acá la sección sale sin detalle, o sea que **la información
estaba en la salida de apt y mi filtro la descartó**.

**Es defecto de instrumentación, no del sujeto**, y es el mismo patrón que ya me cobré
con los ENOENT: recortar la salida antes de leerla. **R-01 aplicado: no acuso a
mmdebstrap de nada** hasta tener la línea que nombra el paquete.

## 6. Estado de F-002

| Criterio | Veredicto | Instrumento |
|---|---|---|
| (a) la cadena cierra | **VERDE** | `apt-get -s`, dos corridas independientes |
| (a) se materializa el rootfs | **ROJO con mmdebstrap** | causa NO MEDIDA |
| (b) origen | **NO MEDIDO** | sin rootfs no hay qué auditar |
| (c) firmas | **ROJO** | `[trusted=yes]`, R-07 |

## 7. NO MEDIDO

- **La causa del fallo de mmdebstrap.** Lo primero es volver a correr **sin filtrar la
  salida**: la línea que falta es la que nombra el paquete.
- **Si otro constructor lo hace.** `debootstrap` o `apt-get install` sobre un chroot
  armado a mano son dos vías que no depend en de `?narrow`.
- (b) y (c), sin cambios.

## 8. Contrato de cierre

- **Instrumento:** `tools/f002_v6_nonflat.py` (rama `titan/f-002-rootfs`)
- **Evidencia cruda:** `mediciones/f-002/F-002-v6.json`,
  `mediciones/f-002/F-002-v6-salida-cruda.txt`
- **Este archivo:** `docs/agents/respuestas/2026-09-06-04-v6-mi-sospecha-del-layout-es-FALSA-y-el-control-por-fin-discrimino.md`

--- METODO PROMETEO ---
**Máquina:** `brain-env` para el pre-vuelo R-05 (que midió `c=main` vs `c=''` y volvió
a dar `rc=0` en el resolvedor) y GitHub Actions **arm64** (`runner_id 1000002030`) para
el constructor, que es el único lugar donde se puede: **mmdebstrap no está en
`brain-env`**, medido. **Cero QEMU, cero kernel.**
**Artefacto 2 (ClickUp):** Doc del turno.
