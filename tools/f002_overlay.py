#!/usr/bin/env python3
"""
F-002 v3 - rootfs de openKylin arm64 con OVERLAY APT PROPIO de SIAO.

Por que v3, y es un cambio de arquitectura, no un parche:
el v2 midio que `huanghe/main` y `huanghe-proposed` NO son un conjunto
consistente. `login.defs` existe SOLO en -proposed y el `passwd` de ahi lo
declara en Depends; en main ese paquete NO EXISTE. Ningun pin puede arreglarlo,
porque el defecto no es que version gana sino que los dos componentes describen
universos distintos de paquetes.

La via correcta (la version fuerte del auditor): -proposed NUNCA entra como
fuente. Se bajan SOLO los .deb que faltan, se verifica su sha256 contra el indice
oficial, se arma un repo local con dpkg-scanpackages, y el rootfs se construye con
main + ese overlay.

CONTROLES:
  N1) solo main                 -> debe FALLAR por libdevmapper (confirmado en v2)
  N2) main + proposed completo  -> debe FALLAR por login.defs (el muro del v2)
  N3) overlay con un sha256 ROTO a proposito -> apt debe RECHAZARLO.
      Este es el control que le falta a casi todos los repos caseros: si apt acepta
      un hash mentido, el overlay no verifica nada y su verde no vale.
  P)  main + overlay            -> el sujeto

El criterio (b) del auditor se vuelve trivial: si -proposed no esta en las fuentes,
nada puede venir de ahi salvo lo que YO puse en el overlay, y eso esta enumerado
con su hash en la salida cruda.
"""
import gzip, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

MIRROR = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PROP = "huanghe-proposed"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
# Lo que el overlay va a servir. Los tres primeros salen del source lvm2 y son la
# cadena que rompia; login.defs es el muro que aparecio despues.
OVERLAY_PKGS = ["libdevmapper1.02.1", "dmsetup", "libdevmapper-event1.02.1"]
OUT = os.environ.get("F002_OUT", "mediciones/f-002")
WORK = os.environ.get("F002_WORK", "/tmp/f002v3")

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line); print(line, flush=True)

def sh(cmd, timeout=2700):
    say("$", (cmd if isinstance(cmd, str) else " ".join(cmd))[:600])
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -9, "", "TIMEOUT tras %ss" % timeout
    except Exception as e:
        return -1, "", repr(e)[:300]

def bajar(url, timeout=300):
    req = urllib.request.Request(url, headers={"User-Agent": "siao-overlay/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def indice(comp):
    d = bajar("%s/dists/%s/main/binary-%s/Packages.gz" % (MIRROR, comp, ARCH))
    return gzip.decompress(d).decode("utf-8", "replace")

def stanza(idx, pkg):
    for st in idx.split("\n\n"):
        if re.search(r"^Package: %s$" % re.escape(pkg), st, re.M):
            return st
    return None

# El setup-hook que el v2 probo necesario con su control N2: base-files trae /bin
# y /lib como directorios REALES, y el PT_INTERP de sus binarios apunta a /lib.
SETUP_HOOK = ('set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; '
              'ln -sfn "usr/$d" "$1/$d"; done; '
              'mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"')


def armar_overlay(destino, romper_hash=False):
    """Baja los .deb de -proposed, verifica sha256 y arma un repo apt local."""
    say(""); say("--- armando el overlay de SIAO en %s (hash roto: %s) ---"
                % (destino, romper_hash))
    pool = os.path.join(destino, "pool")
    shutil.rmtree(destino, ignore_errors=True)
    os.makedirs(pool, exist_ok=True)
    ip = indice(PROP)
    manifiesto = []
    for pkg in OVERLAY_PKGS:
        st = stanza(ip, pkg)
        if not st:
            say("  %s NO ESTA en %s" % (pkg, PROP)); return None, manifiesto
        fn = re.search(r"^Filename: (\S+)$", st, re.M).group(1)
        ver = re.search(r"^Version: (\S+)$", st, re.M).group(1)
        esperado = re.search(r"^SHA256: (\S+)$", st, re.M).group(1)
        blob = bajar("%s/%s" % (MIRROR, fn))
        got = hashlib.sha256(blob).hexdigest()
        ok = (got == esperado)
        say("  %-26s %-18s %9d B  sha256_ok=%s" % (pkg, ver, len(blob), ok))
        say("      esperado %s" % esperado)
        say("      obtenido %s" % got)
        if not ok:
            say("  ABORTO: el mirror no coincide con su propio indice")
            return None, manifiesto
        if romper_hash:
            blob = blob + b"\x00"      # un byte de mas: el hash del indice ya no vale
            say("      *** le agrego un byte a proposito para el control N3 ***")
        open(os.path.join(pool, os.path.basename(fn)), "wb").write(blob)
        manifiesto.append({"paquete": pkg, "version": ver, "sha256_oficial": esperado,
                           "bytes": len(blob), "origen": "%s/%s" % (PROP, fn)})
    rc, o, e = sh(["bash", "-c",
                   "cd %s && dpkg-scanpackages --multiversion pool > Packages 2>/dev/null "
                   "&& gzip -9c Packages > Packages.gz && wc -l < Packages" % destino])
    say("  dpkg-scanpackages rc=%d | lineas del Packages: %s" % (rc, o.strip()))
    if rc != 0:
        say("  scanpackages fallo:", e.strip()[:300]); return None, manifiesto
    if romper_hash:
        # Reescribo el Packages con el sha256 ORIGINAL: apt va a bajar el .deb de
        # 1 byte mas y el hash no va a coincidir. Eso es lo que N3 quiere probar.
        p = os.path.join(destino, "Packages")
        txt = open(p).read()
        for m in manifiesto:
            txt = re.sub(r"(SHA256: )\S+", r"\g<1>" + m["sha256_oficial"], txt, count=1)
        open(p, "w").write(txt)
        sh(["bash", "-c", "cd %s && gzip -9fc Packages > Packages.gz" % destino])
        say("      *** reescribi el Packages con los sha256 oficiales ***")
    rc, o, _ = sh(["bash", "-c", "grep -c '^Package: ' %s/Packages" % destino])
    say("  overlay listo: %s paquetes servidos" % o.strip())
    return destino, manifiesto


def construir(nombre, rootfs, fuentes, con_hook=True):
    say(""); say("=" * 78)
    say(">>> %s" % nombre)
    for f in fuentes:
        say("    fuente:", f)
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (rootfs, rootfs)], timeout=300)
    cmd = ["mmdebstrap", "--mode=root", "--variant=important",
           "--architectures=" + ARCH, "--include=" + ",".join(PKGS),
           '--aptopt=Acquire::AllowInsecureRepositories "true"',
           '--aptopt=APT::Get::AllowUnauthenticated "true"',
           "--verbose"]
    if con_hook:
        cmd.append("--setup-hook=" + SETUP_HOOK)
    cmd += [SUITE, rootfs] + fuentes
    rc, o, e = sh(cmd, timeout=2700)
    say("  mmdebstrap rc=%d" % rc)
    pat = (r"(No such file|unmet|broken|E:|W: |Errors were|no installation candidate|"
           r"Hash Sum mismatch|not going to be|Setting up systemd)")
    vistos, salida = set(), []
    for l in (o + e).splitlines():
        if not re.search(pat, l):
            continue
        k = re.sub(r"[0-9a-f]{8,}", "HASH", l)[:150]
        if k in vistos:
            continue
        vistos.add(k); salida.append(l)
    for l in salida[-40:]:
        say("  MM |", l[:300])
    ok = (rc == 0 and os.path.isfile(os.path.join(rootfs, "usr/lib/systemd/systemd")))
    return ok, rc, (o + e)


def auditar(rootfs, manifiesto):
    res = {}
    rc, o, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % rootfs])
    res["bytes"] = int((o.strip() or "0").split()[0])
    say("  rootfs: %d B (%.3f GiB)" % (res["bytes"], res["bytes"] / 1073741824.0))
    rc, o, _ = sh(["bash", "-c", "cat %s/etc/os-release | head -4" % rootfs])
    res["os_release"] = o.strip()
    for l in o.splitlines():
        say("   |", l)
    rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                   "'${Package} ${Version}\\n' systemd libcryptsetup12 "
                   "libdevmapper1.02.1 base-files passwd 2>&1" % rootfs])
    say("  LA CADENA, instalada:")
    for l in o.splitlines():
        say("   |", l[:140])
    res["cadena"] = o.strip()
    rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                                 "'${Package}\\n' | wc -l" % rootfs])
    res["paquetes_instalados"] = int((o.strip() or "0").split()[0])
    say("  paquetes instalados:", res["paquetes_instalados"])

    # criterio (b): con -proposed fuera de las fuentes, lo unico que puede venir de
    # ahi es lo que yo puse en el overlay. Se verifica version por version.
    im = {}
    for st in indice(SUITE).split("\n\n"):
        m = re.search(r"^Package: (\S+)$", st, re.M)
        v = re.search(r"^Version: (\S+)$", st, re.M)
        if m and v:
            im.setdefault(m.group(1), v.group(1))
    esperados = {m["paquete"]: m["version"] for m in manifiesto}
    rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                                 "'${Package} ${Version}\\n' 2>/dev/null" % rootfs])
    fuera_de_main, del_overlay = [], []
    for line in o.splitlines():
        p = line.split()
        if len(p) != 2:
            continue
        nm, ver = p
        if nm in esperados:
            del_overlay.append("%s %s (overlay esperaba %s)" % (nm, ver, esperados[nm]))
        elif nm in im and ver != im[nm]:
            fuera_de_main.append("%s %s (main tiene %s)" % (nm, ver, im[nm]))
    say("  >>> del OVERLAY:")
    for x in del_overlay:
        say("      ", x)
    say("  >>> instalados con version que NO es la de main (deberia estar vacio):")
    for x in fuera_de_main[:20]:
        say("      ", x)
    res["del_overlay"] = del_overlay
    res["fuera_de_main"] = fuera_de_main
    res["criterio_b"] = "VERDE" if not fuera_de_main else "ROJO"
    say("  CRITERIO (b):", res["criterio_b"])
    return res


def main():
    import platform
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    res = {"falsador": "F-002", "version": 3,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "por_que_v3": ("el v2 midio que main y -proposed no son un conjunto "
                          "consistente: login.defs existe solo en -proposed y el passwd "
                          "de ahi lo pide. Ningun pin arregla eso. -proposed NO entra "
                          "como fuente: se sirve un overlay propio con sha256 verificado."),
           "overlay_pkgs": OVERLAY_PKGS, "controles": {}, "sujeto": {}, "no_medido": []}
    say("== F-002 v3 (overlay propio) ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("POR QUE v3:", res["por_que_v3"])

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host no aarch64")
        say("ABORTO: exige aarch64"); write(res); return 3

    ov, manifiesto = armar_overlay(os.path.join(WORK, "overlay"))
    res["manifiesto"] = manifiesto
    if not ov:
        res["no_medido"].append("el overlay no se pudo armar")
        say("ABORTO: sin overlay no hay sujeto"); write(res); return 3

    f_main = "deb [trusted=yes] %s %s main" % (MIRROR, SUITE)
    f_prop = "deb [trusted=yes] %s %s main" % (MIRROR, PROP)
    f_ov = "deb [trusted=yes] file://%s ./" % ov

    # N1: solo main
    ok1, rc1, t1 = construir("N1-solo-main", os.path.join(WORK, "n1"), [f_main])
    ev1 = [l for l in t1.splitlines() if "not going to be installed" in l or "unmet" in l]
    res["controles"]["N1_solo_main"] = {"esperado": "FALLA por libdevmapper",
                                        "instalo": ok1, "rc": rc1,
                                        "discrimina": not ok1,
                                        "evidencia": "\n".join(ev1)[:600]}
    say("  N1:", "correcto, fallo" if not ok1 else "OJO: instalo con solo main")

    # N2: main + proposed (el muro del v2)
    ok2, rc2, t2 = construir("N2-main-mas-proposed", os.path.join(WORK, "n2"),
                             [f_main, f_prop])
    ev2 = [l for l in t2.splitlines() if "no installation candidate" in l or "E:" in l]
    res["controles"]["N2_main_mas_proposed"] = {
        "esperado": "FALLA por login.defs", "instalo": ok2, "rc": rc2,
        "discrimina": not ok2, "evidencia": "\n".join(ev2[:6])[:600]}
    say("  N2:", "correcto, fallo" if not ok2 else "OJO: instalo con proposed entero")

    # N3: el overlay con hash roto -> apt debe rechazarlo
    ovr, _ = armar_overlay(os.path.join(WORK, "overlay-roto"), romper_hash=True)
    if ovr:
        f_ovr = "deb [trusted=yes] file://%s ./" % ovr
        ok3, rc3, t3 = construir("N3-overlay-con-hash-roto", os.path.join(WORK, "n3"),
                                 [f_main, f_ovr])
        mismatch = [l for l in t3.splitlines()
                    if "Hash Sum mismatch" in l or "mismatch" in l.lower()]
        res["controles"]["N3_overlay_hash_roto"] = {
            "esperado": "apt RECHAZA el .deb por hash", "instalo": ok3, "rc": rc3,
            "discrimina": not ok3, "hash_mismatch_detectado": bool(mismatch),
            "evidencia": "\n".join(mismatch[:5])[:600]}
        say("  N3:", "correcto, apt lo rechazo" if not ok3
            else "OJO: apt ACEPTO un hash mentido: mi overlay no verifica nada")
        if mismatch:
            say("  N3 verbatim:", mismatch[0][:220])

    # P: el sujeto
    okP, rcP, tP = construir("SUJETO-main-mas-overlay", os.path.join(WORK, "rootfs"),
                             [f_main, f_ov])
    res["sujeto"] = {"instalo": okP, "rc": rcP}
    if okP:
        res["sujeto"].update(auditar(os.path.join(WORK, "rootfs"), manifiesto))
        res["veredicto"] = ("VERDE" if res["sujeto"].get("criterio_b") == "VERDE"
                            else "AMARILLO")
    else:
        res["veredicto"] = "ROJO"
        ev = [l for l in tP.splitlines()
              if re.search(r"(No such file|unmet|broken|E:|no installation candidate)", l)]
        res["sujeto"]["evidencia"] = "\n".join(ev[:12])[:1500]
    say(""); say("VEREDICTO F-002 v3:", res["veredicto"])
    res["segundos"] = round(time.time() - t0, 1)
    write(res)
    say("FIN en", res["segundos"], "s")
    return 0 if okP else 3


def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-002-v3.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-002-v3-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    s = res.get("sujeto", {})
    md = ["# F-002 v3 - rootfs openKylin arm64 con overlay apt propio", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "| Criterio | Veredicto |", "|---|---|",
          "| (a) instala systemd | **%s** |" % ("VERDE" if s.get("instalo") else "ROJO"),
          "| (b) nada fuera de main + overlay | **%s** |" % s.get("criterio_b", "NO MEDIDO"),
          "| **F-002 v3** | **%s** |" % res.get("veredicto", "NO MEDIDO"), "",
          "Rootfs: %s B (%.3f GiB) | paquetes: %s"
          % (s.get("bytes", "?"), (s.get("bytes") or 0) / 1073741824.0,
             s.get("paquetes_instalados", "?")), "",
          "## Manifiesto del overlay", "", "```json",
          json.dumps(res.get("manifiesto", []), indent=2, ensure_ascii=False), "```", "",
          "## Controles", "", "```json",
          json.dumps(res["controles"], indent=2, ensure_ascii=False)[:4500], "```", "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Salida cruda, verbatim", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-002-v3.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
