#!/usr/bin/env python3
"""
F-004b, etapa x86: stg + stgdiff sobre baseline (limpio) vs kabi (parcheado).

LAS DOS PASADAS, y por que hacen falta las dos:
  1) stgdiff normal            -> dice si hay CUALQUIER diferencia de ABI.
  2) stgdiff --ignore linux_symbol_crc -> separa la cascada de CRC de un cambio
     REAL de tipos. En F-004 v3 la pasada 1 dio 1.521.915 B y la 2 dio 15.221 B
     con offsets de task_struct corridos: eso fue el ROJO.

PREDICCION DECLARADA ANTES DE CORRER (y firmada en el chat antes del build):
  con el parche KABI, la pasada 2 queda VACIA y task_struct no cambia de tamano.
  Ademas, por el #ifdef __GENKSYMS__ de android_kabi.h:61, los 10.867 CRC de
  F-004 v3 deberian desaparecer tambien de la pasada 1.

El veredicto se escribe contra esa prediccion, no acomodando la prediccion al
resultado. Si sale distinto, el archivo dice PREDICCION FALSA.
"""
import base64, glob, hashlib, os, subprocess, time, urllib.request

OUT = "mediciones/f-004b"
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
                                 headers={"User-Agent": "siao-f004b/1"})
    d = base64.b64decode(urllib.request.urlopen(req, timeout=600).read())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(d)
    os.chmod(dst, 0o755)
    w("  bajado %-20s %10d B | sha256 %s"
      % (rel, len(d), hashlib.sha256(d).hexdigest()[:32]))


def main():
    os.makedirs(OUT, exist_ok=True)
    w("== F-004b: stgdiff del parche KABI ==")
    w("maquina:", os.uname().machine, "| fecha UTC",
      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("PREDICCION DECLARADA: pasada sin CRC VACIA, task_struct sin cambio de tamano.")
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
              % (b, os.path.getsize(dst), hashlib.sha256(open(dst, 'rb').read()).hexdigest()[:32]))
            stgs[b] = dst
        else:
            w("  NO MEDIDO: stg no produjo .stg para", b)

    res = {}
    if len(stgs) == 2:
        for etiqueta, extra, nombre in (
                ("CON CRC", [], "F-004b-abi.report"),
                ("SIN CRC", ["--ignore", "linux_symbol_crc"], "F-004b-abi-sin-crc.report")):
            rep = os.path.join(OUT, nombre)
            w("=== pasada %s ===" % etiqueta)
            rc = run([STGDIFF, "--stg", stgs["baseline"], stgs["kabi"]] + extra +
                     ["--format", "small", "--output", rep])
            n = os.path.getsize(rep) if os.path.isfile(rep) else -1
            txt = open(rep, errors="replace").read() if n > 0 else ""
            w("  rc=%d | reporte %d B | %d lineas" % (rc, n, txt.count("\n")))
            w("  'CRC changed' x %d | 'was added' x %d | 'offset changed' x %d"
              % (txt.count("CRC changed"), txt.count("was added"), txt.count("offset changed")))
            res[etiqueta] = {"rc": rc, "bytes": n, "lineas": txt.count("\n"),
                             "crc": txt.count("CRC changed"),
                             "added": txt.count("was added"),
                             "offset": txt.count("offset changed"),
                             "task_struct": ("struct task_struct' changed" in txt)}
            for l in txt.splitlines()[:100]:
                w("   |", l[:200])
            if txt.count("\n") > 100:
                w("   ... (cortado en el resumen; el reporte va commiteado ENTERO)")
        for b, p in stgs.items():
            os.replace(p, os.path.join(OUT, "%s.stg" % b))

        w("")
        w("================ VEREDICTO CONTRA LA PREDICCION ================")
        w("  F-004 v3 (sin parche):  CON CRC 1.521.915 B | SIN CRC 15.221 B | task_struct CAMBIO")
        w("  F-004b   (con parche):  CON CRC %s B | SIN CRC %s B"
          % (res["CON CRC"]["bytes"], res["SIN CRC"]["bytes"]))
        w("  CRC cambiados: 10.867 -> %d" % res["CON CRC"]["crc"])
        w("  task_struct cambio de tipo?  %s" % res["SIN CRC"]["task_struct"])
        vacio = res["SIN CRC"]["bytes"] <= 0 or res["SIN CRC"]["lineas"] == 0
        sin_task = not res["SIN CRC"]["task_struct"]
        if vacio:
            w("  PREDICCION CUMPLIDA AL 100%: la pasada sin CRC quedo VACIA.")
        elif sin_task:
            w("  PREDICCION PARCIAL: task_struct ya NO cambia (que era la causa raiz),")
            w("  pero queda diferencia de ABI por otra cosa. Se lee en el reporte.")
        else:
            w("  PREDICCION FALSA: task_struct sigue cambiando. El padding no alcanzo")
            w("  o el parche no hizo lo que crei. Gana la medicion.")
    else:
        w("  NO MEDIDO: falta al menos un .stg, brazos con stg =", sorted(stgs))

    open(os.path.join(OUT, "F-004b-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")
    w("salida cruda en", os.path.join(OUT, "F-004b-VEREDICTO.txt"))


if __name__ == "__main__":
    main()
