#!/usr/bin/env python3
"""
F-002 v8 - el overlay minimo REAL: main + {libdevmapper1.02.1, libgcrypt20, libgpg-error0}

COMO SE LLEGO ACA, y es el hallazgo del v7: al sacar el filtro, la salida completa de
mmdebstrap nombro la causa que seis versiones no vieron:

  gpgv : Depends: libgcrypt20 (>= 1.12.1) but 1.10.3-ok2 is to be installed
         Depends: libgpg-error0 (>= 1.49) but 1.47-ok1 is to be installed
  libcryptsetup12 : Depends: libdevmapper1.02.1 (>= 2:1.02.197) but it is not going to be installed

Hay DOS cadenas rotas en huanghe/main arm64. La de libdevmapper la segui desde el v2;
la de gpgv NO LA VI NUNCA, porque mis apt-get -s pedian solo los 6 paquetes de systemd
y gpgv entra por el CONJUNTO ESENCIAL que pide mmdebstrap. Mi resolvedor y mi
constructor median conjuntos distintos: de ahi salia el "apt verde, mmdebstrap rojo"
que atribui primero al Release y despues al layout. Los dos falsos.

CIERRE MEDIDO POR ITERACION (brain-env, agregando solo lo que apt nombra):
  main + los 3 de arriba -> apt-get -s rc=0, 161 paquetes, 3 del overlay. Una ronda.

Este v8 lleva ese overlay al constructor real y cierra los tres criterios.
"""
import email.utils, gzip, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

M = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PROP = "huanghe-proposed"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
# EL OVERLAY MINIMO MEDIDO. No es el del v5/v6/v7.
OVER = ["libdevmapper1.02.1", "libgcrypt20", "libgpg-error0"]
# Lo que sobraba y sale: dmsetup, libdevmapper-event1.02.1
SOBRABAN = ["dmsetup", "libdevmapper-event1.02.1"]
OUT = os.environ.get("F002_OUT", "mediciones/f-002")
WORK = os.environ.get("F002_WORK", "/tmp/f002v8")

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line); print(line, flush=True)

def sh(c, t=2700, guardar=None):
    say("$", (c if isinstance(c, str) else " ".join(c))[:420])
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
        u, headers={"User-Agent": "siao-f002v8/1"}), timeout=t).read()

HOOK = ('set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; '
        'ln -sfn "usr/$d" "$1/$d"; done; '
        'mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"')


def armar_overlay(nombres, destino):
    say(""); say("--- overlay: %s ---" % ", ".join(nombres))
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
    for n in nombres:
        sp = ult(ip, n)
        sm = ult(im, n)
        if not sp:
            say("  %s NO ESTA en %s" % (n, PROP)); return None, man
        fn = re.search(r"^Filename: (\S+)$", sp, re.M).group(1)
        ver = re.search(r"^Version: (\S+)$", sp, re.M).group(1)
        sha = re.search(r"^SHA256: (\S+)$", sp, re.M).group(1)
        vm = re.search(r"^Version: (\S+)$", sm, re.M).group(1) if sm else "no esta en main"
        b = bajar("%s/%s" % (M, fn))
        got = hashlib.sha256(b).hexdigest()
        say("  %-24s %-18s %8d B sha256_ok=%s   main tiene: %s"
            % (n, ver, len(b), got == sha, vm))
        if got != sha:
            say("  ABORTO: sha256 no coincide"); return None, man
        p = destino + "/pool/main/" + os.path.basename(fn)
        open(p, "wb").write(b)
        rc, o, e = sh(["dpkg-deb", "-f", p], 120)
        ent.append("%s\nFilename: pool/main/%s\nSize: %d\nSHA256: %s\n"
                   % (o.rstrip("\n"), os.path.basename(fn), len(b), got))
        man.append({"paquete": n, "version_overlay": ver, "version_en_main": vm,
                    "sha256": got, "bytes": len(b),
                    "origen": "%s/%s" % (PROP, fn)})
    raw = "\n".join(ent).encode(); gz = gzip.compress(raw)
    open(base + "/Packages", "wb").write(raw)
    open(base + "/Packages.gz", "wb").write(gz)
    L = ["Origin: SIAO", "Label: siao-base-s1 overlay", "Suite: %s" % SUITE,
         "Codename: %s" % SUITE, "Version: 3.0", "Architectures: %s" % ARCH,
         "Components: main", "Date: " + email.utils.formatdate(usegmt=True), "SHA256:",
         " %s %d main/binary-%s/Packages" % (hashlib.sha256(raw).hexdigest(), len(raw), ARCH),
         " %s %d main/binary-%s/Packages.gz" % (hashlib.sha256(gz).hexdigest(), len(gz), ARCH)]
    open(destino + "/dists/" + SUITE + "/Release", "w").write("\n".join(L) + "\n")
    return destino, man


def construir(nombre, root, fuentes, etiqueta):
    say(""); say("=" * 78)
    say(">>> %s" % nombre)
    for f in fuentes:
        say("    fuente:", f)
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (root, root)], 300)
    cmd = ["mmdebstrap", "--mode=root", "--variant=important",
           "--architectures=" + ARCH, "--include=" + ",".join(PKGS),
           '--aptopt=Acquire::AllowInsecureRepositories "true"',
           '--aptopt=APT::Get::AllowUnauthenticated "true"',
           "--setup-hook=" + HOOK, "--skip=cleanup/apt/lists", "--verbose",
           SUITE, root] + fuentes
    rc, o, e = sh(cmd, 2700, guardar=os.path.join(OUT, "v8-%s-completo.txt" % etiqueta))
    ok = os.path.isfile(root + "/usr/lib/systemd/systemd")
    say("  rc=%d | systemd presente: %s" % (rc, ok))
    say("  --- unmet/Depends/Setting up, del texto COMPLETO (sin filtro previo) ---")
    for l in (o + e).splitlines():
        if re.search(r"(unmet dependencies|Depends:|but it is|but .* is to be|"
                     r"held broken|Setting up systemd )", l):
            say("   >>>", l.strip()[:260])
    return ok, rc, (o + e)


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
                    guardar=os.path.join(OUT, "v8-policy-completo.txt"))
    por, det = {}, []
    for b in re.split(r"\n(?=\S+:\n)", pol):
        m = re.match(r"^(\S+):", b)
        if not m:
            continue
        p = m.group(1)
        mm = re.search(r"^\s+\*\*\* (\S+) \d+\n\s+\d+ (\S+) (\S+)", b, re.M)
        if mm:
            uri, suite = mm.group(2), mm.group(3)
            k = "OVERLAY-SIAO" if uri.startswith("file:") else suite
            por[k] = por.get(k, 0) + 1
            det.append({"paquete": p, "version": mm.group(1), "uri": uri, "suite": suite})
        else:
            por["solo-en-dpkg-status"] = por.get("solo-en-dpkg-status", 0) + 1
    say("  paquetes instalados: %d" % len(nombres))
    say("  ORIGEN, contado por apt:")
    for k, v in sorted(por.items(), key=lambda x: -x[1]):
        say("      %-44s %d" % (k, v))
    ov = [d for d in det if d["uri"].startswith("file:")]
    say("  del OVERLAY de SIAO, segun apt:")
    for d in ov:
        say("      %-26s %s" % (d["paquete"], d["version"]))
    prop = [d for d in det if PROP in d["suite"] or PROP in d["uri"]]
    sd = [d for d in det if d["paquete"] == "systemd"]
    ctrl = bool(sd) and SUITE in sd[0]["suite"] and PROP not in sd[0]["suite"]
    say("  de %s DIRECTO: %d (debe ser 0: no esta en las fuentes)" % (PROP, len(prop)))
    say("  CONTROL de (b): systemd sale de huanghe (no de proposed)?", ctrl, sd[:1])
    return {"n_paquetes": len(nombres), "por_origen": por,
            "del_overlay": ov, "n_del_overlay": len(ov),
            "n_de_proposed_directo": len(prop), "control_systemd": ctrl,
            "detalle": det[:250]}


def main():
    import platform
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    res = {"falsador": "F-002", "version": 8,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "la_causa": ("gpgv : Depends: libgcrypt20 (>= 1.12.1) but 1.10.3-ok2 is to be "
                        "installed / Depends: libgpg-error0 (>= 1.49) but 1.47-ok1. Son DOS "
                        "cadenas rotas en huanghe/main arm64, no una. gpgv entra por el "
                        "conjunto esencial que pide mmdebstrap, y mis apt-get -s pedian solo "
                        "los 6 de systemd: el resolvedor y el constructor median conjuntos "
                        "distintos, y de ahi salia el 'apt verde, mmdebstrap rojo'."),
           "overlay_minimo_medido": OVER,
           "sobraban": SOBRABAN,
           "prediccion": ("Predigo VERDE: el apt-get -s iterativo en brain-env dio rc=0 y "
                          "161 paquetes con exactamente estos 3, y ahora el pedido del "
                          "resolvedor y el del constructor son el MISMO conjunto."),
           "controles": {}, "no_medido": []}
    say("== F-002 v8: el overlay minimo REAL ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("LA CAUSA (del v7, sin filtro):", res["la_causa"])
    say("OVERLAY MINIMO MEDIDO:", OVER)
    say("SOBRABAN del overlay anterior:", SOBRABAN)
    say("PREDICCION registrada antes de correr:", res["prediccion"])

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host no aarch64"); write(res); return 3

    ov, man = armar_overlay(OVER, WORK + "/overlay")
    res["manifiesto"] = man
    if not ov:
        res["no_medido"].append("overlay no armado"); write(res); return 3
    # control negativo: el overlay VIEJO, el que yo venia usando
    ovv, manv = armar_overlay(["libdevmapper1.02.1"] + SOBRABAN, WORK + "/overlay-viejo")

    fmain = "deb [trusted=yes] %s %s main" % (M, SUITE)
    f_ov = "deb [trusted=yes] file://%s %s main" % (ov, SUITE)
    f_ovv = "deb [trusted=yes] file://%s %s main" % (ovv, SUITE)

    okS, rcS, tS = construir("SUJETO main + overlay MEDIDO (3 correctos)",
                             WORK + "/rootfs", [fmain, f_ov], "sujeto")
    okN, rcN, tN = construir("CONTROL main + overlay VIEJO (el de los v5/v6/v7)",
                             WORK + "/viejo", [fmain, f_ovv], "control-viejo")
    res["sujeto"] = {"instalo": okS, "rc": rcS}
    res["controles"]["overlay_viejo"] = {"instalo": okN, "rc": rcN,
                                         "esperado": "FALLA por gpgv/libgcrypt20"}
    res["controles"]["discrimina"] = (okS != okN)
    say("")
    say("RESULTADO: sujeto=%s (rc %d) | overlay viejo=%s (rc %d)" % (okS, rcS, okN, rcN))
    say("EL CONTROL DISCRIMINA:", res["controles"]["discrimina"])
    res["prediccion_acerto"] = okS

    if okS:
        rc, o, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % (WORK + "/rootfs")])
        res["rootfs_bytes"] = int((o.strip() or "0").split()[0])
        say("  rootfs: %d B (%.3f GiB)"
            % (res["rootfs_bytes"], res["rootfs_bytes"] / 1073741824.0))
        rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                       "'${Package} ${Version}\\n' systemd gpgv libgcrypt20 libgpg-error0 "
                       "libdevmapper1.02.1 libcryptsetup12 base-files 2>&1"
                       % (WORK + "/rootfs")])
        say("  LAS DOS CADENAS, instaladas:")
        for l in o.splitlines():
            say("   |", l[:130])
        res["cadenas"] = o.strip()
        rc, o, _ = sh(["bash", "-c", "cat %s/etc/os-release | head -4" % (WORK + "/rootfs")])
        say("  os-release:")
        for l in o.splitlines():
            say("   |", l)
        res["os_release"] = o.strip()
        res["criterio_b"] = origen(WORK + "/rootfs", [fmain, f_ov])
        b = res["criterio_b"]
        res["veredicto"] = {
            "a_construye": "VERDE",
            "b_origen": ("VERDE" if (b["control_systemd"] and b["n_de_proposed_directo"] == 0)
                         else "AMARILLO"),
            "c_firmas": "ROJO (trusted=yes, R-07)"}
    else:
        res["veredicto"] = {"a_construye": "ROJO", "b_origen": "NO MEDIDO",
                            "c_firmas": "NO MEDIDO"}
    say(""); say("VEREDICTO F-002 v8:", json.dumps(res["veredicto"]))
    say("La prediccion", "ACERTO" if okS else "SE REFUTO")
    res["segundos"] = round(time.time() - t0, 1)
    write(res); say("FIN en", res["segundos"], "s")
    return 0 if okS else 3


def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-002-v8.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-002-v8-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    v = res.get("veredicto", {})
    b = res.get("criterio_b", {})
    md = ["# F-002 v8 - siao-base-s1 = main + 3 paquetes (medidos)", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "## La causa, que seis versiones no vieron", "", res["la_causa"], "",
          "| Criterio | Veredicto |", "|---|---|",
          "| (a) construye systemd | **%s** |" % v.get("a_construye", "?"),
          "| (b) origen por apt-cache policy | **%s** |" % v.get("b_origen", "?"),
          "| (c) firmas | **%s** |" % v.get("c_firmas", "?"), "",
          "**Overlay minimo medido:** %s" % ", ".join(res["overlay_minimo_medido"]),
          "**Sobraban:** %s" % ", ".join(res["sobraban"]), "",
          "Paquetes: %s | del overlay: %s | de -proposed directo: %s | rootfs: %s B"
          % (b.get("n_paquetes", "?"), b.get("n_del_overlay", "?"),
             b.get("n_de_proposed_directo", "?"), res.get("rootfs_bytes", "?")), "",
          "## Manifiesto del overlay", "", "```json",
          json.dumps(res.get("manifiesto", []), indent=2, ensure_ascii=False), "```", "",
          "## Origen contado por apt", "", "```json",
          json.dumps(b.get("por_origen", {}), indent=2, ensure_ascii=False), "```", "",
          "## Controles", "", "```json",
          json.dumps(res["controles"], indent=2, ensure_ascii=False), "```", "",
          "## Prediccion registrada antes de correr", "", res["prediccion"],
          "", "Acerto: %s" % res.get("prediccion_acerto", "sin dato"), "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Bitacora", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-002-v8.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
