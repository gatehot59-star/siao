#!/usr/bin/env python3
"""
F-001-S1 paso 0: el ARNES de QEMU, medido antes de gastar un build de kernel.

DE DONDE SALE ESTE FALSADOR: del Doc de KVM que Abraham me paso, que mide tres
cosas que cambian el diseno de F-001-S1 y que yo NO habia medido:
     Actions x64   -> /dev/kvm USABLE con usermod -aG kvm (api 12, create_vm 4)
     Actions arm64 -> /dev/kvm NO EXISTE
     brain-env     -> /dev/kvm NO EXISTE

LA CONSECUENCIA QUE EL DOC NO SACA: el kernel de SIAO es aarch64, y KVM solo
acelera cuando huesped y anfitrion comparten ISA. En x64 hay KVM pero el huesped
es arm64 -> no aplica. En arm64 la ISA coincide pero NO HAY /dev/kvm. O sea que
F-001-S1 va por TCG en las dos, y el dato util del doc es el inverso del titular:
sirve para NO perder tiempo buscando aceleracion que para este caso no existe.

DOS DEFECTOS MIOS, los dos medidos y los dos corregidos aca:
  1. (run 15:17) el zip trae 'boot-6.6.img' y mi filtro pedia endswith('boot.img').
     No fallo: se salteo, con rc=0 y sin veredicto. Guard demasiado estrecho.
  2. (run 15:23) 'failed to find romfile efi-virtio.rom', rc=1 en 0,1 s. La maquina
     'virt' agrega una NIC virtio por defecto y su ROM de arranque PXE viene en el
     paquete ipxe-qemu. NO era el kernel ni QEMU: era mi invocacion. Se arregla con
     -nic none (la red no hace falta para arrancar sin rootfs) y con el paquete.
  Los dos los delato la salida cruda, no una relectura del codigo.

Y UN CONTROL POSITIVO, porque un instrumento que no puede dar rojo no mide nada:
  antes del arranque real, se corre QEMU con un -kernel que NO existe. Si eso
  tambien dijera 'VERDE', el instrumento seria un adorno.

PREDICCION DECLARADA ANTES DE CORRER:
  el control positivo falla, y el arranque real imprime el banner de Linux y entra
  en panico por falta de init. Ese panico es el VERDE del arnes.
"""
import json, os, re, shutil, struct, subprocess, time, urllib.request, zipfile

OUT = os.environ.get("F001_OUT", "mediciones/f-001-s1")
WORK = os.environ.get("F001_WORK", "/tmp/f001s1")
QEMU_BASE = ("qemu-system-aarch64 -machine virt -cpu cortex-a57 -smp 2 -m 2048 "
             "-nographic -no-reboot -nic none")
log = []


def w(*a):
    s = " ".join(str(x) for x in a)
    log.append(s)
    print(s, flush=True)


def sh(cmd, t=1800, guardar=None):
    w("$", cmd[:280])
    t0 = time.time()
    try:
        r = subprocess.run(["bash", "-c", "set -o pipefail; " + cmd],
                           capture_output=True, text=True, timeout=t)
        rc, o, e = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        rc, o, e = -9, "", "TIMEOUT tras %ss" % t
    except Exception as ex:
        rc, o, e = -1, "", repr(ex)[:200]
    w("  rc=%d en %.1f s | out %d B | err %d B" % (rc, time.time() - t0, len(o), len(e)))
    if guardar:
        os.makedirs(os.path.dirname(guardar), exist_ok=True)
        open(guardar, "w").write("### comando\n%s\n\n### rc\n%d\n\n### stdout ENTERO\n%s\n\n"
                                 "### stderr ENTERO\n%s\n" % (cmd, rc, o, e))
        w("  guardado entero en", guardar.replace(OUT, "<out>"))
    return rc, o, e


def kvm_tres_estados():
    p = "/dev/kvm"
    if not os.path.exists(p):
        return "NO_EXISTE", "el nodo no esta en el filesystem"
    try:
        fd = os.open(p, os.O_RDWR)
        os.close(fd)
        return "USABLE", "abre O_RDWR sin error"
    except PermissionError as e:
        return "SIN_PERMISO", "existe y NO abre: %s (esto NO es ausencia)" % e
    except Exception as e:
        return "EXISTE_PERO_ROTO", repr(e)[:120]


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    arch = os.uname().machine
    w("== F-001-S1 paso 0: el arnes de QEMU ==")
    w("  fecha UTC", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    w("  PREDICCION: el control positivo FALLA, y el arranque real imprime el")
    w("  banner de Linux y entra en panico por falta de init.")
    rc, o, _ = sh("uname -m; nproc; free -m | head -2; df -h / | tail -1")
    for l in o.splitlines():
        w("   |", l[:120])

    estado, razon = kvm_tres_estados()
    w("")
    w("  === /dev/kvm, con los TRES estados separados ===")
    w("  estado: %s" % estado)
    w("  razon : %s" % razon)
    if arch == "x86_64":
        w("  -> ISA NO coincide (huesped arm64 / anfitrion x86_64): KVM IRRELEVANTE aca.")
    else:
        w("  -> ISA coincide, pero sin /dev/kvm tampoco hay aceleracion.")
    w("  CONCLUSION: F-001-S1 va por TCG en las dos maquinas.")

    w("")
    w("  === herramientas ===")
    for b in ("qemu-system-aarch64", "qemu-img", "unzip", "cpio", "zstd"):
        w("   %-22s %s" % (b, shutil.which(b) or "AUSENTE"))
    rc, o, _ = sh("qemu-system-aarch64 --version 2>&1 | head -1")
    for l in o.splitlines():
        w("   |", l[:120])

    w("")
    w("  === CONTROL POSITIVO: QEMU con un -kernel que NO existe ===")
    w("  si esto tambien diera verde, el instrumento seria un adorno.")
    rcx, ox, ex = sh("timeout 30 %s -kernel /tmp/no-existe-este-kernel 2>&1 | head -5"
                     % QEMU_BASE, 60)
    for l in (ox + ex).splitlines()[:5]:
        w("   C|", l[:150])
    control_discrimina = rcx != 0 and not re.search(r"Linux version", ox + ex)
    w("  el control DISCRIMINA (falla como debe): %s" % control_discrimina)

    w("")
    w("  === bajando el boot.img CERTIFICADO de Google ===")
    url = ("https://dl.google.com/android/gki/gki-certified-boot-android15-6.6"
           "-2025-01_r1.zip")
    z = WORK + "/gki.zip"
    if not os.path.isfile(z):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "siao-f001s1/1"})
            open(z, "wb").write(urllib.request.urlopen(req, timeout=600).read())
        except Exception as e:
            w("  NO MEDIDO: no pude bajar el zip: %s" % repr(e)[:140])
            open(os.path.join(OUT, "f001s1-%s-bitacora.txt" % arch), "w").write("\n".join(log) + "\n")
            return
    w("  zip: %d B" % os.path.getsize(z))
    zf = zipfile.ZipFile(z)
    cand = [n for n in zf.namelist() if n.endswith(".img")]
    w("  entradas .img: %s -> elijo %s" % (cand, cand[0]))
    raw = zf.read(cand[0])
    hdr_v = struct.unpack("<I", raw[40:44])[0]
    ksz = struct.unpack("<I", raw[8:12])[0]
    w("  boot.img %d B | magic %r | header_version=%d | kernel_size=%d"
      % (len(raw), raw[:8], hdr_v, ksz))
    img = raw[4096:4096 + ksz]
    open(WORK + "/Image", "wb").write(img)
    w("  Image: %d B | magic %r  (MZ = PE/EFI stub, normal en arm64)" % (len(img), img[:4]))
    k = WORK + "/Image"

    w("")
    w("  === EL ARRANQUE REAL: qemu-system-aarch64 SIN rootfs ===")
    cmd = ("timeout 240 %s -kernel %s -append 'console=ttyAMA0 panic=1 earlycon' "
           "2>&1 | head -200" % (QEMU_BASE, k))
    rc, o, e = sh(cmd, 320, guardar=os.path.join(OUT, "f001s1-%s-boot.txt" % arch))
    todo = o + e
    m = re.search(r"Linux version ([^\s]+)", todo)
    hitos = {"control_discrimina": control_discrimina,
             "banner_linux": bool(m),
             "version_leida": m.group(1) if m else None,
             "memoria_ok": "Memory:" in todo,
             "llego_a_init": ("No working init found" in todo or "Kernel panic" in todo
                              or "Failed to execute" in todo),
             "bytes_de_salida": len(todo)}
    w("")
    w("  === HITOS ===")
    for kk, vv in hitos.items():
        w("   %-20s %s" % (kk, vv))
    w("  --- salida del kernel, primeras 45 lineas ---")
    for l in todo.splitlines()[:45]:
        w("   B|", l[:170])
    ver = ("ARNES VERDE: QEMU ejecuta un kernel arm64 REAL, y el control discrimina"
           if hitos["banner_linux"] and control_discrimina else
           "ARNES ROJO o NO MEDIDO: ver los hitos")
    res = {"arch": arch, "kvm_estado": estado, "kvm_razon": razon,
           "entrada_zip": cand[0], "hitos": hitos, "rc_qemu": rc, "veredicto": ver,
           "fecha_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(res, open(os.path.join(OUT, "f001s1-%s.json" % arch), "w"),
              indent=2, ensure_ascii=False)
    w("")
    w("  VEREDICTO: %s" % ver)
    open(os.path.join(OUT, "f001s1-%s-bitacora.txt" % arch), "w").write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
