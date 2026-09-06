#!/usr/bin/env python3
"""
F-002 v6 - overlay NO FLAT vs FLAT, con mmdebstrap de verdad.

POR QUE: el v5 fallo y yo culpe al Release. Le puse Release y fallo igual, asi que mi
diagnostico era falso y mi control N2 no discriminaba (daba el mismo resultado que el
sujeto). La sospecha que quedo abierta era el LAYOUT: un repo flat no tiene componente.

PRE-VUELO R-05 en brain-env, ya corrido, y acota la sospecha a la mitad:
  no flat -> apt-cache policy c='main' | apt-get install -s rc=0 | 68 paquetes
  flat    -> apt-cache policy c=''     | apt-get install -s rc=0 | 68 paquetes
El componente cambia, pero APT RESUELVE IGUAL en los dos. Asi que si mmdebstrap falla
con los dos, la causa NO es el flat.

mmdebstrap NO esta en brain-env (medido: which -> None), asi que el constructor solo
se puede medir aca.

EL CONTROL DISCRIMINA POR CONSTRUCCION: los dos overlays salen de los MISMOS 3 .deb,
con el MISMO hook y el MISMO Release (salvo Components, que un flat no puede tener).
La unica variable es el layout.
  S) no flat: dists/huanghe/main/binary-arm64/ + pool/main/
  N) flat:    Packages en la raiz + pool/
Si S pasa y N falla -> la causa es el layout, medida.
Si los dos fallan  -> mi sospecha es FALSA y lo digo.
Si los dos pasan   -> el v5 fallaba por otra cosa que ya no esta, y hay que buscarla.
"""
import email.utils, gzip, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

M = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PROP = "huanghe-proposed"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
OVER = ["libdevmapper1.02.1", "dmsetup", "libdevmapper-event1.02.1"]
OUT = os.environ.get("F002_OUT", "mediciones/f-002")
WORK = os.environ.get("F002_WORK", "/tmp/f002v6")

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line); print(line, flush=True)

def sh(c, t=2700):
    say("$", (c if isinstance(c, str) else " ".join(c))[:420])
    try:
        r = subprocess.run(c, shell=isinstance(c, str), capture_output=True,
                           text=True, timeout=t)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -9, "", "TIMEOUT tras %ss" % t
    except Exception as e:
        return -1, "", repr(e)[:300]

def bajar(u, t=300):
    return urllib.request.urlopen(urllib.request.Request(
        u, headers={"User-Agent": "siao-f002v6/1"}), timeout=t).read()

HOOK = ('set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; '
        'ln -sfn "usr/$d" "$1/$d"; done; '
        'mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"')


def traer_debs():
    ip = gzip.decompress(bajar("%s/dists/%s/main/binary-%s/Packages.gz"
                               % (M, PROP, ARCH))).decode("utf-8", "replace")
    os.makedirs(WORK + "/debs", exist_ok=True)
    debs, manifiesto = [], []
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
            say("  ABORTO: sha256 no coincide"); return None, manifiesto
        d = WORK + "/debs/" + os.path.basename(fn)
        open(d, "wb").write(b)
        debs.append(d)
        manifiesto.append({"paquete": p, "version": ver, "sha256": got, "bytes": len(b)})
    return debs, manifiesto


def packages_de(debs, poolrel):
    ent = []
    for d in debs:
        rc, o, e = sh(["dpkg-deb", "-f", d], 120)
        if rc != 0:
            return None
        b = open(d, "rb").read()
        ent.append("%s\nFilename: %s/%s\nSize: %d\nSHA256: %s\n"
                   % (o.rstrip("\n"), poolrel, os.path.basename(d), len(b),
                      hashlib.sha256(b).hexdigest()))
    return "\n".join(ent).encode()


def escribir_release(root, raws, comp=None):
    L = ["Origin: SIAO", "Label: SIAO overlay", "Suite: %s" % SUITE,
         "Codename: %s" % SUITE, "Version: 3.0", "Architectures: %s" % ARCH,
         "Date: " + email.utils.formatdate(usegmt=True)]
    if comp:
        L.append("Components: " + comp)
    L.append("SHA256:")
    for rel, data in raws:
        L.append(" %s %d %s" % (hashlib.sha256(data).hexdigest(), len(data), rel))
    open(root + "/Release", "w").write("\n".join(L) + "\n")
    return L


def armar_nonflat(debs):
    say(""); say("--- overlay NO FLAT (dists/huanghe/main/binary-arm64) ---")
    r = WORK + "/nonflat"
    shutil.rmtree(r, ignore_errors=True)
    os.makedirs(r + "/dists/%s/main/binary-%s" % (SUITE, ARCH))
    os.makedirs(r + "/pool/main")
    for d in debs:
        shutil.copy2(d, r + "/pool/main/")
    raw = packages_de(debs, "pool/main")
    if raw is None:
        return None
    gz = gzip.compress(raw)
    base = r + "/dists/%s/main/binary-%s" % (SUITE, ARCH)
    open(base + "/Packages", "wb").write(raw)
    open(base + "/Packages.gz", "wb").write(gz)
    L = escribir_release(r + "/dists/" + SUITE,
                         [("main/binary-%s/Packages" % ARCH, raw),
                          ("main/binary-%s/Packages.gz" % ARCH, gz)], "main")
    for l in L:
        say("   |", l)
    rc, o, _ = sh(["bash", "-c", "find %s -type f | sort" % r])
    say("  arbol del overlay:")
    for l in o.splitlines():
        say("   ", l.replace(r, "<overlay>"))
    return r


def armar_flat(debs):
    say(""); say("--- overlay FLAT (el del v5, control) ---")
    r = WORK + "/flat"
    shutil.rmtree(r, ignore_errors=True)
    os.makedirs(r + "/pool")
    for d in debs:
        shutil.copy2(d, r + "/pool/")
    raw = packages_de(debs, "pool")
    if raw is None:
        return None
    gz = gzip.compress(raw)
    open(r + "/Packages", "wb").write(raw)
    open(r + "/Packages.gz", "wb").write(gz)
    escribir_release(r, [("Packages", raw), ("Packages.gz", gz)])
    say("  flat armado, sin Components (un flat no puede tenerlo)")
    return r


def construir(nombre, root, fuentes):
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
    rc, o, e = sh(cmd, 2700)
    say("  mmdebstrap rc=%d" % rc)
    pat = (r"(Setting up systemd |unmet|^E: |not going to be|narrow|Release|"
           r"no installation|Hash Sum)")
    vistos = set()
    for l in (o + e).splitlines():
        if not re.search(pat, l):
            continue
        k = l[:110]
        if k in vistos:
            continue
        vistos.add(k); say("  MM |", l[:300])
    ok = os.path.isfile(root + "/usr/lib/systemd/systemd")
    say("  systemd presente:", ok)
    return ok, rc, (o + e)


def origen(root, fuentes):
    """CRITERIO (b) sin lector propio (R-04): apt-cache policy en el chroot."""
    say(""); say("--- CRITERIO (b): apt-cache policy dentro del chroot ---")
    src = root + "/etc/apt/sources.list"
    os.makedirs(os.path.dirname(src), exist_ok=True)
    open(src, "w").write("\n".join(fuentes) + "\n")
    sh(["bash", "-c", "chroot %s apt-get update -qq "
        "-o Acquire::AllowInsecureRepositories=true "
        "-o APT::Get::AllowUnauthenticated=true 2>&1 | tail -3" % root], 900)
    rc, o, _ = sh(["bash", "-c", "chroot %s apt-cache policy 2>&1" % root], 300)
    say("  apt-cache policy (fuentes que ve el rootfs):")
    for l in o.splitlines():
        say("   POL |", l.strip()[:190])
    rc, nm, _ = sh(["bash", "-c", "chroot %s dpkg-query -W -f '${Package}\\n' | sort" % root])
    nombres = [x for x in nm.split() if x]
    rc, pol, _ = sh(["bash", "-c", "chroot %s apt-cache policy %s 2>&1"
                     % (root, " ".join(nombres))], 900)
    por_origen, detalle = {}, []
    for b in re.split(r"\n(?=\S+:\n)", pol):
        m = re.match(r"^(\S+):", b)
        if not m:
            continue
        p = m.group(1)
        mm = re.search(r"^\s+\*\*\* (\S+) \d+\n\s+\d+ (\S+) (\S+)", b, re.M)
        if mm:
            ver, uri, suite = mm.group(1), mm.group(2), mm.group(3)
            clave = ("OVERLAY" if uri.startswith("file:") else suite)
            por_origen[clave] = por_origen.get(clave, 0) + 1
            detalle.append({"paquete": p, "version": ver, "uri": uri, "suite": suite})
        else:
            por_origen["solo-en-dpkg-status"] = por_origen.get("solo-en-dpkg-status", 0) + 1
    say("  ORIGEN, contado por apt:")
    for k, v in sorted(por_origen.items(), key=lambda x: -x[1]):
        say("      %-42s %d" % (k, v))
    ov = [d for d in detalle if d["uri"].startswith("file:")]
    say("  del OVERLAY, segun apt:")
    for d in ov:
        say("      %-28s %s" % (d["paquete"], d["version"]))
    prop = [d for d in detalle if PROP in d["suite"] or PROP in d["uri"]]
    say("  de %s directo: %d (deberia ser 0: no esta en las fuentes)" % (PROP, len(prop)))
    sd = [d for d in detalle if d["paquete"] == "systemd"]
    ctrl = bool(sd) and (SUITE in sd[0]["suite"])
    say("  CONTROL de (b): systemd sale de huanghe?", ctrl, sd[:1])
    return {"n_paquetes": len(nombres), "por_origen": por_origen,
            "del_overlay": ov, "n_de_proposed": len(prop),
            "control_systemd": ctrl, "detalle": detalle[:250]}


def main():
    import platform
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    res = {"falsador": "F-002", "version": 6,
           "pregunta": "un overlay NO FLAT entra donde el FLAT no entraba?",
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "pre_vuelo": ("En brain-env: no flat -> c='main', flat -> c=''; pero "
                         "apt-get install -s dio rc=0 y 68 paquetes en LOS DOS. Asi que "
                         "el componente cambia y el resolvedor no se queja: si mmdebstrap "
                         "falla con los dos, la causa NO es el layout. mmdebstrap no esta "
                         "en brain-env (which -> None), asi que el constructor solo se "
                         "puede medir en el runner."),
           "prediccion": ("Predigo que el NO FLAT pasa y el FLAT falla. Si los dos fallan, "
                          "mi sospecha del layout es falsa y hay que buscar en mmdebstrap."),
           "controles": {}, "sujeto": {}, "no_medido": []}
    say("== F-002 v6: overlay NO FLAT ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("PRE-VUELO (R-05):", res["pre_vuelo"])
    say("PREDICCION registrada antes de correr:", res["prediccion"])

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host no aarch64"); write(res); return 3

    say(""); say("--- bajando los 3 .deb ---")
    debs, manifiesto = traer_debs()
    res["manifiesto"] = manifiesto
    if not debs:
        res["no_medido"].append("no pude bajar los .deb"); write(res); return 3

    nf = armar_nonflat(debs)
    fl = armar_flat(debs)
    if not nf or not fl:
        res["no_medido"].append("no pude armar los overlays"); write(res); return 3

    fmain = "deb [trusted=yes] %s %s main" % (M, SUITE)
    f_nf = "deb [trusted=yes] file://%s %s main" % (nf, SUITE)
    f_fl = "deb [trusted=yes] file://%s ./" % fl

    ok_s, rc_s, t_s = construir("SUJETO overlay NO FLAT", WORK + "/r_nonflat",
                                [fmain, f_nf])
    ok_n, rc_n, t_n = construir("CONTROL overlay FLAT (el del v5)", WORK + "/r_flat",
                                [fmain, f_fl])
    res["sujeto"] = {"layout": "no flat", "instalo": ok_s, "rc": rc_s}
    res["controles"]["FLAT"] = {"layout": "flat", "instalo": ok_n, "rc": rc_n,
                                "evidencia": "\n".join(
                                    [l for l in t_n.splitlines()
                                     if re.search(r"(unmet|^E: |not going to be)", l)][:6])[:700]}
    discrimina = (ok_s != ok_n)
    res["controles"]["discrimina"] = discrimina
    say("")
    say("RESULTADO: no_flat=%s (rc %d) | flat=%s (rc %d)" % (ok_s, rc_s, ok_n, rc_n))
    say("EL CONTROL DISCRIMINA (resultados distintos):", discrimina)
    if ok_s and not ok_n:
        res["veredicto_causa"] = "MEDIDA: el layout flat era la causa"
    elif not ok_s and not ok_n:
        res["veredicto_causa"] = ("MI SOSPECHA ES FALSA: el no flat tambien falla, asi "
                                  "que la causa no es el layout")
    elif ok_s and ok_n:
        res["veredicto_causa"] = ("LOS DOS PASAN: el v5 fallaba por algo que ya no esta, "
                                  "y no puedo atribuirlo al layout")
    else:
        res["veredicto_causa"] = "invertido: el flat pasa y el no flat no. Inesperado"
    say("CAUSA:", res["veredicto_causa"])

    if ok_s:
        rc, o, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % (WORK + "/r_nonflat")])
        res["sujeto"]["bytes"] = int((o.strip() or "0").split()[0])
        say("  rootfs: %d B (%.3f GiB)"
            % (res["sujeto"]["bytes"], res["sujeto"]["bytes"] / 1073741824.0))
        rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                       "'${Package} ${Version}\\n' systemd libdevmapper1.02.1 "
                       "libcryptsetup12 2>&1" % (WORK + "/r_nonflat")])
        say("  LA CADENA:")
        for l in o.splitlines():
            say("   |", l[:120])
        res["sujeto"]["cadena"] = o.strip()
        res["criterio_b"] = origen(WORK + "/r_nonflat", [fmain, f_nf])
        b = res["criterio_b"]
        res["veredicto"] = {"a_construye": "VERDE",
                            "b_origen": ("VERDE" if (b["control_systemd"]
                                                     and b["n_de_proposed"] == 0)
                                         else "AMARILLO"),
                            "c_firmas": "ROJO (trusted=yes, R-07)"}
    else:
        res["veredicto"] = {"a_construye": "ROJO", "b_origen": "NO MEDIDO",
                            "c_firmas": "NO MEDIDO"}
        res["sujeto"]["evidencia"] = "\n".join(
            [l for l in t_s.splitlines()
             if re.search(r"(unmet|^E: |not going to be|narrow)", l)][:8])[:1200]
    say(""); say("VEREDICTO F-002 v6:", json.dumps(res["veredicto"]))
    res["segundos"] = round(time.time() - t0, 1)
    write(res); say("FIN en", res["segundos"], "s")
    return 0 if ok_s else 3


def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-002-v6.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-002-v6-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    v = res.get("veredicto", {})
    b = res.get("criterio_b", {})
    md = ["# F-002 v6 - overlay NO FLAT vs FLAT", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "| Criterio | Veredicto |", "|---|---|",
          "| (a) construye systemd | **%s** |" % v.get("a_construye", "?"),
          "| (b) origen por apt-cache policy | **%s** |" % v.get("b_origen", "?"),
          "| (c) firmas | **%s** |" % v.get("c_firmas", "?"), "",
          "**Causa:** %s" % res.get("veredicto_causa", "?"), "",
          "**El control discrimina:** %s" % res.get("controles", {}).get("discrimina", "?"), "",
          "Paquetes: %s | del overlay: %s | rootfs: %s B"
          % (b.get("n_paquetes", "?"), len(b.get("del_overlay", [])),
             res.get("sujeto", {}).get("bytes", "?")), "",
          "## Origen contado por apt", "", "```json",
          json.dumps(b.get("por_origen", {}), indent=2, ensure_ascii=False), "```", "",
          "## Manifiesto del overlay", "", "```json",
          json.dumps(res.get("manifiesto", []), indent=2, ensure_ascii=False), "```", "",
          "## Prediccion registrada antes de correr", "", res["prediccion"], "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Salida cruda, verbatim", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-002-v6.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
