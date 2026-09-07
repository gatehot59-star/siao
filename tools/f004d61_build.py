#!/usr/bin/env python3
"""
F-004d @ android14-6.1, VERSION 2. Un solo instrumento para los dos brazos.

POR QUE UN INSTRUMENTO NUEVO Y NO UN PARCHE A LOS DOS VIEJOS: el v1 usaba
f004b_kabi.py para el baseline y f004d_sin_sysvipc.py para el brazo de ocho. Dos
codigos distintos para dos brazos que se comparan entre si es exactamente lo que
el metodo prohibe: si difieren, la diferencia observada puede ser del script.
Aca los dos brazos salen del MISMO codigo y la unica variable es el fragmento.

LOS TRES ARREGLOS, cada uno contra un defecto MEDIDO del v1 (run 34049301780):

  ARREGLO 1 - pahole ausente. El brazo de ocho compilo 1.429,7 s y murio asi:
        BTF: .tmp_vmlinux.btf: pahole (pahole) is not available
        Failed to generate BTF for vmlinux
        make[2]: *** [scripts/Makefile.vmlinux:34: vmlinux] Error 1
     android14-6.1 trae CONFIG_DEBUG_INFO_BTF=y y necesita pahole; en 6.6 el
     mismo apt-get alcanzaba. Diferencia de herramientas ENTRE generaciones.
     El workflow instala 'dwarves' (que provee pahole) y ACA se mide que este,
     porque un apt-get que no falla no prueba que el binario quedo en el PATH.

  ARREGLO 2 - el 'fixdep: Permission denied' (Error 126), tres veces, SIEMPRE en
     el brazo baseline y siempre en menos de 1 s. Hipotesis declarada: carrera de
     make -j2, donde gen-hyprel invoca fixdep mientras el linker todavia lo
     escribe (un ELF a medio escribir da EACCES, no ENOENT). Prueba y sorteo a la
     vez: 'make archscripts -j1' ANTES del build paralelo.
     ES UNA PRUEBA REAL, no un parche ciego: si el 126 aparece igual en el paso
     serial, la hipotesis muere y se dice.

  ARREGLO 3 - mi guard roto. El v1 hizo:
        tar -c --zstd -f elf-d.tar.zst vmlinux $(find . -name '*.ko')
        rc=2 en 0.3 s | err 109 B
     y el instrumento SIGUIO, reportando 'ELF para el stgdiff: 20.127.789 B'.
     El artifact existia, pesaba 20 MB, y NO tenia vmlinux adentro. Un artifact
     que existe no prueba que contenga lo que dice (R-12 sobre mi empaquetado).
     Ahora: si vmlinux no existe se ABORTA con mensaje propio, y despues del tar
     se VERIFICA que vmlinux este listado dentro del tarball.

PREDICCION DECLARADA ANTES DE CORRER:
  - archscripts -j1 termina rc=0 en los dos brazos y el 126 NO reaparece.
  - los dos brazos producen vmlinux.
  - el stgdiff da ~68 B, 0 CRC, 0 byte-size, 0 offsets, 0 structs, igual que 6.6.

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
    w("  rc=%d en %.1f s | out %d B | err %d B" % (rc, time.time() - t0, len(o), len(e)))
    if guardar:
        os.makedirs(os.path.dirname(guardar), exist_ok=True)
        open(guardar, "w").write("### comando\n%s\n\n### rc DEL COMANDO\n%d\n\n"
                                 "### stdout ENTERO\n%s\n\n### stderr ENTERO\n%s\n"
                                 % (cmd, rc, o, e))
        w("  guardado entero en", guardar.replace(OUT, "<out>"))
    return rc, o, e


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
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004d61/2"})
    with urllib.request.urlopen(req, timeout=1800) as r, open(tgz, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            h.update(b)
            n += len(b)
    w("  bajado %d B en %.1f s | sha256 %s" % (n, time.time() - t0, h.hexdigest()))
    rc, _, e = sh("tar -xzf %s -C %s" % (tgz, src), 1800)
    if rc != 0:
        w("  ABORTO: no se pudo desempaquetar: %s" % e[:200])
        return None
    os.remove(tgz)
    rc, o, _ = sh("head -5 %s/Makefile" % src)
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
    w("== F-004d @ %s | VERSION 2 | brazo: %s ==" % (RAMA, brazo))
    w("  fecha UTC %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("  PREDICCION: archscripts -j1 rc=0 sin Error 126; los dos brazos producen")
    w("  vmlinux; y el stgdiff da ~68 B con 0 offsets, igual que en 6.6.")
    w("  R-09 | limpiando archivos previos de este brazo")
    for p in sorted(f for f in os.listdir(OUT) if brazo in f):
        os.remove(os.path.join(OUT, p))
        w("     borrado %s" % p)

    rc, o, _ = sh("nproc; free -m | head -2; df -h / | tail -1; clang --version | head -1")
    for l in o.splitlines():
        w("   |", l[:130])

    # ARREGLO 1, primera mitad: que pahole ESTE, medido y no supuesto.
    w("  === ARREGLO 1: pahole ===")
    ph = shutil.which("pahole")
    w("  which pahole -> %s" % (ph or "AUSENTE"))
    if ph:
        rc, o, _ = sh("pahole --version 2>&1 | head -1")
        for l in o.splitlines():
            w("   |", l[:120])
    else:
        w("  AVISO: pahole no esta en el PATH. Si DEBUG_INFO_BTF=y, el link va a fallar")
        w("  igual que en el v1. Se deja constancia ANTES de compilar.")

    src = traer()
    if not src:
        return 3
    if brazo == "baseline":
        rc, o, _ = sh("md5sum %s/include/linux/sched.h" % src)
        for l in o.splitlines():
            w("   CONTROL sched.h intacto |", l[:120])

    obj = WORK + "/out-" + brazo
    if os.path.isdir(obj):
        shutil.rmtree(obj)
    os.makedirs(obj, exist_ok=True)
    mk = "make -C %s O=%s LLVM=1 ARCH=arm64" % (src, obj)

    rc, _, _ = sh("%s gki_defconfig" % mk, 3600,
                  guardar=os.path.join(OUT, "v2-%s-defconfig.txt" % brazo))
    if rc != 0:
        w("  ABORTO: gki_defconfig fallo")
        return 3

    if brazo == "ocho":
        frag = WORK + "/siao8.fragment"
        open(frag, "w").write(FRAGMENTO)
        w("  fragmento de OCHO, verbatim:")
        for l in FRAGMENTO.strip().splitlines():
            w("   |", l)
        rc, _, _ = sh("%s/scripts/kconfig/merge_config.sh -m -O %s %s/.config %s"
                      % (src, obj, obj, frag), 600,
                      guardar=os.path.join(OUT, "v2-ocho-merge.txt"))
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
    w("  ARREGLO 1, segunda mitad | CONFIG_DEBUG_INFO_BTF=y ? -> %s" % btf)
    w("  (si es True y pahole falta, el link de vmlinux va a fallar. Los dos datos")
    w("   quedan medidos ANTES del build, para que la causa no haya que deducirla.)")

    # GUARD del brazo de ocho: sin IPC_NS el contenedor no sirve.
    if brazo == "ocho" and estado.get("CONFIG_IPC_NS") != "y":
        w("  ABORTO POR GUARD: IPC_NS quedo en %r, no en 'y'."
          % estado.get("CONFIG_IPC_NS"))
        cerrar(brazo, {"veredicto": "ABORTADO POR GUARD IPC_NS", "simbolos": estado})
        return 3

    # ARREGLO 2: archscripts EN SERIE, antes del build paralelo.
    w("  === ARREGLO 2: archscripts con -j1 (prueba de la hipotesis de la carrera) ===")
    logs = os.path.join(OUT, "v2-%s-archscripts.txt" % brazo)
    rc_as, o_as, e_as = sh("%s -j1 archscripts" % mk, 3600, guardar=logs)
    e126 = "Error 126" in (o_as + e_as) or "Permission denied" in (o_as + e_as)
    w("  archscripts rc=%d | reaparecio el Error 126 o Permission denied: %s"
      % (rc_as, e126))
    if e126:
        w("  HIPOTESIS MUERTA: el 126 aparece TAMBIEN en serie, asi que NO era una")
        w("  carrera de -j2. Hay que buscar en otro lado. Se declara.")
    elif rc_as == 0:
        w("  HIPOTESIS SOSTENIDA en esta corrida: en serie no aparece.")
        w("  Una corrida no prueba una intermitencia: sigue siendo hipotesis.")
    fx = obj + "/scripts/basic/fixdep"
    if os.path.isfile(fx):
        st = os.stat(fx)
        w("  fixdep: %d B | modo %o | ejecutable para mi: %s"
          % (st.st_size, st.st_mode & 0o777, os.access(fx, os.X_OK)))
    else:
        w("  fixdep NO existe despues de archscripts")
    if rc_as != 0:
        w("  ABORTO: archscripts fallo, no tiene sentido seguir")
        errores(logs)
        cerrar(brazo, {"veredicto": "ROJO en archscripts", "rc_archscripts": rc_as,
                       "error_126": e126, "simbolos": estado})
        return 3

    logb = os.path.join(OUT, "v2-%s-build.txt" % brazo)
    rc, _, _ = sh("%s HOSTCFLAGS='%s' -j$(nproc) Image modules" % (mk, HOSTCFLAGS),
                  20000, guardar=logb)
    w("  --- resumen leido DEL ARCHIVO (R-08) ---")
    errores(logb)

    # ARREGLO 3: el guard duro. Sin vmlinux no hay artifact que valga.
    w("  === ARREGLO 3: guard duro de vmlinux ===")
    vm = obj + "/vmlinux"
    sym = obj + "/Module.symvers"
    hay_vm, hay_sym = os.path.isfile(vm), os.path.isfile(sym)
    w("  vmlinux presente        : %s%s"
      % (hay_vm, " (%d B)" % os.path.getsize(vm) if hay_vm else ""))
    w("  Module.symvers presente : %s" % hay_sym)
    res = {"falsador": "F-004d@6.1 v2", "rama": RAMA, "brazo": brazo,
           "rc_archscripts": rc_as, "error_126": e126, "rc_build": rc,
           "debug_info_btf": btf, "pahole": ph, "parche_al_ack": False,
           "simbolos": estado, "vmlinux": hay_vm, "module_symvers": hay_sym,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if hay_sym:
        raw = open(sym).read()
        res["n_lineas_symvers"] = raw.count("\n")
        res["sha256_symvers"] = hashlib.sha256(raw.encode()).hexdigest()
        w("  Module.symvers: %d lineas | sha256 %s"
          % (res["n_lineas_symvers"], res["sha256_symvers"][:24]))
        open(os.path.join(OUT, "v2-symvers-%s.txt" % brazo), "w").write(raw)
        open(os.path.join(OUT, "v2-config-%s.txt" % brazo), "w").write(cfg)
    if not hay_vm:
        w("  ABORTO POR GUARD: no hay vmlinux, asi que NO se empaqueta nada.")
        w("  El v1 en este punto empaqueto 20 MB sin vmlinux y siguio. Eso no vuelve")
        w("  a pasar: sin vmlinux no hay artifact, y el veredicto es NO MEDIDO.")
        res["veredicto"] = "NO MEDIDO: sin vmlinux"
        cerrar(brazo, res)
        return 3

    tarball = os.path.abspath(os.path.join(OUT, "elf-%s-android14-6.1.tar.zst" % brazo))
    rc_t, _, _ = sh("cd %s && tar -c --zstd -f %s vmlinux $(find . -name '*.ko' | head -400)"
                    % (obj, tarball), 3600)
    if rc_t != 0 or not os.path.isfile(tarball):
        w("  ABORTO: el tar fallo con rc=%d" % rc_t)
        res["veredicto"] = "NO MEDIDO: el tar fallo"
        cerrar(brazo, res)
        return 3
    # Y se VERIFICA el contenido, no solo que el archivo exista.
    rc_v, o_v, _ = sh("tar -t --zstd -f %s | head -3; echo '---'; "
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
    json.dump(res, open(os.path.join(OUT, "v2-%s.json" % brazo), "w"),
              indent=2, ensure_ascii=False)
    open(os.path.join(OUT, "v2-%s-bitacora.txt" % brazo), "w").write("\n".join(log) + "\n")
    w("  cerrado: v2-%s.json y v2-%s-bitacora.txt" % (brazo, brazo))


if __name__ == "__main__":
    sys.exit(main())
