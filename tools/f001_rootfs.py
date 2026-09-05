#!/usr/bin/env python3
"""
Constructor de rootfs openKylin arm64, con CUATRO vias y un veredicto por via.

Se separa del falsador a proposito: construir el rootfs y medir el kernel son
sujetos distintos (E-01), y mezclarlos fue lo que hizo que un fallo de mi
constructor pareciera un fallo del userland.

Cada via declara si el rootfs que produce es COMPLETO (con maintainer scripts
corridos) o DEGRADADO (solo extraccion). Un rootfs degradado sigue sirviendo para
la pregunta de F-001, que es sobre el KERNEL, pero no es el mismo sujeto y se
dice.
"""
import gzip, json, os, re, subprocess, sys, urllib.request

MIRROR = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
LOADER = "ld-linux-aarch64.so.1"

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line); print(line, flush=True)

def sh(cmd, timeout=2700, env=None):
    say("$", (cmd if isinstance(cmd, str) else " ".join(cmd))[:500])
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -9, "", "TIMEOUT tras %ss" % timeout
    except Exception as e:
        return -1, "", repr(e)[:300]

def usuario_sin_privilegios():
    for u in ("runner", "ubuntu", "nobody"):
        rc, o, _ = sh(["id", "-u", u], timeout=30)
        if rc == 0 and o.strip() not in ("", "0"):
            return u
    return None

HOOK = ('set -x; for d in bin sbin lib lib64; do '
        '  if [ ! -e "$1/$d" ] && [ -d "$1/usr/$d" ]; then ln -s "usr/$d" "$1/$d"; fi; '
        'done; '
        'mkdir -p "$1/lib"; '
        '[ -e "$1/lib/%s" ] || ln -s "../usr/lib/%s" "$1/lib/%s"; '
        '[ -e "$1/bin/sh" ] || { mkdir -p "$1/bin"; '
        '  for c in dash bash; do [ -x "$1/usr/bin/$c" ] && ln -sf "../usr/bin/$c" "$1/bin/sh" && break; done; }; '
        'ls -la "$1/lib/%s" "$1/bin/sh" 2>&1 || true'
        % (LOADER, LOADER, LOADER, LOADER))

BASE = ["--architectures=" + ARCH, "--include=" + ",".join(PKGS),
        '--aptopt=Acquire::AllowInsecureRepositories "true"',
        '--aptopt=APT::Get::AllowUnauthenticated "true"']
FUENTE = "deb [trusted=yes] %s %s main" % (MIRROR, SUITE)

def via1(rootfs):
    return ("via 1: mmdebstrap + hook que crea loader Y los symlinks de merged-usr "
            "(los postinst necesitan /bin/sh)",
            ["mmdebstrap", "--variant=important"] + BASE +
            ["--extract-hook=" + HOOK, "--essential-hook=" + HOOK, SUITE, rootfs, FUENTE],
            "COMPLETO")

def via2(rootfs):
    u = usuario_sin_privilegios()
    if not u:
        return None
    return ("via 2: chrootless bajo el usuario '%s' con fakeroot, que es lo que el guard "
            "de mmdebstrap pide" % u,
            ["bash", "-c",
             "install -d -o %s -g %s %s && cd /tmp && su %s -s /bin/bash -c "
             "'fakeroot mmdebstrap --mode=chrootless --variant=important %s %s %s \"%s\"'"
             % (u, u, rootfs, u,
                " ".join("'" + x + "'" for x in BASE), SUITE, rootfs, FUENTE)],
            "COMPLETO")

def via3(rootfs):
    return ("via 3: --variant=extract, SIN configurar paquetes: rootfs DEGRADADO declarado",
            ["mmdebstrap", "--variant=extract"] + BASE +
            ["--extract-hook=" + HOOK, SUITE, rootfs, FUENTE],
            "DEGRADADO")

def via4(rootfs):
    """El metodo que YA dio VERDE en FALSADOR-001, escalado: apt del host contra un
    status vacio para resolver el cierre, y dpkg-deb -x para extraer. Cero chroot,
    cero maintainer scripts."""
    return ("via 4: cierre de dependencias con el apt del HOST (status vacio) + dpkg-deb -x. "
            "Es el metodo que ya probe funcionando. Rootfs DEGRADADO declarado",
            None, "DEGRADADO")

def correr_via4(rootfs):
    apt = "/tmp/aptdir"
    for d in ("etc/apt/apt.conf.d", "etc/apt/preferences.d", "var/lib/apt/lists/partial",
              "var/cache/apt/archives/partial", "var/lib/dpkg"):
        os.makedirs(os.path.join(apt, d), exist_ok=True)
    open(os.path.join(apt, "etc/apt/sources.list"), "w").write(FUENTE + "\n")
    open(os.path.join(apt, "var/lib/dpkg/status"), "w").write("")
    opts = ["-o", "Dir=" + apt,
            "-o", "Dir::State::status=" + os.path.join(apt, "var/lib/dpkg/status"),
            "-o", "Dir::Etc::sourcelist=" + os.path.join(apt, "etc/apt/sources.list"),
            "-o", "Dir::Etc::sourceparts=/dev/null",
            "-o", "APT::Architecture=" + ARCH,
            "-o", "APT::Architectures::=" + ARCH,
            "-o", "Acquire::AllowInsecureRepositories=true",
            "-o", "APT::Get::AllowUnauthenticated=true",
            "-o", "APT::Sandbox::User=root",
            "-o", "Acquire::Languages=none"]
    rc, o, e = sh(["apt-get"] + opts + ["update"], timeout=900)
    say("  apt update rc=%d" % rc)
    for l in (o.splitlines()[-6:] + e.splitlines()[-10:]):
        say("  APT |", l[:250])
    if rc != 0:
        return False, 0
    rc, o, e = sh(["apt-get"] + opts + ["install", "--yes", "--no-install-recommends",
                                        "--print-uris"] + ["?essential"] + PKGS, timeout=900)
    if rc != 0:
        say("  el patron ?essential no anduvo (rc=%d), pido solo los paquetes pedidos" % rc)
        rc, o, e = sh(["apt-get"] + opts + ["install", "--yes", "--no-install-recommends",
                                            "--print-uris"] + PKGS, timeout=900)
    say("  apt --print-uris rc=%d" % rc)
    if rc != 0:
        for l in e.splitlines()[-15:]:
            say("  APT |", l[:250])
        return False, 0
    uris = re.findall(r"'(\S+?)'\s+(\S+?)\s+(\d+)\s+", o)
    say("  paquetes a bajar:", len(uris))
    if not uris:
        say("  cero URIs: nada que bajar"); return False, 0
    debdir = "/tmp/debs"
    os.makedirs(debdir, exist_ok=True)
    os.makedirs(rootfs, exist_ok=True)
    total, n = 0, 0
    for url, fn, size in uris:
        dst = os.path.join(debdir, fn)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "siao-f001/4"})
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
            open(dst, "wb").write(data)
            total += len(data); n += 1
        except Exception as ex:
            say("  DEB ERR", fn, repr(ex)[:120]); continue
    say("  bajados %d paquetes, %d B (%.0f MiB)" % (n, total, total / 1048576.0))
    rc, o, e = sh(["bash", "-c",
                   "set -e; for d in %s/*.deb; do dpkg-deb -x \"$d\" %s; done; echo EXTRAIDOS"
                   % (debdir, rootfs)], timeout=1800)
    say("  dpkg-deb -x rc=%d" % rc, (o + e).strip()[-400:])
    # el ensamblado que dpkg haria
    rc2, o2, e2 = sh(["bash", "-c", HOOK.replace('"$1"', '"%s"' % rootfs).replace('$1', rootfs)],
                     timeout=120)
    say("  ensamblado rc=%d" % rc2, (o2 + e2).strip()[-500:])
    return (rc == 0 and os.path.isdir(os.path.join(rootfs, "usr"))), n

def construir(rootfs):
    vias = [via1, via2, via3, via4]
    for f in vias:
        spec = f(rootfs)
        if spec is None:
            continue
        nombre, cmd, calidad = spec
        say(""); say("  >>>", nombre)
        sh(["bash", "-c", "rm -rf %s" % rootfs], timeout=300)
        if cmd is None:
            ok, n = correr_via4(rootfs)
            rc = 0 if ok else 1
        else:
            rc, o, e = sh(cmd, timeout=2700)
            say("  rc=%d" % rc)
            for l in (o.splitlines()[-12:] + e.splitlines()[-35:]):
                say("  MM |", l[:280])
            ok = (rc == 0 and os.path.isdir(os.path.join(rootfs, "usr")))
        if ok:
            say("  >>> ESTA VIA FUNCIONO. Calidad del rootfs:", calidad)
            return True, nombre, calidad
        say("  >>> fallo, sigo con la proxima")
    return False, "ninguna de las cuatro vias", "NINGUNO"

if __name__ == "__main__":
    rootfs = sys.argv[1] if len(sys.argv) > 1 else "/tmp/f001/rootfs"
    ok, via, calidad = construir(rootfs)
    out = os.environ.get("F001_OUT", "mediciones/f-001")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "rootfs-construccion.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    with open(os.path.join(out, "rootfs-construccion.json"), "w") as f:
        json.dump({"ok": ok, "via": via, "calidad": calidad}, f, indent=2, ensure_ascii=False)
    print(json.dumps({"ok": ok, "via": via, "calidad": calidad}))
    sys.exit(0 if ok else 3)
