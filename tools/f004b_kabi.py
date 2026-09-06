#!/usr/bin/env python3
"""
F-004b-KABI - Se puede prender SYSVIPC SIN romper el KMI?

PREDICCION DECLARADA ANTES DE CORRER (falsable, y firmada en el chat):
  el reporte de stgdiff con --ignore linux_symbol_crc queda VACIO, y task_struct
  NO cambia de tamano. Si sale distinto, esta prediccion muere y se dice.

DE DONDE SALE, y es medicion y no aritmetica de servilleta:
  1) include/linux/sched.h de android15-6.6 deja SEIS slots libres dentro de
     struct task_struct:  ANDROID_KABI_RESERVE(3) .. (8), lineas 1527-1532.
  2) include/linux/android_kabi.h:76 dice que cada slot es
        u64 android_kabi_reservedN      -> 8 B, alineado a 8
     o sea 48 B libres.
  3) struct sysv_sem = un puntero          ->  8 B  (include/linux/sem.h:12)
     struct sysv_shm = un list_head       -> 16 B  (include/linux/shm.h:13)
     total a meter                        -> 24 B  <= 48 B
  4) Y la confirmacion cruzada: el stgdiff de F-004 v3 midio que los offsets se
     corren de 16960 a 17152 bits = 192 bits = 24 BYTES. Los dos caminos,
     independientes, dan el mismo numero.

EL MECANISMO QUE HACE QUE EL CRC TAMPOCO CAMBIE, android_kabi.h:59-74 verbatim:
     #ifdef __GENKSYMS__
     #define _ANDROID_KABI_REPLACE(_orig, _new)   _orig
  genksyms es el que calcula los CRC de Module.symvers, y ve el _orig, no el
  _new. Asi que si el miembro entra por un slot reservado, el CRC NO se mueve.
  Eso predice que los 10.867 CRC cambiados de F-004 v3 tambien desaparecen.

POR QUE sysvshm NECESITA DOS SLOTS, y no es un capricho:
  el guard __ANDROID_KABI_CHECK_SIZE_ALIGN (linea 42) tiene un _Static_assert:
     sizeof(struct{_new;}) <= sizeof(struct{_orig;})
  sysv_shm mide 16 B y un slot mide 8, asi que un ANDROID_KABI_USE simple NO
  compila. Se replican DOS reservados juntos como _orig. **El compilador es el
  testigo: si la cuenta esta mal, el _Static_assert lo dice y no hay veredicto.**

GUARD QUE PUEDE MATAR TODO, y por eso se mide primero:
  ANDROID_KABI_RESERVE(n) se expande a NADA si CONFIG_ANDROID_KABI_RESERVE esta
  apagado (android_kabi.h:100-107). Si en el gki_defconfig esta apagado, los
  slots no existen y este falsador entero es NO MEDIDO. Se mide, no se asume.

MODO DE USO:  f004b_kabi.py build baseline|kabi
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

RAMA = os.environ.get("F004_RAMA", "android15-6.6")
GS = "https://android.googlesource.com/kernel/common"
OUT = os.environ.get("F004_OUT", "mediciones/f-004b")
WORK = os.environ.get("F004_WORK", "/tmp/f004b")
HOSTCFLAGS = "-DUSE_PKCS11_ENGINE"

FRAGMENTO = """# siao-A: HOST, para que systemd de openKylin arranque
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
CONFIG_FHANDLE=y
CONFIG_SYSVIPC=y
CONFIG_POSIX_MQUEUE=y
CONFIG_TMPFS_XATTR=y
CONFIG_AUTOFS_FS=y
# siao-B: CONTENEDOR DE APPS (LXC privilegiado, estilo Waydroid)
CONFIG_PID_NS=y
CONFIG_IPC_NS=y
CONFIG_CGROUP_PIDS=y
"""

# El bloque original, verbatim de android15-6.6 lineas 1075-1078.
ORIG = """#ifdef CONFIG_SYSVIPC
	struct sysv_sem			sysvsem;
	struct sysv_shm			sysvshm;
#endif"""

# Lo que queda en su lugar: los miembros se van a los slots reservados.
NUEVO = """/* SIAO F-004b: sysvsem/sysvshm se movieron a los slots ANDROID_KABI_RESERVE
 * del final de esta struct, para que prender CONFIG_SYSVIPC no corra los
 * offsets de todo lo posterior ni cambie el tamano de task_struct.
 */"""

RES3 = "\tANDROID_KABI_RESERVE(3);"
RES4 = "\tANDROID_KABI_RESERVE(4);"
RES5 = "\tANDROID_KABI_RESERVE(5);"

PATCH3 = """#ifdef CONFIG_SYSVIPC
	ANDROID_KABI_USE(3, struct sysv_sem sysvsem);
#else
	ANDROID_KABI_RESERVE(3);
#endif"""

# sysv_shm mide 16 B: entra replicando DOS reservados juntos como _orig.
PATCH45 = """#ifdef CONFIG_SYSVIPC
	_ANDROID_KABI_REPLACE(u64 android_kabi_reserved4; u64 android_kabi_reserved5,
			      struct sysv_shm sysvshm);
#else
	ANDROID_KABI_RESERVE(4);
	ANDROID_KABI_RESERVE(5);
#endif"""

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
    except subprocess.TimeoutExpired:
        rc, o, e = -9, "", "TIMEOUT"
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
    pat = re.compile(r"error:|_Static_assert|is larger than|not aligned|Error [0-9]+|No space left")
    hits = [(i, l.rstrip()) for i, l in enumerate(open(path, errors="replace"), 1)
            if pat.search(l)]
    say("  lineas con pinta de error: %d" % len(hits))
    for i, l in hits[:n]:
        say("   E%-6d| %s" % (i, l[:200]))


def limpiar(cual):
    b = [os.path.basename(p) for p in sorted(glob.glob(os.path.join(OUT, "*%s*" % cual)))]
    for p in sorted(glob.glob(os.path.join(OUT, "*%s*" % cual))):
        os.remove(p)
    say("  R-09 | archivos previos de '%s' borrados: %s" % (cual, b or "ninguno"))


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
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004b/1"})
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
    return src


def aplicar_parche(src):
    """Devuelve True si el parche se aplico entero. Cada reemplazo se verifica."""
    p = src + "/include/linux/sched.h"
    s = open(p).read()
    antes = len(s)
    say("  sched.h original: %d B | md5 %s"
        % (antes, hashlib.md5(s.encode()).hexdigest()))
    for viejo, nuevo, nombre in ((ORIG, NUEVO, "bloque sysvsem/sysvshm"),
                                 (RES3, PATCH3, "RESERVE(3) -> sysvsem"),
                                 (RES4 + "\n" + RES5, PATCH45, "RESERVE(4)+(5) -> sysvshm")):
        c = s.count(viejo)
        say("  %-28s ocurrencias del original: %d" % (nombre, c))
        if c != 1:
            say("  ABORTO: esperaba exactamente 1. El arbol cambio o mi patron esta mal.")
            return False
        s = s.replace(viejo, nuevo)
    open(p, "w").write(s)
    say("  sched.h parcheado: %d B | md5 %s"
        % (len(s), hashlib.md5(s.encode()).hexdigest()))
    say("  --- el parche, verbatim, tal como quedo en el archivo ---")
    ls = s.splitlines()
    for i, l in enumerate(ls, 1):
        if ("SIAO F-004b" in l or "ANDROID_KABI_USE(3" in l or "_ANDROID_KABI_REPLACE(u64" in l
                or "android_kabi_reserved5," in l or "struct sysv_shm sysvshm" in l):
            for j in range(max(0, i - 3), min(len(ls), i + 4)):
                say("   %5d| %s" % (j + 1, ls[j][:150]))
            say("   ---")
    return True


def build(cual):
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    say("== F-004b build: %s | rama %s ==" % (cual, RAMA))
    say("  PREDICCION DECLARADA: con el parche, el reporte sin CRC queda VACIO")
    say("  y task_struct no cambia de tamano. Falsable.")
    limpiar(cual)
    rc, o, _ = sh("nproc; free -m | head -2; df -h / | tail -1; clang --version | head -1; openssl version")
    for l in o.splitlines():
        say("   |", l[:130])
    src = traer()
    if not src:
        return 3

    if cual == "kabi":
        say("  --- aplicando el parche KABI ---")
        if not aplicar_parche(src):
            return 3

    obj = WORK + "/out-" + cual
    if os.path.isdir(obj):
        shutil.rmtree(obj)
    os.makedirs(obj, exist_ok=True)
    mk = "make -C %s O=%s LLVM=1 ARCH=arm64" % (src, obj)
    rc, _, _ = sh("%s gki_defconfig" % mk, 3600,
                  guardar=os.path.join(OUT, "f004b-%s-defconfig.txt" % cual))
    if rc != 0:
        say("  gki_defconfig fallo"); return 3

    if cual == "kabi":
        frag = WORK + "/siao.fragment"
        open(frag, "w").write(FRAGMENTO)
        rc, _, _ = sh("%s/scripts/kconfig/merge_config.sh -m -O %s %s/.config %s"
                      % (src, obj, obj, frag), 600,
                      guardar=os.path.join(OUT, "f004b-kabi-merge.txt"))
        say("  merge_config rc=%d" % rc)
        sh("%s olddefconfig" % mk, 900)

    cfg = open(obj + "/.config").read()
    # EL GUARD QUE PUEDE MATAR TODO: si esto esta apagado, los slots no existen.
    kabi_on = bool(re.search(r"^CONFIG_ANDROID_KABI_RESERVE=y$", cfg, re.M))
    say("  GUARD | CONFIG_ANDROID_KABI_RESERVE=y ? -> %s" % kabi_on)
    if not kabi_on:
        m = re.search(r"^.*ANDROID_KABI_RESERVE.*$", cfg, re.M)
        say("  linea encontrada en el .config: %s" % (m.group(0) if m else "NINGUNA"))
        say("  Si esta apagado, los slots reservados NO EXISTEN y el falsador")
        say("  entero queda NO MEDIDO. Se declara, no se maquilla.")
    estado = {}
    for s_ in [l.split("=")[0] for l in FRAGMENTO.splitlines() if l.startswith("CONFIG_")]:
        m = re.search(r"^%s=(.*)$" % re.escape(s_), cfg, re.M)
        estado[s_] = m.group(1) if m else (
            "APAGADO" if re.search(r"^# %s is not set$" % re.escape(s_), cfg, re.M) else "AUSENTE")
    say("  estado de los 10 simbolos del fragmento:")
    for k, v in estado.items():
        say("      %-26s %s" % (k, v))

    logf = os.path.join(OUT, "f004b-%s-build.txt" % cual)
    rc, _, _ = sh("%s HOSTCFLAGS='%s' -j$(nproc) Image modules" % (mk, HOSTCFLAGS), 20000,
                  guardar=logf)
    say("  --- resumen leido DEL ARCHIVO (R-08) ---")
    primer_error(logf)

    sym = obj + "/Module.symvers"
    ok = os.path.isfile(sym)
    say("  Module.symvers presente:", ok)
    res = {"brazo": cual, "rama": RAMA, "rc_build": rc, "hostcflags": HOSTCFLAGS,
           "parche_kabi": cual == "kabi", "config_android_kabi_reserve": kabi_on,
           "simbolos_del_fragmento": estado, "module_symvers": ok,
           "prediccion": "reporte sin CRC VACIO y task_struct sin cambio de tamano",
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if ok:
        raw = open(sym).read()
        res["n_lineas_symvers"] = raw.count("\n")
        res["sha256_symvers"] = hashlib.sha256(raw.encode()).hexdigest()
        say("  Module.symvers: %d lineas | sha256 %s"
            % (res["n_lineas_symvers"], res["sha256_symvers"][:20]))
        open(os.path.join(OUT, "symvers-%s.txt" % cual), "w").write(raw)
        open(os.path.join(OUT, "config-%s.txt" % cual), "w").write(cfg)
        rc2, o2, _ = sh("cd %s && ls -la vmlinux && find . -name '*.ko' | wc -l" % obj)
        for l in o2.splitlines():
            say("   |", l[:130])
        sh("cd %s && tar -c --zstd -f %s vmlinux $(find . -name '*.ko' | head -400)"
           % (obj, os.path.abspath(os.path.join(OUT, "elf-%s.tar.zst" % cual))), 3600)
        p = os.path.join(OUT, "elf-%s.tar.zst" % cual)
        if os.path.isfile(p):
            say("  ELF para el stgdiff x86: %d B" % os.path.getsize(p))
    with open(os.path.join(OUT, "f004b-%s.json" % cual), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "f004b-%s-bitacora.txt" % cual), "w") as f:
        f.write("\n".join(log) + "\n")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(build(sys.argv[2] if len(sys.argv) > 2 else "kabi"))
