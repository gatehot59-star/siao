#!/usr/bin/env python3
"""
F-004d @ android14-6.1, VERSION 4.1. Un solo instrumento para los dos brazos.

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

  v3 (VERDE en ABI, 68 B) - el paso serial lleva el MISMO HOSTCFLAGS, mas un
     guard que declara NO MITIGADO si archscripts tarda ~0 s. Dio 0,02 s, asi que
     el 126 quedo como carrera GANADA y no cerrada.

  v4 - TRES defectos de empaquetado, y el primero lo encontro FABLE 5.1
     auditando el CODIGO, no la salida:

     H-2) el v3 compilaba 'Image modules' y empaquetaba SOLO vmlinux y los .ko.
          'arch/arm64/boot/Image' -- el unico artefacto ARRANCABLE de todo el
          build -- se tiraba con el directorio de trabajo. Consecuencia: el
          kernel que el proyecto declara VERDE en ABI no existia como cosa que
          se pueda pasar a QEMU, y F-001-S2 no era ejecutable. Es el defecto mas
          caro de la serie porque no rompe ningun rc: el veredicto de ABI era
          correcto y el artefacto faltaba en silencio.
          ARREGLO: 'arch/arm64/boot/Image' entra al tarball, con guard duro de
          presencia adentro, y con su sha256 y bytes en el JSON.

     H-2b) el tope silencioso: '$(find . -name "*.ko" | head -400)'. En la
          corrida del v3 no corto nada (60 modulos por brazo, medido en el
          veredicto), asi que era un riesgo LATENTE y no un defecto
          materializado -- pero un tope que no avisa cuando corta no tiene
          forma de avisar.
          ARREGLO: lista de miembros explicita, sin tope, con la cuenta real
          registrada y un guard que compara la cuenta de la lista contra la
          cuenta DENTRO del tarball. Si difieren, es NO MEDIDO.

     H-2c) un defecto mio que FABLE no vio: la escritura de '.config' estaba
          ANIDADA dentro de 'if hay_sym:'. O sea el .config solo se guardaba si
          Module.symvers existia. En la corrida del v3 existio y por eso el
          archivo esta ahi (v3-config-ocho.txt, 205.550 B) -- pero un brazo que
          produjera vmlinux sin symvers habria perdido justo el archivo que
          dice con que configuracion se construyo.
          ARREGLO: el .config se escribe SIEMPRE, apenas se lee.

     Y un KAT gratis, propuesto por FABLE: 'Image' es literalmente el vmlinux
     pasado por objcopy con los OBJCOPYFLAGS_Image de arm64. Reconstruirlo y
     cruzar sha256 verifica de una sola vez que el vmlinux y el Image del
     tarball salieron del MISMO link. Con una salvedad de metodo: los flags NO
     se hardcodean de memoria, se LEEN de 'arch/arm64/Makefile' del arbol que se
     acaba de bajar, y si la linea no esta el KAT se declara NO MEDIDO en vez de
     rojo. Un KAT que compara contra una constante recordada mide mi memoria.

  v4.1 (este) - un defecto MIO del v4, encontrado por el banco de pruebas
     'test_f004d61_empaquetado.py' ANTES de gastar un run:

     H-2d) el guard de contenido del tarball usaba la regex '^\\./?vmlinux$'.
          Eso NO es "punto y barra opcionales": '\\.' es un punto OBLIGATORIO y
          solo la barra es opcional. Como GNU tar lista 'vmlinux' pelado, la
          regex nunca matcheaba, el guard daba FALSO NEGATIVO y el instrumento
          habria abortado con 'NO MEDIDO: tarball sin vmlinux' DESPUES de dos
          horas de build correcto. Peor: el control negativo del banco
          ('detecta un tarball SIN Image') estaba PASANDO por la razon
          equivocada, porque una regex que no matchea nunca tampoco matchea en
          el caso malo. Un control que pasa sin discriminar no es un control.
          ARREGLO: '^(?:\\./)?vmlinux$'. Y el listado se lee UNA vez en Python;
          se fueron los tres 'grep -c' del shell, que eran una segunda fuente de
          verdad para lo mismo.

PREDICCION DECLARADA ANTES DE CORRER EL v4.1:
  - el brazo 'ocho' produce vmlinux, Module.symvers Y arch/arm64/boot/Image.
  - el KAT da IDENTICO: sha256(objcopy(vmlinux)) == sha256(Image).
  - n_modulos = 60, igual que el v3 (si difiere, algo cambio en el arbol y hay
    que mirar eso ANTES de interpretar cualquier otra cosa).
  - archscripts vuelve a tardar ~0 s y el guard vuelve a declarar NO MITIGADO:
    el 126 no se cierra en este run y no es lo que este run mide.
  Si el KAT sale DISTINTO, no hay que seguir: el vmlinux y el Image no vienen
  del mismo link y todo el veredicto de ABI queda en duda.

MODO DE USO:  f004d61_build.py baseline|ocho
BANCO:        test_f004d61_empaquetado.py   (corre sin kernel, 24 casos)
"""
import hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

RAMA = os.environ.get("F004_RAMA", "android14-6.1")
GS = "https://android.googlesource.com/kernel/common"
OUT = os.environ.get("F004_OUT", "mediciones/f-004d-61")
WORK = os.environ.get("F004_WORK", "/tmp/f004d61")
HOSTCFLAGS = "-DUSE_PKCS11_ENGINE"
IMAGE_REL = "arch/arm64/boot/Image"

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


def sha256_de(path, trozo=1 << 20):
    """sha256 COMPLETO de 64 hex. El f004d61_stg.py trunca a 32 y lo rotula
    sha256: ese defecto esta declarado en el mapa y no se replica aca."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(trozo)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def en_el_listado(lista, miembro):
    """Busca un miembro en la salida de 'tar -t'. GNU tar puede listar 'x' o
    './x' segun como se lo invoco, asi que el prefijo es opcional -- y ESO fue
    el H-2d: '\\./?x' pide el punto obligatorio y la barra opcional, que es la
    lectura al reves. El grupo tiene que envolver a los dos."""
    return re.search(r"^(?:\./)?%s$" % re.escape(miembro), lista, re.M) is not None


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


def flags_objcopy_de_la_fuente(src):
    """Lee OBJCOPYFLAGS_Image de arch/arm64/Makefile EN VEZ de recordarlo.
    Devuelve (flags, linea_cruda). flags None => el KAT es NO MEDIDO."""
    mkf = os.path.join(src, "arch/arm64/Makefile")
    if not os.path.isfile(mkf):
        return None, "AUSENTE: %s" % mkf
    for l in open(mkf, errors="replace"):
        m = re.match(r"\s*OBJCOPYFLAGS_Image\s*:?\+?=\s*(.*?)\s*$", l)
        if m:
            return m.group(1), l.rstrip("\n")
    return None, "no hay linea OBJCOPYFLAGS_Image en arch/arm64/Makefile"


def kat_objcopy(src, obj, dest):
    """KAT de FABLE: Image == objcopy(vmlinux) con los flags de la fuente.
    Tres estados, nunca dos: identico, distinto, NO MEDIDO."""
    res = {"kat": "NO MEDIDO", "kat_identico": None}
    flags, crudo = flags_objcopy_de_la_fuente(src)
    res["objcopyflags_de_la_fuente"] = crudo
    w("  OBJCOPYFLAGS_Image, LEIDO del arbol (no de memoria):")
    w("   | %s" % crudo)
    if not flags:
        w("  KAT NO MEDIDO: no pude leer los flags de la fuente.")
        res["kat"] = "NO MEDIDO: sin OBJCOPYFLAGS_Image en la fuente"
        return res
    oc = shutil.which("llvm-objcopy") or shutil.which("objcopy")
    res["objcopy"] = oc
    w("  objcopy usado: %s" % (oc or "AUSENTE"))
    if not oc:
        res["kat"] = "NO MEDIDO: no hay objcopy en la maquina"
        return res
    vm = os.path.join(obj, "vmlinux")
    img = os.path.join(obj, IMAGE_REL)
    if not (os.path.isfile(vm) and os.path.isfile(img)):
        res["kat"] = "NO MEDIDO: falta vmlinux o Image"
        return res
    rc, _, e, _ = sh("%s %s %s %s" % (oc, flags, vm, dest), 3600)
    if rc != 0 or not os.path.isfile(dest):
        w("  KAT NO MEDIDO: objcopy rc=%d | %s" % (rc, e[:200]))
        res["kat"] = "NO MEDIDO: objcopy rc=%d" % rc
        return res
    a, b = sha256_de(dest), sha256_de(img)
    res.update({"sha256_reconstruido": a, "sha256_image": b,
                "bytes_reconstruido": os.path.getsize(dest),
                "bytes_image": os.path.getsize(img),
                "kat_identico": a == b,
                "kat": "IDENTICO" if a == b else "DISTINTO"})
    w("  Image del build   : %d B | sha256 %s" % (res["bytes_image"], b))
    w("  Image reconstruido: %d B | sha256 %s" % (res["bytes_reconstruido"], a))
    w("  KAT -> %s" % res["kat"])
    if not res["kat_identico"]:
        w("  ATENCION: el vmlinux y el Image NO salieron del mismo link.")
    return res


def lista_de_miembros(obj, lst):
    """Reemplaza a '$(find . -name "*.ko" | head -400)'. Sin tope, y devuelve la
    cuenta real para poder cruzarla contra lo que quedo DENTRO del tarball."""
    kos = []
    for raiz, _, files in os.walk(obj):
        for f in files:
            if f.endswith(".ko"):
                kos.append(os.path.relpath(os.path.join(raiz, f), obj))
    kos.sort()
    with open(lst, "w") as fh:
        fh.write("vmlinux\n")
        fh.write(IMAGE_REL + "\n")
        for k in kos:
            fh.write(k + "\n")
    w("  miembros del tarball: 2 fijos (vmlinux, %s) + %d modulos, SIN tope"
      % (IMAGE_REL, len(kos)))
    return kos


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
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004d61/4"})
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
    w("== F-004d @ %s | VERSION 4.1 | brazo: %s ==" % (RAMA, brazo))
    w("  fecha UTC %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("  QUE MIDE ESTE RUN: que el brazo produzca arch/arm64/boot/Image, o sea")
    w("  un kernel ARRANCABLE, que el v3 compilaba y tiraba (H-2 de FABLE).")
    w("  PREDICCION: Image presente, KAT objcopy IDENTICO, n_modulos 60, y")
    w("  archscripts vuelve a dar ~0 s (el 126 NO se cierra en este run).")
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
                     guardar=os.path.join(OUT, "v4-%s-defconfig.txt" % brazo))
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
                         guardar=os.path.join(OUT, "v4-ocho-merge.txt"))
        w("  merge_config rc=%d" % rc)
        sh("%s olddefconfig" % mk, 900)

    cfg = open(obj + "/.config").read()
    # H-2c: el v3 escribia esto DENTRO de 'if hay_sym'. Ahora va siempre, apenas
    # se lee, porque el .config es lo que dice CON QUE se construyo el brazo.
    open(os.path.join(OUT, "v4-config-%s.txt" % brazo), "w").write(cfg)
    w("  .config guardado SIEMPRE (H-2c): v4-config-%s.txt | %d B"
      % (brazo, len(cfg)))
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
    # Los 16 que systemd exige, ya verificados en el .config del v3 (ADR-008 S4).
    # Se re-miden aca porque el inventario se re-mide, no se recuerda.
    SYSTEMD16 = ("BLK_DEV_INITRD RD_GZIP TMPFS DEVTMPFS DEVTMPFS_MOUNT CGROUPS "
                 "UNIX INOTIFY_USER SIGNALFD TIMERFD EPOLL FHANDLE AUTOFS_FS "
                 "POSIX_MQUEUE PID_NS IPC_NS").split()
    en_y = [s_ for s_ in SYSTEMD16
            if re.search(r"^CONFIG_%s=y$" % s_, cfg, re.M)]
    w("  precondicion de F-001-S2: %d/16 simbolos de systemd en =y" % len(en_y))
    if len(en_y) < len(SYSTEMD16):
        w("  FALTAN: %s" % " ".join(s_ for s_ in SYSTEMD16 if s_ not in en_y))

    if brazo == "ocho" and estado.get("CONFIG_IPC_NS") != "y":
        w("  ABORTO POR GUARD: IPC_NS quedo en %r, no en 'y'."
          % estado.get("CONFIG_IPC_NS"))
        cerrar(brazo, {"veredicto": "ABORTADO POR GUARD IPC_NS", "simbolos": estado})
        return 3

    w("  === archscripts en SERIE, con la firma de host DEFINITIVA ===")
    logs = os.path.join(OUT, "v4-%s-archscripts.txt" % brazo)
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

    logb = os.path.join(OUT, "v4-%s-build.txt" % brazo)
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

    w("  === guard duro de los TRES artefactos (el v3 solo miraba dos) ===")
    vm = obj + "/vmlinux"
    sym = obj + "/Module.symvers"
    img = os.path.join(obj, IMAGE_REL)
    hay_vm, hay_sym, hay_img = (os.path.isfile(vm), os.path.isfile(sym),
                                os.path.isfile(img))
    w("  vmlinux presente        : %s%s"
      % (hay_vm, " (%d B)" % os.path.getsize(vm) if hay_vm else ""))
    w("  Module.symvers presente : %s" % hay_sym)
    w("  %s presente : %s%s"
      % (IMAGE_REL, hay_img,
         " (%d B)" % os.path.getsize(img) if hay_img else "  <-- ESTE es el H-2"))
    res = {"falsador": "F-004d@6.1 v4.1", "rama": RAMA, "brazo": brazo,
           "rc_archscripts": rc_as, "segundos_archscripts": round(dt_as, 2),
           "archscripts_hizo_trabajo": hizo_trabajo,
           "error_126_serial": e126, "error_126_paralelo": e126b,
           "rc_build": rc, "debug_info_btf": btf, "pahole": ph,
           "parche_al_ack": False, "simbolos": estado,
           "systemd16_en_y": len(en_y),
           "vmlinux": hay_vm, "module_symvers": hay_sym, "image": hay_img,
           "cap_head_400": "eliminado en v4",
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if hay_sym:
        raw = open(sym).read()
        res["n_lineas_symvers"] = raw.count("\n")
        res["sha256_symvers"] = hashlib.sha256(raw.encode()).hexdigest()
        w("  Module.symvers: %d lineas | sha256 %s"
          % (res["n_lineas_symvers"], res["sha256_symvers"][:24]))
        open(os.path.join(OUT, "v4-symvers-%s.txt" % brazo), "w").write(raw)
    if not hay_vm:
        w("  ABORTO POR GUARD: no hay vmlinux, no se empaqueta nada.")
        res["veredicto"] = "NO MEDIDO: sin vmlinux"
        cerrar(brazo, res)
        return 3
    if not hay_img:
        w("  ABORTO POR GUARD: no hay %s. El v3 llegaba hasta aca sin notarlo."
          % IMAGE_REL)
        res["veredicto"] = "NO MEDIDO: sin Image"
        cerrar(brazo, res)
        return 3
    res["bytes_vmlinux"] = os.path.getsize(vm)
    res["bytes_image"] = os.path.getsize(img)
    res["sha256_vmlinux"] = sha256_de(vm)
    res["sha256_image_del_build"] = sha256_de(img)
    w("  sha256 vmlinux (64 hex): %s" % res["sha256_vmlinux"])
    w("  sha256 Image   (64 hex): %s" % res["sha256_image_del_build"])

    w("  === KAT de FABLE: Image == objcopy(vmlinux), flags de la FUENTE ===")
    res["kat_objcopy"] = kat_objcopy(src, obj, WORK + "/Image-desde-vmlinux-" + brazo)

    lst = WORK + "/miembros-%s.txt" % brazo
    kos = lista_de_miembros(obj, lst)
    res["n_modulos"] = len(kos)
    tarball = os.path.abspath(os.path.join(OUT, "elf-%s-android14-6.1.tar.zst" % brazo))
    rc_t, _, _, _ = sh("cd %s && tar -c --zstd -f %s -T %s" % (obj, tarball, lst), 3600)
    if rc_t != 0 or not os.path.isfile(tarball):
        w("  ABORTO: el tar fallo con rc=%d" % rc_t)
        res["veredicto"] = "NO MEDIDO: el tar fallo"
        cerrar(brazo, res)
        return 3
    # H-2d: UNA sola fuente de verdad. Se lista el tarball a archivo y se lee en
    # Python; los tres 'grep -c' del v4 eran una segunda lectura del mismo dato.
    listado = tarball + ".lista"
    rc_v, _, _, _ = sh("tar -t --zstd -f %s > %s" % (tarball, listado), 900)
    lista = open(listado, errors="replace").read() if os.path.isfile(listado) else ""
    tiene_vm = en_el_listado(lista, "vmlinux")
    tiene_img = en_el_listado(lista, IMAGE_REL)
    ko_dentro = len(re.findall(r"\.ko$", lista, re.M))
    w("  listado del tarball: %d entradas | rc del tar -t = %d"
      % (len(lista.splitlines()), rc_v))
    w("  contiene vmlinux: %s | contiene %s: %s | .ko: %d de %d | tarball %d B"
      % (tiene_vm, IMAGE_REL, tiene_img, ko_dentro, len(kos),
         os.path.getsize(tarball)))
    res.update({"tarball_tiene_vmlinux": tiene_vm, "tarball_tiene_image": tiene_img,
                "ko_dentro_del_tarball": ko_dentro,
                "entradas_del_tarball": len(lista.splitlines()),
                "bytes_tarball": os.path.getsize(tarball)})
    if not tiene_vm:
        w("  ABORTO POR GUARD: el tarball existe pero no tiene vmlinux adentro.")
        res["veredicto"] = "NO MEDIDO: tarball sin vmlinux"
        cerrar(brazo, res)
        return 3
    if not tiene_img:
        w("  ABORTO POR GUARD: el tarball no tiene %s adentro. Es el H-2 otra vez."
          % IMAGE_REL)
        res["veredicto"] = "NO MEDIDO: tarball sin Image"
        cerrar(brazo, res)
        return 3
    if ko_dentro != len(kos):
        w("  ABORTO POR GUARD: la lista tenia %d .ko y el tarball tiene %d."
          % (len(kos), ko_dentro))
        w("  Un tope silencioso es exactamente lo que el v4 vino a eliminar.")
        res["veredicto"] = "NO MEDIDO: la cuenta de modulos no cierra"
        cerrar(brazo, res)
        return 3
    kat = res["kat_objcopy"].get("kat")
    if kat == "DISTINTO":
        w("  VEREDICTO ROJO: el KAT dice que vmlinux y Image no son del mismo link.")
        res["veredicto"] = "ROJO: KAT objcopy DISTINTO"
        cerrar(brazo, res)
        return 3
    res["veredicto"] = ("brazo OK: vmlinux, Image y symvers producidos y "
                        "verificados | KAT objcopy: %s" % kat)
    cerrar(brazo, res)
    return 0


def cerrar(brazo, res):
    json.dump(res, open(os.path.join(OUT, "v4-%s.json" % brazo), "w"),
              indent=2, ensure_ascii=False)
    open(os.path.join(OUT, "v4-%s-bitacora.txt" % brazo), "w").write("\n".join(log) + "\n")
    w("  cerrado: v4-%s.json y v4-%s-bitacora.txt" % (brazo, brazo))


if __name__ == "__main__":
    sys.exit(main())
