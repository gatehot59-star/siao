# 2026-09-06 · El tercer muro era MI PIN, y el rootfs ya se construye

## 1. Pedido literal

> "Armá el overlay propio y relanzá"

Hecho: overlay construido, verificado y corrido en `ubuntu-24.04-arm` (aarch64
nativo, `runner_id 1000002027`, 158,2 s). **Y el resultado me refuta a mí, no al
repo.**

## 2. El resultado que da vuelta todo

Mi control **N2** (`main` + `huanghe-proposed`, **sin pin**) estaba puesto para
**fallar** por `login.defs`. No falló:

```plain
>>> N2-main-mas-proposed
  mmdebstrap rc=0
  MM | Setting up systemd (259.5-ok1.2) ...
  MM | Setting up systemd-sysv (259.5-ok1.2) ...
  MM | Setting up systemd-resolved (259.5-ok1.2) ...
  N2: OJO: instalo con proposed entero
```

`instalo: true`, `rc: 0`, y el binario `/usr/lib/systemd/systemd` existe en el
rootfs. **El rootfs de openKylin arm64 con systemd se construye hoy.**

## 3. Tres cosas que me refuto de una sola medición

### 3.1 El "tercer muro" del v2 era MÍO

`E: Package 'login.defs' has no installation candidate` no era una inconsistencia
del repo: **`login.defs` quedaba sin candidato porque mi propio pin le ponía
`Pin-Priority: -10` a todo `-proposed`**. El paquete estaba ahí; yo lo había
prohibido. Sin el pin, se instala.

### 3.2 Mi conclusión publicada es falsa

Escribí, con tabla y como hallazgo de producto: *"`main` y `-proposed` NO son un
conjunto consistente"*, y de ahí saqué que eso *"dice algo sobre el QA de
openKylin en arm64 que hay que pesar antes de 30 meses de roadmap"*.

**Es falso.** Son consistentes: instalan juntos, sin pin, en 158 segundos. Fue **un
defecto mío disfrazado de defecto ajeno**, que es exactamente el error más caro de
esta clase, porque manda a desconfiar de la base del proyecto por algo que rompí yo.

### 3.3 El overlay no era necesario para esta pregunta

Lo armé bien: los tres `.deb` bajaron con **sha256 verificado 3 de 3** contra el
índice oficial, `dpkg-scanpackages` produjo un `Packages` de 82 líneas con 3
paquetes. **Y resolvía un problema que no existía.**

Sigue siendo buena idea para el producto (control de versiones, paquetes
recompilados, el Agent Bridge), pero **hoy no es lo que desbloquea F-002**.

## 4. Por qué falló el overlay, medido

En la evidencia del sujeto está la causa, y es una línea de `apt`:

```plain
?narrow(?or(?archive(^huanghe$),?codename(^huanghe$)),?architecture(arm64),
        ?and(?or(?priority(required),?priority(important)),?not(?essential)))
```

**`mmdebstrap` restringe el conjunto esencial a paquetes cuyo `archive` o
`codename` sea `huanghe`.** Mi repo local no tiene archivo `Release`, así que no
tiene ni `archive` ni `codename`, y queda **afuera del `narrow`**. No está mal
armado: le falta un `Release` con `Suite`/`Codename` para entrar en ese filtro.

**Es un límite del arnés, no del overlay ni de openKylin**, y se arregla con un
`Release` de cuatro líneas.

## 5. Y mi control N3 NO discrimina, aunque el script dijo "correcto"

```json
"N3_overlay_hash_roto": {
  "esperado": "apt RECHAZA el .deb por hash",
  "instalo": false, "rc": 25,
  "discrimina": true,
  "hash_mismatch_detectado": false
}
```

Puse ese control justamente para probar que mi overlay **verifica** hashes. Falló,
y mi script lo cantó como correcto. **Pero `hash_mismatch_detectado` es `false`:
falló por el MISMO `narrow` que el sujeto, no por el hash mentido.** O sea que dio
el veredicto correcto **por la razón equivocada**, y no probó nada.

**Se declara NO MEDIDO**, y el bug del script queda anotado: mi criterio de
"discrimina" era `not instalo`, cuando debía ser `not instalo AND
hash_mismatch_detectado`. Un control cuyo criterio no mira la causa es un control
que se autoaprueba.

## 6. Estado real de F-002

| Criterio | Veredicto |
|---|---|
| (a) se construye el rootfs con systemd | **VERDE**, vía `main` + `huanghe-proposed` sin pin |
| (b) nada indeseado entra de `-proposed` | **NO MEDIDO** para ese camino |
| el overlay como vía | **ROJO por el arnés**: le falta el `Release` |
| N3 (el overlay verifica hashes) | **NO MEDIDO** |

## 7. NO MEDIDO

- **El criterio (b) del camino que funciona.** N2 era un control, no el sujeto, así
  que no lo audité por origen. Es lo primero que hay que medir ahora.
- **Cuántos paquetes vinieron de `-proposed`** en ese rootfs, y si alguno es un
  riesgo. Sin ese número, `main + -proposed` no está aprobado como base.
- **El tamaño real del rootfs** y su `p_align` a escala: no llegué a auditarlo.
- **Si el overlay con `Release` entra en el `narrow`.** Identificado, no probado.
- **La firma GPG:** todas las corridas muestran `NO_PUBKEY 8B313CEAFF592D96`. Anduve
  con `[trusted=yes]`, o sea **sin verificar firmas del repo**. Para un producto eso
  no alcanza y hay que conseguir la clave pública de openKylin.

## 8. Contrato de cierre

- **Instrumento:** `tools/f002_overlay.py` (rama `titan/f-002-rootfs`)
- **Evidencia cruda del runner:** `mediciones/f-002/F-002-v3-salida-cruda.txt`,
  `mediciones/f-002/F-002-v3.json`
- **Este archivo:** `docs/agents/respuestas/2026-09-06-01-el-tercer-muro-era-MI-PIN-y-el-rootfs-YA-SE-CONSTRUYE.md`

--- METODO PROMETEO ---
**Máquina:** GitHub Actions **arm64** (aarch64 nativo, `nproc 2`, `runner_id
1000002027`), 158,2 s. **Cero QEMU, cero kernel.**
**Artefacto 2 (ClickUp):** Doc del turno con la refutación completa.
