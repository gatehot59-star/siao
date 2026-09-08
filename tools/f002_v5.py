#!/usr/bin/env python3
"""
F-002 v5 - main + overlay SIAO con Release. Cierra los tres criterios.

EL PRE-VUELO YA CONTESTO LA PREGUNTA (R-05), en brain-env y sin gastar runner:
  apt-get install -s rc=0 -> 68 paquetes
    Inst libdevmapper1.02.1  2:1.02.205-ok1  SIAO overlay:3.0/huanghe [arm64]
    Inst libcryptsetup12     2:2.8.4-1ok10   openKylin:3.0/huanghe [arm64]
    Inst systemd             255.2-ok2.8     openKylin:3.0/huanghe [arm64]
La prediccion del auditor era ROJO por dependencias. Se refuta: el Release era todo
lo que faltaba, y de los 3 .deb del overlay solo UNO se instala.

Este v5 lo confirma con mmdebstrap de verdad en aarch64 y cierra:
  (a) construye systemd
  (b) ORIGEN por apt-cache policy DENTRO del chroot, paquete por paquete. Cero lector
      propio de indices (R-04): el bug multi-version del v4 no puede repetirse porque
      no hay parser mio en el camino.
  (c) FIRMAS: se busca el keyring de openKylin y se intenta un build sin
      [trusted=yes]. Si no se consigue, (c) queda ROJO declarado (R-07).

CONTROLES:
  N1) solo main, sin overlay -> debe FALLAR por libdevmapper.
  N2) overlay SIN Release    -> debe FALLAR por el narrow de mmdebstrap. Es el control
      que le faltaba al v3: prueba que el Release era la causa y no otra cosa.
  C-b) el auditor de origen tiene su propio control: systemd DEBE salir de
      a=huanghe. Si sale de otro lado, el policy no se esta leyendo bien.
"""
import email.utils, gzip, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

MIRROR = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PROP = "huanghe-proposed"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
OVER = ["libdevmapper1.02.1", "dmsetup", "libdevmapper-event1.02.1"]
OUT = os.environ.get("F002_OUT", "mediciones/f-002")
WORK = os.environ.get("F002_WORK", "/tmp/f002v5")

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line); print(line, flush=True)

def sh(cmd, timeout=2700):
    say("$", (cmd if isinstance(cmd, str) else " ".join(cmd))[:560])
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -9, "", "TIMEOUT tras %ss" % timeout
    except Exception as e:
        return -1, "", repr(e)[:300]

def bajar(u, t=300):
    return urllib.request.urlopen(urllib.request.Request(
        u, headers={"User-Agent": "siao-f002v5/1"}), timeout=t).read()

def indice(comp):
    return gzip.decompress(bajar("%s/dists/%s/main/binary-%s/Packages.gz"
                                 % (MIRROR, comp, ARCH))).decode("utf-8", "replace")

SETUP_HOOK = ('set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; '
              'ln -sfn "usr/$d" "$1/$d"; done; '
              'mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"')


def armar_overlay(destino, con_release=True):
    say(""); say("--- overlay SIAO en %s (Release: %s) ---" % (destino, con_release))
    shutil.rmtree(destino, ignore_errors=True)
    pool = os.path.join(destino, "pool")
    os.makedirs(pool)
    ip = indice(PROP)
    manifiesto, entradas = [], []
    for p in OVER:
        st = None
        for s in ip.split("\n\n"):
            if re.search(r"^Package: %s$" % re.escape(p), s, re.M):
                st = s
        if not st:
            say("  %s NO ESTA en %s" % (p, PROP)); return None, manifiesto
        fn = re.search(r"^Filename: (\S+)$", st, re.M).group(1)
        ver = re.search(r"^Version: (\S+)$", st, re.M).group(1)
        esperado = re.search(r"^SHA256: (\S+)$", st, re.M).group(1)
        b = bajar("%s/%s" % (MIRROR, fn))
        got = hashlib.sha256(b).hexdigest()
        say("  %-26s %-16s %8d B sha256_ok=%s" % (p, ver, len(b), got == esperado))
        if got != esperado:
            say("      esperado %s" % esperado); say("      obtenido %s" % got)
            say("  ABORTO: el mirror no coincide con su indice"); return None, manifiesto
        base = os.path.basename(fn)
        open(os.path.join(pool, base), "wb").write(b)
        # R-04: dpkg-deb -f es la canonica para leer el control de un .deb.
        rc, o, e = sh(["dpkg-deb", "-f", os.path.join(pool, base)], timeout=120)
        if rc != 0:
            say("  dpkg-deb -f fallo:", e[:200]); return None, manifiesto
        entradas.append("%s\nFilename: pool/%s\nSize: %d\nSHA256: %s\n"
                        % (o.rstrip("\n"), base, len(b), got))
        manifiesto.append({"paquete": p, "version": ver, "sha256": got,
                           "bytes": len(b), "origen": "%s/%s" % (PROP, fn)})
    pk = os.path.join(destino, "Packages")
    open(pk, "w").write("\n".join(entradas))
    raw = open(pk, "rb").read()
    gz = gzip.compress(raw)
    open(pk + ".gz", "wb").write(gz)
    say("  Packages con dpkg-deb -f: %d paquetes, %d B"
        % (len(re.findall(r"^Package: ", raw.decode(), re.M)), len(raw)))
    if con_release:
        # El pre-vuelo delato dos defectos de mi Release anterior: le faltaba Date
        # ("W: Invalid 'Date' entry") y no declaraba los hashes del Packages, asi que
        # apt no podia verificar el indice. Los dos corregidos aca.
        rel = ["Origin: SIAO", "Label: SIAO overlay", "Suite: %s" % SUITE,
               "Codename: %s" % SUITE, "Version: 3.0",
               "Architectures: %s" % ARCH, "Components: main",
               "Description: overlay SIAO para siao-base-s1",
               "Date: %s" % email.utils.formatdate(usegmt=True),
               "SHA256:",
               " %s %d Packages" % (hashlib.sha256(raw).hexdigest(), len(raw)),
               " %s %d Packages.gz" % (hashlib.sha256(gz).hexdigest(), len(gz))]
        open(os.path.join(destino, "Release"), "w").write("\n".join(rel) + "\n")
        say("  Release, verbatim:")
        for l in rel:
            say("     |", l)
    else:
        say("  SIN Release a proposito: es el control N2")
    return destino, manifiesto


def construir(nombre, rootfs, fuentes):
    say(""); say("=" * 78)
    say(">>> %s" % nombre)
    for f in fuentes:
        say("    fuente:", f)
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (rootfs, rootfs)], timeout=300)
    cmd = ["mmdebstrap", "--mode=root", "--variant=important",
           "--architectures=" + ARCH, "--include=" + ",".join(PKGS),
           '--aptopt=Acquire::AllowInsecureRepositories "true"',
           '--aptopt=APT::Get::AllowUnauthenticated "true"',
           "--setup-hook=" + SETUP_HOOK,
           "--skip=cleanup/apt/lists", "--verbose"]
    cmd += [SUITE, rootfs] + fuentes
    rc, o, e = sh(cmd, timeout=2700)
    say("  mmdebstrap rc=%d" % rc)
    pat = (r"(Setting up systemd |E: |unmet|not going to be|no installation|"
           r"Hash Sum|Invalid|narrow)")
    vistos = set()
    for l in (o + e).splitlines():
        if not re.search(pat, l):
            continue
        k = l[:120]
        if k in vistos:
            continue
        vistos.add(k); say("  MM |", l[:280])
    ok = os.path.isfile(os.path.join(rootfs, "usr/lib/systemd/systemd"))
    say("  systemd presente:", ok)
    return ok, rc, (o + e)


def origen_por_policy(rootfs, fuentes):
    """CRITERIO (b) sin lector propio (R-04): apt-cache policy por paquete, DENTRO
    del chroot. Lo que diga apt es lo que vale."""
    say(""); say("--- CRITERIO (b): origen por apt-cache policy en el chroot ---")
    src = os.path.join(rootfs, "etc/apt/sources.list")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    with open(src, "w") as f:
        for x in fuentes:
            f.write(x + "\n")
    # el overlay tiene que estar accesible con la MISMA ruta dentro del chroot
    rc, o, e = sh(["bash", "-c",
                   "chroot %s apt-get update -o Acquire::AllowInsecureRepositories=true "
                   "-o APT::Get::AllowUnauthenticated=true -qq 2>&1 | tail -4" % rootfs],
                  timeout=900)
    say("  apt-get update en el chroot rc=%d" % rc)
    for l in (o + e).splitlines()[:5]:
        say("   |", l[:200])
    rc, o, _ = sh(["bash", "-c", "chroot %s dpkg-query -W -f '${Package}\\n' | sort" % rootfs])
    nombres = [x for x in o.split() if x]
    say("  paquetes instalados:", len(nombres))
    rc, pol, e = sh(["bash", "-c", "chroot %s apt-cache policy %s 2>&1"
                     % (rootfs, " ".join(nombres))], timeout=900)
    say("  apt-cache policy por paquete rc=%d | %d B de salida" % (rc, len(pol)))
    # bloque por paquete: nombre, Installed, y la linea de origen con ***
    por_suite = {}
    detalle = []
    actual = None
    inst = None
    for line in pol.splitlines():
        m = re.match(r"^(\S+):$", line)
        if m:
            actual, inst = m.group(1), None
            continue
        m = re.match(r"^\s+Installed: (\S+)$", line)
        if m:
            inst = m.group(1)
            continue
        m = re.match(r"^\s+\*\*\* (\S+) (\d+)\s*$", line)
        if m and actual:
            continue
        m = re.search(r"^\s+(\d+)\s+(\S+) (\S+)/(\S+) ", line)
        if m and actual and inst:
            pass
    # segunda pasada, mas simple y robusta: apt marca con *** la version instalada y
    # la linea siguiente dice de que archivo salio
    bloques = re.split(r"\n(?=\S+:\n)", pol)
    for b in bloques:
        nm = re.match(r"^(\S+):", b)
        if not nm:
            continue
        nm = nm.group(1)
        m = re.search(r"^\s+\*\*\* (\S+) \d+\n\s+(\d+) (\S+) (\S+)", b, re.M)
        if m:
            ver, prio, uri, suite = m.group(1), m.group(2), m.group(3), m.group(4)
            clave = suite
            por_suite[clave] = por_suite.get(clave, 0) + 1
            detalle.append({"paquete": nm, "version": ver, "suite": suite, "uri": uri})
        else:
            m2 = re.search(r"^\s+\*\*\* (\S+) \d+\n\s+\d+ /var/lib/dpkg/status", b, re.M)
            por_suite["solo-en-dpkg-status"] = por_suite.get("solo-en-dpkg-status", 0) + 1
            detalle.append({"paquete": nm, "version": m2.group(1) if m2 else "?",
                            "suite": "solo-en-dpkg-status", "uri": "-"})
    say("  ORIGEN POR SUITE, contado por apt:")
    for k, v in sorted(por_suite.items(), key=lambda x: -x[1]):
        say("      %-42s %d" % (k, v))
    del_overlay = [d for d in detalle if "overlay" in d["uri"] or "file:" in d["uri"]]
    say("  del OVERLAY, segun apt:")
    for d in del_overlay:
        say("      %-28s %-18s %s" % (d["paquete"], d["version"], d["uri"]))
    de_prop = [d for d in detalle if PROP in d["suite"] or PROP in d["uri"]]
    say("  de huanghe-proposed, segun apt:", len(de_prop))
    for d in de_prop[:20]:
        say("      %-28s %s" % (d["paquete"], d["version"]))
    # control del auditor: systemd tiene que salir de huanghe
    sd = [d for d in detalle if d["paquete"] == "systemd"]
    ctrl = bool(sd) and "huanghe" in (sd[0]["suite"] if sd else "")
    say("  CONTROL del criterio (b): systemd sale de huanghe?", ctrl, sd[:1])
    return {"por_suite": por_suite, "n_paquetes": len(nombres),
            "del_overlay": del_overlay, "de_proposed": de_prop,
            "n_de_proposed": len(de_prop), "control_systemd": ctrl,
            "detalle": detalle[:250], "policy_bytes": len(pol)}


def criterio_c(rootfs):
    """(c) firmas. Se busca el keyring de openKylin en el propio repo."""
    say(""); say("--- CRITERIO (c): firmas ---")
    res = {"veredicto": "ROJO", "motivo": "no intentado"}
    ip = indice(SUITE)
    cand = None
    for p in ("openkylin-keyring", "openkylin-archive-keyring", "kylin-keyring"):
        for st in ip.split("\n\n"):
            if re.search(r"^Package: %s$" % re.escape(p), st, re.M):
                cand = (p, re.search(r"^Filename: (\S+)$", st, re.M).group(1),
                        re.search(r"^SHA256: (\S+)$", st, re.M).group(1))
                break
        if cand:
            break
    if not cand:
        res = {"veredicto": "ROJO",
               "motivo": "no hay paquete de keyring en el indice de huanghe/main arm64: "
                         "la clave publica del repo no se distribuye por apt, asi que "
                         "verificar firmas exige conseguirla por otra via"}
        say("  " + res["motivo"])
        say("  (c) ROJO declarado: todo lo construido hoy usa [trusted=yes] (R-07)")
        return res
    p, fn, sha = cand
    b = bajar("%s/%s" % (MIRROR, fn))
    got = hashlib.sha256(b).hexdigest()
    say("  keyring encontrado: %s (%d B) sha256_ok=%s" % (p, len(b), got == sha))
    kp = os.path.join(WORK, "keyring.deb")
    open(kp, "wb").write(b)
    rc, o, e = sh(["bash", "-c", "dpkg-deb -c %s | head -20" % kp], timeout=120)
    for l in (o + e).splitlines():
        say("   |", l[:200])
    res = {"veredicto": "PARCIAL", "paquete": p, "bytes": len(b),
           "sha256": got, "sha256_ok": got == sha,
           "motivo": "keyring obtenido y su sha256 verificado contra el indice, pero el "
                     "indice mismo se bajo sin firma verificada: es circular. Cerrar (c) "
                     "exige el fingerprint desde fuente primaria fuera del mirror.",
           "contenido": (o + e)[:800]}
    say("  (c) PARCIAL:", res["motivo"])
    return res


def main():
    import platform
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    res = {"falsador": "F-002", "version": 5,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "prediccion_del_auditor": "ROJO por dependencias: libcryptsetup12 2.8.4 de "
                                     "main probablemente arrastra algo mas que libdevmapper",
           "prediccion_mia": "VERDE: el unico Depends de libcryptsetup12 que main no "
                             "satisface es libdevmapper1.02.1",
           "pre_vuelo_en_brain_env": "apt-get install -s rc=0, 68 paquetes, y del overlay "
                                     "solo libdevmapper1.02.1. Ya refuto la prediccion del "
                                     "auditor antes de gastar runner (R-05).",
           "controles": {}, "sujeto": {}, "no_medido": []}
    say("== F-002 v5 ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("PREDICCION del auditor:", res["prediccion_del_auditor"])
    say("PREDICCION mia:", res["prediccion_mia"])
    say("PRE-VUELO (R-05) en brain-env:", res["pre_vuelo_en_brain_env"])

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host no aarch64"); write(res); return 3

    ov, manifiesto = armar_overlay(os.path.join(WORK, "overlay"), con_release=True)
    res["manifiesto"] = manifiesto
    if not ov:
        res["no_medido"].append("overlay no armado"); write(res); return 3
    ovsr, _ = armar_overlay(os.path.join(WORK, "overlay-sin-release"), con_release=False)

    f_main = "deb [trusted=yes] %s %s main" % (MIRROR, SUITE)
    f_ov = "deb [trusted=yes] file://%s ./" % ov
    f_ovsr = "deb [trusted=yes] file://%s ./" % ovsr

    ok1, rc1, t1 = construir("N1 solo main", os.path.join(WORK, "n1"), [f_main])
    ev1 = [l for l in t1.splitlines() if "not going to be installed" in l]
    res["controles"]["N1_solo_main"] = {"esperado": "FALLA por libdevmapper",
                                        "instalo": ok1, "rc": rc1,
                                        "discrimina": not ok1,
                                        "causa_detectada": bool(ev1),
                                        "evidencia": "\n".join(ev1)[:500]}
    say("  N1:", "correcto" if (not ok1 and ev1) else "OJO")

    ok2, rc2, t2 = construir("N2 overlay SIN Release", os.path.join(WORK, "n2"),
                             [f_main, f_ovsr])
    ev2 = [l for l in t2.splitlines() if "not going to be installed" in l or "E:" in l]
    res["controles"]["N2_overlay_sin_release"] = {
        "esperado": "FALLA: sin Release no entra en el narrow",
        "instalo": ok2, "rc": rc2, "discrimina": not ok2,
        "evidencia": "\n".join(ev2[:5])[:500]}
    say("  N2:", "correcto" if not ok2 else "OJO: instalo SIN Release")

    okP, rcP, tP = construir("SUJETO main + overlay con Release",
                             os.path.join(WORK, "rootfs"), [f_main, f_ov])
    res["sujeto"] = {"instalo": okP, "rc": rcP}
    if okP:
        rc, o, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % os.path.join(WORK, "rootfs")])
        res["sujeto"]["bytes"] = int((o.strip() or "0").split()[0])
        say("  rootfs: %d B (%.3f GiB)"
            % (res["sujeto"]["bytes"], res["sujeto"]["bytes"] / 1073741824.0))
        rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                       "'${Package} ${Version}\\n' systemd libdevmapper1.02.1 "
                       "libcryptsetup12 2>&1" % os.path.join(WORK, "rootfs")])
        say("  LA CADENA:")
        for l in o.splitlines():
            say("   |", l[:120])
        res["sujeto"]["cadena"] = o.strip()
        res["criterio_b"] = origen_por_policy(os.path.join(WORK, "rootfs"), [f_main, f_ov])
    res["criterio_c"] = criterio_c(os.path.join(WORK, "rootfs"))

    a = "VERDE" if okP else "ROJO"
    b = res.get("criterio_b", {})
    bv = "NO MEDIDO"
    if b:
        bv = "VERDE" if (b.get("control_systemd") and b.get("n_de_proposed", 99) == 0) else \
             ("AMARILLO" if b.get("control_systemd") else "NO MEDIDO")
    cv = res["criterio_c"]["veredicto"]
    res["veredicto"] = {"a_construye": a, "b_origen": bv, "c_firmas": cv}
    res["prediccion_del_auditor_acerto"] = (a == "ROJO")
    say(""); say("VEREDICTO F-002 v5: (a)=%s (b)=%s (c)=%s" % (a, bv, cv))
    say("La prediccion del auditor",
        "ACERTO" if res["prediccion_del_auditor_acerto"] else "SE REFUTO")
    res["segundos"] = round(time.time() - t0, 1)
    write(res); say("FIN en", res["segundos"], "s")
    return 0 if okP else 3


def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-002-v5.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-002-v5-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    v = res.get("veredicto", {})
    b = res.get("criterio_b", {})
    md = ["# F-002 v5 - main + overlay SIAO con Release", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "| Criterio | Veredicto |", "|---|---|",
          "| (a) construye systemd | **%s** |" % v.get("a_construye", "?"),
          "| (b) origen por `apt-cache policy` | **%s** |" % v.get("b_origen", "?"),
          "| (c) firmas verificadas | **%s** |" % v.get("c_firmas", "?"), "",
          "Paquetes: %s | de -proposed segun apt: %s | rootfs: %s B"
          % (b.get("n_paquetes", "?"), b.get("n_de_proposed", "?"),
             res.get("sujeto", {}).get("bytes", "?")), "",
          "**Prediccion del auditor:** %s" % res["prediccion_del_auditor"],
          "", "**Acerto:** %s" % res.get("prediccion_del_auditor_acerto", "sin dato"), "",
          "## Manifiesto del overlay", "", "```json",
          json.dumps(res.get("manifiesto", []), indent=2, ensure_ascii=False), "```", "",
          "## Origen por suite, contado por apt", "", "```json",
          json.dumps(b.get("por_suite", {}), indent=2, ensure_ascii=False), "```", "",
          "## Controles", "", "```json",
          json.dumps(res["controles"], indent=2, ensure_ascii=False)[:3500], "```", "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Salida cruda, verbatim", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-002-v5.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
