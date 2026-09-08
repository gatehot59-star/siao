#!/usr/bin/env python3
"""
F-004d@6.1, etapa x86: stgdiff de la generacion android14-6.1.

R-17 APLICADA, y es la razon de que este archivo exista en vez de reusar el otro:
  el baseline.stg commiteado es de android15-6.6. Un resultado de una generacion NO
  se cita para otra. Asi que este run compila SU PROPIO baseline en 6.1 y compara
  6.1 contra 6.1. Cero cruces.

R-15 APLICADA: escribe VEREDICTO.md y agrega su linea al indice, para que ningun run
  vuelva a quedar huerfano como F-004d en 6.6.

PREDICCION DECLARADA (la del auditor, la firmo): mismo resultado que en 6.6, o sea
  ~68 B, 0 CRC, 0 byte-size, 0 offsets, 0 structs tocadas.
  Base: SYSVIPC y CGROUP_PIDS son las dos unicas causas medidas, y el fragmento de
  ocho no las prende. Y el pre-vuelo mide algo que va A FAVOR: en 6.1 el
  gki_defconfig ya trae CONFIG_POSIX_MQUEUE=y, asi que IPC_NS tiene mas margen.
"""
import base64, glob, hashlib, json, os, re, subprocess, time, urllib.request

OUT = os.environ.get("F004_OUT", "mediciones/f-004d-61")
RAMA = os.environ.get("F004_RAMA", "android14-6.1")
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
    w("$ " + " ".join(cmd)[:360])
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
                                 headers={"User-Agent": "siao-f004d61/1"})
    d = base64.b64decode(urllib.request.urlopen(req, timeout=600).read())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(d)
    os.chmod(dst, 0o755)
    w("  bajado %-18s %10d B" % (rel, len(d)))


def stgear(brazo):
    vm = "/tmp/k/%s/vmlinux" % brazo
    if not os.path.isfile(vm):
        w("  NO MEDIDO: no llego el vmlinux de '%s'" % brazo)
        return None
    kos = sorted(glob.glob("/tmp/k/%s/**/*.ko" % brazo, recursive=True))
    w("  %-9s vmlinux %d B | modulos %d" % (brazo, os.path.getsize(vm), len(kos)))
    dst = os.path.join(OUT, "%s-android14-6.1.stg" % brazo)
    if run([STG, "-o", dst, "--elf", vm] + kos) != 0 or not os.path.isfile(dst):
        w("  NO MEDIDO: stg no produjo el .stg de '%s'" % brazo)
        return None
    w("  %-9s .stg %d B | sha256 %s"
      % (brazo, os.path.getsize(dst),
         hashlib.sha256(open(dst, "rb").read()).hexdigest()[:32]))
    return dst


def main():
    os.makedirs(OUT, exist_ok=True)
    w("== F-004d en la generacion %s ==" % RAMA)
    w("  maquina %s | fecha UTC %s"
      % (os.uname().machine, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
    w("  PREDICCION: ~68 B, 0 CRC, 0 byte-size, 0 offsets, 0 structs.")
    w("  R-17: baseline PROPIO de 6.1. No se cita nada de 6.6.")
    traer("bin/stg", STG)
    traer("bin/stgdiff", STGDIFF)
    traer("lib64/libc++.so", LIB + "/libc++.so")

    a = stgear("baseline")
    b = stgear("ocho")
    med = {}
    if a and b:
        for et, extra, nom in (("CON CRC", [], "F-004d-61-abi.report"),
                               ("SIN CRC", ["--ignore", "linux_symbol_crc"],
                                "F-004d-61-abi-sin-crc.report")):
            rep = os.path.join(OUT, nom)
            w("=== pasada %s ===" % et)
            rc = run([STGDIFF, "--stg", a, b] + extra +
                     ["--format", "small", "--output", rep])
            txt = open(rep, errors="replace").read() if os.path.isfile(rep) else ""
            med[et] = {"rc": rc, "bytes": len(txt),
                       "crc": txt.count("CRC changed"),
                       "added": txt.count("was added"),
                       "byte_size": txt.count("byte size changed"),
                       "offset": txt.count("offset changed"),
                       "structs": sorted(set(re.findall(r"^type '([^']+)' changed",
                                                        txt, re.M)))}
            m = med[et]
            w("  rc=%d | %d B | CRC x%d | added x%d | byte-size x%d | offset x%d"
              % (rc, m["bytes"], m["crc"], m["added"], m["byte_size"], m["offset"]))
            w("  structs tocadas: %s" % (m["structs"] or "NINGUNA"))
            if et == "SIN CRC":
                w("  --- reporte ENTERO ---")
                for l in txt.splitlines():
                    w("   |", l[:200])
    else:
        w("  NO MEDIDO: falta al menos un brazo")

    s = med.get("SIN CRC")
    if s:
        limpio = s["byte_size"] == 0 and s["offset"] == 0
        ver = ("VERDE: fragmento de OCHO ABI-compatible en %s, sin parche al ACK" % RAMA
               if limpio else
               "ROJO: %d byte-size y %d offsets en %s" % (s["byte_size"], s["offset"], RAMA))
    else:
        ver = "NO MEDIDO"
    w("")
    w("================ VEREDICTO ================")
    w("  serie, cada una contra SU PROPIO baseline de SU generacion:")
    w("    F-004d @ android15-6.6 : SIN CRC     68 B | offsets 0 | CRC 0   (medido ayer)")
    w("    F-004d @ android14-6.1 : SIN CRC %6s B | offsets %s | CRC %s"
      % (s["bytes"] if s else "?", s["offset"] if s else "?",
         med.get("CON CRC", {}).get("crc", "?")))
    w("  %s" % ver)
    w("  R-13: esto dice ABI-compatible. Que un .ko real CARGUE es F-007c.")

    json.dump({"falsador": "F-004d@6.1", "rama": RAMA, "med": med, "veredicto": ver,
               "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
              open(os.path.join(OUT, "F-004d-61.json"), "w"), indent=2, ensure_ascii=False)
    open(os.path.join(OUT, "F-004d-61-VEREDICTO.txt"), "w").write("\n".join(lineas) + "\n")

    # R-15: VEREDICTO.md y linea en el indice, para que ningun run quede huerfano.
    open(os.path.join(OUT, "VEREDICTO.md"), "w").write(
        "# F-004d @ %s\n\n**Veredicto:** %s\n\n"
        "| pasada | bytes | CRC | byte-size | offsets | structs |\n|---|---|---|---|---|---|\n"
        % (RAMA, ver) +
        "".join("| %s | %d | %d | %d | %d | %s |\n"
                % (k, v["bytes"], v["crc"], v["byte_size"], v["offset"],
                   v["structs"] or "ninguna")
                for k, v in med.items()) +
        "\n**R-17:** baseline propio de %s. No se cita nada de otra generacion.\n" % RAMA)
    idx = "mediciones/INDICE.md"
    prev = open(idx).read() if os.path.isfile(idx) else (
        "# Indice de mediciones (R-15)\n\n"
        "Un run sin linea aca esta NO LEIDO y bloquea el siguiente falsador.\n\n"
        "| falsador | generacion | veredicto | evidencia |\n|---|---|---|---|\n")
    linea = "| F-004d | %s | %s | `%s/` |\n" % (RAMA, ver, OUT)
    if linea not in prev:
        open(idx, "w").write(prev + linea)
    w("  R-15: VEREDICTO.md escrito y linea agregada a %s" % idx)


if __name__ == "__main__":
    main()
