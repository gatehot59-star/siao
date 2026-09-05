#!/usr/bin/env python3
"""
FALSADOR F-001 - Arranca el userland openKylin sobre un kernel GKI REAL?

Cuatro brazos, y son sujetos DISTINTOS a proposito:

  C) EL .config REAL DEL GKI. Se baja el gki-certified-boot de Google, se saca el
     Image del boot.img y se extrae el .config EMBEBIDO (IKCFG_ST). Esto cierra
     el caveat que declare en el ADR-002: un defconfig NO es un .config.
     Ademas se corre lxc-checkconfig contra ese config real.

  F002) EL ROOTFS con mmdebstrap contra los repos apt de openKylin (H3 del
     auditor: ningun ISO es el punto de partida). Se mide su tamano real.

  F003) p_align sobre ESE rootfs, a escala, no sobre 12 paquetes.

  P) CONTROL POSITIVO: el rootfs arranca en QEMU con el kernel del PROPIO runner.
  S) EL SUJETO: el mismo rootfs, el mismo arnes, con el Image del GKI.

POR QUE INITRAMFS Y NO DISCO: el brazo C mide que en GKI CONFIG_VIRTIO_BLK y
CONFIG_VIRTIO_PCI son MODULOS, y los modulos viven en system_dlkm, fuera del
boot.img. Con disco virtio el GKI no podria montar la raiz NUNCA, y eso seria un
limite del ARNES disfrazado de ROJO del userland. Con initramfs no hace falta
ningun driver de bloque, y P y S usan EXACTAMENTE el mismo metodo: la unica
variable es el kernel. Eso es lo que hace valida la comparacion.
"""
import gzip, json, os, platform, re, struct, subprocess, sys, time, urllib.request, zipfile, zlib

GKI_URLS = [
    ("android16-6.12", "https://dl.google.com/android/gki/gki-certified-boot-android16-6.12-2026-06_r1.zip"),
    ("android15-6.6",  "https://dl.google.com/android/gki/gki-certified-boot-android15-6.6-2025-01_r1.zip"),
]
MIRROR = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
OUT = os.environ.get("F001_OUT", "mediciones/f-001")
WORK = os.environ.get("F001_WORK", "/tmp/f001")

NEED = ["CONFIG_NAMESPACES", "CONFIG_PID_NS", "CONFIG_USER_NS", "CONFIG_IPC_NS",
        "CONFIG_NET_NS", "CONFIG_UTS_NS", "CONFIG_CGROUPS", "CONFIG_MEMCG",
        "CONFIG_CGROUP_BPF", "CONFIG_CGROUP_SCHED", "CONFIG_CGROUP_FREEZER",
        "CONFIG_CGROUP_DEVICE", "CONFIG_CGROUP_PIDS", "CONFIG_SECCOMP",
        "CONFIG_SECCOMP_FILTER", "CONFIG_FANOTIFY", "CONFIG_INOTIFY_USER",
        "CONFIG_TMPFS", "CONFIG_TMPFS_POSIX_ACL", "CONFIG_TMPFS_XATTR",
        "CONFIG_DEVTMPFS", "CONFIG_PROC_FS", "CONFIG_SYSFS", "CONFIG_AUTOFS_FS",
        "CONFIG_OVERLAY_FS", "CONFIG_SQUASHFS", "CONFIG_EXT4_FS", "CONFIG_VETH",
        "CONFIG_BRIDGE", "CONFIG_MACVLAN", "CONFIG_VIRTIO", "CONFIG_VIRTIO_PCI",
        "CONFIG_VIRTIO_BLK", "CONFIG_VIRTIO_NET", "CONFIG_VIRTIO_CONSOLE",
        "CONFIG_VIRTIO_MMIO", "CONFIG_SERIAL_AMBA_PL011",
        "CONFIG_SERIAL_AMBA_PL011_CONSOLE", "CONFIG_BLK_DEV_INITRD",
        "CONFIG_RD_GZIP", "CONFIG_ANDROID_BINDERFS", "CONFIG_ANDROID_BINDER_IPC",
        "CONFIG_KEYS", "CONFIG_BLK_DEV_LOOP", "CONFIG_CHECKPOINT_RESTORE",
        "CONFIG_IKCONFIG", "CONFIG_MODULES", "CONFIG_ARM64_16K_PAGES",
        "CONFIG_ARM64_4K_PAGES", "CONFIG_ARM64_64K_PAGES"]

# Lo que LXC necesita para EXISTIR. Sin esto no hay contenedor de apps.
CRITICOS_LXC = ["CONFIG_PID_NS", "CONFIG_USER_NS", "CONFIG_NET_NS", "CONFIG_IPC_NS",
                "CONFIG_UTS_NS", "CONFIG_CGROUPS"]

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line); print(line, flush=True)

def sh(cmd, timeout=1800, env=None):
    pretty = cmd if isinstance(cmd, str) else " ".join(cmd)
    say("$", pretty[:400])
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout, env=env)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        def dec(x):
            if x is None:
                return ""
            return x.decode("utf-8", "replace") if isinstance(x, bytes) else x
        return -9, dec(e.stdout), "TIMEOUT tras %ss" % timeout
    except Exception as e:
        return -1, "", repr(e)[:300]

def get(url, timeout=420):
    req = urllib.request.Request(url, headers={"User-Agent": "siao-f001/2"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()

def kernel_from_bootimg(blob):
    if blob[:8] != b"ANDROID!":
        return None, "magic no es ANDROID!: %r" % blob[:8]
    kernel_size = struct.unpack_from("<I", blob, 8)[0]
    hdr = struct.unpack_from("<I", blob, 40)[0]
    page = 4096 if hdr >= 3 else (struct.unpack_from("<I", blob, 36)[0] or 2048)
    return blob[page:page + kernel_size], "hdr_v%d kernel_size=%d page=%d" % (hdr, kernel_size, page)

def maybe_decompress(k):
    if k[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(k), "gzip"
        except Exception:
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            return d.decompress(k), "gzip-parcial"
    if k[:4] == b"\x04\x22\x4d\x18":
        try:
            import lz4.frame
            return lz4.frame.decompress(k), "lz4"
        except Exception as ex:
            return k, "lz4-sin-lib(%s)" % repr(ex)[:50]
    return k, "crudo"

def extract_ikconfig(blob):
    i = blob.find(b"IKCFG_ST")
    if i < 0:
        return None, "no hay marca IKCFG_ST"
    j = blob.find(b"IKCFG_ED", i + 8)
    chunk = blob[i + 8: j if j > 0 else len(blob)]
    if chunk[:2] != b"\x1f\x8b":
        return None, "tras IKCFG_ST no hay gzip: %r" % chunk[:4]
    try:
        return gzip.decompress(chunk).decode("utf-8", "replace"), "ok (%d B gz)" % len(chunk)
    except Exception:
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            return d.decompress(chunk).decode("utf-8", "replace"), "gzip parcial"
        except Exception as ex:
            return None, "gunzip fallo: %s" % repr(ex)[:80]

def leer_config(txt):
    got = {}
    for line in txt.splitlines():
        line = line.strip()
        m = re.match(r"^(CONFIG_[A-Z0-9_]+)=(.*)$", line)
        if m:
            got[m.group(1)] = m.group(2)
        m2 = re.match(r"^# (CONFIG_[A-Z0-9_]+) is not set$", line)
        if m2:
            got[m2.group(1)] = "n"
    return got

def hitos_de(texto):
    return {
        "kernel arranco": bool(re.search(r"Booting Linux on physical CPU|Linux version", texto)),
        "desempaco initramfs": bool(re.search(r"Unpacking initramfs|Freeing initrd", texto)),
        "systemd arranco": bool(re.search(r"systemd\[1\]|systemd v?\d+ running|Detected architecture", texto)),
        "llego a basic.target": "Reached target Basic System" in texto or "basic.target" in texto,
        "llego a multi-user": "Reached target Multi-User" in texto or "Reached target multi-user" in texto,
        "panic": "Kernel panic" in texto,
        "sin init": bool(re.search(r"No working init|Failed to execute .*init|Requested init", texto)),
    }

def main():
    t0 = time.time()
    res = {"falsador": "F-001", "version": 2,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "maquina": {"arch": platform.machine(), "nproc": os.cpu_count(),
                       "kernel": platform.release(), "pagesize": os.sysconf("SC_PAGESIZE"),
                       "kvm": os.path.exists("/dev/kvm"),
                       "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
                       "run_id": os.environ.get("GITHUB_RUN_ID", "no-actions")},
           "C_config_real_del_gki": {"veredicto": "NO MEDIDO"},
           "F002_rootfs": {"veredicto": "NO MEDIDO"},
           "F003_alineacion": {"veredicto": "NO MEDIDO"},
           "P_control_positivo": {"veredicto": "NO MEDIDO"},
           "S_sujeto_gki": {"veredicto": "NO MEDIDO"},
           "prediccion_registrada_antes_de_correr": (
               "Predigo que S NO va a llegar a multi-user: si CONFIG_PID_NS esta apagado en "
               "el config real, systemd no puede armar namespaces de PID. Lo escribo ANTES "
               "para que el resultado pueda refutarme."),
           "no_medido": []}
    say("== FALSADOR F-001 v2 ==")
    say("maquina:", json.dumps(res["maquina"]))
    say("PREDICCION registrada antes de correr:", res["prediccion_registrada_antes_de_correr"])
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)

    if res["maquina"]["arch"] not in ("aarch64", "arm64"):
        res["no_medido"].append("host %s, no aarch64" % res["maquina"]["arch"])
        say("ABORTO: F-001 exige aarch64 nativo"); write(res); return 0

    # ---------------- BRAZO C ------------------------------------------
    say(""); say("--- BRAZO C: el .config REAL del GKI ---")
    gki_image, gki_cfg = None, {}
    for rama, url in GKI_URLS:
        try:
            st, blob = get(url)
        except Exception as ex:
            say("GKI ERR", rama, repr(ex)[:160]); continue
        import hashlib
        say("GKI", st, len(blob), "B", rama, "sha256", hashlib.sha256(blob).hexdigest())
        zp = os.path.join(WORK, "gki-%s.zip" % rama)
        open(zp, "wb").write(blob)
        raw = None
        with zipfile.ZipFile(zp) as z:
            say("  zip contiene:", [(i.filename, i.file_size) for i in z.infolist()])
            for i in z.infolist():
                if i.filename.endswith(".img"):
                    raw = z.read(i); say("  img:", i.filename, len(raw), "B"); break
        if raw is None:
            say("  sin .img"); continue
        k, info = kernel_from_bootimg(raw); say("  boot.img:", info)
        if not k:
            continue
        k2, how = maybe_decompress(k); say("  kernel:", len(k), "->", len(k2), "B (%s)" % how)
        cfg, cinfo = extract_ikconfig(k2); say("  ikconfig:", cinfo)
        if not cfg:
            res["no_medido"].append("sin ikconfig en %s" % rama); continue
        got = leer_config(cfg)
        mver = re.search(r"Linux/arm64 (\S+)", cfg)
        ver = mver.group(1) if mver else "?"
        say("  .config REAL de Linux/arm64 %s: %d simbolos, %d lineas" % (ver, len(got), cfg.count("\n")))
        cp = os.path.join(OUT, "gki-%s.config" % rama)
        open(cp, "w").write(cfg)
        say("  commiteado en:", cp)
        si, mods, off, aus = [], [], [], []
        for kk in NEED:
            v = got.get(kk)
            if v is None:
                aus.append(kk); est = "AUSENTE del .config"
            elif v == "n":
                off.append(kk); est = "APAGADO (# is not set)"
            elif v == "m":
                mods.append(kk); est = "=m MODULO (vive en system_dlkm, NO en el boot.img)"
            else:
                si.append(kk); est = "=" + v
            say("    %-42s %s" % (kk, est))
        criticos_off = [k_ for k_ in CRITICOS_LXC if got.get(k_) in (None, "n")]
        say("  --> APAGADOS:", off)
        say("  --> MODULOS:", mods)
        say("  --> AUSENTES:", aus)
        say("  --> CRITICOS PARA UN CONTENEDOR, apagados o ausentes:", criticos_off)
        rc, o, e = sh(["bash", "-c", "CONFIG=%s lxc-checkconfig" % cp], timeout=180)
        limpio = re.sub(r"\x1b\[[0-9;]*m", "", o + e)
        say("  lxc-checkconfig rc=%d" % rc)
        for line in limpio.splitlines():
            say("    LXC |", line)
        veredicto_c = "ROJO" if criticos_off else "VERDE"
        res["C_config_real_del_gki"] = {
            "veredicto": veredicto_c, "rama": rama, "url": url, "kernel": ver,
            "sha256_zip": hashlib.sha256(blob).hexdigest(), "simbolos": len(got),
            "en_y": si, "modulos": mods, "apagados": off, "ausentes": aus,
            "criticos_lxc_apagados": criticos_off, "config_commiteado": cp,
            "lxc_checkconfig_rc": rc, "lxc_checkconfig": limpio[:8000]}
        gki_cfg = got
        gki_image = os.path.join(WORK, "Image-%s" % rama)
        open(gki_image, "wb").write(k2)
        res["S_sujeto_gki"]["rama"] = rama
        say("C:", veredicto_c, "- criticos apagados:", criticos_off or "ninguno")
        break

    # ---------------- F-002: rootfs -------------------------------------
    say(""); say("--- F-002: rootfs openKylin arm64 con mmdebstrap ---")
    rootfs = os.path.join(WORK, "rootfs")
    rc, o, e = sh(["mmdebstrap", "--architectures=arm64", "--variant=important",
                   "--include=" + ",".join(PKGS),
                   '--aptopt=Acquire::AllowInsecureRepositories "true"',
                   '--aptopt=APT::Get::AllowUnauthenticated "true"',
                   SUITE, rootfs,
                   "deb [trusted=yes] %s %s main" % (MIRROR, SUITE)], timeout=2700)
    say("mmdebstrap rc=%d" % rc)
    for line in (o.splitlines()[-20:] + e.splitlines()[-45:]):
        say("  MM |", line[:280])
    if rc != 0 or not os.path.isdir(os.path.join(rootfs, "usr")):
        res["F002_rootfs"] = {"veredicto": "ROJO", "rc": rc}
        res["no_medido"].append("sin rootfs: P y S quedan NO MEDIDO")
        say("F-002: ROJO. Sin rootfs no hay nada que arrancar."); write(res); return 0
    rc2, o2, _ = sh(["bash", "-c", "du -sb %s | cut -f1" % rootfs])
    size = int((o2.strip() or "0").split()[0])
    rc3, o3, e3 = sh(["bash", "-c", "cat %s/etc/os-release 2>/dev/null | head -5" % rootfs])
    rc4, o4, _ = sh(["bash", "-c", "ls %s/lib/systemd/systemd %s/usr/lib/systemd/systemd 2>&1" % (rootfs, rootfs)])
    say("rootfs: %d B (%.3f GiB)" % (size, size / 1073741824.0))
    say("os-release del rootfs:"); [say("  |", l) for l in o3.splitlines()]
    say("systemd presente:", o4.strip()[:200])
    res["F002_rootfs"] = {"veredicto": "VERDE", "bytes": size,
                          "gib": round(size / 1073741824.0, 3), "paquetes": PKGS,
                          "os_release": o3.strip(), "systemd": o4.strip()[:200]}

    # ---------------- F-003: alineacion a escala ------------------------
    aligns, nelf = {}, 0
    for root, _d, files in os.walk(rootfs):
        for fn in files:
            p = os.path.join(root, fn)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            try:
                with open(p, "rb") as f:
                    h = f.read(64)
                    if h[:4] != b"\x7fELF" or len(h) < 64 or h[4] != 2:
                        continue
                    e_ = "<" if h[5] == 1 else ">"
                    phoff = struct.unpack_from(e_ + "Q", h, 32)[0]
                    phes = struct.unpack_from(e_ + "H", h, 54)[0]
                    phn = struct.unpack_from(e_ + "H", h, 56)[0]
                    f.seek(phoff); ph = f.read(phes * phn)
                for i in range(phn):
                    o_ = i * phes
                    if o_ + 56 > len(ph):
                        break
                    if struct.unpack_from(e_ + "I", ph, o_)[0] != 1:
                        continue
                    al = struct.unpack_from(e_ + "Q", ph, o_ + 48)[0]
                    aligns[al] = aligns.get(al, 0) + 1
                nelf += 1
            except Exception:
                continue
    say("F-003 a escala: %d ELF | p_align: %s" % (nelf, dict(sorted(aligns.items()))))
    res["F003_alineacion"] = {"elfs": nelf, "p_align": {str(k): v for k, v in sorted(aligns.items())},
                              "minimo": (min(aligns) if aligns else None),
                              "veredicto": ("VERDE" if aligns and min(aligns) >= 16384
                                            else ("ROJO" if aligns else "NO MEDIDO"))}
    say("F-003:", res["F003_alineacion"]["veredicto"])

    # ---------------- initramfs comun a P y S ---------------------------
    say(""); say("--- el arnes: initramfs, porque virtio_blk es MODULO en GKI ---")
    cpio = os.path.join(WORK, "rootfs.cpio.gz")
    rc, o, e = sh(["bash", "-c",
                   "cd %s && find . -print0 | cpio --null -o -H newc 2>/dev/null | gzip -1 > %s"
                   % (rootfs, cpio)], timeout=1800)
    tam = os.path.getsize(cpio) if os.path.exists(cpio) else 0
    say("cpio.gz rc=%d | %d B (%.0f MiB)" % (rc, tam, tam / 1048576.0))
    if tam < 1000000:
        res["no_medido"].append("initramfs no se armo: P y S NO MEDIDO")
        say("sin initramfs: P y S quedan NO MEDIDO"); write(res); return 0

    def arrancar(nombre, kernel, seg=600):
        cons = os.path.join(WORK, "consola-%s.log" % nombre)
        append = ("rdinit=/lib/systemd/systemd console=ttyAMA0 systemd.log_level=info "
                  "systemd.show_status=true systemd.log_target=console "
                  "systemd.unit=multi-user.target panic=5")
        cmd = ["qemu-system-aarch64", "-M", "virt", "-cpu", "max", "-smp", "2", "-m", "4096",
               "-kernel", kernel, "-initrd", cpio, "-append", append,
               "-display", "none", "-no-reboot", "-serial", "file:%s" % cons]
        if os.path.exists("/dev/kvm"):
            cmd.insert(1, "-enable-kvm")
        rc, o, e = sh(cmd, timeout=seg)
        txt = open(cons, "rb").read().decode("utf-8", "replace") if os.path.exists(cons) else ""
        say("QEMU[%s] rc=%d | consola %d B" % (nombre, rc, len(txt)))
        if e.strip():
            say("  qemu stderr:", e.strip()[:400])
        dst = os.path.join(OUT, "consola-%s.log" % nombre)
        open(dst, "w").write(txt)
        return rc, txt, dst

    # ---------------- P: control positivo -------------------------------
    say(""); say("--- P: CONTROL POSITIVO (kernel del propio runner) ---")
    kus = sorted([os.path.join("/boot", f) for f in os.listdir("/boot")
                  if f.startswith("vmlinuz")], reverse=True) if os.path.isdir("/boot") else []
    say("kernels del runner:", kus)
    if not kus:
        res["no_medido"].append("sin kernel del runner: no hay control positivo, S es NO MEDIDO")
        say("P: NO MEDIDO - no hay /boot/vmlinuz")
    else:
        rc, txt, dst = arrancar("control-positivo", kus[0])
        h = hitos_de(txt)
        for k_, v_ in h.items():
            say("  [P] %-22s %s" % (k_, v_))
        for line in txt.splitlines()[-50:]:
            say("  P |", line[:200])
        ok = h["systemd arranco"]
        res["P_control_positivo"] = {"veredicto": "VERDE" if ok else "ROJO", "hitos": h,
                                     "kernel": kus[0], "consola": dst, "qemu_rc": rc,
                                     "llego_a_multiuser": h["llego a multi-user"]}
        say("P:", res["P_control_positivo"]["veredicto"],
            "(systemd corrio: %s | multi-user: %s)" % (h["systemd arranco"], h["llego a multi-user"]))

    # ---------------- S: el sujeto --------------------------------------
    say(""); say("--- S: EL SUJETO (Image del GKI, MISMO arnes) ---")
    if not gki_image:
        res["S_sujeto_gki"]["veredicto"] = "NO MEDIDO"
        res["S_sujeto_gki"]["motivo"] = "no consegui el Image del GKI"
        say("S: NO MEDIDO - sin Image")
    elif res["P_control_positivo"].get("veredicto") != "VERDE":
        res["S_sujeto_gki"]["veredicto"] = "NO MEDIDO"
        res["S_sujeto_gki"]["motivo"] = ("el control positivo no dio VERDE: el arnes no sirve "
                                         "de instrumento, asi que un fallo del GKI no seria "
                                         "atribuible al GKI")
        say("S: NO MEDIDO - control positivo fallado")
    else:
        rc, txt, dst = arrancar("sujeto-gki", gki_image)
        h = hitos_de(txt)
        for k_, v_ in h.items():
            say("  [S] %-22s %s" % (k_, v_))
        for line in txt.splitlines()[-70:]:
            say("  S |", line[:200])
        if h["llego a multi-user"]:
            v = "VERDE"
        elif h["systemd arranco"]:
            v = "AMARILLO"
        elif h["kernel arranco"]:
            v = "ROJO"
        else:
            v = "NO MEDIDO"
        res["S_sujeto_gki"].update({"veredicto": v, "hitos": h, "consola": dst, "qemu_rc": rc})
        say("S:", v)
        pred_ok = not h["llego a multi-user"]
        res["prediccion_acerto"] = pred_ok
        say("La prediccion que registre antes de correr", "ACERTO" if pred_ok else "SE REFUTO")

    res["segundos"] = round(time.time() - t0, 1)
    write(res); say("FIN en", res["segundos"], "s")
    return 0

def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "F-001.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "F-001-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    md = ["# FALSADOR F-001 v2 - userland openKylin sobre kernel GKI real", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "| Brazo | Veredicto |", "|---|---|",
          "| C - `.config` REAL del GKI | **%s** |" % res["C_config_real_del_gki"].get("veredicto"),
          "| F-002 - rootfs con mmdebstrap | **%s** |" % res["F002_rootfs"].get("veredicto"),
          "| F-003 - alineacion sobre ese rootfs | **%s** |" % res["F003_alineacion"].get("veredicto"),
          "| P - control positivo | **%s** |" % res["P_control_positivo"].get("veredicto"),
          "| S - SUJETO: GKI | **%s** |" % res["S_sujeto_gki"].get("veredicto"), "",
          "Prediccion registrada antes de correr: %s" % res["prediccion_registrada_antes_de_correr"],
          "", "Acerto: %s" % res.get("prediccion_acerto", "sin dato"), "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Salida cruda, verbatim", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "F-001.md"), "w") as f:
        f.write("\n".join(md))

if __name__ == "__main__":
    sys.exit(main())
