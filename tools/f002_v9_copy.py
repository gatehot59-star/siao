#!/usr/bin/env python3
"""
F-002 v9 - copy:// en vez de file://. La causa la nombro mmdebstrap, con el fix incluido.

LA LINEA QUE CERRO SEIS VERSIONES DE BUSQUEDA, verbatim del v8 sin filtro:

  E: package file .../overlay/pool/main/libgpg-error0_1.59-ok1_arm64.deb not accessible
     from chroot directory -- use copy:// instead of file:// or a bind-mount.

Y el resto de esa misma salida muestra que TODO LO DEMAS YA ANDABA con el overlay de 3
correctos: 60 paquetes resueltos sin un solo unmet, los .deb del overlay bajados y
CONFIGURADOS por dpkg, y el proceso llegando a "--configure --pending".

El problema nunca fue el Release (v3), ni el layout flat (v6), ni el conjunto de
paquetes (v8 lo corrigio y sirvio). Era el ESQUEMA DE LA URL: con file://, el .deb
vive afuera del chroot y dpkg, que corre ADENTRO, no lo alcanza. copy:// hace que
mmdebstrap lo copie al target antes de instalar.

CONTROL QUE DISCRIMINA POR CONSTRUCCION: el MISMO overlay, los MISMOS paquetes, la
MISMA orden, servido con copy:// y con file://. Unica variable: cuatro letras.
"""
import email.utils, gzip, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

M = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PROP = "huanghe-proposed"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
OVER = ["libdevmapper1.02.1", "libgcrypt20", "libgpg-error0"]
OUT = os.environ.get("F002_OUT", "mediciones/f-002")
WORK = os.environ.get("F002_WORK", "/tmp/f002v9")

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line); print(line, flush=True)

def sh(c, t=2700, guardar=None):
    say("$", (c if isinstance(c, str) else " ".join(c))[:400])
    try:
        r = subprocess.run(c, shell=isinstance(c, str), capture_output=True,
                           text=True, timeout=t)
        rc, o, e = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        rc, o, e = -9, "", "TIMEOUT tras %ss" % t
    except Exception as ex:
        rc, o, e = -1, "", repr(ex)[:300]
    if guardar:
        os.makedirs(os.path.dirname(guardar), exist_ok=True)
        with open(guardar, "w") as f:
            f.write("### comando\n%s\n\n### rc=%d\n\n### stdout\n%s\n\n### stderr\n%s\n"
                    % ((c if isinstance(c, str) else " ".join(c)), rc, o, e))
        say("  salida COMPLETA en", guardar.replace(OUT, "<out>"),
            "(%d B out, %d B err)" % (len(o), len(e)))
    return rc, o, e

def bajar(u, t=300):
    return urllib.request.urlopen(urllib.request.Request(
        u, headers={"User-Agent": "siao-f002v9/1"}), timeout=t).read()

HOOK = ('set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; '
        'ln -sfn "usr/$d" "$1/$d"; done; '
        'mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"')


def armar_overlay(destino):
    say(""); say("--- overlay siao-base-s1: %s ---" % ", ".join(OVER))
    ip = gzip.decompress(bajar("%s/dists/%s/main/binary-%s/Packages.gz"
                               % (M, PROP, ARCH))).decode("utf-8", "replace")
    im = gzip.decompress(bajar("%s/dists/%s/main/binary-%s/Packages.gz"
                               % (M, SUITE, ARCH))).decode("utf-8", "replace")
    def ult(idx, n):
        s = None
        for x in idx.split("\n\n"):
            if re.search(r"^Package: %s$" % re.escape(n), x, re.M):
                s = x
        return s
    shutil.rmtree(destino, ignore_errors=True)
    base = destino + "/dists/%s/main/binary-%s" % (SUITE, ARCH)
    os.makedirs(base); os.makedirs(destino + "/pool/main")
    ent, man = [], []
    for n in OVER:
        sp, sm = ult(ip, n), ult(im, n)
        fn = re.search(r"^Filename: (\S+)$", sp, re.M).group(1)
        ver = re.search(r"^Version: (\S+)$", sp, re.M).group(1)
        sha = re.search(r"^SHA256: (\S+)$", sp, re.M).group(1)
        vm = re.search(r"^Version: (\S+)$", sm, re.M).group(1) if sm else "no esta en main"
        b = bajar("%s/%s" % (M, fn))
        got = hashlib.sha256(b).hexdigest()
        say("  %-22s %-16s %8d B sha256_ok=%s   main: %s"
            % (n, ver, len(b), got == sha, vm))
        if got != sha:
            return None, man
        p = destino + "/pool/main/" + os.path.basename(fn)
        open(p, "wb").write(b)
        rc, o, e = sh(["dpkg-deb", "-f", p], 120)
        ent.append("%s\nFilename: pool/main/%s\nSize: %d\nSHA256: %s\n"
                   % (o.rstrip("\n"), os.path.basename(fn), len(b), got))
        man.append({"paquete": n, "version": ver, "version_en_main": vm,
                    "sha256": got, "bytes": len(b), "origen": "%s/%s" % (PROP, fn)})
    raw = "\n".join(ent).encode(); gz = gzip.compress(raw)
    open(base + "/Packages", "wb").write(raw)
    open(base + "/Packages.gz", "wb").write(gz)
    L = ["Origin: SIAO", "Label: siao-base-s1", "Suite: %s" % SUITE,
         "Codename: %s" % SUITE, "Version: 3.0", "Architectures: %s" % ARCH,
         "Components: main", "Date: " + email.utils.formatdate(usegmt=True), "SHA256:",
         " %s %d main/binary-%s/Packages" % (hashlib.sha256(raw).hexdigest(), len(raw), ARCH),
         " %s %d main/binary-%s/Packages.gz" % (hashlib.sha256(gz).hexdigest(), len(gz), ARCH)]
    open(destino + "/dists/" + SUITE + "/Release", "w").write("\n".join(L) + "\n")
    say("  Release y Packages escritos")
    return destino, man


def construir(nombre, root, esquema, ov, etiqueta):
    say(""); say("=" * 78)
    say(">>> %s   (esquema: %s)" % (nombre, esquema))
    fuentes = ["deb [trusted=yes] %s %s main" % (M, SUITE),
               "deb [trusted=yes] %s//%s %s main" % (esquema, ov, SUITE)]
    for f in fuentes:
        say("    fuente:", f)
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (root, root)], 300)
    cmd = ["mmdebstrap", "--mode=root", "--variant=important",
           "--architectures=" + ARCH, "--include=" + ",".join(PKGS),
           '--aptopt=Acquire::AllowInsecureRepositories "true"',
           '--aptopt=APT::Get::AllowUnauthenticated "true"',
           "--setup-hook=" + HOOK, "--skip=cleanup/apt/lists", "--verbose",
           SUITE, root] + fuentes
    rc, o, e = sh(cmd, 2700, guardar=os.path.join(OUT, "v9-%s-completo.txt" % etiqueta))
    ok = os.path.isfile(root + "/usr/lib/systemd/systemd")
    say("  rc=%d | systemd presente: %s" % (rc, ok))
    say("  --- las lineas que importan, del texto COMPLETO ---")
    for l in (o + e).splitlines():
        if re.search(r"(unmet dependencies|Depends:|but it is|not accessible from chroot|"
                     r"Setting up systemd |^E: |newly installed)", l):
            say("   >>>", l.strip()[:250])
    return ok, rc, (o + e), fuentes


def origen(root, fuentes):
    say(""); say("--- CRITERIO (b): apt-cache policy dentro del chroot (R-04) ---")
    os.makedirs(root + "/etc/apt", exist_ok=True)
    open(root + "/etc/apt/sources.list", "w").write("\n".join(fuentes) + "\n")
    sh(["bash", "-c", "chroot %s apt-get update -qq "
        "-o Acquire::AllowInsecureRepositories=true "
        "-o APT::Get::AllowUnauthenticated=true 2>&1 | tail -3" % root], 900)
    rc, nm, _ = sh(["bash", "-c", "chroot %s dpkg-query -W -f '${Package}\\n' | sort" % root])
    nombres = [x for x in nm.split() if x]
    rc, pol, _ = sh(["bash", "-c", "chroot %s apt-cache policy %s 2>&1"
                     % (root, " ".join(nombres))], 900,
                    guardar=os.path.join(OUT, "v9-policy-completo.txt"))
    por, det = {}, []
    for b in re.split(r"\n(?=\S+:\n)", pol):
        m = re.match(r"^(\S+):", b)
        if not m:
            continue
        mm = re.search(r"^\s+\*\*\* (\S+) \d+\n\s+\d+ (\S+) (\S+)", b, re.M)
        if mm:
            uri, suite = mm.group(2), mm.group(3)
            k = "OVERLAY-SIAO" if ("file:" in uri or "copy:" in uri) else suite
            por[k] = por.get(k, 0) + 1
            det.append({"paquete": m.group(1), "version": mm.group(1),
                        "uri": uri, "suite": suite})
        else:
            por["solo-en-dpkg-status"] = por.get("solo-en-dpkg-status", 0) + 1
    say("  paquetes instalados: %d" % len(nombres))
    say("  ORIGEN, contado por apt:")
    for k, v in sorted(por.items(), key=lambda x: -x[1]):
        say("      %-44s %d" % (k, v))
    ov = [d for d in det if "file:" in d["uri"] or "copy:" in d["uri"]]
    say("  del OVERLAY, segun apt:")
    for d in ov:
        say("      %-24s %s" % (d["paquete"], d["version"]))
    prop = [d for d in det if PROP in d["suite"] or PROP in d["uri"]]
    sd = [d for d in det if d["paquete"] == "systemd"]
    ctrl = bool(sd) and SUITE in sd[0]["suite"] and PROP not in sd[0]["suite"]
    say("  de %s DIRECTO: %d (debe ser 0)" % (PROP, len(prop)))
    say("  CONTROL de (b): systemd de huanghe y NO de proposed?", ctrl, sd[:1])
    return {"n_paquetes": len(nombres), "por_origen": por, "del_overlay": ov,
            "n_del_overlay": len(ov), "n_de_proposed_directo": len(prop),
            "control_systemd": ctrl, "detalle": det[:250]}


def main():
    import platform
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    res = {"falsador": "F-002", "version": 9,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "la_causa": ("mmdebstrap la nombro con el fix incluido: 'package file ... not "
                        "accessible from chroot directory -- use copy:// instead of "
                        "file://'. Con file:// el .deb vive afuera del chroot y dpkg corre "
                        "adentro. Seis versiones buscandola, y estaba escrita en la salida "
                        "que yo venia filtrando."),
           "overlay": OVER,
           "prediccion": ("Predigo VERDE con copy:// y ROJO con file://. El v8 ya mostro "
                          "que con el overlay de estos 3 no hay ni un unmet: 60 paquetes "
                          "resueltos y los del overlay configurados por dpkg."),
           "controles": {}, "no_medido": []}
    say("== F-002 v9: copy:// ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("LA CAUSA:", res["la_causa"])
    say("PREDICCION registrada antes de correr:", res["prediccion"])

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host no aarch64"); write(res); return 3

    ov, man = armar_overlay(WORK + "/overlay")
    res["manifiesto"] = man
    if not ov:
        res["no_medido"].append("overlay no armado"); write(res); return 3

    okS, rcS, tS, fS = construir("SUJETO con copy://", WORK + "/rootfs", "copy:", ov, "sujeto-copy")
    okN, rcN, tN, fN = construir("CONTROL con file:// (el de los v5-v8)",
                                 WORK + "/con-file", "file:", ov, "control-file")
    res["sujeto"] = {"esquema": "copy://", "instalo": okS, "rc": rcS}
    res["controles"]["file"] = {
        "esquema": "file://", "instalo": okN, "rc": rcN,
        "causa_detectada": ("not accessible from chroot" in tN),
        "evidencia": "\n".join([l for l in tN.splitlines()
                                if "not accessible from chroot" in l])[:500]}
    res["controles"]["discrimina"] = (okS != okN)
    say("")
    say("RESULTADO: copy://=%s (rc %d) | file://=%s (rc %d)" % (okS, rcS, okN, rcN))
    say("EL CONTROL DISCRIMINA:", res["controles"]["discrimina"])
    res["prediccion_acerto"] = (okS and not okN)

    if okS:
        rc, o, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % (WORK + "/rootfs")])
        res["rootfs_bytes"] = int((o.strip() or "0").split()[0])
        say("  rootfs: %d B (%.3f GiB)"
            % (res["rootfs_bytes"], res["rootfs_bytes"] / 1073741824.0))
        rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                       "'${Package} ${Version}\\n' systemd gpgv libgcrypt20 libgpg-error0 "
                       "libdevmapper1.02.1 libcryptsetup12 base-files 2>&1"
                       % (WORK + "/rootfs")])
        say("  LAS DOS CADENAS QUE ESTABAN ROTAS, ahora instaladas:")
        for l in o.splitlines():
            say("   |", l[:130])
        res["cadenas"] = o.strip()
        rc, o, _ = sh(["bash", "-c", "cat %s/etc/os-release | head -4" % (WORK + "/rootfs")])
        say("  os-release del rootfs:")
        for l in o.splitlines():
            say("   |", l)
        res["os_release"] = o.strip()
        rc, o, _ = sh(["bash", "-c", "ls -la %s/usr/lib/systemd/systemd" % (WORK + "/rootfs")])
        say("  el init:", o.strip()[:160])
        res["criterio_b"] = origen(WORK + "/rootfs", fS)
        b = res["criterio_b"]
        res["veredicto"] = {
            "a_construye": "VERDE",
            "b_origen": ("VERDE" if (b["control_systemd"] and b["n_de_proposed_directo"] == 0)
                         else "AMARILLO"),
            "c_firmas": "ROJO (trusted=yes, R-07)"}
    else:
        res["veredicto"] = {"a_construye": "ROJO", "b_origen": "NO MEDIDO",
                            "c_firmas": "NO MEDIDO"}
    say(""); say("VEREDICTO F-002 v9:", json.dumps(res["veredicto"]))
    say("La prediccion", "ACERTO" if res["prediccion_acerto"] else "SE REFUTO")
    res["segundos"] = round(time.time() - t0, 1)
    write(res); say("FIN en", res["segundos"], "s")
    return 0 if okS else 3


def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-002-v9.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-002-v9-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    v = res.get("veredicto", {})
    b = res.get("criterio_b", {})
    md = ["# F-002 v9 - siao-base-s1: main + 3 paquetes, servidos con copy://", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "## La causa, nombrada por mmdebstrap con su fix", "", res["la_causa"], "",
          "| Criterio | Veredicto |", "|---|---|",
          "| (a) construye systemd | **%s** |" % v.get("a_construye", "?"),
          "| (b) origen por apt-cache policy | **%s** |" % v.get("b_origen", "?"),
          "| (c) firmas | **%s** |" % v.get("c_firmas", "?"), "",
          "| Esquema | Instalo | rc |", "|---|---|---|",
          "| copy:// (sujeto) | %s | %s |" % (res.get("sujeto", {}).get("instalo"),
                                              res.get("sujeto", {}).get("rc")),
          "| file:// (control) | %s | %s |" % (res["controles"].get("file", {}).get("instalo"),
                                               res["controles"].get("file", {}).get("rc")), "",
          "**El control discrimina:** %s" % res["controles"].get("discrimina", "?"), "",
          "Paquetes: %s | del overlay: %s | de -proposed directo: %s | rootfs: %s B"
          % (b.get("n_paquetes", "?"), b.get("n_del_overlay", "?"),
             b.get("n_de_proposed_directo", "?"), res.get("rootfs_bytes", "?")), "",
          "## siao-base-s1: el manifiesto", "", "```json",
          json.dumps(res.get("manifiesto", []), indent=2, ensure_ascii=False), "```", "",
          "## Origen contado por apt", "", "```json",
          json.dumps(b.get("por_origen", {}), indent=2, ensure_ascii=False), "```", "",
          "## Prediccion registrada antes de correr", "", res["prediccion"],
          "", "Acerto: %s" % res.get("prediccion_acerto", "sin dato"), "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Bitacora", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-002-v9.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
