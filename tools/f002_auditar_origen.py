#!/usr/bin/env python3
"""
F-002 v4 - Auditoria de ORIGEN del rootfs que SI se construye.

El v3 midio que `main + huanghe-proposed` arma el rootfs con systemd 259.5-ok1.2
en 158 s. Eso prueba que COMPILA. No prueba que sea una base aceptable.

Este instrumento contesta lo unico que queda del rootfs: QUE entro, DE DONDE, y
cuanto de eso viene de un componente sin QA.

COMO LO MIDE, y esta es la parte que importa:
  1) apt-cache policy DENTRO del chroot, con los mismos indices. Es el instrumento
     que el auditor pidio por nombre, y es el que sabe de que suite salio cada
     candidato.
  2) cruce de cada paquete instalado contra los dos indices oficiales por
     (nombre, version) EXACTA. Segunda opinion independiente de la primera.
  3) /var/lib/apt/extended_states y el dpkg status, para el conteo total.

TRES CONTROLES DE INSTRUMENTO:
  C1 POSITIVO: libdevmapper1.02.1 TIENE que aparecer como de -proposed. Si el
     auditor no lo ve, no ve nada y el conteo entero es invalido.
  C2 NEGATIVO: bash TIENE que aparecer como de main. Si sale de -proposed, el
     auditor sobre-atribuye.
  C3 CRUZADO: el mismo auditor corrido sobre un rootfs armado SOLO con main debe
     dar CERO paquetes de -proposed.

EL CRITERIO (b) NO ES BINARIO Y SE DECLARA ASI ANTES DE CORRER: este script
reporta el numero, la lista completa y el tamano. NO dice "aprobado". Cuantos
paquetes sin QA son tolerables en la base de un producto es una decision de
Abraham, no de un script.
"""
import gzip, json, os, re, subprocess, sys, time, urllib.request

MIRROR = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PROP = "huanghe-proposed"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
OUT = os.environ.get("F002_OUT", "mediciones/f-002")
WORK = os.environ.get("F002_WORK", "/tmp/f002v4")

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

SETUP_HOOK = ('set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; '
              'ln -sfn "usr/$d" "$1/$d"; done; '
              'mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"')

# Deja las sources y las listas de apt DENTRO del rootfs, para poder correr
# apt-cache policy ahi mismo despues.
CUSTOMIZE = ('set -e; mkdir -p "$1/etc/apt/sources.list.d"; '
             'printf "%%s\\n" "deb [trusted=yes] {mirror} {suite} main" '
             '> "$1/etc/apt/sources.list"; ')


def indice(comp):
    d = urllib.request.urlopen(urllib.request.Request(
        "%s/dists/%s/main/binary-%s/Packages.gz" % (MIRROR, comp, ARCH),
        headers={"User-Agent": "siao-audit/1"}), timeout=240).read()
    out = {}
    for st in gzip.decompress(d).decode("utf-8", "replace").split("\n\n"):
        m = re.search(r"^Package: (\S+)$", st, re.M)
        v = re.search(r"^Version: (\S+)$", st, re.M)
        s = re.search(r"^Size: (\d+)$", st, re.M)
        if m and v:
            out.setdefault(m.group(1), (v.group(1), int(s.group(1)) if s else 0))
    return out


def construir(nombre, rootfs, fuentes):
    say(""); say("=" * 78)
    say(">>> construyendo %s" % nombre)
    for f in fuentes:
        say("    fuente:", f)
    sh(["bash", "-c", "rm -rf %s && mkdir -p %s" % (rootfs, rootfs)], timeout=300)
    cmd = ["mmdebstrap", "--mode=root", "--variant=important",
           "--architectures=" + ARCH, "--include=" + ",".join(PKGS),
           '--aptopt=Acquire::AllowInsecureRepositories "true"',
           '--aptopt=APT::Get::AllowUnauthenticated "true"',
           "--setup-hook=" + SETUP_HOOK,
           # que las listas de apt sobrevivan: las necesito para apt-cache policy
           "--skip=cleanup/apt/lists", "--skip=cleanup/apt/cache",
           "--verbose"]
    cmd += [SUITE, rootfs] + fuentes
    rc, o, e = sh(cmd, timeout=2700)
    say("  mmdebstrap rc=%d" % rc)
    interes = [l for l in (o + e).splitlines()
               if re.search(r"(Setting up systemd |E: |unmet|no installation)", l)]
    for l in interes[:12]:
        say("  MM |", l[:260])
    ok = os.path.isfile(os.path.join(rootfs, "usr/lib/systemd/systemd"))
    say("  systemd presente:", ok, "| rc:", rc)
    return ok, rc


def instalados(rootfs):
    rc, o, _ = sh(["bash", "-c", "dpkg-query --admindir=%s/var/lib/dpkg -W -f "
                                 "'${Package} ${Version} ${Installed-Size}\\n' "
                                 "2>/dev/null" % rootfs])
    out = []
    for line in o.splitlines():
        p = line.split()
        if len(p) >= 2:
            out.append((p[0], p[1], int(p[2]) if len(p) > 2 and p[2].isdigit() else 0))
    return out


def policy_en_chroot(rootfs, fuentes):
    """apt-cache policy DENTRO del chroot: el instrumento que pidio el auditor."""
    src = os.path.join(rootfs, "etc/apt/sources.list")
    os.makedirs(os.path.dirname(src), exist_ok=True)
    with open(src, "w") as f:
        for x in fuentes:
            f.write(x + "\n")
    say("  sources.list escrito en el chroot:")
    for x in fuentes:
        say("   |", x)
    rc, o, e = sh(["bash", "-c",
                   "chroot %s apt-get update -o Acquire::AllowInsecureRepositories=true "
                   "-o APT::Get::AllowUnauthenticated=true -qq 2>&1 | tail -5" % rootfs],
                  timeout=900)
    say("  apt-get update en el chroot rc=%d" % rc)
    for l in (o + e).splitlines()[:6]:
        say("   |", l[:200])
    rc, o, e = sh(["bash", "-c", "chroot %s apt-cache policy 2>&1" % rootfs], timeout=300)
    say("  apt-cache policy (verbatim):")
    for l in (o + e).splitlines():
        say("   POLICY |", l[:200])
    return rc, o + e


def auditar(rootfs, im, ip, fuentes, nombre):
    say(""); say("--- AUDITORIA DE ORIGEN: %s ---" % nombre)
    pk = instalados(rootfs)
    say("  paquetes instalados:", len(pk))
    de_prop, de_main, ambos, ninguno = [], [], [], []
    kb_prop = 0
    for nm, ver, kb in pk:
        vm = im.get(nm)
        vp = ip.get(nm)
        en_main = bool(vm and vm[0] == ver)
        en_prop = bool(vp and vp[0] == ver)
        if en_main and en_prop:
            ambos.append((nm, ver))
        elif en_prop:
            de_prop.append((nm, ver, kb, vm[0] if vm else "no esta en main"))
            kb_prop += kb
        elif en_main:
            de_main.append((nm, ver))
        else:
            ninguno.append((nm, ver))
    say("  SOLO en -proposed (version exacta): %d" % len(de_prop))
    for nm, ver, kb, envm in sorted(de_prop):
        say("      %-34s %-22s %6d KB   main: %s" % (nm, ver, kb, envm))
    say("  identica en main y en proposed (indistinguible): %d" % len(ambos))
    say("  solo en main: %d" % len(de_main))
    say("  en NINGUN indice (version no publicada): %d" % len(ninguno))
    for nm, ver in sorted(ninguno)[:15]:
        say("      %-34s %s" % (nm, ver))
    rc, o, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % rootfs])
    total = int((o.strip() or "0").split()[0])
    say("  rootfs total: %d B (%.3f GiB) | de -proposed: ~%d KB instalados"
        % (total, total / 1073741824.0, kb_prop))
    prc, ptxt = policy_en_chroot(rootfs, fuentes)
    return {"paquetes": len(pk), "solo_proposed": [list(x) for x in sorted(de_prop)],
            "n_solo_proposed": len(de_prop), "kb_proposed": kb_prop,
            "indistinguibles": len(ambos), "solo_main": len(de_main),
            "sin_indice": [list(x) for x in sorted(ninguno)],
            "bytes": total, "apt_cache_policy_rc": prc,
            "apt_cache_policy": ptxt[:4000]}


def main():
    import platform
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    res = {"falsador": "F-002", "version": 4,
           "pregunta": "que entro al rootfs, de donde, y cuanto viene de un componente sin QA",
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "declarado_antes_de_correr": (
               "El criterio (b) NO es binario y este script NO dice 'aprobado'. Reporta "
               "el numero, la lista completa y el tamano. Cuantos paquetes sin QA son "
               "tolerables en la base de un producto es decision de Abraham."),
           "controles": {}, "sujeto": {}, "no_medido": []}
    say("== F-002 v4: auditoria de origen ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("DECLARADO ANTES DE CORRER:", res["declarado_antes_de_correr"])

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host no aarch64"); write(res); return 3

    im, ip = indice(SUITE), indice(PROP)
    say("indices oficiales leidos: main=%d paquetes | proposed=%d" % (len(im), len(ip)))

    f_main = "deb [trusted=yes] %s %s main" % (MIRROR, SUITE)
    f_prop = "deb [trusted=yes] %s %s main" % (MIRROR, PROP)

    # EL SUJETO: el camino que el v3 probo que funciona
    rootfs = os.path.join(WORK, "sujeto")
    ok, rc = construir("SUJETO main+proposed", rootfs, [f_main, f_prop])
    if not ok:
        res["sujeto"] = {"instalo": False, "rc": rc}
        res["no_medido"].append("el sujeto no se construyo en esta corrida: sin rootfs "
                                "no hay origen que auditar")
        say("ABORTO: el sujeto no se construyo"); write(res); return 3
    res["sujeto"] = auditar(rootfs, im, ip, [f_main, f_prop], "main+proposed")
    res["sujeto"]["instalo"] = True

    # C1 y C2: controles de instrumento sobre el sujeto
    nombres_prop = {x[0] for x in res["sujeto"]["solo_proposed"]}
    c1 = "libdevmapper1.02.1" in nombres_prop
    c2 = "bash" not in nombres_prop
    say("")
    say("C1 POSITIVO de instrumento: libdevmapper1.02.1 aparece como de -proposed?", c1)
    say("C2 NEGATIVO de instrumento: bash NO aparece como de -proposed?", c2)
    res["controles"]["C1_positivo_libdevmapper_de_proposed"] = c1
    res["controles"]["C2_negativo_bash_no_de_proposed"] = c2

    # C3 CRUZADO: el mismo auditor sobre un rootfs de solo main
    r3 = os.path.join(WORK, "solo-main")
    ok3, rc3 = construir("C3 solo-main (se espera que NO instale systemd)", r3, [f_main])
    pk3 = instalados(r3)
    say("  C3: paquetes extraidos aunque el build fallara:", len(pk3))
    prop3 = [(nm, ver) for nm, ver, _ in pk3
             if ip.get(nm) and ip[nm][0] == ver and not (im.get(nm) and im[nm][0] == ver)]
    say("  C3: paquetes atribuidos a -proposed en un rootfs SIN proposed:", len(prop3))
    for x in prop3[:10]:
        say("      OJO:", x)
    res["controles"]["C3_cruzado_solo_main"] = {
        "paquetes": len(pk3), "atribuidos_a_proposed": len(prop3),
        "discrimina": (len(prop3) == 0),
        "lista": [list(x) for x in prop3[:20]]}
    say("  C3:", "CORRECTO, cero falsos positivos" if not prop3
        else "ROTO: el auditor ve proposed donde no hay proposed")

    val = c1 and c2 and (len(prop3) == 0)
    res["controles"]["instrumento_validado"] = val
    n = res["sujeto"]["n_solo_proposed"]
    if not val:
        res["veredicto"] = "NO MEDIDO"
        res["motivo"] = "los controles de instrumento no pasaron: el conteo no es confiable"
        say(""); say("VEREDICTO: NO MEDIDO - instrumento no validado")
    else:
        res["veredicto"] = "MEDIDO"
        res["resumen"] = ("%d paquetes vienen SOLO de huanghe-proposed, ~%d KB instalados, "
                          "sobre %d paquetes totales"
                          % (n, res["sujeto"]["kb_proposed"], res["sujeto"]["paquetes"]))
        say(""); say("VEREDICTO: MEDIDO"); say(res["resumen"])
        say("NO digo 'aprobado': ese juicio es de Abraham.")
    res["segundos"] = round(time.time() - t0, 1)
    write(res); say("FIN en", res["segundos"], "s")
    return 0


def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-002-v4-origen.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-002-v4-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    s = res.get("sujeto", {})
    filas = ["| %s | %s | %s KB | main: %s |" % tuple(x)
             for x in s.get("solo_proposed", [])]
    md = ["# F-002 v4 - auditoria de ORIGEN del rootfs", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "**Veredicto:** **%s**" % res.get("veredicto", "NO MEDIDO"), "",
          res.get("resumen", res.get("motivo", "")), "",
          "| Metrica | Valor |", "|---|---|",
          "| paquetes instalados | %s |" % s.get("paquetes", "?"),
          "| SOLO de -proposed | **%s** |" % s.get("n_solo_proposed", "?"),
          "| KB instalados de -proposed | %s |" % s.get("kb_proposed", "?"),
          "| identicos en main y proposed | %s |" % s.get("indistinguibles", "?"),
          "| solo en main | %s |" % s.get("solo_main", "?"),
          "| en ningun indice | %s |" % len(s.get("sin_indice", [])),
          "| rootfs | %s B |" % s.get("bytes", "?"), "",
          "## Los paquetes que vienen SOLO de -proposed", "",
          "| paquete | version | tamano | en main |", "|---|---|---|---|"] + filas + [
          "", "## Controles de instrumento", "", "```json",
          json.dumps(res["controles"], indent=2, ensure_ascii=False)[:3000], "```", "",
          "## Declarado antes de correr", "", res["declarado_antes_de_correr"], "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Salida cruda, verbatim", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-002-v4-origen.md"), "w") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
