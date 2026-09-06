#!/usr/bin/env python3
"""
F-004d - El fragmento de OCHO, sin un solo parche al ACK, es KMI-safe?

DE QUIEN ES LA IDEA: del auditor, y es mejor que la mia. Yo demostre que EXISTE
salida (el padding KABI); el pregunta si HACE FALTA usarla. La contabilidad del
reporte de F-004 v3 le da la razon: 15.221 B = task_struct (SYSVIPC) + cgroup
(CGROUP_PIDS), y NADA MAS. Si salen los dos simbolos, no queda nada que parchear.

PREDICCION DECLARADA ANTES DE CORRER (la del auditor, la firmo igual):
  reporte sin CRC = UNA linea ('put_pid_ns' was added), CERO CRC cambiados,
  CERO 'byte size changed', CERO 'offset changed', y CERO structs tocadas.
  Fragmento KMI-safe con CERO deuda: sin parche al ACK, sin consumir slots de
  Google, sin rebase por cada LTS.

EL GUARD DURO QUE ESTE FALSADOR NECESITA, y que el auditor no nombro:
  CONFIG_IPC_NS depende de (SYSVIPC || POSIX_MQUEUE) en Kconfig. Ya lo medi en
  F-001: IPC_NS aparecia AUSENTE del .config del GKI justamente porque las dos
  estaban apagadas. Sacar SYSVIPC del fragmento PODRIA apagar IPC_NS y dejar al
  contenedor de apps sin namespace de IPC, que SI es bloqueador.
  El fragmento conserva POSIX_MQUEUE=y, asi que la prediccion es que IPC_NS
  sobrevive por esa via. PERO NO SE ASUME: si IPC_NS no queda =y, este falsador
  ABORTA y se declara, porque un verde de KMI con el contenedor roto no sirve.

CONTRA QUE SE COMPARA, y por que es valido:
  contra mediciones/f-004b/baseline.stg, que esta commiteado y salio con sha256
  IDENTICO (440f48ed6759f80e..., 11.317.742 B) en dos runs y dos runners
  distintos. El propio resultado es el control: si el clang del runner difiriera,
  el reporte seria ruido masivo en vez de una linea.
  NOTA MEDIDA HOY, y va en contra de la reproducibilidad: el tar.gz que sirve
  googlesource NO es byte-identico entre runs (3dac554d... en F-004 v3,
  a5e654aa... en F-004c) porque +archive regenera el tarball. Lo que si se
  repitio identico es el .stg, que es lo que importa.

MODO DE USO:  f004d_sin_sysvipc.py build
"""
import hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

RAMA = os.environ.get("F004_RAMA", "android15-6.6")
GS = "https://android.googlesource.com/kernel/common"
OUT = os.environ.get("F004_OUT", "mediciones/f-004d")
WORK = os.environ.get("F004_WORK", "/tmp/f004d")
HOSTCFLAGS = "-DUSE_PKCS11_ENGINE"

# OCHO simbolos: el de F-004c menos CONFIG_SYSVIPC.
FRAGMENTO = """# siao-A: HOST, para que systemd de openKylin arranque
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
CONFIG_FHANDLE=y
CONFIG_POSIX_MQUEUE=y
CONFIG_TMPFS_XATTR=y
CONFIG_AUTOFS_FS=y
# siao-B: CONTENEDOR DE APPS (LXC privilegiado, estilo Waydroid)
CONFIG_PID_NS=y
CONFIG_IPC_NS=y
"""

log = []


def say(*a):
    s = " ".join(str(x) for x in a)
    log.append(s)
    print(s, flush=True)


def sh(cmd, t=21000, guardar=None):
    say("$", cmd[:300])
    t0 = time.time()
    try:
        r = subprocess.run(["bash", "-c", "set -o pipefail; " + cmd],
                           capture_output=True, text=True, timeout=t)
        rc, o, e = r.returncode, r.stdout, r.stderr
    except Exception as ex:
        rc, o, e = -1, "", repr(ex)[:300]
    say("  rc=%d en %.1f s | out %d B | err %d B" % (rc, time.time() - t0, len(o), len(e)))
    if guardar:
        os.makedirs(os.path.dirname(guardar), exist_ok=True)
        with open(guardar, "w") as f:
            f.write("### comando\n%s\n\n### rc DEL COMANDO\n%d\n\n### stdout ENTERO\n%s\n\n"
                    "### stderr ENTERO\n%s\n" % (cmd, rc, o, e))
        say("  guardado entero en", guardar.replace(OUT, "<out>"))
    return rc, o, e


def primer_error(path, n=40):
    if not os.path.isfile(path):
        return
    pat = re.compile(r"error:|Permission denied|Error 1[0-9][0-9]|Error [0-9]|No space left")
    hits = [(i, l.rstrip()) for i, l in enumerate(open(path, errors="replace"), 1)
            if pat.search(l)]
    say("  lineas con pinta de error: %d" % len(hits))
    for i, l in hits[:n]:
        say("   E%-6d| %s" % (i, l[:200]))


def traer():
    src = WORK + "/ack"
    if os.path.isfile(src + "/Makefile"):
        return src
    os.makedirs(src, exist_ok=True)
    u = "%s/+archive/refs/heads/%s.tar.gz" % (GS, RAMA)
    say("  bajando", u)
    tgz = WORK + "/ack.tar.gz"
    h = hashlib.sha256()
    n = 0
    t0 = time.time()
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004d/1"})
    with urllib.request.urlopen(req, timeout=1800) as r, open(tgz, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b); h.update(b); n += len(b)
    say("  bajado %d B en %.1f s | sha256 %s" % (n, time.time() - t0, h.hexdigest()))
    rc, _, e = sh("tar -xzf %s -C %s" % (tgz, src), 1800)
    if rc != 0:
        say("  no se pudo desempaquetar:", e[:200]); return None
    os.remove(tgz)
    # Guard contra el Error 126 de F-004c: fixdep no ejecutable. Se MIDE, no se reza.
    rc, o, _ = sh("ls -la %s/scripts/basic/ 2>/dev/null | head -5; "
                  "stat -c '%%A %%n' %s/scripts/basic/*.c 2>/dev/null | head -3" % (src, src))
    for l in o.splitlines():
        say("   fs|", l[:130])
    return src


def build():
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    say("== F-004d: fragmento de OCHO, CERO parche al ACK | rama %s ==" % RAMA)
    say("  PREDICCION (del auditor, la firmo): reporte sin CRC = UNA linea,")
    say("  0 CRC, 0 byte-size, 0 offsets, 0 structs tocadas. Cero deuda.")
    say("  --- el fragmento, verbatim ---")
    for l in FRAGMENTO.strip().splitlines():
        say("   |", l)
    n = len([l for l in FRAGMENTO.splitlines() if l.startswith("CONFIG_")])
    say("  simbolos: %d (eran 9 en F-004c, 10 en F-004b)" % n)
    if n != 8:
        say("  ABORTO: esperaba 8"); return 3
    if "CONFIG_SYSVIPC" in FRAGMENTO or "CONFIG_CGROUP_PIDS" in FRAGMENTO:
        say("  ABORTO: el fragmento todavia tiene uno de los dos rompedores"); return 3

    rc, o, _ = sh("nproc; free -m | head -2; df -h / | tail -1; "
                  "clang --version | head -1; openssl version")
    for l in o.splitlines():
        say("   |", l[:130])
    src = traer()
    if not src:
        return 3
    say("  CONTROL: el arbol NO se parchea. md5 de sched.h intacto:")
    rc, o, _ = sh("md5sum %s/include/linux/sched.h" % src)
    for l in o.splitlines():
        say("   |", l[:130])

    obj = WORK + "/out-d"
    if os.path.isdir(obj):
        shutil.rmtree(obj)
    os.makedirs(obj, exist_ok=True)
    mk = "make -C %s O=%s LLVM=1 ARCH=arm64" % (src, obj)
    rc, _, _ = sh("%s gki_defconfig" % mk, 3600,
                  guardar=os.path.join(OUT, "f004d-defconfig.txt"))
    if rc != 0:
        say("  gki_defconfig fallo"); return 3

    frag = WORK + "/siao8.fragment"
    open(frag, "w").write(FRAGMENTO)
    rc, _, _ = sh("%s/scripts/kconfig/merge_config.sh -m -O %s %s/.config %s"
                  % (src, obj, obj, frag), 600,
                  guardar=os.path.join(OUT, "f004d-merge.txt"))
    say("  merge_config rc=%d" % rc)
    sh("%s olddefconfig" % mk, 900)

    cfg = open(obj + "/.config").read()
    estado = {}
    for s_ in [l.split("=")[0] for l in FRAGMENTO.splitlines() if l.startswith("CONFIG_")]:
        m = re.search(r"^%s=(.*)$" % re.escape(s_), cfg, re.M)
        estado[s_] = m.group(1) if m else (
            "APAGADO" if re.search(r"^# %s is not set$" % re.escape(s_), cfg, re.M) else "AUSENTE")
    say("  estado de los 8 simbolos:")
    for k, v in estado.items():
        say("      %-24s %s" % (k, v))
    # Los dos que NO deben estar.
    for s_ in ("CONFIG_SYSVIPC", "CONFIG_CGROUP_PIDS"):
        m = re.search(r"^%s=(.*)$" % s_, cfg, re.M)
        say("  CONTROL | %-22s %s" % (s_, m.group(1) if m else "NO esta en =y (correcto)"))

    # EL GUARD DURO: sin IPC_NS el contenedor de apps no sirve, y un verde de KMI
    # con el contenedor roto es un verde inutil.
    if estado.get("CONFIG_IPC_NS") != "y":
        say("  ABORTO POR GUARD: CONFIG_IPC_NS quedo en '%s', no en 'y'."
            % estado.get("CONFIG_IPC_NS"))
        say("  Sacar SYSVIPC apago IPC_NS y POSIX_MQUEUE no alcanzo para sostenerlo.")
        say("  El fragmento de OCHO NO es viable: el contenedor pierde IPC namespace.")
        say("  Se declara y NO se sigue: no tiene sentido medir el KMI de esto.")
        with open(os.path.join(OUT, "f004d-bitacora.txt"), "w") as f:
            f.write("\n".join(log) + "\n")
        with open(os.path.join(OUT, "f004d.json"), "w") as f:
            json.dump({"veredicto": "ABORTADO POR GUARD IPC_NS",
                       "ipc_ns": estado.get("CONFIG_IPC_NS"),
                       "simbolos": estado}, f, indent=2, ensure_ascii=False)
        return 3
    say("  GUARD OK: IPC_NS=y sobrevive por POSIX_MQUEUE, sin SYSVIPC.")

    logf = os.path.join(OUT, "f004d-build.txt")
    rc, _, _ = sh("%s HOSTCFLAGS='%s' -j$(nproc) Image modules" % (mk, HOSTCFLAGS), 20000,
                  guardar=logf)
    primer_error(logf)
    sym = obj + "/Module.symvers"
    ok = os.path.isfile(sym)
    say("  Module.symvers presente:", ok)
    res = {"falsador": "F-004d", "rama": RAMA, "rc_build": rc, "parche_al_ack": False,
           "n_simbolos": n, "simbolos": estado, "module_symvers": ok,
           "prediccion": "1 linea, 0 CRC, 0 byte-size, 0 offsets",
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if ok:
        raw = open(sym).read()
        res["n_lineas_symvers"] = raw.count("\n")
        res["sha256_symvers"] = hashlib.sha256(raw.encode()).hexdigest()
        say("  Module.symvers: %d lineas" % res["n_lineas_symvers"])
        open(os.path.join(OUT, "symvers-d.txt"), "w").write(raw)
        open(os.path.join(OUT, "config-d.txt"), "w").write(cfg)
        sh("cd %s && tar -c --zstd -f %s vmlinux $(find . -name '*.ko' | head -400)"
           % (obj, os.path.abspath(os.path.join(OUT, "elf-d.tar.zst"))), 3600)
        p = os.path.join(OUT, "elf-d.tar.zst")
        if os.path.isfile(p):
            say("  ELF para el stgdiff x86: %d B" % os.path.getsize(p))
    with open(os.path.join(OUT, "f004d.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "f004d-bitacora.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(build())
