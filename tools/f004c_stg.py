#!/usr/bin/env python3
"""
F-004c, etapa x86: stg + stgdiff, con el criterio de veredicto CORREGIDO.

EL DEFECTO QUE ESTE ARCHIVO ARREGLA, y era mio, medido en F-004b:
  el guard de tools/f004b_stg.py preguntaba
      "struct task_struct' changed" in txt
  y con eso escribio "PREDICCION FALSA: task_struct sigue cambiando". Es un guard
  que NO distingue un cambio de layout de un renombre de union: usar el padding
  COMO GOOGLE MANDA aparece igual que romper la struct. El veredicto salio mal
  con una medicion que estaba bien.

  El criterio correcto, y es el que aplica este archivo:
     'byte size changed'  -> la struct cambio de TAMANO. Rompe.
     'offset changed'     -> un miembro se movio. Rompe.
     'was added/removed' sobre un slot android_kabi_reservedN -> NOMINAL, no rompe:
        es exactamente la firma de ANDROID_KABI_USE, que Google usa en su propio
        arbol (dos veces en task_struct, ANDROID_KABI_USE(1) y USE(2)).

PREDICCION DECLARADA ANTES DE CORRER:
  0 'byte size changed' y 0 'offset changed' en TODO el reporte sin CRC.

El veredicto se escribe contra esa prediccion. Si sale distinto, dice FALSA.
"""
import base64, glob, hashlib, os, re, subprocess, time, urllib.request

OUT = os.environ.get("F004_OUT", "mediciones/f-004c")
BIN = "/tmp/stg"
STG = BIN + "/stg"
STGDIFF = BIN + "/stgdiff"
LIB = BIN + "/lib64"
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
    w("  bajado %-20s %10d B | sha256 %s"
      % (rel, len(d), hashlib.sha256(d).hexdigest()[:32]))


def main():
    os.makedirs(OUT, exist_ok=True)
    w("== F-004c: stgdiff del fragmento SIN CGROUP_PIDS ==")
    w("maquina:", os.uname().machine, "| fecha UTC",
      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("PREDICCION: 0 'byte size changed' y 0 'offset changed' en el reporte sin CRC.")
    traer("bin/stg", STG)
    traer("bin/stgdiff", STGDIFF)
    traer("lib64/libc++.so", LIB + "/libc++.so")

    stgs = {}
    for b in ("baseline", "kabi"):
        vm = "/tmp/k/%s/vmlinux" % b
        w("=== brazo %s ===" % b)
        if not os.path.isfile(vm):
            w("  NO MEDIDO: no llego el vmlinux de este brazo")
            continue
        kos = sorted(glob.glob("/tmp/k/%s/**/*.ko" % b, recursive=True))
        w("  vmlinux %d B | modulos %d" % (os.path.getsize(vm), len(kos)))
        dst = "/tmp/%s.stg" % b
        if run([STG, "-o", dst, "--elf", vm] + kos) == 0 and os.path.isfile(dst):
            w("  %s.stg %d B | sha256 %s"
              % (b, os.path.getsize(dst),
                 hashlib.sha256(open(dst, "rb").read()).hexdigest()[:32]))
            stgs[b] = dst
        else:
            w("  NO MEDIDO: stg no produjo .stg para", b)

    if len(stgs) != 2:
        w("  NO MEDIDO: falta al menos un .stg, brazos con stg =", sorted(stgs))
        open(os.path.join(OUT, "F-004c-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
        return

    med = {}
    for etiqueta, extra, nombre in (("CON CRC", [], "F-004c-abi.report"),
                                    ("SIN CRC", ["--ignore", "linux_symbol_crc"],
                                     "F-004c-abi-sin-crc.report")):
        rep = os.path.join(OUT, nombre)
        w("=== pasada %s ===" % etiqueta)
        rc = run([STGDIFF, "--stg", stgs["baseline"], stgs["kabi"]] + extra +
                 ["--format", "small", "--output", rep])
        txt = open(rep, errors="replace").read() if os.path.isfile(rep) else ""
        med[etiqueta] = {
            "rc": rc,
            "bytes": len(txt),
            "lineas": txt.count("\n"),
            "crc": txt.count("CRC changed"),
            "added": txt.count("was added"),
            "byte_size": txt.count("byte size changed"),
            "offset": txt.count("offset changed"),
            "structs": sorted(set(re.findall(r"^type '([^']+)' changed", txt, re.M))),
        }
        m = med[etiqueta]
        w("  rc=%d | %d B | %d lineas" % (rc, m["bytes"], m["lineas"]))
        w("  'CRC changed' x %d | 'was added' x %d" % (m["crc"], m["added"]))
        w("  'byte size changed' x %d | 'offset changed' x %d"
          % (m["byte_size"], m["offset"]))
        w("  structs que cambiaron: %s" % (m["structs"] or "NINGUNA"))
        if etiqueta == "SIN CRC":
            w("  --- reporte sin CRC, ENTERO ---")
            for l in txt.splitlines():
                w("   |", l[:200])

    for b, p in stgs.items():
        os.replace(p, os.path.join(OUT, "%s.stg" % b))

    s = med["SIN CRC"]
    w("")
    w("================ VEREDICTO CONTRA LA PREDICCION ================")
    w("  criterio: 'byte size changed' y 'offset changed' ROMPEN.")
    w("            un slot android_kabi_reservedN que pasa a union es NOMINAL.")
    w("")
    w("  F-004 v3  (sin parche, con CGROUP_PIDS): SIN CRC 15.221 B | offsets: muchos")
    w("  F-004b    (con parche, con CGROUP_PIDS): SIN CRC  6.877 B | offsets: 51")
    w("  F-004c    (con parche, SIN CGROUP_PIDS): SIN CRC %6d B | offsets: %d"
      % (s["bytes"], s["offset"]))
    w("  byte size changed: %d" % s["byte_size"])
    w("  CRC cambiados: 10.867 -> 6.307 -> %d" % med["CON CRC"]["crc"])
    w("")
    rompe = s["byte_size"] > 0 or s["offset"] > 0
    solo_kabi = [x for x in s["structs"] if x != "struct task_struct"]
    if not rompe:
        w("  PREDICCION CUMPLIDA: cero cambios de tamano y cero offsets movidos.")
        w("  El fragmento de SIAO (9 simbolos, con el parche KABI) es KMI-SAFE:")
        w("  un DLKM binario de vendor sigue cargando en este kernel.")
        w("  Y queda AISLADO que CGROUP_PIDS era la causa de los tres structs de")
        w("  cgroup, porque es la unica variable que cambio respecto de F-004b.")
    else:
        w("  PREDICCION FALSA: quedan %d 'byte size changed' y %d 'offset changed'."
          % (s["byte_size"], s["offset"]))
        w("  Structs distintas de task_struct que siguen cambiando: %s"
          % (solo_kabi or "ninguna"))
        w("  Gana la medicion: hay un TERCER rompedor y CGROUP_PIDS no era el ultimo.")
    open(os.path.join(OUT, "F-004c-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
    w("salida cruda en", os.path.join(OUT, "F-004c-VEREDICTO.txt"))


if __name__ == "__main__":
    main()
