#!/usr/bin/env python3
"""
F-004 v3, etapa x86: generar los .stg de los dos brazos y correr stgdiff.

POR QUE ESTA ETAPA CORRE EN x86 Y NO EN arm64:
  el binario que Google publica es kernel/prebuilts/build-tools/linux-x86/bin/stgdiff
  (blob a84c44ef...), o sea LINUX-X86. No corre en el runner aarch64. Pero stg LEE
  el ELF, no lo ejecuta, asi que un job x86 puede leer un vmlinux aarch64.

EL DEFECTO DE LA CORRIDA ANTERIOR, medido y no supuesto (run 34010702399):
     /tmp/stg/stg: error while loading shared libraries: libc++.so:
     cannot open shared object file: No such file or directory
  rc=127 en las TRES formas de invocacion, o sea que no era la bandera: era que
  el binario no arrancaba. La libc++ que necesita esta en el MISMO prebuilt, en
  linux-x86/lib64/libc++.so (blob 4ac92caa...), medido antes de este cambio.
  Asi que se baja tambien y se apunta con LD_LIBRARY_PATH.
  Ese rc=127 es la razon por la que el guard importa: 'no produjo .stg' no era
  'el ELF esta mal', era 'el instrumento no arranco'. Dos estados distintos.

QUE COMPARA, Y QUE NO:
  compara MI baseline contra MI fragmento, los dos con el MISMO clang del runner y
  el MISMO HOSTCFLAGS. Esa comparacion es valida porque el compilador es constante.
  Comparar contra el .stg de referencia de Google NO seria valido: su .stg lo produjo
  su toolchain hermetico. Eso queda declarado y NO se hace.

NO ADIVINA BANDERAS: prueba varias formas de invocacion y COMMITEA la salida cruda
de cada intento, incluido el --help. Si ninguna funciona, el resultado es NO MEDIDO
con la razon pegada, nunca un veredicto.
"""
import base64, glob, hashlib, os, subprocess, time, urllib.request

OUT = "mediciones/f-004-v3"
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
    w("$ " + " ".join(cmd)[:400])
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t, env=env())
        rc, o, e = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        rc, o, e = -9, "", "TIMEOUT"
    except Exception as ex:
        rc, o, e = -1, "", repr(ex)[:200]
    w("  rc=%d en %.1f s" % (rc, time.time() - t0))
    for l in (o + e).splitlines()[:60]:
        w("   |", l[:200])
    return rc


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def traer(rel, dst):
    u = "%s/%s?format=TEXT" % (BASE, rel)
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004/3"})
    d = base64.b64decode(urllib.request.urlopen(req, timeout=600).read())
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(d)
    os.chmod(dst, 0o755)
    w("  bajado %-22s -> %-24s %10d B | sha256 %s" % (rel, dst, len(d), sha(dst)[:32]))


def main():
    os.makedirs(OUT, exist_ok=True)
    w("== F-004 v3 etapa x86: stg + stgdiff ==")
    w("maquina:", os.uname().machine, "| fecha UTC",
      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("  el instrumento y SU libreria salen del mismo prebuilt de Google:")
    traer("bin/stg", STG)
    traer("bin/stgdiff", STGDIFF)
    traer("lib64/libc++.so", LIB + "/libc++.so")
    w("  LD_LIBRARY_PATH =", env()["LD_LIBRARY_PATH"])
    run(["ldd", STG], 120)
    run([STG, "--help"], 120)
    run([STGDIFF, "--help"], 120)

    stgs = {}
    for b in ("baseline", "siao"):
        vm = "/tmp/k/%s/vmlinux" % b
        w("=== brazo %s ===" % b)
        if not os.path.isfile(vm):
            w("  NO MEDIDO: no llego el vmlinux de este brazo")
            continue
        kos = sorted(glob.glob("/tmp/k/%s/**/*.ko" % b, recursive=True))
        w("  vmlinux %d B | modulos %d" % (os.path.getsize(vm), len(kos)))
        dst = "/tmp/%s.stg" % b
        for cmd in ([STG, "-o", dst, "--elf", vm] + kos,
                    [STG, "--output", dst, "--elf", vm],
                    [STG, "-o", dst, vm]):
            if run(cmd) == 0 and os.path.isfile(dst):
                break
        if os.path.isfile(dst):
            w("  %s.stg -> %d B | sha256 %s" % (b, os.path.getsize(dst), sha(dst)[:32]))
            stgs[b] = dst
        else:
            w("  NO MEDIDO: stg no produjo .stg para", b)

    w("=== stgdiff baseline vs siao (unica variable: el fragmento) ===")
    if len(stgs) == 2:
        rep = os.path.join(OUT, "F-004-abi.report")
        rc = run([STGDIFF, "--stg", stgs["baseline"], stgs["siao"],
                  "--format", "small", "--output", rep])
        if not os.path.isfile(rep):
            rc = run([STGDIFF, "--stg", stgs["baseline"], stgs["siao"], "--output", rep])
        w("  stgdiff rc=%d" % rc)
        w("  interpretacion declarada ANTES de leer: rc=0 significa ABI equivalente;")
        w("  rc distinto de 0 con reporte significa que HAY diferencias de ABI.")
        if os.path.isfile(rep):
            w("  reporte: %d B" % os.path.getsize(rep))
            with open(rep, errors="replace") as f:
                for i, l in enumerate(f):
                    if i >= 150:
                        w("   ... (resumen cortado; el reporte va commiteado ENTERO)")
                        break
                    w("   R|", l.rstrip()[:200])
        for b, p in stgs.items():
            os.replace(p, os.path.join(OUT, "%s.stg" % b))
            w("  %s.stg commiteado en %s" % (b, OUT))
    else:
        w("  NO MEDIDO: falta al menos un .stg, brazos con stg =", sorted(stgs))

    with open(os.path.join(OUT, "F-004-STGDIFF.txt"), "w") as f:
        f.write("\n".join(lineas) + "\n")
    w("salida cruda en", os.path.join(OUT, "F-004-STGDIFF.txt"))


if __name__ == "__main__":
    main()
