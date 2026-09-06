#!/usr/bin/env python3
"""
F-004 v3, etapa x86: generar los .stg de los dos brazos y correr stgdiff.

POR QUE ESTA ETAPA CORRE EN x86 Y NO EN arm64:
  el binario que Google publica es kernel/prebuilts/build-tools/linux-x86/bin/stgdiff
  (blob a84c44ef...), o sea LINUX-X86. No corre en el runner aarch64. Pero stg LEE
  el ELF, no lo ejecuta, asi que un job x86 puede leer un vmlinux aarch64.

QUE COMPARA, Y QUE NO:
  compara MI baseline contra MI fragmento, los dos con el MISMO clang del runner y
  el MISMO HOSTCFLAGS. Esa comparacion es valida porque el compilador es constante.
  Comparar contra el .stg de referencia de Google NO seria valido: su .stg lo produjo
  su toolchain hermetico. Eso queda declarado y NO se hace.

NO ADIVINA BANDERAS: prueba varias formas de invocacion y COMMITEA la salida cruda
de cada intento, incluido el --help del binario. Si ninguna funciona, el resultado
es NO MEDIDO con la razon pegada, no un veredicto.
"""
import glob, hashlib, os, subprocess, time

OUT = "mediciones/f-004-v3"
STG = "/tmp/stg/stg"
STGDIFF = "/tmp/stg/stgdiff"
lineas = []


def w(*a):
    s = " ".join(str(x) for x in a)
    lineas.append(s)
    print(s, flush=True)


def run(cmd, t=3600):
    w("$ " + " ".join(cmd)[:400])
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t)
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


def main():
    os.makedirs(OUT, exist_ok=True)
    w("== F-004 v3 etapa x86: stg + stgdiff ==")
    w("maquina:", os.uname().machine, "| fecha UTC", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    for p in (STG, STGDIFF):
        if os.path.isfile(p):
            w("  %s | %d B | sha256 %s" % (p, os.path.getsize(p), sha(p)))
        else:
            w("  FALTA el binario:", p)
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
        intentos = [
            [STG, "-o", dst, "--elf", vm] + kos,
            [STG, "--output", dst, "--elf", vm],
            [STG, "-o", dst, vm],
        ]
        for cmd in intentos:
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
        if rc != 0:
            rc = run([STGDIFF, "--stg", stgs["baseline"], stgs["siao"], "--output", rep])
        w("  stgdiff rc=%d  (0 = sin cambios de ABI; distinto de 0 = hay diferencias)" % rc)
        if os.path.isfile(rep):
            w("  reporte: %d B" % os.path.getsize(rep))
            with open(rep, errors="replace") as f:
                for i, l in enumerate(f):
                    if i >= 120:
                        w("   ... (reporte truncado en el resumen; el archivo va commiteado entero)")
                        break
                    w("   R|", l.rstrip()[:200])
        for b, p in stgs.items():
            os.replace(p, os.path.join(OUT, "%s.stg" % b))
    else:
        w("  NO MEDIDO: falta al menos un .stg, brazos con stg =", sorted(stgs))

    with open(os.path.join(OUT, "F-004-STGDIFF.txt"), "w") as f:
        f.write("\n".join(lineas) + "\n")
    w("salida cruda en", os.path.join(OUT, "F-004-STGDIFF.txt"))


if __name__ == "__main__":
    main()
