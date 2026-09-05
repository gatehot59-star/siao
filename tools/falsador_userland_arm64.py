#!/usr/bin/env python3
"""
FALSADOR-001 v2 - El userland ARM64 de openKylin 3.0, fuera de su ISO.

Pregunta que puede dar ROJO:
  (A) Los binarios arm64 de openKylin 3.0 (huanghe) estan alineados a paginas
      de 16 KB, como exige Android 15+ en dispositivos nuevos?
  (B) Ese userland EJECUTA en un aarch64 ajeno (chroot en un runner de GitHub),
      o solo vive adentro de su propio ISO?

Por que hay un v2: el v1 dio B=ROJO y el ROJO era del INSTRUMENTO. El rootfs no
tenia base-files (los symlinks de merged-usr) ni libtinfo, asi que el PT_INTERP
no resolvia y el kernel contestaba ENOENT, indistinguible de "el binario no
existe". Y el control negativo devolvia la MISMA firma, o sea que no controlaba
nada. Los tres arreglos estan abajo, marcados v2.

Controles:
  - POSITIVO de (B): el bash del propio runner en chroot. Si falla, el
    instrumento esta roto y (B) es NO MEDIDO, no ROJO.
  - NEGATIVO de (B), v2: DOS firmas, ELF corrupto y ruta inexistente. Si
    coinciden, el control NO DISCRIMINA y (B) es NO MEDIDO.
  - GUARD DE PRECONDICION, v2: PT_INTERP y DT_NEEDED resueltos dentro del
    rootfs ANTES de ejecutar. Un rootfs incompleto no puede disfrazarse de
    ROJO de openKylin.
  - de (A): se imprime el p_align crudo de cada PT_LOAD. Un instrumento que
    solo dijera OK/FALLA no seria auditable.

Salida: JSON + markdown + salida cruda verbatim en mediciones/.
"""
import json, os, platform, re, shutil, struct, subprocess, sys, tarfile, time, urllib.request

MIRROR = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"          # openKylin 3.0
ARCH = "arm64"
# 16384 = 16 KB (Android 15+), 65536 = 64 KB (default de Debian/arm64 moderno),
# 4096 = 4 KB (lo que NO sirve en dispositivos de paginas grandes)
PAGE_16K = 16384
# v2: sin base-files no hay /lib -> usr/lib y el interprete no resuelve; sin
# libtinfo6 bash no arranca. Los demas son los DT_NEEDED de coreutils.
WANTED = ["base-files", "libc6", "libgcc-s1", "bash", "dash", "coreutils",
          "libtinfo6", "libselinux1", "libpcre2-8-0", "libacl1", "libattr1",
          "libgmp10"]
OUT = os.environ.get("FALSADOR_OUT", "mediciones")
WORK = os.environ.get("FALSADOR_WORK", "/tmp/falsador-work")

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line)
    print(line, flush=True)

def get(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": "siao-falsador/2"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()

# ---------------------------------------------------------------- ar (.deb)
def ar_members(blob):
    """Parser del formato ar en Python puro: no depende del binario 'ar'."""
    if blob[:8] != b"!<arch>\n":
        raise ValueError("no es un archivo ar: magic=%r" % blob[:8])
    off, out = 8, {}
    while off + 60 <= len(blob):
        hdr = blob[off:off+60]
        name = hdr[0:16].decode("latin1").strip().rstrip("/")
        size = int(hdr[48:58].decode("latin1").strip() or "0")
        out[name] = blob[off+60:off+60+size]
        off += 60 + size + (size % 2)
    return out

def decompress(name, data):
    if name.endswith(".xz") or name.endswith(".lzma"):
        import lzma; return lzma.decompress(data), "xz"
    if name.endswith(".gz"):
        import gzip; return gzip.decompress(data), "gz"
    if name.endswith(".zst"):
        try:
            import zstandard
            return zstandard.ZstdDecompressor().decompress(data, max_output_size=1 << 30), "zst"
        except Exception as e:
            raise RuntimeError("data.tar.zst y sin zstandard: %s" % e)
    if name.endswith(".tar"):
        return data, "raw"
    raise RuntimeError("compresion desconocida: %s" % name)

# ---------------------------------------------------------------- ELF
def elf_loads(path):
    """(arch, [(p_align, p_offset, p_vaddr, p_filesz)]) de los PT_LOAD.
    Se lee a mano: el resultado no depende de la arquitectura del lector, y eso
    es justamente lo que el job x64 comprueba."""
    with open(path, "rb") as f:
        h = f.read(64)
        if h[:4] != b"\x7fELF" or len(h) < 64:
            return None, []
        if h[4] != 2:
            return "elf32", []
        e = "<" if h[5] == 1 else ">"
        machine = struct.unpack_from(e + "H", h, 18)[0]
        arch = {183: "aarch64", 62: "x86_64", 243: "riscv"}.get(machine, "machine=%d" % machine)
        e_phoff = struct.unpack_from(e + "Q", h, 32)[0]
        e_phentsize = struct.unpack_from(e + "H", h, 54)[0]
        e_phnum = struct.unpack_from(e + "H", h, 56)[0]
        f.seek(e_phoff)
        ph = f.read(e_phentsize * e_phnum)
        loads = []
        for i in range(e_phnum):
            o = i * e_phentsize
            if o + 56 > len(ph):
                break
            if struct.unpack_from(e + "I", ph, o)[0] != 1:      # PT_LOAD
                continue
            loads.append((struct.unpack_from(e + "Q", ph, o + 48)[0],
                          struct.unpack_from(e + "Q", ph, o + 8)[0],
                          struct.unpack_from(e + "Q", ph, o + 16)[0],
                          struct.unpack_from(e + "Q", ph, o + 32)[0]))
        return arch, loads

def elf_dyn(path):
    """v2: (PT_INTERP, [DT_NEEDED]) leidos a mano. Sin ldd ni readelf, que no
    sirven cross-arch. Es la pieza que le faltaba al v1."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF" or len(data) < 64 or data[4] != 2:
        return None, []
    e = "<" if data[5] == 1 else ">"
    e_phoff = struct.unpack_from(e + "Q", data, 32)[0]
    e_phentsize = struct.unpack_from(e + "H", data, 54)[0]
    e_phnum = struct.unpack_from(e + "H", data, 56)[0]
    interp, dyn, loads = None, None, []
    for i in range(e_phnum):
        o = e_phoff + i * e_phentsize
        if o + 56 > len(data):
            break
        p_type = struct.unpack_from(e + "I", data, o)[0]
        p_offset = struct.unpack_from(e + "Q", data, o + 8)[0]
        p_vaddr = struct.unpack_from(e + "Q", data, o + 16)[0]
        p_filesz = struct.unpack_from(e + "Q", data, o + 32)[0]
        if p_type == 3:
            interp = data[p_offset:p_offset + p_filesz].split(b"\x00")[0].decode("latin1")
        elif p_type == 2:
            dyn = (p_offset, p_filesz)
        elif p_type == 1:
            loads.append((p_vaddr, p_offset, p_filesz))
    needed = []
    if dyn:
        off, size = dyn
        ents, i = [], off
        while i + 16 <= off + size and i + 16 <= len(data):
            tag, val = struct.unpack_from(e + "QQ", data, i)
            if tag == 0:
                break
            ents.append((tag, val))
            i += 16
        strt = [v for t, v in ents if t == 5]
        if strt:
            soff = None
            for vaddr, poff, fsz in loads:
                if vaddr <= strt[0] < vaddr + fsz:
                    soff = poff + (strt[0] - vaddr)
                    break
            if soff is not None:
                for t, v in ents:
                    if t == 1:
                        end = data.find(b"\x00", soff + v)
                        needed.append(data[soff + v:end].decode("latin1"))
    return interp, needed

# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    res = {
        "falsador": "FALSADOR-001", "version": 2,
        "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "maquina": {
            "arch": platform.machine(), "nproc": os.cpu_count(),
            "kernel": platform.release(),
            "pagesize": os.sysconf("SC_PAGESIZE") if hasattr(os, "sysconf") else None,
            "runner_os": os.environ.get("RUNNER_OS", "no-actions"),
            "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", "no-actions"),
        },
        "fuente": {"mirror": MIRROR, "suite": SUITE, "arch": ARCH},
        "A_alineacion": {"veredicto": "NO MEDIDO", "paquetes": {}},
        "B_ejecucion": {"veredicto": "NO MEDIDO"},
        "controles": {}, "no_medido": [],
    }
    say("== FALSADOR-001 v2 ==")
    say("maquina:", json.dumps(res["maquina"]))

    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    # ---- 0. indice de paquetes ------------------------------------------
    idx = None
    for comp in ("Packages.gz", "Packages.xz"):
        url = "%s/dists/%s/main/binary-%s/%s" % (MIRROR, SUITE, ARCH, comp)
        try:
            st, blob = get(url)
            say("INDICE", st, len(blob), "bytes", url)
            if comp.endswith(".xz"):
                import lzma; idx = lzma.decompress(blob).decode("utf-8", "replace")
            else:
                import gzip; idx = gzip.decompress(blob).decode("utf-8", "replace")
            res["fuente"]["indice"] = url
            break
        except Exception as ex:
            say("INDICE ERR", url, repr(ex)[:200])
    if not idx:
        say("ABORTO: sin indice de paquetes. A y B quedan NO MEDIDO.")
        res["no_medido"].append("indice de paquetes inaccesible")
        write(res); return 2
    say("INDICE lineas", idx.count("\n"))

    # ---- 1. resolver paquetes -------------------------------------------
    debs = {}
    for stanza in idx.split("\n\n"):
        m = re.search(r"^Package: (\S+)$", stanza, re.M)
        if not m or m.group(1) not in WANTED or m.group(1) in debs:
            continue
        fn = re.search(r"^Filename: (\S+)$", stanza, re.M)
        if not fn:
            continue
        ver = re.search(r"^Version: (\S+)$", stanza, re.M)
        sz = re.search(r"^Size: (\d+)$", stanza, re.M)
        sha = re.search(r"^SHA256: (\S+)$", stanza, re.M)
        debs[m.group(1)] = {"filename": fn.group(1),
                            "version": ver.group(1) if ver else "?",
                            "size": int(sz.group(1)) if sz else -1,
                            "sha256": sha.group(1) if sha else "?"}
    for k in WANTED:
        if k in debs:
            say("PAQUETE", k, debs[k]["version"], debs[k]["size"], "B")
    faltan = [w for w in WANTED if w not in debs]
    if faltan:
        say("NO ESTAN EN EL INDICE:", faltan)
        res["no_medido"].append("paquetes ausentes del indice: %s" % faltan)
    res["fuente"]["paquetes_ausentes"] = faltan

    # ---- 2. bajar, extraer, medir alineacion ---------------------------
    rootfs = os.path.join(WORK, "rootfs")
    os.makedirs(rootfs, exist_ok=True)
    aligns_all, vistos = [], set()
    for name in [w for w in WANTED if w in debs]:
        meta = debs[name]
        url = "%s/%s" % (MIRROR, meta["filename"])
        try:
            st, blob = get(url)
        except Exception as ex:
            say("DEB ERR", name, repr(ex)[:200])
            res["no_medido"].append("%s: descarga fallo" % name); continue
        import hashlib
        got = hashlib.sha256(blob).hexdigest()
        ok_hash = (got == meta["sha256"])
        say("DEB", st, len(blob), "B", name, "sha256_ok=%s" % ok_hash)
        if not ok_hash:
            say("  esperado", meta["sha256"]); say("  obtenido", got)
            res["no_medido"].append("%s: sha256 no coincide" % name); continue
        mem = ar_members(blob)
        dataname = [k for k in mem if k.startswith("data.tar")]
        if not dataname:
            say("  sin data.tar en el .deb:", list(mem)); continue
        try:
            raw, howto = decompress(dataname[0], mem[dataname[0]])
        except Exception as ex:
            say("  DESCOMPRESION FALLA", dataname[0], repr(ex)[:200])
            res["no_medido"].append("%s: %s" % (name, repr(ex)[:120])); continue
        import io
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            tf.extractall(rootfs, filter="tar")
        say("  extraido", dataname[0], "(%s)" % howto, len(raw), "B")
        res["A_alineacion"]["paquetes"][name] = {"version": meta["version"],
                                                 "compresion": howto}

    # medir TODOS los ELF del rootfs, una sola vez
    elfs = []
    for root, _d, files in os.walk(rootfs):
        for fn in files:
            p = os.path.join(root, fn)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            rel = os.path.relpath(p, rootfs)
            if rel in vistos:
                continue
            vistos.add(rel)
            try:
                arch, loads = elf_loads(p)
            except Exception:
                continue
            if not loads:
                continue
            al = sorted(set(a for a, _o, _v, _s in loads))
            elfs.append({"path": rel, "arch": arch, "p_align": al,
                         "loads": [{"align": a, "off": o, "vaddr": v, "filesz": s}
                                   for a, o, v, s in loads]})
            aligns_all.extend(al)
    res["A_alineacion"]["elfs"] = elfs[:60]

    # ---- 3. veredicto A ------------------------------------------------
    if aligns_all:
        uniq = sorted(set(aligns_all))
        peor = min(uniq)
        arches = sorted(set(e["arch"] for e in elfs))
        say("ELF medidos:", len(elfs), "| arquitecturas:", arches)
        say("ALINEACIONES CRUDAS observadas (p_align de PT_LOAD):", uniq)
        res["A_alineacion"].update({"p_align_observados": uniq, "minimo": peor,
                                    "elfs_medidos": len(elfs), "arquitecturas": arches})
        if peor >= PAGE_16K:
            res["A_alineacion"]["veredicto"] = "VERDE"
            say("A: VERDE - todo PT_LOAD alinea a >= 16384 (minimo observado %d)" % peor)
        else:
            res["A_alineacion"]["veredicto"] = "ROJO"
            say("A: ROJO - hay PT_LOAD con p_align %d < 16384: recompilar" % peor)
    else:
        say("A: NO MEDIDO - cero ELF leidos")
        res["no_medido"].append("cero ELF leidos")

    # ---- 4. (B) solo en aarch64 ----------------------------------------
    host_arch = platform.machine()
    if host_arch not in ("aarch64", "arm64"):
        res["B_ejecucion"] = {"veredicto": "NO MEDIDO",
                              "motivo": "el host es %s, no aarch64: un ELF arm64 no "
                                        "puede ejecutar aca sin emulador" % host_arch}
        res["no_medido"].append("B: host %s, no aarch64" % host_arch)
        say("B: NO MEDIDO -", res["B_ejecucion"]["motivo"])
        res["segundos"] = round(time.time() - t0, 1); write(res)
        say("FIN en", res["segundos"], "s"); return 0

    # v2: symlinks de merged-usr. base-files deberia traerlos; si no, se crean
    # A MANO y se DICE, porque un rootfs arreglado en silencio es un verde falso.
    creados = []
    for link, target in (("lib", "usr/lib"), ("bin", "usr/bin"),
                         ("sbin", "usr/sbin"), ("lib64", "usr/lib64")):
        lp = os.path.join(rootfs, link)
        tp = os.path.join(rootfs, target)
        if not os.path.exists(lp) and os.path.isdir(tp):
            os.symlink(target, lp); creados.append("%s -> %s" % (link, target))
    say("SYMLINKS merged-usr que base-files NO trajo y cree a mano:", creados or "ninguno")
    res["controles"]["symlinks_creados_a_mano"] = creados

    # elegir un sujeto que EXISTA (v1 asumia /bin/bash y no existia)
    cand = ["/usr/bin/bash", "/bin/bash", "/usr/bin/dash", "/bin/sh"]
    sujeto = None
    for c in cand:
        if os.path.isfile(os.path.join(rootfs, c.lstrip("/"))):
            sujeto = c; break
    say("SUJETO elegido:", sujeto, "| candidatos:", cand)
    res["B_ejecucion"]["sujeto"] = sujeto
    if not sujeto:
        res["B_ejecucion"] = {"veredicto": "NO MEDIDO",
                              "motivo": "ningun shell presente en el rootfs"}
        res["no_medido"].append("B: sin shell en el rootfs")
        say("B: NO MEDIDO - ningun shell en el rootfs")
        res["segundos"] = round(time.time() - t0, 1); write(res)
        return 0

    # v2: GUARD DE PRECONDICION. Esto es lo que le faltaba al v1.
    sp = os.path.join(rootfs, sujeto.lstrip("/"))
    interp, needed = elf_dyn(sp)
    say("PT_INTERP del sujeto:", interp)
    say("DT_NEEDED del sujeto:", needed)
    faltantes = []
    if interp:
        ip = os.path.join(rootfs, interp.lstrip("/"))
        if not os.path.exists(ip):
            faltantes.append("PT_INTERP %s" % interp)
        say("  interprete presente:", os.path.exists(ip), "->", ip)
    libmap = {}
    for root, _d, files in os.walk(rootfs):
        for fn in files + _d:
            libmap.setdefault(fn, os.path.join(root, fn))
    for so in needed:
        if so not in libmap:
            faltantes.append("DT_NEEDED %s" % so)
        say("  needed", so, "presente:", so in libmap)
    res["controles"]["precondicion_faltantes"] = faltantes
    if faltantes:
        res["B_ejecucion"] = {"veredicto": "NO MEDIDO", "sujeto": sujeto,
                             "motivo": "el rootfs esta incompleto: %s. Un ENOENT aca "
                                       "seria de MI rootfs, no de openKylin" % faltantes}
        res["no_medido"].append("B: rootfs incompleto: %s" % faltantes)
        say("B: NO MEDIDO - rootfs incompleto:", faltantes)
        res["segundos"] = round(time.time() - t0, 1); write(res)
        say("FIN en", res["segundos"], "s"); return 0
    say("GUARD DE PRECONDICION: pasa, interprete y librerias estan")

    # control POSITIVO
    pos = os.path.join(WORK, "poschroot")
    ok_pos = False
    try:
        for d in ("bin", "lib", "lib64", "usr/bin", "usr/lib"):
            os.makedirs(os.path.join(pos, d), exist_ok=True)
        sh = shutil.which("bash") or "/bin/bash"
        shutil.copy2(sh, os.path.join(pos, "bin", "bash"))
        ldd = subprocess.run(["ldd", sh], capture_output=True, text=True).stdout
        for so in re.findall(r"(/\S+\.so\S*)", ldd):
            if os.path.exists(so):
                dst = os.path.join(pos, so.lstrip("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(so, dst)
        r = subprocess.run(["chroot", pos, "/bin/bash", "-c", "echo CONTROL_POSITIVO_OK"],
                           capture_output=True, text=True, timeout=60)
        say("CONTROL POSITIVO rc=%d out=%r err=%r" % (r.returncode, r.stdout.strip(),
                                                      r.stderr.strip()[:200]))
        ok_pos = (r.returncode == 0 and "CONTROL_POSITIVO_OK" in r.stdout)
    except Exception as ex:
        say("CONTROL POSITIVO EXC", repr(ex)[:200])
    res["controles"]["positivo_chroot_del_runner"] = ok_pos

    # v2: DOS controles negativos, y se comparan las FIRMAS
    def firma(cmd):
        try:
            r = subprocess.run(["chroot", pos] + cmd, capture_output=True,
                               text=True, timeout=30)
            return r.returncode, r.stderr.strip()[:160]
        except Exception as ex:
            return -1, repr(ex)[:160]
    bad = os.path.join(pos, "bin", "roto")
    with open(bad, "wb") as f:
        f.write(b"\x7fELF" + os.urandom(400))
    os.chmod(bad, 0o755)
    rc_corrupto, err_corrupto = firma(["/bin/roto"])
    rc_inexistente, err_inexistente = firma(["/bin/no-existe-nunca"])
    say("CONTROL NEGATIVO 1 (ELF corrupto)    rc=%d err=%r" % (rc_corrupto, err_corrupto))
    say("CONTROL NEGATIVO 2 (ruta inexistente) rc=%d err=%r" % (rc_inexistente, err_inexistente))
    firmas_iguales = (err_corrupto.replace("roto", "X") == err_inexistente.replace("no-existe-nunca", "X"))
    discrimina = (rc_corrupto != 0 and rc_inexistente != 0 and not firmas_iguales)
    say("CONTROL NEGATIVO discrimina corrupto de inexistente:", discrimina,
        "(firmas iguales: %s)" % firmas_iguales)
    res["controles"].update({"negativo_elf_corrupto": {"rc": rc_corrupto, "err": err_corrupto},
                             "negativo_ruta_inexistente": {"rc": rc_inexistente,
                                                           "err": err_inexistente},
                             "negativo_discrimina": discrimina})

    if not ok_pos:
        res["B_ejecucion"].update({"veredicto": "NO MEDIDO",
                                   "motivo": "el control positivo no paso: chroot no sirve aca"})
        say("B: NO MEDIDO - control positivo fallado")
    else:
        pruebas = []
        for cmd in ([sujeto, "-c", "echo OPENKYLIN_USERLAND_VIVO"],
                    [sujeto, "--version"],
                    ["/usr/bin/uname", "-m"],
                    ["/usr/bin/env", "true"],
                    ["/usr/bin/ldd", "--version"]):
            try:
                r = subprocess.run(["chroot", rootfs] + cmd, capture_output=True,
                                   text=True, timeout=60)
                pruebas.append({"cmd": cmd, "rc": r.returncode,
                                "stdout": r.stdout[:500], "stderr": r.stderr[:500]})
                say("CHROOT openKylin", cmd, "rc=%d" % r.returncode,
                    "out=%r" % r.stdout.strip()[:200], "err=%r" % r.stderr.strip()[:200])
            except Exception as ex:
                pruebas.append({"cmd": cmd, "rc": -1, "stderr": repr(ex)[:300]})
                say("CHROOT openKylin", cmd, "EXC", repr(ex)[:200])
        res["B_ejecucion"]["pruebas"] = pruebas
        vivo = any(p["rc"] == 0 and "OPENKYLIN_USERLAND_VIVO" in p.get("stdout", "")
                   for p in pruebas)
        if vivo and not discrimina:
            # un verde con un control que no discrimina sigue siendo verde: el
            # control negativo protege contra falsos VERDES por ejecucion de
            # basura, y aca ejecuto y devolvio la cadena exacta esperada.
            say("NOTA: el control negativo no discrimino, pero B dio VERDE con la"
                " cadena exacta esperada, que la basura no puede producir")
        if vivo:
            res["B_ejecucion"]["veredicto"] = "VERDE"
        elif discrimina:
            res["B_ejecucion"]["veredicto"] = "ROJO"
        else:
            res["B_ejecucion"]["veredicto"] = "NO MEDIDO"
            res["B_ejecucion"]["motivo"] = ("no ejecuto, pero el control negativo no "
                                            "discrimina corrupto de inexistente: no puedo "
                                            "afirmar que el fallo sea de openKylin")
            res["no_medido"].append("B: fallo sin control que discrimine")
        say("B:", res["B_ejecucion"]["veredicto"],
            "- el userland arm64 de openKylin", "EJECUTA" if vivo else "NO EJECUTA",
            "en un aarch64 ajeno")

    res["segundos"] = round(time.time() - t0, 1)
    write(res)
    say("FIN en", res["segundos"], "s")
    return 0

def write(res):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "FALSADOR-001-userland-arm64.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "FALSADOR-001-userland-arm64-salida-cruda.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    a = res["A_alineacion"]["veredicto"]; b = res["B_ejecucion"]["veredicto"]
    md = ["# FALSADOR-001 v2 - el userland ARM64 de openKylin 3.0 fuera de su ISO", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** `%s`" % json.dumps(res["maquina"]), "",
          "| Pregunta | Veredicto |", "|---|---|",
          "| A - paginas de 16 KB (`p_align` >= 16384) | **%s** |" % a,
          "| B - ejecuta en un aarch64 ajeno (chroot) | **%s** |" % b, "",
          "Controles del instrumento:", "", "```json",
          json.dumps(res["controles"], indent=2, ensure_ascii=False), "```", "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Salida cruda, verbatim", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "FALSADOR-001-userland-arm64.md"), "w") as f:
        f.write("\n".join(md))

if __name__ == "__main__":
    sys.exit(main())
