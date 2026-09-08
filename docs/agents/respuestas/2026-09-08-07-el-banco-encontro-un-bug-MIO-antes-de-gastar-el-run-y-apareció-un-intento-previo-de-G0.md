# El banco encontró un bug MÍO antes de gastar el run, y de paso apareció un intento previo de G0 que murió en la primera línea

**Fecha (UTC):** 2026-09-08 · **main:** `4fb4979` · **rama de trabajo:** `titan/f-004d-61-v4-empaqueta-Image` @ `1a9c4fc`

## 1 · Pedido

"Dale, corregí el build y rebuildeá el brazo ocho."

## 2 · Herramientas y máquina declaradas

- **API de GitHub** (`push_files`, `get_file_contents`, `get_commit`): lectura del instrumento y escritura del v4/v4.1 en una **rama de trabajo**, no en `main`.
- **`brain-env`** (gateway `build/run`): ejecución del banco de pruebas. Se cayó una vez con SSE 502 y una vez con `Bad substitution` por `${PIPESTATUS}`; las dos veces se reintentó distinto.
- **Actions arm64** (`ubuntu-24.04-arm`): el rebuild. **Gasta 1 run**, autorizado.
- Escrituras: 3 commits a la rama de trabajo, 1 a `main` (bitácora y evidencia).

## 3 · Qué se midió

| Sujeto | Instrumento | Resultado |
|---|---|---|
| el v4 recién escrito | `test_f004d61_empaquetado.py`, 24 casos | **22 PASA, 2 FALLA** → bug propio |
| el bug | `tar -t \| cat -A` sobre un tarball sintético | el tar SÍ tenía los miembros: la **regex** era la rota |
| el v4.1 corregido | el mismo banco, ampliado a 33 casos | **33 PASA, 0 FALLA** |
| los controles negativos | comparación bueno/malo con el mismo instrumento | **discriminan** |
| el intento previo de G0 | `ls` + `cat` de `mediciones/f-001-s1b/` | **738 B, un archivo, rc=25 en el primer comando** |
| el run del rebuild | API de runs de Actions, sin credencial | **`queued`**, `2026-09-08T14:33:13Z` |

## 4 · Evidencia cruda verbatim

El banco completo, las dos pasadas y el diagnóstico están en
**`mediciones/f-004d-61/v4-banco-en-brain-env.txt`**. Lo decisivo:

```plain
-- 4. tar con -T y los guards de contenido --   (codigo v4, md5 d951f1cd...)
  PASA   tar -T arma el tarball  | rc=0
  FALLA  el tarball contiene vmlinux
  FALLA  el tarball contiene arch/arm64/boot/Image
  PASA   CONTROL: el guard detecta un tarball SIN Image     <-- pasaba SIN discriminar
== RESULTADO: 22 PASA, 2 FALLA ==
```

```plain
$ (cd dbg/out && tar -c --zstd -f t.tar.zst -T lst.txt); tar -t --zstd -f t.tar.zst | cat -A
rc_tar=0
vmlinux$
arch/arm64/boot/Image$
drivers/a.ko$
```

```plain
== RESULTADO: 33 PASA, 0 FALLA ==    (codigo v4.1, md5 3d8de2ad...)
  PASA   EL CONTROL NEGATIVO DISCRIMINA (bueno True, malo False)  | bueno=True malo_sin_image=True
```

```plain
$ runs de Actions, sin credencial
  queued       None       2026-09-08T14:33:13Z  F-004d@6.1 v4 - rebuild del brazo ocho CON el Image
```

## 5 · Veredicto (conclusión, no medición)

**El banco se pagó solo en su primera corrida.** La regex `^\./?vmlinux$` pide un punto **obligatorio** y solo la barra opcional, que es la lectura al revés de lo que quise escribir. Con eso, el guard de contenido del tarball daba **falso negativo** y el instrumento habría abortado con *"NO MEDIDO: tarball sin vmlinux"* **después de dos horas de build correcto**. Es el mismo turno en que acepté tres hallazgos de FABLE sobre mis instrumentos, y escribí uno nuevo del mismo tipo.

**Y hay algo peor que el bug:** en esa misma pasada el control negativo *"detecta un tarball SIN Image"* **pasó**. Una regex que no matchea nunca tampoco matchea en el caso malo, así que el control estaba verde sin medir nada. Por eso el v4.1 agrega el caso `EL CONTROL NEGATIVO DISCRIMINA`, que compara el tarball bueno y el malo **con el mismo instrumento**: un control que solo mira el caso malo no es un control.

**Los tres arreglos de FABLE quedaron implementados** (`Image` al tarball con guard duro, `head -400` reemplazado por lista explícita con cuenta cruzada, `.config` fuera del `if hay_sym`), más su KAT de `objcopy` **con los flags leídos del `arch/arm64/Makefile` del árbol** y no de memoria, y tres estados en vez de dos: `IDENTICO`, `DISTINTO`, `NO MEDIDO`.

**El run está encolado, no terminado.** Todo lo de arriba es sobre el empaquetado; el kernel todavía no se construyó.

## 6 · El hallazgo que corrige mi propio ADR-008

Mirando la lista de runs apareció **F-001-S1b "G0 systemd + IPC trace"**, que corrió el 2026-09-07 y terminó en `failure`. Existe `tools/f001s1b_qemu.py` en `main` con seis guards G0..G5, y dejó **738 bytes** de evidencia: un solo archivo con `rc=25` y `E: invalid mirror: deb`, un bug de quoting en el primer comando de todo el falsador.

**G0 sigue NO MEDIDO** (el run nunca llegó al kernel ni a QEMU), pero **mi framing estaba mal en dos documentos**: presenté F-001-S2 como el primer intento, y no lo es. Y sobre todo, escribí que *"virtio-blk nunca existió como opción"* cuando ese diseño previo ya usaba **dos fragmentos separados**, uno de producto y uno de **arnés** con `virtio/mmio/ext4` solo para el test. No refuta el initramfs de FABLE (el arnés obliga a un kernel distinto del que se midió con `stgdiff`), pero mi "no existe" fue más fuerte de lo que medí, **con el archivo en el repo**.

Detalle completo, con la salida íntegra de 738 B: **`mediciones/f-001-s1b/HALLAZGO-hubo-un-intento-previo-de-G0-y-murio-en-la-primera-linea.md`**.

## 7 · Archivos generados

- `tools/f004d61_build.py` → **v4.1** (en la rama de trabajo)
- `tools/test_f004d61_empaquetado.py` → banco de 33 casos (en la rama de trabajo)
- `.github/workflows/f-004d-61-v4.yml` (en la rama de trabajo; corre el banco como **gate** antes del build)
- `mediciones/f-004d-61/v4-banco-en-brain-env.txt`
- `mediciones/f-001-s1b/HALLAZGO-hubo-un-intento-previo-de-G0-y-murio-en-la-primera-linea.md`
- este archivo

## 8 · NO MEDIDO, declarado

- **El rebuild.** Encolado a las 14:33 UTC. Ni `Image`, ni KAT, ni `n_modulos` medidos todavía.
- **Si el `Error 126` reaparece.** El v4.1 no lo toca y el guard va a volver a declarar NO MITIGADO si `archscripts` da ~0 s. No es lo que este run mide.
- **El build completo del instrumento.** El banco prueba el **empaquetado**, no el build: eso solo se puede ejecutar en Actions y por eso el workflow corre el banco también en el runner, como segundo testigo.
- **Cuánto tarda un boot de systemd en TCG.** Los 600 s del S1b y los 900 s de FABLE son los dos inferidos.

--- METODO PROMETEO ---
Máquina: brain-env para el banco · Actions arm64 para el rebuild · API de GitHub para la escritura.
Artefactos: los seis del §7, más el Doc público de ClickUp.
