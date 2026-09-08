# CORRECCIÓN H-1 · el campo `llego_a_init` de F-001-S1 nunca midió eso

**Fecha (UTC):** 2026-09-08 · **Hallado por:** FABLE 5.1 (auditoría de instrumentos) · **Confirmado midiendo por:** BRAIN
**Sujetos:** `mediciones/f-001-s1/f001s1-aarch64.json`, `f001s1-x86_64.json`, sus dos bitácoras, y `tools/f001s1_arnes.py`.

> **Los JSON originales NO se editan.** Son la salida cruda del instrumento y W-01 manda commitearla verbatim. Esta corrección vive **al lado** de la evidencia y el mapa apunta acá.

---

## 1 · Lo que dice la evidencia publicada

```json
"hitos": {
    "banner_linux": true,
    "version_leida": "6.6.58-android15-8-g217cec2d0381-ab12874290-4k",
    "memoria_ok": true,
    "llego_a_init": false,
    "bytes_de_salida": 15217
}
```

Y de ahí viajó, como *"S1 no llegó a init"*, al informe técnico de auditoría, al briefing de FABLE y al pedido formal.

## 2 · Las dos capas del defecto, medidas

### Capa 1 · la consola está truncada

```plain
$ head -2 mediciones/f-001-s1/f001s1-aarch64-boot.txt
### comando
timeout 240 qemu-system-aarch64 -machine virt -cpu cortex-a57 -smp 2 -m 2048 -nographic -no-reboot -kernel /tmp/f001s1/Image -append 'console=ttyAMA0 panic=1 earlycon' 2>&1 | head -200

$ grep -cE '^\[ *[0-9]+\.[0-9]+\]' mediciones/f-001-s1/f001s1-aarch64-boot.txt
200

$ grep -oE '^\[ *[0-9]+\.[0-9]+\]' mediciones/f-001-s1/f001s1-aarch64-boot.txt | tail -1
[    0.458069]

$ grep -v '^$' mediciones/f-001-s1/f001s1-aarch64-boot.txt | tail -3
[    0.451795][    T1] ashmem: initialized
[    0.456189][    T1] hw perfevents: enabled with armv8_pmuv3 PMU driver, 7 counters available
[    0.457734][    T7] watchdog: Delayed init of the lockup detector failed: -19
[    0.458069][    T7] watchdog: Hard watchdog permanently disabled

$ grep -n -i 'init process|systemd|VFS:|unpack rootfs'   (regex extendida)
137:[    0.228240][    T1] VFS: Disk quotas dquot_6.6.0
138:[    0.228627][    T1] VFS: Dquot-cache hash table entries: 512 (order 0, 4096 bytes)
```

**Exactamente 200 líneas** con timestamp de kernel: el `head -200` cortó. La última es a **t=0,458 s**, en mitad de la inicialización de drivers. **Cero** líneas de `Run ... as init process`, `unpack rootfs` o `VFS: Unable to mount root fs`: las dos coincidencias de `VFS:` son cuotas de disco, no montaje de root. El kernel siguió; el archivo no.

*(Nota de precisión sobre el reporte de FABLE: el archivo entero son 211 líneas y 15.464 B porque lleva cabecera; los **15.217 B** del JSON son la consola sola. No cambia el hallazgo.)*

### Capa 2 · el campo calcula la negación de su nombre

`tools/f001s1_arnes.py`, líneas 158-165 verbatim:

```python
    hitos = {"control_discrimina": control_discrimina,
             "banner_linux": bool(m),
             "version_leida": m.group(1) if m else None,
             "memoria_ok": "Memory:" in todo,
             "llego_a_init": ("No working init found" in todo or "Kernel panic" in todo
                              or "Failed to execute" in todo),
             "bytes_de_salida": len(todo)}
```

El campo se pone en **`True` cuando aparece un mensaje de FALLO de init**. Consecuencias:

1. **El nombre miente sobre lo que calcula.** Mide *"vi un error de init"*, no *"llegó a init"*.
2. **La semántica está invertida:** un `Kernel panic` habría producido `llego_a_init: true`.
3. **Y opera sobre texto truncado**, así que ni siquiera mide bien lo que mide.

El `false` significa, literalmente: *"en los primeros 0,458 s de consola no apareció un mensaje de error de init"*. Es compatible con que el kernel haya arrancado init, con que haya paniqueado a t=0,6 s, y con cualquier otra cosa.

## 3 · Estado corregido

| Campo | Publicado | Correcto |
|---|---|---|
| `banner_linux` | `true` | **`true`**, intacto |
| `version_leida` | `6.6.58-android15-8-...` | intacto |
| `memoria_ok` | `true` | intacto |
| `control_discrimina` | `true` | intacto |
| `llego_a_init` | `false` | **NO MEDIDO** |
| veredicto del arnés | `ARNES VERDE` | **`ARNES VERDE`**, sobrevive: se sostiene en el banner y en el control que discrimina, no en este campo |

**Lo que queda prohibido afirmar:** *"S1 no llegó a init"*, *"el kernel se detuvo antes de init"*, o cualquier variante. Lo que S1 mide es que **QEMU ejecuta un kernel arm64 real en esa máquina** y que el control negativo discrimina. Nada más, y con eso alcanza para lo que se usó.

**Lo que NO cambia:** que F-001-S1 **no es G0**. Sigue siendo cierto por dos razones independientes de este campo: corrió el **GKI stock de Google** (no el fragmento de OCHO) y **sin rootfs** (`-kernel` sin `-initrd` ni `root=`), así que no había systemd que arrancar. G0 sigue NO MEDIDO y F-001-S2 sigue siendo el paso 1.

## 4 · El arreglo del instrumento, y por qué no está en este commit

El fix es: sacar el `| head -200`, mandar la consola a archivo con `-serial file:`, y renombrar el campo a lo que calcula (`vio_error_de_init`) agregando `salida_truncada`.

**No se commitea todavía** porque **ningún script se entrega sin ejecutarlo**, y ejecutar este exige QEMU más el `boot.img` del GKI. Va **junto con** `tools/f001s2_arnes.py`, en el turno que corra F-001-S2, y ese instrumento nace leyendo hitos **del archivo** y guardando su propio sha256 en el JSON, para que H-3 no se repita.

--- METODO PROMETEO ---
Máquina: brain-env (container) para las mediciones · API de GitHub para la escritura.
Evidencia cruda: los bloques del §2, sin recortar. Veredicto: el §3, marcado como conclusión.
