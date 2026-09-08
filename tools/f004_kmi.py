#!/usr/bin/env python3
"""
F-004 - El fragmento de SIAO rompe el KMI?

POR QUE NO ES stgdiff, y esto se midio en el pre-vuelo (R-05):
  abi_gki_aarch64.stg de android15-6.6  -> EXISTE, 8.014.732 B (7,6 MiB) decodificado
  api.github.com/repos/google/stg       -> 404
  .../stg/tags                          -> 404
  prebuilts/kernel-build-tools          -> 404 en las dos rutas probadas
  paquete 'stg' en ubuntu-ports arm64   -> NO ESTA
  paquete 'abigail-tools'               -> PRESENTE
La REFERENCIA esta; la HERRAMIENTA no la consegui por ninguna de las cinco vias que
medi. F-004 con stgdiff queda NO MEDIDO por falta de instrumento, declarado.

LA VIA QUE MIDE LA MISMA PREGUNTA:
el enforcer real del KMI no es stgdiff, es CONFIG_MODVERSIONS=y, que ya medi en el
.config del GKI. Con MODVERSIONS, un cambio de layout no produce un diff: produce un
modulo que NO CARGA, porque el CRC del simbolo no coincide. Esos CRC viven en
Module.symvers, uno por linea: <CRC> <simbolo> <modulo> <export>.

Asi que: dos builds del MISMO arbol con el MISMO compilador, uno con gki_defconfig
puro y otro con gki_defconfig + fragmento, y se comparan los Module.symvers.
  - simbolo que DESAPARECE  -> rompe cualquier DLKM que lo use. ROJO.
  - CRC que CAMBIA          -> el DLKM no carga. ROJO.
  - simbolo que se AGREGA   -> aditivo. No rompe nada.

CAVEAT QUE HACE VALIDA LA COMPARACION, declarado antes de correr: los dos builds usan
el MISMO compilador (el clang del runner, no el de Google). Comparar mi baseline contra
mi fragmento es valido porque el compilador es constante. Comparar mi build contra el
.stg de Google NO lo seria, y por eso no lo hago.

MODO DE USO (dos fases, porque cada build tarda y van en jobs distintos):
  f004_kmi.py build baseline|siao   -> compila y deja Module.symvers + .config
  f004_kmi.py comparar              -> lee los dos y emite el veredicto
"""
import base64, hashlib, json, os, re, subprocess, sys, time, urllib.request

RAMA = os.environ.get("F004_RAMA", "android15-6.6")
GS = "https://android.googlesource.com/kernel/common"
OUT = os.environ.get("F004_OUT", "mediciones/f-004")
WORK = os.environ.get("F004_WORK", "/tmp/f004")

# El fragmento del ADR-003, con lo medido en el .config real del GKI.
# A = host (systemd), B = contenedor de apps. C y D no entran: C es Fase 3 y D es
# solo del arnes QEMU, asi que no deben tocar el KMI del dispositivo.
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
    log.append(line); print(line, flush=True)

def sh(c, t=21000, guardar=None, cwd=None):
    say("$", (c if isinstance(c, str) else " ".join(c))[:300])
    t0 = time.time()
    try:
        r = subprocess.run(c, shell=isinstance(c, str), capture_output=True,
                           text=True, timeout=t, cwd=cwd)
        rc, o, e = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        rc, o, e = -9, "", "TIMEOUT tras %ss" % t
    except Exception as ex:
        rc, o, e = -1, "", repr(ex)[:300]
    say("  rc=%d en %.1f s" % (rc, time.time() - t0))
    if guardar:
        os.makedirs(os.path.dirname(guardar), exist_ok=True)
        with open(guardar, "w") as f:
            f.write("### comando\n%s\n\n### rc=%d\n\n### stdout (ultimos 200k)\n%s\n\n"
                    "### stderr (ultimos 200k)\n%s\n"
                    % ((c if isinstance(c, str) else " ".join(c)), rc, o[-200000:], e[-200000:]))
        say("  salida guardada en", guardar.replace(OUT, "<out>"),
            "(%d B out, %d B err)" % (len(o), len(e)))
    return rc, o, e


def traer_arbol():
    """El archive tar.gz de googlesource: un solo GET, sin git ni repo."""
    src = WORK + "/ack"
    if os.path.isfile(src + "/Makefile"):
        say("  el arbol ya esta en", src)
        return src
    os.makedirs(src, exist_ok=True)
    u = "%s/+archive/refs/heads/%s.tar.gz" % (GS, RAMA)
    say("  bajando", u)
    t0 = time.time()
    tgz = WORK + "/ack.tar.gz"
    req = urllib.request.Request(u, headers={"User-Agent": "siao-f004/1"})
    with urllib.request.urlopen(req, timeout=1800) as r, open(tgz, "wb") as f:
        n = 0
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b); n += len(b)
    say("  bajado: %d B (%.1f MiB) en %.1f s" % (n, n / 1048576, time.time() - t0))
    say("  sha256 del tar.gz:", hashlib.sha256(open(tgz, "rb").read()).hexdigest())
    rc, o, e = sh(["bash", "-c", "tar -xzf %s -C %s" % (tgz, src)], 1800)
    if rc != 0:
        say("  no se pudo desempaquetar:", e[:300]); return None
    rc, o, _ = sh(["bash", "-c", "head -5 %s/Makefile" % src])
    say("  Makefile del arbol:")
    for l in o.splitlines():
        say("   |", l[:100])
    return src


def build(cual):
    """cual = baseline | siao"""
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    say("== F-004 build: %s | rama %s ==" % (cual, RAMA))
    rc, o, _ = sh(["bash", "-c", "nproc; free -m | head -2; df -h / | tail -1; "
                                 "clang --version | head -1; ld.lld --version 2>&1 | head -1"])
    for l in o.splitlines():
        say("   |", l[:120])
    src = traer_arbol()
    if not src:
        return 3
    obj = WORK + "/out-" + cual
    os.makedirs(obj, exist_ok=True)
    base = ("make -C %s O=%s LLVM=1 ARCH=arm64 gki_defconfig" % (src, obj))
    rc, o, e = sh(["bash", "-c", base], 3600,
                  guardar=os.path.join(OUT, "f004-%s-defconfig.txt" % cual))
    if rc != 0:
        say("  gki_defconfig fallo"); return 3
    if cual == "siao":
        frag = WORK + "/siao.fragment"
        open(frag, "w").write(FRAGMENTO)
        say("  fragmento SIAO, verbatim:")
        for l in FRAGMENTO.strip().splitlines():
            say("   |", l)
        rc, o, e = sh(["bash", "-c",
                       "%s/scripts/kconfig/merge_config.sh -m -O %s %s/.config %s"
                       % (src, obj, obj, frag)], 600,
                      guardar=os.path.join(OUT, "f004-siao-merge.txt"))
        say("  merge_config rc=%d" % rc)
        rc, o, e = sh(["bash", "-c", "make -C %s O=%s LLVM=1 ARCH=arm64 olddefconfig"
                       % (src, obj)], 900)
    pedidos = [l.split("=")[0] for l in FRAGMENTO.splitlines()
               if l.startswith("CONFIG_")]
    cfg = open(obj + "/.config").read()
    estado = {}
    for s in pedidos:
        m = re.search(r"^%s=(.*)$" % re.escape(s), cfg, re.M)
        estado[s] = m.group(1) if m else ("APAGADO" if re.search(
            r"^# %s is not set$" % re.escape(s), cfg, re.M) else "AUSENTE")
    say("  estado de los simbolos del fragmento en el .config de este brazo:")
    for s, v in estado.items():
        say("      %-26s %s" % (s, v))
    rc, o, e = sh(["bash", "-c",
                   "make -C %s O=%s LLVM=1 ARCH=arm64 -j$(nproc) Image modules 2>&1 | tail -40"
                   % (src, obj)], 20000,
                  guardar=os.path.join(OUT, "f004-%s-build.txt" % cual))
    say("  ultimas lineas del build:")
    for l in (o + e).splitlines()[-25:]:
        say("   |", l[:180])
    sym = obj + "/Module.symvers"
    ok = os.path.isfile(sym)
    say("  Module.symvers presente:", ok)
    res = {"brazo": cual, "rama": RAMA, "rc_build": rc,
           "simbolos_del_fragmento": estado,
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
    with open(os.path.join(OUT, "f004-%s.json" % cual), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "f004-%s-bitacora.txt" % cual), "w") as f:
        f.write("\n".join(log) + "\n")
    return 0 if ok else 3


def leer_symvers(p):
    """Module.symvers: <CRC> <simbolo> <modulo> <export> [ns]"""
    d = {}
    for line in open(p):
        c = line.split()
        if len(c) >= 4:
            d[c[1]] = (c[0], c[3])
    return d


def comparar():
    os.makedirs(OUT, exist_ok=True)
    say("== F-004 comparar ==")
    a = os.path.join(OUT, "symvers-baseline.txt")
    b = os.path.join(OUT, "symvers-siao.txt")
    res = {"falsador": "F-004", "rama": RAMA,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "por_que_no_stgdiff": (
               "medido en el pre-vuelo: el .stg de referencia existe (8.014.732 B) pero "
               "stgdiff no lo consegui por ninguna de las 5 vias probadas (google/stg 404, "
               "/tags 404, prebuilts 404 x2, paquete stg ausente en ubuntu-ports arm64). "
               "stgdiff queda NO MEDIDO por falta de instrumento."),
           "por_que_module_symvers": (
               "CONFIG_MODVERSIONS=y esta medido en el .config del GKI: con eso, un cambio "
               "de layout no da un diff, da un modulo que no carga porque el CRC no "
               "coincide. Los CRC viven en Module.symvers, y esa es la misma pregunta."),
           "caveat": ("los dos brazos usan el MISMO compilador del runner, no el de Google. "
                      "Comparar baseline vs fragmento es valido porque el compilador es "
                      "constante; comparar contra el .stg de Google NO lo seria."),
           "no_medido": []}
    if not (os.path.isfile(a) and os.path.isfile(b)):
        say("  falta un brazo: baseline=%s siao=%s" % (os.path.isfile(a), os.path.isfile(b)))
        res["veredicto"] = "NO MEDIDO"
        res["no_medido"].append("falta al menos un Module.symvers")
        write_cmp(res); return 3
    A, B = leer_symvers(a), leer_symvers(b)
    say("  baseline: %d simbolos exportados" % len(A))
    say("  siao    : %d simbolos exportados" % len(B))
    desaparecidos = sorted(set(A) - set(B))
    agregados = sorted(set(B) - set(A))
    crc_cambiado = sorted(s for s in (set(A) & set(B)) if A[s][0] != B[s][0])
    export_cambiado = sorted(s for s in (set(A) & set(B)) if A[s][1] != B[s][1])
    say("")
    say("  DESAPARECIDOS (rompen cualquier DLKM que los use): %d" % len(desaparecidos))
    for s in desaparecidos[:40]:
        say("      -", s)
    say("  CRC CAMBIADO (el DLKM no carga): %d" % len(crc_cambiado))
    for s in crc_cambiado[:40]:
        say("      ~ %-44s %s -> %s" % (s, A[s][0], B[s][0]))
    say("  TIPO DE EXPORT CAMBIADO: %d" % len(export_cambiado))
    for s in export_cambiado[:20]:
        say("      ! %-44s %s -> %s" % (s, A[s][1], B[s][1]))
    say("  AGREGADOS (aditivo, no rompe): %d" % len(agregados))
    for s in agregados[:40]:
        say("      +", s)
    res.update({"n_baseline": len(A), "n_siao": len(B),
                "desaparecidos": desaparecidos, "n_desaparecidos": len(desaparecidos),
                "crc_cambiado": [[s, A[s][0], B[s][0]] for s in crc_cambiado],
                "n_crc_cambiado": len(crc_cambiado),
                "export_cambiado": [[s, A[s][1], B[s][1]] for s in export_cambiado],
                "agregados": agregados, "n_agregados": len(agregados)})
    rompe = desaparecidos or crc_cambiado or export_cambiado
    res["veredicto"] = "ROJO: el fragmento toca el KMI" if rompe else \
                       "VERDE: el fragmento es ADITIVO, no rompe el KMI"
    say(""); say("VEREDICTO F-004:", res["veredicto"])
    try:
        u = "%s/+/refs/heads/%s/android/abi_gki_aarch64?format=TEXT" % (GS, RAMA)
        d = urllib.request.urlopen(urllib.request.Request(
            u, headers={"User-Agent": "siao-f004/1"}), timeout=300).read()
        lista = base64.b64decode(d).decode("utf-8", "replace")
        prot = set(x.strip() for x in lista.splitlines()
                   if x.strip() and not x.strip().startswith(("#", "[")))
        say("  lista de simbolos protegidos de Google: %d" % len(prot))
        tocados = sorted((set(desaparecidos) | set(crc_cambiado)) & prot)
        say("  de los tocados, cuantos estan en la lista protegida: %d" % len(tocados))
        for s in tocados[:30]:
            say("      !!", s)
        res["n_protegidos"] = len(prot)
        res["protegidos_tocados"] = tocados
    except Exception as ex:
        res["no_medido"].append("no pude bajar la lista protegida: %s" % repr(ex)[:120])
        say("  no pude bajar la lista protegida:", repr(ex)[:150])
    write_cmp(res)
    return 0 if not rompe else 3


def write_cmp(res):
    with open(os.path.join(OUT, "F-004.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-004-bitacora.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    md = ["# F-004 - el fragmento de SIAO rompe el KMI?", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Rama ACK:** `%s`" % res["rama"], "",
          "**Veredicto:** **%s**" % res.get("veredicto", "NO MEDIDO"), "",
          "| Metrica | Valor |", "|---|---|",
          "| simbolos exportados, baseline | %s |" % res.get("n_baseline", "?"),
          "| simbolos exportados, con fragmento | %s |" % res.get("n_siao", "?"),
          "| **desaparecidos** | **%s** |" % res.get("n_desaparecidos", "?"),
          "| **CRC cambiado** | **%s** |" % res.get("n_crc_cambiado", "?"),
          "| agregados | %s |" % res.get("n_agregados", "?"),
          "| en la lista protegida de Google | %s |" % res.get("n_protegidos", "?"),
          "| de los tocados, protegidos | %s |" % len(res.get("protegidos_tocados", [])), "",
          "## Por que NO es stgdiff", "", res["por_que_no_stgdiff"], "",
          "## Por que Module.symvers mide la misma pregunta", "",
          res["por_que_module_symvers"], "",
          "## Caveat que hace valida la comparacion", "", res["caveat"], "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Bitacora", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-004.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "comparar"
    if modo == "build":
        sys.exit(build(sys.argv[2]))
    sys.exit(comparar())
