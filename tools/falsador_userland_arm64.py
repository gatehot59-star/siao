#!/usr/bin/env python3
"""
FALSADOR-001 - El userland ARM64 de openKylin 3.0, fuera de su ISO.

Pregunta que puede dar ROJO:
  (A) Los binarios arm64 de openKylin 3.0 (huanghe) estan alineados a paginas
      de 16 KB, como exige Android 15+ en dispositivos nuevos?
  (B) Ese userland EJECUTA en un aarch64 ajeno (chroot en un runner de GitHub),
      o solo vive adentro de su propio ISO?

Controles:
  - Control POSITIVO de (B): /bin/bash del propio runner corre en chroot -> si
    esto falla, el instrumento esta roto y (B) queda NO MEDIDO, no ROJO.
  - Control NEGATIVO de (B): un ELF corrupto NO debe ejecutar. Si ejecuta,
    el instrumento no discrimina y todo (B) es invalido.
  - Control de (A): se imprime el p_align crudo de cada segmento LOAD. Un
    instrumento que solo dijera OK/FALLA no seria auditable.

Salida: JSON + markdown en mediciones/. Verbatim, sin recortar.
"""
import json, os, platform, re, shutil, struct, subprocess, sys, tarfile, time, urllib.request

MIRROR = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"          # openKylin 3.0
ARCH = "arm64"
# 16384 = 16 KB (Android 15+), 65536 = 64 KB (default de Debian/arm64 moderno),
# 4096 = 4 KB (lo que NO sirve en dispositivos de paginas grandes)
PAGE_16K = 16384
WANTED = ["libc6", "bash", "coreutils"]
OUT = os.environ.get("FALSADOR_OUT", "mediciones")
WORK = os.environ.get("FALSADOR_WORK", "/tmp/falsador-work")

log = []
def say(*a):
    line = " ".join(str(x) for x in a)
    log.append(line)
    print(line, flush=True)

def get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "siao-falsador/1"})
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
        data = blob[off+60:off+60+size]
        out[name] = data
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
    """Devuelve (arch, [(p_align, p_offset, p_vaddr, p_filesz)]) de los LOAD.
    Lee el ELF a mano: el resultado no depende de la arquitectura del lector."""
    with open(path, "rb") as f:
        h = f.read(64)
        if h[:4] != b"\x7fELF":
            return None, []
        is64 = h[4] == 2
        le = h[5] == 1
        e = "<" if le else ">"
        machine = struct.unpack_from(e + "H", h, 18)[0]
        arch = {183: "aarch64", 62: "x86_64", 243: "riscv"}.get(machine, "machine=%d" % machine)
        if not is64:
            return arch, []
        e_phoff = struct.unpack_from(e + "Q", h, 32)[0]
        e_phentsize = struct.unpack_from(e + "H", h, 54)[0]
        e_phnum = struct.unpack_from(e + "H", h, 56)[0]
        f.seek(e_phoff)
        ph = f.read(e_phentsize * e_phnum)
        loads = []
        for i in range(e_phnum):
            o = i * e_phentsize
            p_type = struct.unpack_from(e + "I", ph, o)[0]
            if p_type != 1:      # PT_LOAD
                continue
            p_offset = struct.unpack_from(e + "Q", ph, o + 8)[0]
            p_vaddr = struct.unpack_from(e + "Q", ph, o + 16)[0]
            p_filesz = struct.unpack_from(e + "Q", ph, o + 32)[0]
            p_align = struct.unpack_from(e + "Q", ph, o + 48)[0]
            loads.append((p_align, p_offset, p_vaddr, p_filesz))
        return arch, loads

# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    res = {
        "falsador": "FALSADOR-001",
        "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "maquina": {
            "arch": platform.machine(),
            "nproc": os.cpu_count(),
            "kernel": platform.release(),
            "runner_os": os.environ.get("RUNNER_OS", "no-actions"),
            "runner_arch": os.environ.get("RUNNER_ARCH", "no-actions"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", "no-actions"),
        },
        "fuente": {"mirror": MIRROR, "suite": SUITE, "arch": ARCH},
        "A_alineacion": {"veredicto": "NO MEDIDO", "paquetes": {}},
        "B_ejecucion": {"veredicto": "NO MEDIDO"},
        "controles": {},
        "no_medido": [],
    }
    say("== FALSADOR-001 ==")
    say("maquina:", json.dumps(res["maquina"]))

    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    # ---- 0. indice de paquetes ------------------------------------------
    idx = None
    for comp in ("Packages.xz", "Packages.gz"):
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

    # ---- 1. resolver los paquetes que queremos --------------------------
    debs = {}
    for stanza in idx.split("\n\n"):
        m = re.search(r"^Package: (\S+)$", stanza, re.M)
        if not m or m.group(1) not in WANTED:
            continue
        fn = re.search(r"^Filename: (\S+)$", stanza, re.M)
        ver = re.search(r"^Version: (\S+)$", stanza, re.M)
        sz = re.search(r"^Size: (\d+)$", stanza, re.M)
        sha = re.search(r"^SHA256: (\S+)$", stanza, re.M)
        if fn and m.group(1) not in debs:
            debs[m.group(1)] = {"filename": fn.group(1),
                                "version": ver.group(1) if ver else "?",
                                "size": int(sz.group(1)) if sz else -1,
                                "sha256": sha.group(1) if sha else "?"}
    for k, v in debs.items():
        say("PAQUETE", k, v["version"], v["size"], "B")
    faltan = [w for w in WANTED if w not in debs]
    if faltan:
        say("NO ESTAN EN EL INDICE:", faltan)
        res["no_medido"].append("paquetes ausentes del indice: %s" % faltan)

    # ---- 2. bajar, extraer, medir alineacion ---------------------------
    rootfs = os.path.join(WORK, "rootfs")
    os.makedirs(rootfs, exist_ok=True)
    aligns_all = []
    for name, meta in debs.items():
        url = "%s/%s" % (MIRROR, meta["filename"])
        try:
            st, blob = get(url)
        except Exception as ex:
            say("DEB ERR", name, repr(ex)[:200]); continue
        import hashlib
        got = hashlib.sha256(blob).hexdigest()
        ok_hash = (got == meta["sha256"])
        say("DEB", st, len(blob), "B", name, "sha256_ok=%s" % ok_hash)
        if not ok_hash:
            say("  esperado", meta["sha256"]); say("  obtenido", got)
            res["no_medido"].append("%s: sha256 no coincide" % name)
            continue
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
        # medir ELFs de este paquete
        pkg = {"version": meta["version"], "compresion": howto, "elfs": []}
        for root, _dirs, files in os.walk(rootfs):
            for fn in files:
                p = os.path.join(root, fn)
                if os.path.islink(p) or not os.path.isfile(p):
                    continue
                try:
                    arch, loads = elf_loads(p)
                except Exception:
                    continue
                if not loads:
                    continue
                al = sorted(set(a for a, _o, _v, _s in loads))
                rel = os.path.relpath(p, rootfs)
                if any(e["path"] == rel for e in pkg["elfs"]):
                    continue
                pkg["elfs"].append({"path": rel, "arch": arch, "p_align": al,
                                    "loads": [{"align": a, "off": o, "vaddr": v, "filesz": s}
                                              for a, o, v, s in loads]})
                aligns_all.extend(al)
        pkg["elfs"] = pkg["elfs"][:40]
        res["A_alineacion"]["paquetes"][name] = pkg

    # ---- 3. veredicto A ------------------------------------------------
    if aligns_all:
        uniq = sorted(set(aligns_all))
        peor = min(uniq)
        say("ALINEACIONES CRUDAS observadas (p_align de PT_LOAD):", uniq)
        res["A_alineacion"]["p_align_observados"] = uniq
        res["A_alineacion"]["minimo"] = peor
        res["A_alineacion"]["elfs_medidos"] = len(aligns_all)
        if peor >= PAGE_16K:
            res["A_alineacion"]["veredicto"] = "VERDE"
            say("A: VERDE - todo LOAD alinea a >= 16384 (min %d)" % peor)
        else:
            res["A_alineacion"]["veredicto"] = "ROJO"
            say("A: ROJO - hay LOAD con p_align %d < 16384: hay que recompilar" % peor)
    else:
        say("A: NO MEDIDO - cero ELF leidos")
        res["no_medido"].append("cero ELF leidos")

    # ---- 4. controles y veredicto B (ejecucion real) -------------------
    host_arch = platform.machine()
    if host_arch not in ("aarch64", "arm64"):
        res["B_ejecucion"]["veredicto"] = "NO MEDIDO"
        res["B_ejecucion"]["motivo"] = ("el host es %s, no aarch64: un ELF arm64 no "
                                        "puede ejecutar aca sin emulador" % host_arch)
        res["no_medido"].append("B: host %s, no aarch64" % host_arch)
        say("B: NO MEDIDO -", res["B_ejecucion"]["motivo"])
    else:
        # control POSITIVO: el bash del propio runner en chroot
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
            say("CONTROL POSITIVO rc=%d out=%r err=%r" % (r.returncode, r.stdout.strip(), r.stderr.strip()[:200]))
            ok_pos = (r.returncode == 0 and "CONTROL_POSITIVO_OK" in r.stdout)
        except Exception as ex:
            say("CONTROL POSITIVO EXC", repr(ex)[:200])
        res["controles"]["positivo_chroot_del_runner"] = ok_pos

        # control NEGATIVO: un ELF corrupto NO debe ejecutar
        ok_neg = False
        try:
            bad = os.path.join(pos, "bin", "roto")
            with open(bad, "wb") as f:
                f.write(b"\x7fELF" + os.urandom(200))
            os.chmod(bad, 0o755)
            r = subprocess.run(["chroot", pos, "/bin/roto"], capture_output=True, text=True, timeout=30)
            say("CONTROL NEGATIVO rc=%d err=%r" % (r.returncode, r.stderr.strip()[:120]))
            ok_neg = (r.returncode != 0)
        except Exception as ex:
            say("CONTROL NEGATIVO (excepcion = no ejecuto, correcto)", repr(ex)[:120])
            ok_neg = True
        res["controles"]["negativo_elf_corrupto_no_ejecuta"] = ok_neg

        if not (ok_pos and ok_neg):
            res["B_ejecucion"]["veredicto"] = "NO MEDIDO"
            res["B_ejecucion"]["motivo"] = "los controles del instrumento no pasaron"
            say("B: NO MEDIDO - instrumento no validado (pos=%s neg=%s)" % (ok_pos, ok_neg))
        else:
            # EL FALSADOR: el bash de openKylin, con SU glibc, en chroot
            pruebas = []
            for cmd in (["/bin/bash", "-c", "echo OPENKYLIN_USERLAND_VIVO"],
                        ["/bin/bash", "--version"],
                        ["/usr/bin/uname", "-m"],
                        ["/usr/bin/env", "true"]):
                try:
                    r = subprocess.run(["chroot", rootfs] + cmd, capture_output=True,
                                       text=True, timeout=60)
                    pruebas.append({"cmd": cmd, "rc": r.returncode,
                                    "stdout": r.stdout[:400], "stderr": r.stderr[:400]})
                    say("CHROOT openKylin", cmd, "rc=%d" % r.returncode,
                        "out=%r" % r.stdout.strip()[:120], "err=%r" % r.stderr.strip()[:200])
                except Exception as ex:
                    pruebas.append({"cmd": cmd, "rc": -1, "stderr": repr(ex)[:300]})
                    say("CHROOT openKylin", cmd, "EXC", repr(ex)[:200])
            res["B_ejecucion"]["pruebas"] = pruebas
            vivo = any(p["rc"] == 0 and "OPENKYLIN_USERLAND_VIVO" in p.get("stdout", "")
                       for p in pruebas)
            res["B_ejecucion"]["veredicto"] = "VERDE" if vivo else "ROJO"
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
    md = ["# FALSADOR-001 - el userland ARM64 de openKylin 3.0 fuera de su ISO", "",
          "**Fecha (UTC):** %s" % res["fecha_utc"],
          "**Maquina:** %s" % json.dumps(res["maquina"]), "",
          "| Pregunta | Veredicto |", "|---|---|",
          "| A - paginas de 16 KB (`p_align` >= 16384) | **%s** |" % a,
          "| B - ejecuta en un aarch64 ajeno (chroot) | **%s** |" % b, "",
          "Controles del instrumento: `%s`" % json.dumps(res["controles"]), "",
          "NO MEDIDO: %s" % (res["no_medido"] or "nada"), "",
          "## Salida cruda, verbatim", "", "```plain", "\n".join(log), "```", ""]
    with open(os.path.join(OUT, "FALSADOR-001-userland-arm64.md"), "w") as f:
        f.write("\n".join(md))

if __name__ == "__main__":
    sys.exit(main())
