#!/usr/bin/env python3
"""
F-004 v3 - El fragmento de SIAO rompe el KMI?

QUE CAMBIA RESPECTO DE v2, y cada cambio es una regla nacida de un defecto medido:

  R-08 (mio, medido dos veces): el log se guarda ENTERO con escritura directa a
       archivo, el resumen se produce DESPUES leyendo ese archivo, y el rc se
       captura del COMANDO y nunca de un filtro. En v2 el build corria con
       '2>&1 | tail -40', asi que rc era el de tail (el archivo decia rc=0 sobre
       un build que fallo) y las 2.501 lineas previas al error se tiraban.

  R-09 (mio, medido): antes de correr un brazo se BORRAN sus archivos anteriores.
       En v2 el brazo 'siao' quedo con el log del intento viejo al lado de un
       script nuevo, o sea un rojo falso esperando ser leido.

  R-10: 'CERRADO' solo con todos los criterios verdes.

EL FIX DEL ARNES, medido en el fuente de Google y NO adivinado:
  certs/extract-cert.c de android15-6.6 (3.976 B) tiene guardas ASIMETRICAS:
     linea  81: static const char *key_pass;   bajo #ifdef USE_PKCS11_ENGINE
     linea 115: key_pass = getenv("KBUILD_SIGN_PIN");  bajo la MISMA guarda
     linea 152: if (key_pass)                  bajo el #else de OPENSSL_IS_BORINGSSL
  Con OpenSSL normal y sin USE_PKCS11_ENGINE, el USO se compila y la DECLARACION
  no. De ahi el 'use of undeclared identifier key_pass'.
  Por eso el fix es HOSTCFLAGS=-DUSE_PKCS11_ENGINE y NO -DOPENSSL_NO_ENGINE:
  ese otro define no toca esta guarda y ademas esconde la API ENGINE_*, o sea
  que sumaria errores. Prediccion declarada ANTES de correr: con USE_PKCS11_ENGINE
  compila.

LO QUE ESTE INSTRUMENTO NO HACE, Y ES DELIBERADO:
  no toca NINGUN CONFIG_* del baseline. Nada de MODULE_SIG=n: en ACK
  'bool sig_ok' esta compilado incondicionalmente a proposito (comentario de
  Google en include/linux/module.h:451), pero apagar MODULE_SIG convierte
  is_module_sig_enforced() y module_sig_ok() en static inline, o sea que
  DESAPARECEN de Module.symvers. Un baseline modificado no es baseline.

MODO DE USO:
  f004_kmi_v3.py build baseline|siao
  f004_kmi_v3.py comparar
"""
import base64, glob, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

RAMA = os.environ.get("F004_RAMA", "android15-6.6")
GS = "https://android.googlesource.com/kernel/common"
OUT = os.environ.get("F004_OUT", "mediciones/f-004-v3")
WORK = os.environ.get("F004_WORK", "/tmp/f004v3")

# El fragmento del ADR-003. A = host (systemd), B = contenedor de apps.
# C (USER_NS, APPARMOR) es Fase 3 y D (virtio) es solo del arnes QEMU: no entran,
# porque no deben tocar el KMI del dispositivo.
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

log = []


def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line)
    print(line, flush=True)


def sh(cmd, t=21000, guardar=None, env=None):
    """R-08: stdout+stderr van ENTEROS a archivo; rc es del comando, no de un filtro."""
    say("$", cmd[:300])
    t0 = time.time()
    e = dict(os.environ)
    if env:
        e.update(env)
    rc, o, err = -1, "", ""
    try:
        r = subprocess.run(["bash", "-c", "set -o pipefail; " + cmd],
                           capture_output=True, text=True, timeout=t, env=e)
        rc, o, err = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        rc, err = -9, "TIMEOUT tras %ss" % t
    except Exception as ex:
        rc, err = -1, repr(ex)[:300]
    say("  rc=%d en %.1f s | stdout %d B | stderr %d B" % (rc, time.time() - t0, len(o), len(err)))
    if guardar:
        os.makedirs(os.path.dirname(guardar), exist_ok=True)
        with open(guardar, "w") as f:
            f.write("### comando\n%s\n\n### rc DEL COMANDO (no de un filtro)\n%d\n\n"
                    "### stdout ENTERO\n%s\n\n### stderr ENTERO\n%s\n" % (cmd, rc, o, err))
        say("  guardado entero en", guardar.replace(OUT, "<out>"))
    return rc, o, err


def primer_error(path, n=40):
    """El resumen se produce leyendo el ARCHIVO, nunca un pipe (R-08)."""
    if not os.path.isfile(path):
        say("  no hay archivo para resumir:", path)
        return
    pat = re.compile(r"error:|error!|fatal|No such file|Killed|No space left|"
                     r"undefined reference|Error [0-9]+")
    hits = []
    with open(path, errors="replace") as f:
        for i, line in enumerate(f, 1):
            if pat.search(line):
                hits.append((i, line.rstrip()))
    say("  lineas con pinta de error: %d" % len(hits))
    for i, line in hits[:n]:
        say("   E%-6d| %s" % (i, line[:200]))


def limpiar_brazo(cual):
    """R-09: el log viejo de un brazo cuyo codigo cambio es un veredicto falso."""
    borrados = []
    for p in sorted(glob.glob(os.path.join(OUT, "*%s*" % cual))):
        os.remove(p)
        borrados.append(os.path.basename(p))
    say("  R-09 | archivos previos de '%s' borrados: %s" % (cual, borrados or "ninguno"))


def traer_arbol():
    src = WORK + "/ack"
    if os.path.isfile(src + "/Makefile"):
        say("  el arbol ya esta en", src)
        return src
    os.makedirs(src, exist_ok=True)
    u = "%s/+archive/refs/heads/%s.tar.gz" % (GS, RAMA)
    say("  bajando", u)
    t0 = time.time()
    tgz = WORK + "/ack.tar.gz"
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004/3"})
    h = hashlib.sha256()
    n = 0
    with urllib.request.urlopen(req, timeout=1800) as r, open(tgz, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            h.update(b)
            n += len(b)
    say("  bajado: %d B (%.1f MiB) en %.1f s" % (n, n / 1048576, time.time() - t0))
    say("  sha256 del tar.gz:", h.hexdigest())
    rc, _, e = sh("tar -xzf %s -C %s" % (tgz, src), 1800)
    if rc != 0:
        say("  no se pudo desempaquetar:", e[:300])
        return None
    os.remove(tgz)
    rc, o, _ = sh("head -5 %s/Makefile" % src)
    for l in o.splitlines():
        say("   |", l[:100])
    return src


def estado_fragmento(cfg_path):
    cfg = open(cfg_path).read()
    estado = {}
    for s in [l.split("=")[0] for l in FRAGMENTO.splitlines() if l.startswith("CONFIG_")]:
        m = re.search(r"^%s=(.*)$" % re.escape(s), cfg, re.M)
        estado[s] = m.group(1) if m else (
            "APAGADO" if re.search(r"^# %s is not set$" % re.escape(s), cfg, re.M) else "AUSENTE")
    say("  estado de los 10 simbolos del fragmento en este brazo:")
    for s, v in estado.items():
        say("      %-26s %s" % (s, v))
    return estado, cfg


def build(cual):
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    say("== F-004 v3 build: %s | rama %s ==" % (cual, RAMA))
    limpiar_brazo(cual)
    rc, o, _ = sh("nproc; free -m | head -2; df -h / | tail -1; clang --version | head -1; "
                  "ld.lld --version 2>&1 | head -1; openssl version")
    for l in o.splitlines():
        say("   |", l[:140])
    src = traer_arbol()
    if not src:
        return 3

    # El fix del arnes, verbatim y con su razon, para que se pueda refutar.
    hostcflags = "-DUSE_PKCS11_ENGINE"
    say("  FIX DEL ARNES: HOSTCFLAGS=%s" % hostcflags)
    say("  razon medida: key_pass se DECLARA en extract-cert.c:81 bajo")
    say("                #ifdef USE_PKCS11_ENGINE y se USA en :152 bajo otra guarda")
    say("  se aplica IGUAL a los dos brazos, y NO toca ningun CONFIG_*")
    rc, o, _ = sh("grep -n 'key_pass\\|USE_PKCS11_ENGINE' %s/certs/extract-cert.c" % src)
    for l in o.splitlines():
        say("   src|", l[:160])

    obj = WORK + "/out-" + cual
    if os.path.isdir(obj):
        shutil.rmtree(obj)
    os.makedirs(obj, exist_ok=True)
    mk = "make -C %s O=%s LLVM=1 ARCH=arm64" % (src, obj)

    rc, _, _ = sh("%s gki_defconfig" % mk, 3600,
                  guardar=os.path.join(OUT, "f004v3-%s-defconfig.txt" % cual))
    if rc != 0:
        say("  gki_defconfig fallo")
        return 3

    if cual == "siao":
        frag = WORK + "/siao.fragment"
        open(frag, "w").write(FRAGMENTO)
        say("  fragmento SIAO, verbatim:")
        for l in FRAGMENTO.strip().splitlines():
            say("   |", l)
        rc, _, _ = sh("%s/scripts/kconfig/merge_config.sh -m -O %s %s/.config %s"
                      % (src, obj, obj, frag), 600,
                      guardar=os.path.join(OUT, "f004v3-siao-merge.txt"))
        say("  merge_config rc=%d" % rc)
        rc, _, _ = sh("%s olddefconfig" % mk, 900)

    estado, cfg = estado_fragmento(obj + "/.config")
    # Control de que el baseline NO fue tocado por el fix del arnes.
    sig = {k: (re.search(r"^%s=(.*)$" % k, cfg, re.M).group(1)
               if re.search(r"^%s=" % k, cfg, re.M) else "no=y")
           for k in ["CONFIG_MODULE_SIG", "CONFIG_MODULE_SIG_PROTECT", "CONFIG_MODVERSIONS"]}
    say("  CONTROL de que el arnes no contamino el KMI:", json.dumps(sig))

    logf = os.path.join(OUT, "f004v3-%s-build.txt" % cual)
    rc, _, _ = sh("%s HOSTCFLAGS='%s' -j$(nproc) Image modules" % (mk, hostcflags), 20000,
                  guardar=logf)
    say("  --- resumen leido DEL ARCHIVO, no de un pipe ---")
    primer_error(logf)

    sym = obj + "/Module.symvers"
    ok = os.path.isfile(sym)
    say("  Module.symvers presente:", ok)
    res = {"brazo": cual, "rama": RAMA, "rc_build": rc, "hostcflags": hostcflags,
           "simbolos_del_fragmento": estado, "control_sig_y_modversions": sig,
           "module_symvers": ok,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if ok:
        raw = open(sym).read()
        res["n_lineas_symvers"] = raw.count("\n")
        res["sha256_symvers"] = hashlib.sha256(raw.encode()).hexdigest()
        say("  Module.symvers: %d lineas | sha256 %s"
            % (res["n_lineas_symvers"], res["sha256_symvers"][:20]))
        open(os.path.join(OUT, "symvers-%s.txt" % cual), "w").write(raw)
        open(os.path.join(OUT, "config-%s.txt" % cual), "w").write(cfg)
        # Para el stgdiff en x86: vmlinux + los .ko, comprimidos.
        rc2, o2, _ = sh("cd %s && ls -la vmlinux 2>/dev/null; find . -name '*.ko' | wc -l" % obj)
        for l in o2.splitlines():
            say("   |", l[:140])
        sh("cd %s && tar -c --zstd -f %s vmlinux $(find . -name '*.ko' | head -400)"
           % (obj, os.path.abspath(os.path.join(OUT, "elf-%s.tar.zst" % cual))), 3600)
        p = os.path.join(OUT, "elf-%s.tar.zst" % cual)
        if os.path.isfile(p):
            say("  ELF empaquetado para el stgdiff x86: %d B" % os.path.getsize(p))
    with open(os.path.join(OUT, "f004v3-%s.json" % cual), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "f004v3-%s-bitacora.txt" % cual), "w") as f:
        f.write("\n".join(log) + "\n")
    return 0 if ok else 3


def leer_symvers(p):
    d = {}
    for line in open(p):
        c = line.split()
        if len(c) >= 4:
            d[c[1]] = (c[0], c[3])
    return d


def comparar():
    os.makedirs(OUT, exist_ok=True)
    say("== F-004 v3 comparar (CRIBA, no veredicto: R-06 del auditor) ==")
    a = os.path.join(OUT, "symvers-baseline.txt")
    b = os.path.join(OUT, "symvers-siao.txt")
    res = {"falsador": "F-004-lite v3", "rama": RAMA,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "que_mide": ("CRIBA por CRC de Module.symvers. NO ve cambios de layout de "
                        "structs que un DLKM use sin exportar: eso lo dice stgdiff. "
                        "Por eso es F-004-lite y no F-004."),
           "caveat": ("los dos brazos usan el MISMO clang del runner y el MISMO "
                      "HOSTCFLAGS. Comparar baseline vs fragmento es valido porque el "
                      "compilador es constante; comparar contra el .stg de Google NO."),
           "no_medido": []}
    if not (os.path.isfile(a) and os.path.isfile(b)):
        say("  falta un brazo: baseline=%s siao=%s" % (os.path.isfile(a), os.path.isfile(b)))
        res["veredicto"] = "NO MEDIDO"
        res["no_medido"].append("falta al menos un Module.symvers")
        escribir(res)
        return 3
    A, B = leer_symvers(a), leer_symvers(b)
    say("  baseline: %d simbolos exportados" % len(A))
    say("  siao    : %d simbolos exportados" % len(B))
    desap = sorted(set(A) - set(B))
    agreg = sorted(set(B) - set(A))
    crc = sorted(s for s in (set(A) & set(B)) if A[s][0] != B[s][0])
    exp = sorted(s for s in (set(A) & set(B)) if A[s][1] != B[s][1])
    say("  DESAPARECIDOS (rompen cualquier DLKM que los use): %d" % len(desap))
    for s in desap[:40]:
        say("      -", s)
    say("  CRC CAMBIADO (el DLKM no carga): %d" % len(crc))
    for s in crc[:40]:
        say("      ~ %-44s %s -> %s" % (s, A[s][0], B[s][0]))
    say("  TIPO DE EXPORT CAMBIADO: %d" % len(exp))
    for s in exp[:20]:
        say("      ! %-44s %s -> %s" % (s, A[s][1], B[s][1]))
    say("  AGREGADOS (aditivo, no rompe): %d" % len(agreg))
    for s in agreg[:40]:
        say("      +", s)
    res.update({"n_baseline": len(A), "n_siao": len(B),
                "desaparecidos": desap, "n_desaparecidos": len(desap),
                "crc_cambiado": [[s, A[s][0], B[s][0]] for s in crc], "n_crc_cambiado": len(crc),
                "export_cambiado": [[s, A[s][1], B[s][1]] for s in exp],
                "agregados": agreg, "n_agregados": len(agreg)})
    rompe = desap or crc or exp
    res["veredicto"] = ("ROJO en la criba: el fragmento toca simbolos exportados" if rompe
                        else "VERDE en la criba: el fragmento es ADITIVO en Module.symvers")
    say("")
    say("VEREDICTO F-004-lite:", res["veredicto"])
    try:
        u = "%s/+/refs/heads/%s/android/abi_gki_aarch64?format=TEXT" % (GS, RAMA)
        d = urllib.request.urlopen(urllib.request.Request(
            u, headers={"User-Agent": "siao-f004/3"}), timeout=300).read()
        lista = base64.b64decode(d).decode("utf-8", "replace")
        prot = set(x.strip() for x in lista.splitlines()
                   if x.strip() and not x.strip().startswith(("#", "[")))
        tocados = sorted((set(desap) | set(crc)) & prot)
        say("  lista de simbolos protegidos de Google: %d" % len(prot))
        say("  de los tocados, cuantos estan protegidos: %d" % len(tocados))
        for s in tocados[:30]:
            say("      !!", s)
        res["n_protegidos"] = len(prot)
        res["protegidos_tocados"] = tocados
    except Exception as ex:
        res["no_medido"].append("no pude bajar la lista protegida: %s" % repr(ex)[:120])
        say("  no pude bajar la lista protegida:", repr(ex)[:150])
    res["no_medido"].append("stgdiff: es el veredicto real y corre en el job x86")
    escribir(res)
    return 0 if not rompe else 3


def escribir(res):
    with open(os.path.join(OUT, "F-004-v3.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-004-v3-bitacora.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    md = ["# F-004-lite v3 - criba por Module.symvers", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Rama ACK:** `%s`" % res["rama"], "",
          "**Veredicto de la CRIBA:** **%s**" % res.get("veredicto", "NO MEDIDO"), "",
          "| Metrica | Valor |", "|---|---|",
          "| exportados, baseline | %s |" % res.get("n_baseline", "?"),
          "| exportados, con fragmento | %s |" % res.get("n_siao", "?"),
          "| **desaparecidos** | **%s** |" % res.get("n_desaparecidos", "?"),
          "| **CRC cambiado** | **%s** |" % res.get("n_crc_cambiado", "?"),
          "| agregados | %s |" % res.get("n_agregados", "?"),
          "| protegidos por Google | %s |" % res.get("n_protegidos", "?"),
          "| de los tocados, protegidos | %s |" % len(res.get("protegidos_tocados", [])), "",
          "## Que mide y que NO", "", res["que_mide"], "",
          "## Caveat", "", res["caveat"], "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Bitacora", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-004-v3.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "comparar"
    sys.exit(build(sys.argv[2]) if modo == "build" else comparar())
