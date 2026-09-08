#!/usr/bin/env python3
"""
F-004 v3, segunda medicion x86: stgdiff IGNORANDO linux_symbol_crc.

POR QUE HACE FALTA, y por que sin esto el veredicto anterior es ambiguo:
  la primera pasada dio rc=4 con un reporte de 1.521.915 B donde practicamente
  todas las entradas son 'CRC changed'. Eso admite DOS lecturas con consecuencias
  distintas, y firmar una sin medir seria exactamente el error que el auditor
  atajo antes:
     (1) solo cambiaron los CRC  -> un DLKM compilado contra el GKI de stock NO
         carga, pero RECOMPILADO contra este kernel si. Es un costo de build.
     (2) tambien cambiaron los TIPOS -> el layout cambio de verdad y recompilar
         no alcanza: hay que tocar el fragmento.

  El propio --help de stgdiff lista 'ignore options: ... linux_symbol_crc ...',
  o sea que la herramienta trae la separacion. Con los CRC ignorados, lo que
  quede en el reporte son cambios de tipo.

Prediccion declarada ANTES de correr, para que sea falsable: el reporte sin CRC
va a ser MUCHO mas chico que 1,5 MB. Si sale vacio, el rojo es enteramente CRC.
"""
import base64, hashlib, os, subprocess, time, urllib.request

OUT = "mediciones/f-004-v3"
BIN = "/tmp/stg"
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


def run(cmd, t=1800):
    w("$ " + " ".join(cmd)[:400])
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
    u = "%s/%s?format=TEXT" % (BASE, rel)
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004/3"})
    d = base64.b64decode(urllib.request.urlopen(req, timeout=600).read())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(d)
    os.chmod(dst, 0o755)
    w("  bajado %-20s %10d B | sha256 %s"
      % (rel, len(d), hashlib.sha256(d).hexdigest()[:32]))


def main():
    w("== F-004 v3: stgdiff ignorando linux_symbol_crc ==")
    w("maquina:", os.uname().machine, "| fecha UTC",
      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    traer("bin/stgdiff", STGDIFF)
    traer("lib64/libc++.so", LIB + "/libc++.so")
    a, b = os.path.join(OUT, "baseline.stg"), os.path.join(OUT, "siao.stg")
    for p in (a, b):
        if not os.path.isfile(p):
            w("  NO MEDIDO: falta", p)
            open(os.path.join(OUT, "F-004-SIN-CRC.txt"), "w").write("\n".join(lineas) + "\n")
            return
        w("  %s: %d B" % (p, os.path.getsize(p)))

    rep = os.path.join(OUT, "F-004-abi-sin-crc.report")
    rc = run([STGDIFF, "--stg", a, b, "--ignore", "linux_symbol_crc",
              "--format", "small", "--output", rep])
    w("  rc=%d" % rc)
    if os.path.isfile(rep):
        txt = open(rep, errors="replace").read()
        w("  reporte SIN CRC: %d B | %d lineas" % (len(txt), txt.count("\n")))
        w("  (el primero, CON CRC, media 1.521.915 B)")
        if not txt.strip():
            w("  VACIO -> todo el rojo anterior era CRC y NINGUN tipo cambio.")
        for l in txt.splitlines()[:120]:
            w("   S|", l[:200])
        if txt.count("\n") > 120:
            w("   ... (cortado en el resumen; el reporte va commiteado ENTERO)")
    else:
        w("  no se produjo reporte")
    # Cuantas entradas del primer reporte son EXCLUSIVAMENTE de CRC.
    p1 = os.path.join(OUT, "F-004-abi.report")
    if os.path.isfile(p1):
        t1 = open(p1, errors="replace").read()
        w("  reporte CON CRC: %d B | 'CRC changed' aparece %d veces | 'was added' %d"
          % (len(t1), t1.count("CRC changed"), t1.count("was added")))
    open(os.path.join(OUT, "F-004-SIN-CRC.txt"), "w").write("\n".join(lineas) + "\n")
    w("salida cruda en", os.path.join(OUT, "F-004-SIN-CRC.txt"))


if __name__ == "__main__":
    main()
