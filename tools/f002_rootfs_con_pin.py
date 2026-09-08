#!/usr/bin/env python3
"""
F-002 v2 - Se construye el rootfs de openKylin arm64?

Dos criterios, como pidio el auditor:
  (a) instala systemd
  (b) SOLO los paquetes pineados vinieron de huanghe-proposed. Un rootfs que
      instala arrastrando cientos de paquetes sin QA no cuenta como verde.

Y TRES CONTROLES, porque un verde sin control no distingue "lo arregle" de
"andaba igual":
  N1) SIN pin: debe FALLAR con la dependencia rota. Si pasa, el pin no era la
      causa y el diagnostico entero del ROJO 2 se cae.
  N2) SIN el hook de merged-usr: debe fallar con el ENOENT del interprete. Si
      pasa, mi diagnostico del cuarto ENOENT era falso.
  P)  el sujeto: con pin Y con hook.

ME REFUTO ANTES DE CORRER: en el ADR-003 propuse "--include=usr-is-merged" como
fix. ES FALSO y lo medi. usr-is-merged es un paquete TRANSICIONAL cuyo preinst
solo VERIFICA que el sistema ya este merged y FALLA si no lo esta:
    is_merged() { for dir in /bin /sbin /lib; do
      [ "$(readlink -f $DPKG_ROOT$dir)" = "$DPKG_ROOT/usr$dir" ] || return 1 ...
Su data.tar solo trae changelog y copyright: no crea un solo symlink. Incluirlo
habria hecho fallar el build ANTES, no arreglarlo. El que convierte es 'usrmerge',
que depende de perl y corre en postinst, o sea demasiado tarde.
La via correcta es un SETUP-HOOK que cree los symlinks en el arbol VACIO, antes de
que se extraiga el primer paquete.

DEFECTO CAZADO ANTES DE CORRER: escribi el pin con 'n=huanghe-proposed'. MEDIDO:
los DOS Release declaran 'Codename: huanghe', y n= es Codename, asi que el pin no
habria matcheado nunca. El campo correcto es a= (Suite).
"""
import json, os, re, subprocess, sys, time

MIRROR = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PROP = "huanghe-proposed"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
# Los unicos que se permiten venir de -proposed. lvm2 los produce a los tres.
PINEADOS = ["libdevmapper1.02.1", "dmsetup", "libdevmapper-event1.02.1"]
OUT = os.environ.get("F002_OUT", "mediciones/f-002")
WORK = os.environ.get("F002_WORK", "/tmp/f002")

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

# setup-hook: corre sobre el arbol VACIO, antes de extraer nada. Esto es lo que
# base-files NO trae (medido: sus unicos symlinks son os-release y 3 licencias)
# y lo que usr-is-merged NO hace (solo verifica).
SETUP_HOOK = ('set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; '
              'ln -sfn "usr/$d" "$1/$d"; done; '
              'mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"; '
              'ls -la "$1" | head -20')

PIN_HOOK = ('set -e; mkdir -p "$1/etc/apt/preferences.d"; '
            'cp %s "$1/etc/apt/preferences.d/siao-pins"; '
            'echo "--- PIN ESCRITO EN EL TARGET ---"; '
            'cat "$1/etc/apt/preferences.d/siao-pins"')

# a= es SUITE. NO usar n=, que es CODENAME: los dos Release declaran
# "Codename: huanghe", asi que un pin con n= no matchea nunca.
PREFS = """Package: *
Pin: release a=%(prop)s
Pin-Priority: -10

Package: %(pins)s
Pin: release a=%(prop)s
Pin-Priority: 990
""" % {"prop": PROP, "pins": " ".join(PINEADOS)}


def construir(nombre, rootfs, con_pin, con_hook):
    say(""); say("=" * 78)
    say(">>> %s  (pin=%s, hook merged-usr=%s)" % (nombre, con_pin, con_hook))
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (rootfs, rootfs)], timeout=300)
    prefs = os.path.join(WORK, "prefs-%s" % nombre)
    open(prefs, "w").write(PREFS)
    cmd = ["mmdebstrap", "--mode=root", "--variant=important",
           "--architectures=" + ARCH,
           "--include=" + ",".join(PKGS),
           '--aptopt=Acquire::AllowInsecureRepositories "true"',
           '--aptopt=APT::Get::AllowUnauthenticated "true"',
           "--verbose"]
    if con_hook:
        cmd.append("--setup-hook=" + SETUP_HOOK)
    if con_pin:
        # El pin se escribe DENTRO del target en un setup-hook: el apt de
        # mmdebstrap lee etc/apt/preferences.d del chroot. Un --aptopt con
        # Dir::Etc no es confiable porque mmdebstrap arma su propio Dir::Etc.
        cmd.append("--setup-hook=" + PIN_HOOK % prefs)
    fuentes = ["deb [trusted=yes] %s %s main" % (MIRROR, SUITE)]
    if con_pin:
        fuentes.append("deb [trusted=yes] %s %s main" % (MIRROR, PROP))
    cmd += [SUITE, rootfs] + fuentes
    rc, o, e = sh(cmd, timeout=2700)
    say("  mmdebstrap rc=%d" % rc)
    pat = (r"(No such file|unmet|broken|E:|Errors were|dpkg:|HOOK|lrwxrwxrwx|"
           r"setup failed|not going to be|PIN ESCRITO)")
    for l in [x for x in (o + e).splitlines() if re.search(pat, x)][-45:]:
        say("  MM |", l[:280])
    ok = (rc == 0 and os.path.isfile(os.path.join(rootfs, "usr/lib/systemd/systemd")))
    if not ok and rc == 0:
        say("  rc=0 pero NO hay /usr/lib/systemd/systemd: no cuenta como verde")
        rc2, o2, _ = sh(["bash", "-c", "ls %s/usr/lib/systemd/ 2>&1 | head -5" % rootfs])
        say("  |", o2.strip()[:300])
    return ok, rc, (o + e)


def auditar(rootfs):
    """El segundo criterio: quien vino de -proposed."""
    import gzip, urllib.request
    res = {}
    rc, o, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % rootfs])
    res["bytes"] = int((o.strip() or "0").split()[0])
    rc, o, _ = sh(["bash", "-c", "cat %s/etc/os-release | head -4" % rootfs])
    res["os_release"] = o.strip()
    say("  rootfs: %d B (%.3f GiB)" % (res["bytes"], res["bytes"] / 1073741824.0))
    say("  os-release:")
    for l in o.splitlines():
        say("   |", l)

    rc, o, _ = sh(["bash", "-c",
                   "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                   "'${Package} ${Version}\\n' libdevmapper1.02.1 libcryptsetup12 "
                   "systemd base-files 2>&1" % rootfs])
    say("  LA CADENA, instalada:")
    for l in o.splitlines():
        say("   |", l[:140])
    res["cadena"] = o.strip()

    rc, o, e = sh(["bash", "-c",
                   "dpkg-query --admindir=%s/var/lib/dpkg -W -f '${Package}\\n' "
                   "| sort | wc -l" % rootfs])
    res["paquetes_instalados"] = int((o.strip() or "0").split()[0])
    say("  paquetes instalados:", res["paquetes_instalados"])

    def idx(comp):
        u = "%s/dists/%s/main/binary-%s/Packages.gz" % (MIRROR, comp, ARCH)
        req = urllib.request.Request(u, headers={"User-Agent": "siao/1"})
        d = urllib.request.urlopen(req, timeout=180).read()
        out = {}
        for st in gzip.decompress(d).decode("utf-8", "replace").split("\n\n"):
            m = re.search(r"^Package: (\S+)$", st, re.M)
            v = re.search(r"^Version: (\S+)$", st, re.M)
            if m and v:
                out.setdefault(m.group(1), v.group(1))
        return out

    im, ip = idx(SUITE), idx(PROP)
    say("  indices leidos: main=%d paquetes, proposed=%d" % (len(im), len(ip)))
    rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                                 "'${Package} ${Version}\\n' 2>/dev/null" % rootfs])
    de_proposed, solo_prop = [], []
    for line in o.splitlines():
        p = line.split()
        if len(p) != 2:
            continue
        nm, ver = p
        vm, vp = im.get(nm), ip.get(nm)
        if vp and ver == vp and vm is not None and ver != vm:
            de_proposed.append("%s %s (main tenia %s)" % (nm, ver, vm))
        elif vp and ver == vp and vm is None:
            solo_prop.append("%s %s (no esta en main)" % (nm, ver))
    say("  >>> VINIERON DE -proposed (version de proposed, distinta de main):")
    for x in de_proposed:
        say("      ", x)
    if solo_prop:
        say("  >>> solo existen en proposed:")
        for x in solo_prop[:20]:
            say("      ", x)
    res["de_proposed"] = de_proposed
    res["solo_en_proposed"] = solo_prop
    inesperados = [x for x in de_proposed if x.split()[0] not in PINEADOS]
    res["inesperados"] = inesperados
    res["criterio_b"] = "VERDE" if not inesperados else "ROJO"
    say("  CRITERIO (b):", res["criterio_b"],
        "- inesperados de proposed:", inesperados or "ninguno")
    return res


def main():
    import platform
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    res = {"falsador": "F-002", "version": 2,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "me_refuto_antes_de_correr": (
               "En el ADR-003 propuse --include=usr-is-merged como fix. ES FALSO: ese "
               "paquete es transicional, su preinst solo VERIFICA que el sistema ya "
               "este merged y FALLA si no lo esta; su data.tar trae changelog y "
               "copyright. Habria hecho fallar el build antes, no arreglarlo."),
           "defecto_cazado_antes_de_correr": (
               "Escribi el pin con n=huanghe-proposed. MEDIDO: los DOS Release declaran "
               "Codename: huanghe, y n= es Codename, asi que el pin no habria matcheado "
               "nunca y -proposed entraba con prioridad 500: el criterio (b) daba rojo y "
               "yo iba a culpar al repo. El campo correcto es a= (Suite)."),
           "pineados": PINEADOS, "preferences": PREFS,
           "controles": {}, "sujeto": {}, "no_medido": []}
    say("== F-002 v2 ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("ME REFUTO ANTES DE CORRER:", res["me_refuto_antes_de_correr"])
    say("DEFECTO CAZADO ANTES DE CORRER:", res["defecto_cazado_antes_de_correr"])
    say(""); say("preferences.d que voy a usar:")
    for l in PREFS.splitlines():
        say("   |", l)

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host no aarch64")
        say("ABORTO: exige aarch64"); write(res); return 3

    ok1, rc1, txt1 = construir("N1-sin-pin", os.path.join(WORK, "n1"), False, True)
    ev1 = [l for l in txt1.splitlines()
           if "not going to be installed" in l or "unmet" in l or "held broken" in l]
    res["controles"]["N1_sin_pin"] = {
        "esperado": "FALLA por libdevmapper", "instalo": ok1, "rc": rc1,
        "discrimina": (not ok1), "evidencia": "\n".join(ev1)[:900]}
    say("  N1:", "CORRECTO, fallo como se esperaba" if not ok1
        else "OJO: instalo SIN pin, o sea que el pin NO era la causa")

    ok2, rc2, txt2 = construir("N2-sin-hook", os.path.join(WORK, "n2"), True, False)
    enoent = [l for l in txt2.splitlines() if "No such file or directory" in l]
    res["controles"]["N2_sin_hook_mergedusr"] = {
        "esperado": "FALLA con ENOENT del interprete", "instalo": ok2, "rc": rc2,
        "discrimina": (not ok2), "enoent_encontrado": bool(enoent),
        "evidencia": "\n".join(enoent)[:900]}
    say("  N2:", "CORRECTO, fallo" if not ok2 else "OJO: instalo SIN el hook")
    if enoent:
        say("  N2 ENOENT verbatim:", enoent[0][:220])

    okP, rcP, txtP = construir("SUJETO-pin-y-hook", os.path.join(WORK, "rootfs"),
                               True, True)
    res["sujeto"] = {"instalo": okP, "rc": rcP}
    if okP:
        res["sujeto"].update(auditar(os.path.join(WORK, "rootfs")))
        res["veredicto"] = ("VERDE" if res["sujeto"].get("criterio_b") == "VERDE"
                            else "AMARILLO")
    else:
        res["veredicto"] = "ROJO"
        res["sujeto"]["evidencia"] = "\n".join(
            [l for l in txtP.splitlines()
             if re.search(r"(No such file|unmet|broken|E:|dpkg:)", l)])[:2000]
    say(""); say("VEREDICTO F-002:", res["veredicto"])

    val = (res["controles"]["N1_sin_pin"]["discrimina"]
           and res["controles"]["N2_sin_hook_mergedusr"]["discrimina"])
    res["controles"]["ambos_discriminan"] = val
    if okP and not val:
        say("ADVERTENCIA: el sujeto dio verde pero un control no discrimina: no "
            "puedo atribuir el verde al fix con certeza")
        res["veredicto_calificado"] = "VERDE sin control que lo atribuya al fix"
    res["segundos"] = round(time.time() - t0, 1)
    write(res)
    say("FIN en", res["segundos"], "s")
    return 0 if okP else 3


def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-002.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-002-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    s = res.get("sujeto", {})
    md = ["# F-002 v2 - rootfs openKylin arm64 con pin de un solo paquete", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "| Criterio | Veredicto |", "|---|---|",
          "| (a) instala systemd | **%s** |" % ("VERDE" if s.get("instalo") else "ROJO"),
          "| (b) solo los pineados de -proposed | **%s** |" % s.get("criterio_b", "NO MEDIDO"),
          "| **F-002** | **%s** |" % res.get("veredicto", "NO MEDIDO"), "",
          "Tamano del rootfs: %s B (%.3f GiB)" % (s.get("bytes", "?"),
                                                 (s.get("bytes") or 0) / 1073741824.0),
          "Paquetes instalados: %s" % s.get("paquetes_instalados", "?"), "",
          "## Controles negativos", "", "```json",
          json.dumps(res["controles"], indent=2, ensure_ascii=False)[:4000], "```", "",
          "## Me refuto antes de correr", "", res["me_refuto_antes_de_correr"], "",
          "## Defecto cazado antes de correr", "", res["defecto_cazado_antes_de_correr"], "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Salida cruda, verbatim", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-002.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
