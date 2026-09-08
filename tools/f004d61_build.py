#!/usr/bin/env python3
"""
F-004d @ android14-6.1, VERSION 3. Un solo instrumento para los dos brazos.

POR QUE UN INSTRUMENTO UNICO: el v1 usaba f004b_kabi.py para el baseline y
f004d_sin_sysvipc.py para el brazo de ocho. Dos codigos distintos para dos brazos
que se comparan entre si es lo que el metodo prohibe: si difieren, la diferencia
observada puede ser del script. Aca la unica variable es el fragmento.

HISTORIAL DE DEFECTOS MEDIDOS, y que arregla cada version:

  v1 (run 34049301780) - DOS causas de arnes, ninguna del fragmento:
     a) pahole ausente -> el link de vmlinux murio con
           BTF: .tmp_vmlinux.btf: pahole (pahole) is not available
        android14-6.1 trae CONFIG_DEBUG_INFO_BTF=y; en 6.6 el mismo apt-get
        alcanzaba. Diferencia de herramientas ENTRE generaciones (R-17).
     b) 'fixdep: Permission denied' (Error 126) en el brazo baseline.
     c) y un guard MIO roto: el tar fallo con rc=2 y el instrumento siguio,
        reportando un artifact de 20 MB SIN vmlinux adentro.

  v2 (run 34126598730) - pahole RESUELTO (v1.25, vmlinux de 354.673.168 B en el
     brazo de ocho) y el guard de vmlinux FUNCIONO (el brazo caido no empaqueto
     nada). Pero el 126 volvio, y la bitacora dijo por que:
           make ... -j1 archscripts        -> rc=0 en 0.0 s
           fixdep: 71464 B | modo 755 | ejecutable: True
           make ... HOSTCFLAGS='...' -j2 Image modules
             HOSTCC scripts/basic/fixdep   <-- LO RECOMPILA
             /bin/sh: 1: scripts/basic/fixdep: Permission denied
     CAUSA RAIZ, y es un defecto de mi arnes: le pasaba HOSTCFLAGS al build
     paralelo y NO al paso serial. HOSTCFLAGS es parte de la firma de los targets
     de host, asi que make INVALIDA fixdep y gen-hyprel y los rehace -- esta vez
     en paralelo. Mi candado serial protegia un binario que despues se tiraba.
     Y el 0,0 s lo delataba: un paso de mitigacion que no hace trabajo no mitiga.

  v3 (este) - el paso serial lleva el MISMO HOSTCFLAGS, mas un guard que declara
     NO MITIGADO si archscripts vuelve a tardar ~0 s.

PREDICCION DECLARADA ANTES DE CORRER:
  - archscripts tarda MAS de 0,5 s (ahora si tiene trabajo: rehacer los targets
    de host con la firma definitiva).
  - el 126 NO reaparece en el build paralelo.
  - los dos brazos producen vmlinux.
  - el stgdiff da ~68 B, 0 CRC, 0 byte-size, 0 offsets, 0 structs, igual que 6.6.
  Si el 126 reaparece con el HOSTCFLAGS ya aplicado en serie, la hipotesis de la
  carrera MUERE y hay que buscar en otro lado.

MODO DE USO:  f004d61_build.py baseline|ocho
"""
import hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

RAMA = os.environ.get("F004_RAMA", "android14-6.1")
GS = "https://android.googlesource.com/kernel/common"
OUT = os.environ.get("F004_OUT", "mediciones/f-004d-61")
WORK = os.environ.get("F004_WORK", "/tmp/f004d61")
HOSTCFLAGS = "-DUSE_PKCS11_ENGINE"

# OCHO simbolos: sin SYSVIPC y sin CGROUP_PIDS, las dos unicas causas medidas.
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


def w(*a):
    s = " ".join(str(x) for x in a)
    log.append(s)
    print(s, flush=True)


def sh(cmd, t=21000, guardar=None):
    w("$", cmd[:280])
    t0 = time.time()
    try:
        r = subprocess.run(["bash", "-c", "set -o pipefail; " + cmd],
                           capture_output=True, text=True, timeout=t)
        rc, o, e = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        rc, o, e = -9, "", "TIMEOUT tras %ss" % t
    except Exception as ex:
        rc, o, e = -1, "", repr(ex)[:200]
    dt = time.time() - t0
    w("  rc=%d en %.1f s | out %d B | err %d B" % (rc, dt, len(o), len(e)))
    if guardar:
        os.makedirs(os.path.dirname(guardar), exist_ok=True)
        open(guardar, "w").write("### comando\n%s\n\n### rc DEL COMANDO\n%d\n\n"
                                 "### segundos\n%.2f\n\n### stdout ENTERO\n%s\n\n"
                                 "### stderr ENTERO\n%s\n" % (cmd, rc, dt, o, e))
        w("  guardado entero en", guardar.replace(OUT, "<out>"))
    return rc, o, e, dt


def errores(path, n=25):
    if not os.path.isfile(path):
        return []
    pat = re.compile(r"error:|Error 1[0-9][0-9]|Error [0-9]|Permission denied|"
                     r"is not available|No space left|undefined reference")
    hits = [(i, l.rstrip()) for i, l in enumerate(open(path, errors="replace"), 1)
            if pat.search(l)]
    w("  lineas con pinta de error: %d" % len(hits))
    for i, l in hits[:n]:
        w("   E%-6d| %s" % (i, l[:190]))
    return hits


def traer():
    src = WORK + "/ack"
    if os.path.isfile(src + "/Makefile"):
        w("  el arbol ya esta en", src)
        return src
    os.makedirs(src, exist_ok=True)
    u = "%s/+archive/refs/heads/%s.tar.gz" % (GS, RAMA)
    w("  bajando", u)
    tgz = WORK + "/ack.tar.gz"
    h = hashlib.sha256()
    n = 0
    t0 = time.time()
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004d61/3"})
    with urllib.request.urlopen(req, timeout=1800) as r, open(tgz, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            h.update(b)
            n += len(b)
    w("  bajado %d B en %.1f s | sha256 %s" % (n, time.time() - t0, h.hexdigest()))
    rc, _, e, _ = sh("tar -xzf %s -C %s" % (tgz, src), 1800)
    if rc != 0:
        w("  ABORTO: no se pudo desempaquetar: %s" % e[:200])
        return None
    os.remove(tgz)
    rc, o, _, _ = sh("head -5 %s/Makefile" % src)
    for l in o.splitlines():
        w("   |", l[:100])
    return src


def main():
    brazo = sys.argv[1] if len(sys.argv) > 1 else "ocho"
    if brazo not in ("baseline", "ocho"):
        w("ABORTO: brazo desconocido %r" % brazo)
        return 3
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    w("== F-004d @ %s | VERSION 3 | brazo: %s ==" % (RAMA, brazo))
    w("  fecha UTC %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("  PREDICCION: archscripts CON HOSTCFLAGS tarda mas de 0,5 s, el 126 no")
    w("  reaparece, los dos brazos producen vmlinux, y el stgdiff da ~68 B.")
    w("  R-09 | limpiando archivos previos de este brazo")
    for p in sorted(f for f in os.listdir(OUT) if brazo in f):
        os.remove(os.path.join(OUT, p))
        w("     borrado %s" % p)

    rc, o, _, _ = sh("nproc; free -m | head -2; df -h / | tail -1; clang --version | head -1")
    for l in o.splitlines():
        w("   |", l[:130])

    w("  === pahole, medido y no supuesto ===")
    ph = shutil.which("pahole")
    w("  which pahole -> %s" % (ph or "AUSENTE"))
    if ph:
        rc, o, _, _ = sh("pahole --version 2>&1 | head -1")
        for l in o.splitlines():
            w("   |", l[:120])

    src = traer()
    if not src:
        return 3
    if brazo == "baseline":
        rc, o, _, _ = sh("md5sum %s/include/linux/sched.h" % src)
        for l in o.splitlines():
            w("   CONTROL sched.h intacto |", l[:120])

    obj = WORK + "/out-" + brazo
    if os.path.isdir(obj):
        shutil.rmtree(obj)
    os.makedirs(obj, exist_ok=True)
    # EL ARREGLO DEL v3: HOSTCFLAGS forma parte del comando base, asi que TODOS
    # los pasos (defconfig, archscripts, build) comparten la misma firma de host
    # y make no tiene motivo para rehacer fixdep en el paso paralelo.
    mk = "make -C %s O=%s LLVM=1 ARCH=arm64 HOSTCFLAGS='%s'" % (src, obj, HOSTCFLAGS)
    w("  comando base (HOSTCFLAGS en TODOS los pasos, arreglo del v3):")
    w("   | %s" % mk)

    rc, _, _, _ = sh("%s gki_defconfig" % mk, 3600,
                     guardar=os.path.join(OUT, "v3-%s-defconfig.txt" % brazo))
    if rc != 0:
        w("  ABORTO: gki_defconfig fallo")
        return 3

    if brazo == "ocho":
        frag = WORK + "/siao8.fragment"
        open(frag, "w").write(FRAGMENTO)
        w("  fragmento de OCHO, verbatim:")
        for l in FRAGMENTO.strip().splitlines():
            w("   |", l)
        rc, _, _, _ = sh("%s/scripts/kconfig/merge_config.sh -m -O %s %s/.config %s"
                         % (src, obj, obj, frag), 600,
                         guardar=os.path.join(OUT, "v3-ocho-merge.txt"))
        w("  merge_config rc=%d" % rc)
        sh("%s olddefconfig" % mk, 900)

    cfg = open(obj + "/.config").read()
    estado = {}
    for s_ in [l.split("=")[0] for l in FRAGMENTO.splitlines() if l.startswith("CONFIG_")]:
        m = re.search(r"^%s=(.*)$" % re.escape(s_), cfg, re.M)
        estado[s_] = m.group(1) if m else (
            "APAGADO" if re.search(r"^# %s is not set$" % re.escape(s_), cfg, re.M)
            else "AUSENTE")
    w("  estado de los 8 simbolos del fragmento en ESTE brazo:")
    for k, v in estado.items():
        w("      %-24s %s" % (k, v))
    for s_ in ("CONFIG_SYSVIPC", "CONFIG_CGROUP_PIDS"):
        m = re.search(r"^%s=(.*)$" % s_, cfg, re.M)
        w("  CONTROL | %-22s %s" % (s_, m.group(1) if m else "NO esta en =y (correcto)"))
    btf = bool(re.search(r"^CONFIG_DEBUG_INFO_BTF=y$", cfg, re.M))
    w("  CONFIG_DEBUG_INFO_BTF=y ? -> %s | pahole -> %s" % (btf, ph or "AUSENTE"))

    if brazo == "ocho" and estado.get("CONFIG_IPC_NS") != "y":
        w("  ABORTO POR GUARD: IPC_NS quedo en %r, no en 'y'."
          % estado.get("CONFIG_IPC_NS"))
        cerrar(brazo, {"veredicto": "ABORTADO POR GUARD IPC_NS", "simbolos": estado})
        return 3

    w("  === archscripts en SERIE, con la firma de host DEFINITIVA ===")
    logs = os.path.join(OUT, "v3-%s-archscripts.txt" % brazo)
    rc_as, o_as, e_as, dt_as = sh("%s -j1 archscripts" % mk, 3600, guardar=logs)
    e126 = "Error 126" in (o_as + e_as) or "Permission denied" in (o_as + e_as)
    hizo_trabajo = dt_as >= 0.5 or "HOSTCC" in (o_as + e_as)
    w("  archscripts rc=%d en %.2f s | Error 126 o Permission denied: %s"
      % (rc_as, dt_as, e126))
    w("  HOSTCC en su salida: %s | hizo trabajo: %s"
      % ("HOSTCC" in (o_as + e_as), hizo_trabajo))
    # EL GUARD QUE FALTABA EN v2: un paso que no hace trabajo no mitiga nada.
    if not hizo_trabajo:
        w("  AVISO NO MITIGADO: archscripts no hizo trabajo (%.2f s, sin HOSTCC)."
          % dt_as)
        w("  En el v2 esto tardo 0,0 s y yo lo lei como 'hipotesis sostenida'.")
        w("  Un exito sin trabajo no es un exito: es un NO MEDIDO. Se declara y")
        w("  se sigue, porque el build paralelo es el que decide.")
    if e126:
        w("  HIPOTESIS MUERTA: el 126 aparece en SERIE con la firma definitiva.")
        w("  No era una carrera de -j2. Hay que buscar en otro lado.")
    fx = obj + "/scripts/basic/fixdep"
    if os.path.isfile(fx):
        st = os.stat(fx)
        w("  fixdep: %d B | modo %o | ejecutable: %s | mtime %s"
          % (st.st_size, st.st_mode & 0o777, os.access(fx, os.X_OK),
             time.strftime("%H:%M:%S", time.gmtime(st.st_mtime))))
    else:
        w("  fixdep NO existe despues de archscripts")
    if rc_as != 0:
        w("  ABORTO: archscripts fallo")
        errores(logs)
        cerrar(brazo, {"veredicto": "ROJO en archscripts", "rc_archscripts": rc_as,
                       "error_126": e126, "segundos_archscripts": round(dt_as, 2),
                       "hizo_trabajo": hizo_trabajo, "simbolos": estado})
        return 3

    logb = os.path.join(OUT, "v3-%s-build.txt" % brazo)
    rc, _, _, _ = sh("%s -j$(nproc) Image modules" % mk, 20000, guardar=logb)
    w("  --- resumen leido DEL ARCHIVO (R-08) ---")
    hits = errores(logb)
    e126b = any("Error 126" in l or "Permission denied" in l for _, l in hits)
    w("  el 126 reaparecio en el build PARALELO: %s" % e126b)
    if e126b:
        w("  HIPOTESIS MUERTA: con HOSTCFLAGS unificado el 126 sigue. No es la")
        w("  recompilacion de fixdep. Proxima via: -j1 en todo el build.")
    else:
        w("  HIPOTESIS SOSTENIDA: unificar HOSTCFLAGS elimino el 126 en este brazo.")

    w("  === guard duro de vmlinux ===")
    vm = obj + "/vmlinux"
    sym = obj + "/Module.symvers"
    hay_vm, hay_sym = os.path.isfile(vm), os.path.isfile(sym)
    w("  vmlinux presente        : %s%s"
      % (hay_vm, " (%d B)" % os.path.getsize(vm) if hay_vm else ""))
    w("  Module.symvers presente : %s" % hay_sym)
    res = {"falsador": "F-004d@6.1 v3", "rama": RAMA, "brazo": brazo,
           "rc_archscripts": rc_as, "segundos_archscripts": round(dt_as, 2),
           "archscripts_hizo_trabajo": hizo_trabajo,
           "error_126_serial": e126, "error_126_paralelo": e126b,
           "rc_build": rc, "debug_info_btf": btf, "pahole": ph,
           "parche_al_ack": False, "simbolos": estado,
           "vmlinux": hay_vm, "module_symvers": hay_sym,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if hay_sym:
        raw = open(sym).read()
        res["n_lineas_symvers"] = raw.count("\n")
        res["sha256_symvers"] = hashlib.sha256(raw.encode()).hexdigest()
        w("  Module.symvers: %d lineas | sha256 %s"
          % (res["n_lineas_symvers"], res["sha256_symvers"][:24]))
        open(os.path.join(OUT, "v3-symvers-%s.txt" % brazo), "w").write(raw)
        open(os.path.join(OUT, "v3-config-%s.txt" % brazo), "w").write(cfg)
    if not hay_vm:
        w("  ABORTO POR GUARD: no hay vmlinux, no se empaqueta nada.")
        res["veredicto"] = "NO MEDIDO: sin vmlinux"
        cerrar(brazo, res)
        return 3

    tarball = os.path.abspath(os.path.join(OUT, "elf-%s-android14-6.1.tar.zst" % brazo))
    rc_t, _, _, _ = sh("cd %s && tar -c --zstd -f %s vmlinux "
                       "$(find . -name '*.ko' | head -400)" % (obj, tarball), 3600)
    if rc_t != 0 or not os.path.isfile(tarball):
        w("  ABORTO: el tar fallo con rc=%d" % rc_t)
        res["veredicto"] = "NO MEDIDO: el tar fallo"
        cerrar(brazo, res)
        return 3
    rc_v, o_v, _, _ = sh("tar -t --zstd -f %s | head -3; echo '---'; "
                         "tar -t --zstd -f %s | grep -c '\\.ko$'" % (tarball, tarball), 600)
    for l in o_v.splitlines():
        w("   tar|", l[:120])
    tiene_vm = "vmlinux" in o_v
    w("  el tarball CONTIENE vmlinux: %s | %d B" % (tiene_vm, os.path.getsize(tarball)))
    if not tiene_vm:
        w("  ABORTO POR GUARD: el tarball existe pero no tiene vmlinux adentro.")
        res["veredicto"] = "NO MEDIDO: tarball sin vmlinux"
        cerrar(brazo, res)
        return 3
    res["veredicto"] = "brazo OK: vmlinux y symvers producidos y verificados"
    cerrar(brazo, res)
    return 0


def cerrar(brazo, res):
    json.dump(res, open(os.path.join(OUT, "v3-%s.json" % brazo), "w"),
              indent=2, ensure_ascii=False)
    open(os.path.join(OUT, "v3-%s-bitacora.txt" % brazo), "w").write("\n".join(log) + "\n")
    w("  cerrado: v3-%s.json y v3-%s-bitacora.txt" % (brazo, brazo))


if __name__ == "__main__":
    sys.exit(main())
