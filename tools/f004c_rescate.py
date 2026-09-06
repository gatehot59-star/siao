#!/usr/bin/env python3
"""
F-004c RESCATE - la comparacion sin recompilar el baseline.

QUE PASO, y es un defecto mio de arnes, no del sujeto (run 34032264479):
  el brazo 'baseline' de F-004c murio a los ~5 minutos, o sea antes del build
  largo. La causa NO quedo commiteada, porque el job de stgdiff bajaba el
  artifact de evidencia a /tmp/art y NUNCA lo copiaba a mediciones/. Asi que la
  bitacora del brazo caido se perdio con el runner. Queda NO MEDIDO y declarado.
  (Sospecha, no medicion: traer() no atrapa excepciones de urlopen, y una caida
  de red bajando los 238 MB del arbol mata el script con traceback en ese tiempo.)

POR QUE LA COMPARACION SE PUEDE HACER IGUAL, y esto SI esta medido:
  el brazo baseline es, por construccion, arbol LIMPIO + gki_defconfig PURO. No
  depende del fragmento ni del parche. Y su .stg salio IDENTICO en dos corridas
  independientes, en runners distintos:
     F-004 v3 (run 34009100653, runner 1000002044): baseline.stg 11.317.742 B
                                                    sha256 440f48ed6759f80e...
     F-004b   (run 34030115053, runner 1000002053): baseline.stg 11.317.742 B
                                                    sha256 440f48ed6759f80e...
  Mismo tamano y mismo hash, dos veces. Eso es reproducibilidad medida, no fe.
  Asi que se reusa el baseline.stg commiteado en mediciones/f-004b/.

  LO QUE ESTO DEBILITA, declarado: el clang del runner podria diferir entre runs.
  Contra eso: los dos hashes anteriores son identicos, y si el de hoy difiere el
  reporte lo va a mostrar como ruido masivo, no como cero. O sea que el propio
  resultado es el control.

QUE NO SE HACE: no se toca el .stg de referencia de Google. Se compara MI baseline
contra MI fragmento, que es la unica comparacion valida.

PREDICCION, la misma que firme antes de F-004c:
  0 'byte size changed' y 0 'offset changed' en el reporte sin CRC.
"""
import base64, glob, hashlib, os, re, subprocess, time, urllib.request

OUT = "mediciones/f-004c"
REF = "mediciones/f-004b/baseline.stg"
BIN = "/tmp/stg"
STG, STGDIFF, LIB = BIN + "/stg", BIN + "/stgdiff", BIN + "/lib64"
BASE = ("https://android.googlesource.com/kernel/prebuilts/build-tools/"
        "+/refs/heads/main/linux-x86")
lineas = []


def w(*a):
    s = " ".join(str(x) for x in a)
    lineas.append(s)
    print(s, flush=True)


def env():
    e = dict(os.environ)
    e["LD_LIBRARY_PATH"] = LIB + ":" + e.get("LD_LIBRARY_PATH", "")
    return e


def run(cmd, t=3600):
    w("$ " + " ".join(cmd)[:380])
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t, env=env())
        rc, o, e = r.returncode, r.stdout, r.stderr
    except Exception as ex:
        rc, o, e = -1, "", repr(ex)[:200]
    w("  rc=%d en %.1f s" % (rc, time.time() - t0))
    for l in (o + e).splitlines()[:40]:
        w("   |", l[:200])
    return rc


def traer(rel, dst):
    req = urllib.request.Request("%s/%s?format=TEXT" % (BASE, rel),
                                 headers={"User-Agent": "siao-f004c/1"})
    d = base64.b64decode(urllib.request.urlopen(req, timeout=600).read())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(d)
    os.chmod(dst, 0o755)
    w("  bajado %-18s %10d B" % (rel, len(d)))


def main():
    os.makedirs(OUT, exist_ok=True)
    w("== F-004c RESCATE: kabi de F-004c vs baseline reproducible de F-004b ==")
    w("maquina:", os.uname().machine, "| fecha UTC",
      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("PREDICCION: 0 'byte size changed' y 0 'offset changed' en el reporte sin CRC.")
    traer("bin/stg", STG)
    traer("bin/stgdiff", STGDIFF)
    traer("lib64/libc++.so", LIB + "/libc++.so")

    if not os.path.isfile(REF):
        w("  NO MEDIDO: no esta el baseline de referencia", REF)
        open(os.path.join(OUT, "F-004c-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
        return
    w("  baseline reusado: %s | %d B | sha256 %s"
      % (REF, os.path.getsize(REF),
         hashlib.sha256(open(REF, "rb").read()).hexdigest()[:32]))
    w("  (identico en los runs 34009100653 y 34030115053: reproducibilidad medida)")

    vm = "/tmp/k/kabi/vmlinux"
    if not os.path.isfile(vm):
        w("  NO MEDIDO: no llego el vmlinux del brazo kabi")
        open(os.path.join(OUT, "F-004c-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
        return
    kos = sorted(glob.glob("/tmp/k/kabi/**/*.ko", recursive=True))
    w("  vmlinux %d B | modulos %d" % (os.path.getsize(vm), len(kos)))
    dst = os.path.join(OUT, "kabi.stg")
    if run([STG, "-o", dst, "--elf", vm] + kos) != 0 or not os.path.isfile(dst):
        w("  NO MEDIDO: stg no produjo el .stg")
        open(os.path.join(OUT, "F-004c-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
        return
    w("  kabi.stg %d B | sha256 %s"
      % (os.path.getsize(dst), hashlib.sha256(open(dst, "rb").read()).hexdigest()[:32]))

    med = {}
    for etiqueta, extra, nombre in (("CON CRC", [], "F-004c-abi.report"),
                                    ("SIN CRC", ["--ignore", "linux_symbol_crc"],
                                     "F-004c-abi-sin-crc.report")):
        rep = os.path.join(OUT, nombre)
        w("=== pasada %s ===" % etiqueta)
        rc = run([STGDIFF, "--stg", REF, dst] + extra + ["--format", "small", "--output", rep])
        txt = open(rep, errors="replace").read() if os.path.isfile(rep) else ""
        med[etiqueta] = {"rc": rc, "bytes": len(txt), "crc": txt.count("CRC changed"),
                         "added": txt.count("was added"),
                         "byte_size": txt.count("byte size changed"),
                         "offset": txt.count("offset changed"),
                         "structs": sorted(set(re.findall(r"^type '([^']+)' changed", txt, re.M)))}
        m = med[etiqueta]
        w("  rc=%d | %d B | 'CRC changed' x %d | 'was added' x %d"
          % (rc, m["bytes"], m["crc"], m["added"]))
        w("  'byte size changed' x %d | 'offset changed' x %d" % (m["byte_size"], m["offset"]))
        w("  structs que cambiaron: %s" % (m["structs"] or "NINGUNA"))
        if etiqueta == "SIN CRC":
            w("  --- reporte sin CRC, ENTERO ---")
            for l in txt.splitlines():
                w("   |", l[:200])

    s = med["SIN CRC"]
    w("")
    w("================ VEREDICTO CONTRA LA PREDICCION ================")
    w("  criterio: 'byte size changed' y 'offset changed' ROMPEN el KMI.")
    w("            un slot android_kabi_reservedN que pasa a union es NOMINAL.")
    w("")
    w("  F-004 v3 (sin parche, con CGROUP_PIDS): SIN CRC 15.221 B | offsets muchos")
    w("  F-004b   (con parche, con CGROUP_PIDS): SIN CRC  6.877 B | offsets 51")
    w("  F-004c   (con parche, SIN CGROUP_PIDS): SIN CRC %6d B | offsets %d"
      % (s["bytes"], s["offset"]))
    w("  byte size changed: %d" % s["byte_size"])
    w("  CRC cambiados: 10.867 -> 6.307 -> %d" % med["CON CRC"]["crc"])
    w("")
    if s["byte_size"] == 0 and s["offset"] == 0:
        w("  PREDICCION CUMPLIDA: cero cambios de tamano y cero offsets movidos.")
        w("  El fragmento de 9 simbolos con el parche KABI es KMI-SAFE: un DLKM")
        w("  binario de vendor sigue cargando en este kernel.")
        w("  Y queda AISLADO que CGROUP_PIDS era la causa de los tres structs de")
        w("  cgroup: fue la unica variable que cambio respecto de F-004b.")
    else:
        w("  PREDICCION FALSA: quedan %d 'byte size changed' y %d 'offset changed'."
          % (s["byte_size"], s["offset"]))
        w("  Structs distintas de task_struct que siguen cambiando: %s"
          % ([x for x in s["structs"] if x != "struct task_struct"] or "ninguna"))
        w("  Gana la medicion: CGROUP_PIDS no era el ultimo rompedor.")
    open(os.path.join(OUT, "F-004c-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    main()
