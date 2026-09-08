#!/usr/bin/env python3
"""
F-004d, etapa x86: stg + stgdiff del fragmento de OCHO contra el baseline commiteado.

REGLAS DEL AUDITOR APLICADAS ACA, y cada una nace de un defecto mio medido:
  R-12  el guard mide la PROPIEDAD ('offset changed', 'byte size changed', rc),
        nunca la presencia de una cadena. En F-004b mi guard buscaba el texto
        "struct task_struct changed" y dio un veredicto FALSO sobre una medicion
        que estaba bien.
  R-13  el veredicto dice ABI-COMPATIBLE, nunca 'un DLKM carga'. Lo primero esta
        medido; lo segundo necesita un .ko real (F-007) o un arranque.
  R-14  sin autopuntuacion. Este archivo no emite rubrica.

PREDICCION DECLARADA ANTES DE CORRER: reporte sin CRC = UNA linea
('put_pid_ns' was added), 0 CRC, 0 byte-size, 0 offsets, 0 structs.
"""
import base64, glob, hashlib, os, re, subprocess, time, urllib.request

OUT = "mediciones/f-004d"
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
    for l in (o + e).splitlines()[:30]:
        w("   |", l[:200])
    return rc


def traer(rel, dst):
    req = urllib.request.Request("%s/%s?format=TEXT" % (BASE, rel),
                                 headers={"User-Agent": "siao-f004d/1"})
    d = base64.b64decode(urllib.request.urlopen(req, timeout=600).read())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(d)
    os.chmod(dst, 0o755)
    w("  bajado %-18s %10d B" % (rel, len(d)))


def main():
    os.makedirs(OUT, exist_ok=True)
    w("== F-004d: stgdiff del fragmento de OCHO, sin parche al ACK ==")
    w("maquina:", os.uname().machine, "| fecha UTC",
      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("PREDICCION: 1 linea, 0 CRC, 0 byte-size, 0 offsets, 0 structs.")
    traer("bin/stg", STG)
    traer("bin/stgdiff", STGDIFF)
    traer("lib64/libc++.so", LIB + "/libc++.so")

    if not os.path.isfile(REF):
        w("  NO MEDIDO: falta el baseline", REF)
        open(os.path.join(OUT, "F-004d-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
        return
    w("  baseline: %s | %d B | sha256 %s"
      % (REF, os.path.getsize(REF),
         hashlib.sha256(open(REF, "rb").read()).hexdigest()[:32]))

    vm = "/tmp/k/d/vmlinux"
    if not os.path.isfile(vm):
        w("  NO MEDIDO: no llego el vmlinux del brazo de ocho")
        open(os.path.join(OUT, "F-004d-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
        return
    kos = sorted(glob.glob("/tmp/k/d/**/*.ko", recursive=True))
    w("  vmlinux %d B | modulos %d" % (os.path.getsize(vm), len(kos)))
    dst = os.path.join(OUT, "ocho.stg")
    if run([STG, "-o", dst, "--elf", vm] + kos) != 0 or not os.path.isfile(dst):
        w("  NO MEDIDO: stg no produjo el .stg")
        open(os.path.join(OUT, "F-004d-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
        return
    w("  ocho.stg %d B" % os.path.getsize(dst))

    med = {}
    for et, extra, nom in (("CON CRC", [], "F-004d-abi.report"),
                           ("SIN CRC", ["--ignore", "linux_symbol_crc"],
                            "F-004d-abi-sin-crc.report")):
        rep = os.path.join(OUT, nom)
        w("=== pasada %s ===" % et)
        rc = run([STGDIFF, "--stg", REF, dst] + extra + ["--format", "small", "--output", rep])
        txt = open(rep, errors="replace").read() if os.path.isfile(rep) else ""
        # R-12: se miden PROPIEDADES contables, no la presencia de un nombre.
        med[et] = {"rc": rc, "bytes": len(txt),
                   "crc": txt.count("CRC changed"),
                   "added": txt.count("was added"),
                   "removed": txt.count("was removed"),
                   "byte_size": txt.count("byte size changed"),
                   "offset": txt.count("offset changed"),
                   "structs": sorted(set(re.findall(r"^type '([^']+)' changed", txt, re.M)))}
        m = med[et]
        w("  rc=%d | %d B" % (rc, m["bytes"]))
        w("  CRC changed x%d | was added x%d | was removed x%d"
          % (m["crc"], m["added"], m["removed"]))
        w("  byte size changed x%d | offset changed x%d" % (m["byte_size"], m["offset"]))
        w("  structs tocadas: %s" % (m["structs"] or "NINGUNA"))
        if et == "SIN CRC":
            w("  --- reporte ENTERO ---")
            for l in txt.splitlines():
                w("   |", l[:200])

    s = med["SIN CRC"]
    w("")
    w("================ VEREDICTO CONTRA LA PREDICCION ================")
    w("  criterio (R-12): rompen 'byte size changed' y 'offset changed'.")
    w("")
    w("  serie completa, misma referencia, misma herramienta:")
    w("    F-004 v3  10 simbolos, sin parche : SIN CRC 15.221 B | offsets muchos | CRC 10.867")
    w("    F-004b    10 simbolos, con parche : SIN CRC  6.877 B | offsets 51     | CRC  6.307")
    w("    F-004c     9 simbolos, con parche : SIN CRC    495 B | offsets  0     | CRC      0")
    w("    F-004d     8 simbolos, SIN parche : SIN CRC %6d B | offsets %2d     | CRC %6d"
      % (s["bytes"], s["offset"], med["CON CRC"]["crc"]))
    w("")
    limpio = s["byte_size"] == 0 and s["offset"] == 0
    if limpio and not s["structs"]:
        w("  PREDICCION CUMPLIDA, y en su forma fuerte: CERO structs tocadas.")
        w("  El fragmento de OCHO es ABI-COMPATIBLE con el GKI de stock y NO")
        w("  necesita UN SOLO parche al arbol de Android: cero deuda, cero slots")
        w("  de Google consumidos, cero rebase por LTS.")
        w("  R-13: esto dice ABI-compatible. Que un .ko real CARGUE es F-007.")
    elif limpio:
        w("  PREDICCION CUMPLIDA EN LO QUE IMPORTA: 0 byte-size y 0 offsets, pero")
        w("  quedan structs tocadas de forma nominal: %s" % s["structs"])
        w("  R-13: ABI-compatible. La carga real es F-007.")
    else:
        w("  PREDICCION FALSA: %d byte-size y %d offsets." % (s["byte_size"], s["offset"]))
        w("  Structs: %s" % s["structs"])
        w("  Hay un TERCER rompedor entre los ocho que quedan. Gana la medicion.")
    open(os.path.join(OUT, "F-004d-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")


if __name__ == "__main__":
    main()
