#!/usr/bin/env python3
"""
F-002 v7 - SIN FILTRO, y dos vías que no dependen del ?narrow.

POR QUE: el v6 dejó la causa en NO MEDIDO por defecto MÍO. Mi filtro de salida se comió
la línea del unmet que nombra el paquete: en el control N1 el MISMO filtro sí la
mostraba, así que la información existía y yo la descarté. Cuarta vez en dos jornadas
que recorto la evidencia antes de leerla.

QUE CAMBIA:
  1. CERO FILTRO. stdout+stderr completos de cada corrida van a un archivo que se
     commitea. Leo DESPUES, del archivo.
  2. Dos brazos que no dependen del ?narrow:
     B1) mmdebstrap --variant=minimal SIN --include, y despues apt-get install DENTRO
         del chroot. El ?narrow solo aplica al conjunto esencial que mmdebstrap resuelve;
         si instalamos systemd despues, adentro, ese filtro no participa.
     B2) debootstrap, otro constructor entero.
  3. B0) mmdebstrap tal cual el v6, para tener el rojo de referencia en la MISMA corrida
     y no comparar contra la memoria.

DECLARADO ANTES DE CORRER:
  - Si B1 anda -> la causa es que el ?narrow excluye al overlay del conjunto esencial, y
    queda MEDIDO por diferencia con B0.
  - Si B1 falla y B2 anda -> el problema es mmdebstrap, y F-002 cierra con debootstrap.
  - Si los tres fallan -> la causa no esta en el constructor y hay que volver al
    resolvedor, aunque apt-get -s haya dado rc=0 dos veces.
"""
import email.utils, gzip, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

M = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PROP = "huanghe-proposed"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
OVER = ["libdevmapper1.02.1", "dmsetup", "libdevmapper-event1.02.1"]
OUT = os.environ.get("F002_OUT", "mediciones/f-002")
WORK = os.environ.get("F002_WORK", "/tmp/f002v7")

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line); print(line, flush=True)

def sh(c, t=2700, guardar=None):
    """Corre y, si guardar, escribe stdout+stderr COMPLETOS a ese archivo."""
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
        say("  salida COMPLETA guardada en", guardar.replace(OUT, "<out>"),
            "(%d B stdout, %d B stderr)" % (len(o), len(e)))
    return rc, o, e

def bajar(u, t=300):
    return urllib.request.urlopen(urllib.request.Request(
        u, headers={"User-Agent": "siao-f002v7/1"}), timeout=t).read()

HOOK = ('set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; '
        'ln -sfn "usr/$d" "$1/$d"; done; '
        'mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"')


def traer_debs():
    ip = gzip.decompress(bajar("%s/dists/%s/main/binary-%s/Packages.gz"
                               % (M, PROP, ARCH))).decode("utf-8", "replace")
    os.makedirs(WORK + "/debs", exist_ok=True)
    debs, man = [], []
    for p in OVER:
        st = None
        for s in ip.split("\n\n"):
            if re.search(r"^Package: %s$" % re.escape(p), s, re.M):
                st = s
        fn = re.search(r"^Filename: (\S+)$", st, re.M).group(1)
        ver = re.search(r"^Version: (\S+)$", st, re.M).group(1)
        sha = re.search(r"^SHA256: (\S+)$", st, re.M).group(1)
        b = bajar("%s/%s" % (M, fn))
        got = hashlib.sha256(b).hexdigest()
        say("  %-26s %-16s %8d B sha256_ok=%s" % (p, ver, len(b), got == sha))
        if got != sha:
            return None, man
        d = WORK + "/debs/" + os.path.basename(fn)
        open(d, "wb").write(b)
        debs.append(d)
        man.append({"paquete": p, "version": ver, "sha256": got, "bytes": len(b)})
    return debs, man


def armar_overlay(debs):
    """No flat, que es el que el v6 probo que apt lee bien."""
    r = WORK + "/overlay"
    shutil.rmtree(r, ignore_errors=True)
    base = r + "/dists/%s/main/binary-%s" % (SUITE, ARCH)
    os.makedirs(base); os.makedirs(r + "/pool/main")
    ent = []
    for d in debs:
        shutil.copy2(d, r + "/pool/main/")
        rc, o, e = sh(["dpkg-deb", "-f", d], 120)
        b = open(d, "rb").read()
        ent.append("%s\nFilename: pool/main/%s\nSize: %d\nSHA256: %s\n"
                   % (o.rstrip("\n"), os.path.basename(d), len(b),
                      hashlib.sha256(b).hexdigest()))
    raw = "\n".join(ent).encode()
    gz = gzip.compress(raw)
    open(base + "/Packages", "wb").write(raw)
    open(base + "/Packages.gz", "wb").write(gz)
    L = ["Origin: SIAO", "Label: SIAO overlay", "Suite: %s" % SUITE,
         "Codename: %s" % SUITE, "Version: 3.0", "Architectures: %s" % ARCH,
         "Components: main", "Date: " + email.utils.formatdate(usegmt=True), "SHA256:",
         " %s %d main/binary-%s/Packages" % (hashlib.sha256(raw).hexdigest(), len(raw), ARCH),
         " %s %d main/binary-%s/Packages.gz" % (hashlib.sha256(gz).hexdigest(), len(gz), ARCH)]
    open(r + "/dists/" + SUITE + "/Release", "w").write("\n".join(L) + "\n")
    say("  overlay no flat armado en", r)
    return r


def b0_mmdebstrap_como_v6(root, fuentes):
    say(""); say("=" * 78)
    say(">>> B0: mmdebstrap tal cual el v6 (el rojo de referencia, en ESTA corrida)")
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (root, root)], 300)
    cmd = ["mmdebstrap", "--mode=root", "--variant=important",
           "--architectures=" + ARCH, "--include=" + ",".join(PKGS),
           '--aptopt=Acquire::AllowInsecureRepositories "true"',
           '--aptopt=APT::Get::AllowUnauthenticated "true"',
           "--setup-hook=" + HOOK, "--skip=cleanup/apt/lists", "--verbose",
           SUITE, root] + fuentes
    rc, o, e = sh(cmd, 2700, guardar=os.path.join(OUT, "v7-B0-mmdebstrap-completo.txt"))
    ok = os.path.isfile(root + "/usr/lib/systemd/systemd")
    say("  rc=%d | systemd presente: %s" % (rc, ok))
    # AHORA leo del texto completo, sin filtro previo
    say("  --- lineas de unmet/Depends, leidas DESPUES del archivo completo ---")
    txt = o + e
    for i, l in enumerate(txt.splitlines()):
        if re.search(r"(unmet dependencies|Depends:|Recommends:|but it is|held broken)", l):
            say("   >>>", l.strip()[:280])
    return ok, rc, txt


def b1_minimal_mas_apt(root, fuentes):
    """El ?narrow solo aplica al essential que resuelve mmdebstrap. Si armamos el
    minimal y despues instalamos systemd DENTRO, ese filtro no participa."""
    say(""); say("=" * 78)
    say(">>> B1: mmdebstrap --variant=minimal SIN --include, y apt-get install adentro")
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (root, root)], 300)
    cmd = ["mmdebstrap", "--mode=root", "--variant=minimal",
           "--architectures=" + ARCH,
           '--aptopt=Acquire::AllowInsecureRepositories "true"',
           '--aptopt=APT::Get::AllowUnauthenticated "true"',
           "--setup-hook=" + HOOK, "--skip=cleanup/apt/lists", "--verbose",
           SUITE, root] + fuentes
    rc, o, e = sh(cmd, 2700, guardar=os.path.join(OUT, "v7-B1a-minimal-completo.txt"))
    say("  minimal rc=%d | existe /usr/bin: %s" % (rc, os.path.isdir(root + "/usr/bin")))
    if rc != 0:
        say("  el minimal ya fallo: leo el unmet completo")
        for l in (o + e).splitlines():
            if re.search(r"(unmet|Depends:|but it is|held broken)", l):
                say("   >>>", l.strip()[:280])
        return False, rc, (o + e)
    # sources.list dentro del chroot y apt-get install adentro
    os.makedirs(root + "/etc/apt", exist_ok=True)
    open(root + "/etc/apt/sources.list", "w").write("\n".join(fuentes) + "\n")
    for d in ("/proc", "/sys", "/dev"):
        sh(["bash", "-c", "mkdir -p %s%s" % (root, d)], 60)
    sh(["bash", "-c", "mount --bind /proc %s/proc || true" % root], 60)
    rc2, o2, e2 = sh(["bash", "-c",
                      "chroot %s apt-get update "
                      "-o Acquire::AllowInsecureRepositories=true "
                      "-o APT::Get::AllowUnauthenticated=true 2>&1" % root],
                     900, guardar=os.path.join(OUT, "v7-B1b-aptupdate-completo.txt"))
    say("  apt-get update adentro rc=%d" % rc2)
    rc3, o3, e3 = sh(["bash", "-c",
                      "chroot %s env DEBIAN_FRONTEND=noninteractive apt-get install "
                      "-y --no-install-recommends "
                      "-o Acquire::AllowInsecureRepositories=true "
                      "-o APT::Get::AllowUnauthenticated=true %s 2>&1"
                      % (root, " ".join(PKGS))],
                     1800, guardar=os.path.join(OUT, "v7-B1c-install-completo.txt"))
    say("  apt-get install adentro rc=%d" % rc3)
    say("  --- lineas de unmet/Depends del install, del texto COMPLETO ---")
    for l in (o3 + e3).splitlines():
        if re.search(r"(unmet|Depends:|but it is|held broken|Setting up systemd)", l):
            say("   >>>", l.strip()[:280])
    sh(["bash", "-c", "umount %s/proc || true" % root], 60)
    ok = os.path.isfile(root + "/usr/lib/systemd/systemd")
    say("  systemd presente: %s" % ok)
    return ok, rc3, (o3 + e3)


def b2_debootstrap(root, ov):
    say(""); say("=" * 78)
    say(">>> B2: debootstrap, otro constructor")
    rc, o, e = sh(["bash", "-c", "command -v debootstrap || echo AUSENTE"], 60)
    say("  debootstrap:", o.strip() or e.strip())
    if "AUSENTE" in (o + e):
        say("  no esta instalado: B2 NO MEDIDO")
        return None, -1, "debootstrap ausente"
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (root, root)], 300)
    rc, o, e = sh(["bash", "-c",
                   "debootstrap --arch=%s --variant=minbase --no-check-gpg "
                   "--include=systemd,systemd-sysv,dbus,udev,iproute2,libpam-systemd "
                   "%s %s %s 2>&1" % (ARCH, SUITE, root, M)],
                  2700, guardar=os.path.join(OUT, "v7-B2-debootstrap-completo.txt"))
    say("  debootstrap rc=%d" % rc)
    say("  --- ultimas 25 lineas, del texto COMPLETO ---")
    for l in (o + e).splitlines()[-25:]:
        say("   |", l[:250])
    ok = os.path.isfile(root + "/usr/lib/systemd/systemd")
    say("  systemd presente: %s" % ok)
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
                    guardar=os.path.join(OUT, "v7-policy-completo.txt"))
    por, det = {}, []
    for b in re.split(r"\n(?=\S+:\n)", pol):
        m = re.match(r"^(\S+):", b)
        if not m:
            continue
        p = m.group(1)
        mm = re.search(r"^\s+\*\*\* (\S+) \d+\n\s+\d+ (\S+) (\S+)", b, re.M)
        if mm:
            uri, suite = mm.group(2), mm.group(3)
            k = "OVERLAY" if uri.startswith("file:") else suite
            por[k] = por.get(k, 0) + 1
            det.append({"paquete": p, "version": mm.group(1), "uri": uri, "suite": suite})
        else:
            por["solo-en-dpkg-status"] = por.get("solo-en-dpkg-status", 0) + 1
    say("  paquetes: %d | ORIGEN contado por apt:" % len(nombres))
    for k, v in sorted(por.items(), key=lambda x: -x[1]):
        say("      %-42s %d" % (k, v))
    ov = [d for d in det if d["uri"].startswith("file:")]
    for d in ov:
        say("      del OVERLAY: %-28s %s" % (d["paquete"], d["version"]))
    prop = [d for d in det if PROP in d["suite"] or PROP in d["uri"]]
    sd = [d for d in det if d["paquete"] == "systemd"]
    ctrl = bool(sd) and SUITE in sd[0]["suite"]
    say("  de %s directo: %d | CONTROL systemd de huanghe: %s %s"
        % (PROP, len(prop), ctrl, sd[:1]))
    return {"n_paquetes": len(nombres), "por_origen": por, "del_overlay": ov,
            "n_de_proposed": len(prop), "control_systemd": ctrl, "detalle": det[:250]}


def main():
    import platform
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    res = {"falsador": "F-002", "version": 7,
           "pregunta": "cual es la causa real, y hay un constructor que si funcione",
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "defecto_que_corrige": ("el v6 dejo la causa en NO MEDIDO porque mi filtro se "
                                   "comio la linea del unmet. Cuarta vez que recorto la "
                                   "evidencia antes de leerla. Este v7 guarda stdout+stderr "
                                   "COMPLETOS en archivos commiteados y los lee despues."),
           "declarado_antes_de_correr": (
               "Si B1 anda -> la causa es el ?narrow excluyendo al overlay del conjunto "
               "esencial, MEDIDO por diferencia con B0. Si B1 falla y B2 anda -> el "
               "problema es mmdebstrap. Si los tres fallan -> la causa no esta en el "
               "constructor y hay que volver al resolvedor."),
           "brazos": {}, "no_medido": []}
    say("== F-002 v7: SIN FILTRO ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("DEFECTO QUE CORRIGE:", res["defecto_que_corrige"])
    say("DECLARADO ANTES DE CORRER:", res["declarado_antes_de_correr"])

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host no aarch64"); write(res); return 3

    say(""); say("--- los 3 .deb ---")
    debs, man = traer_debs()
    res["manifiesto"] = man
    if not debs:
        res["no_medido"].append("no pude bajar los .deb"); write(res); return 3
    ov = armar_overlay(debs)
    fmain = "deb [trusted=yes] %s %s main" % (M, SUITE)
    f_ov = "deb [trusted=yes] file://%s %s main" % (ov, SUITE)
    fuentes = [fmain, f_ov]

    ok0, rc0, t0txt = b0_mmdebstrap_como_v6(WORK + "/b0", fuentes)
    res["brazos"]["B0_mmdebstrap_v6"] = {"instalo": ok0, "rc": rc0}

    ok1, rc1, t1txt = b1_minimal_mas_apt(WORK + "/b1", fuentes)
    res["brazos"]["B1_minimal_mas_apt_adentro"] = {"instalo": ok1, "rc": rc1}

    ok2, rc2, t2txt = b2_debootstrap(WORK + "/b2", ov)
    res["brazos"]["B2_debootstrap"] = {"instalo": ok2, "rc": rc2}

    say(""); say("=" * 78)
    say("RESULTADO: B0=%s | B1=%s | B2=%s" % (ok0, ok1, ok2))
    if ok1 and not ok0:
        res["causa"] = ("MEDIDA: el ?narrow de mmdebstrap excluye al overlay del conjunto "
                        "esencial. Instalando DESPUES, adentro del chroot, funciona.")
        ganador = WORK + "/b1"
    elif ok2 and not ok0:
        res["causa"] = "MEDIDA: es mmdebstrap. debootstrap construye lo mismo sin problema."
        ganador = WORK + "/b2"
    elif ok0:
        res["causa"] = ("INESPERADO: B0 anduvo en esta corrida. Algo cambio respecto del "
                        "v6 y hay que aislarlo antes de creerle.")
        ganador = WORK + "/b0"
    else:
        res["causa"] = ("NO MEDIDA: los tres brazos fallan. La causa no esta en el "
                        "constructor, y eso contradice el rc=0 de apt-get -s: hay que "
                        "volver al resolvedor con la salida completa en la mano.")
        ganador = None
    say("CAUSA:", res["causa"])

    if ganador:
        rc, o, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % ganador])
        res["rootfs_bytes"] = int((o.strip() or "0").split()[0])
        say("  rootfs: %d B (%.3f GiB)"
            % (res["rootfs_bytes"], res["rootfs_bytes"] / 1073741824.0))
        rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                       "'${Package} ${Version}\\n' systemd libdevmapper1.02.1 "
                       "libcryptsetup12 2>&1" % ganador])
        say("  LA CADENA:")
        for l in o.splitlines():
            say("   |", l[:120])
        res["cadena"] = o.strip()
        res["criterio_b"] = origen(ganador, fuentes)
        b = res["criterio_b"]
        res["veredicto"] = {"a": "VERDE",
                            "b": ("VERDE" if (b["control_systemd"] and b["n_de_proposed"] == 0)
                                  else "AMARILLO"),
                            "c": "ROJO (trusted=yes, R-07)"}
    else:
        res["veredicto"] = {"a": "ROJO", "b": "NO MEDIDO", "c": "NO MEDIDO"}
    say(""); say("VEREDICTO F-002 v7:", json.dumps(res["veredicto"]))
    res["segundos"] = round(time.time() - t0, 1)
    write(res); say("FIN en", res["segundos"], "s")
    return 0 if ganador else 3


def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-002-v7.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-002-v7-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    v = res.get("veredicto", {})
    b = res.get("criterio_b", {})
    md = ["# F-002 v7 - sin filtro, tres constructores", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "**Causa:** %s" % res.get("causa", "?"), "",
          "| Brazo | Instalo | rc |", "|---|---|---|"] + [
          "| %s | %s | %s |" % (k, x.get("instalo"), x.get("rc"))
          for k, x in res.get("brazos", {}).items()] + [
          "", "| Criterio | Veredicto |", "|---|---|",
          "| (a) construye | **%s** |" % v.get("a", "?"),
          "| (b) origen | **%s** |" % v.get("b", "?"),
          "| (c) firmas | **%s** |" % v.get("c", "?"), "",
          "Paquetes: %s | del overlay: %s | rootfs: %s B"
          % (b.get("n_paquetes", "?"), len(b.get("del_overlay", [])),
             res.get("rootfs_bytes", "?")), "",
          "## Origen contado por apt", "", "```json",
          json.dumps(b.get("por_origen", {}), indent=2, ensure_ascii=False), "```", "",
          "## Salidas COMPLETAS, sin filtro", "",
          "`v7-B0-mmdebstrap-completo.txt`, `v7-B1a-minimal-completo.txt`, "
          "`v7-B1b-aptupdate-completo.txt`, `v7-B1c-install-completo.txt`, "
          "`v7-B2-debootstrap-completo.txt`, `v7-policy-completo.txt`", "",
          "## Declarado antes de correr", "", res["declarado_antes_de_correr"], "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Bitacora de la corrida", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-002-v7.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
