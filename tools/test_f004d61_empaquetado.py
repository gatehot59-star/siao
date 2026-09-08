#!/usr/bin/env python3
"""
Banco de pruebas de lo NUEVO del f004d61_build.py v4, para poder ejecutarlo sin
un build de kernel de 2 horas.

POR QUE EXISTE: el metodo prohibe commitear un script sin ejecutarlo, y el v4 no
se puede ejecutar entero en el taller (2 nucleos Celeron, un build de arm64 no
termina). Pero las TRES piezas que el v4 agrega no necesitan un kernel: son
lectura de flags, reconstruccion por objcopy y armado del tarball. Se prueban
contra un arbol SINTETICO, con controles negativos que tienen que dar rojo.

Si este banco pasa y despues el run de Actions falla, el defecto esta en el
build, no en el empaquetado: eso es lo que este archivo compra.

MODO DE USO:  test_f004d61_empaquetado.py
Salida: PASA/FALLA por caso, y exit 1 si alguno falla.
"""
import os, re, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f004d61_build as B

OK = []
MAL = []


def caso(nombre, cond, detalle=""):
    (OK if cond else MAL).append(nombre)
    print("  %-6s %s%s" % ("PASA" if cond else "FALLA", nombre,
                           ("  | " + detalle) if detalle else ""))


def elf_real():
    """Un ELF de verdad para hacer de vmlinux. No sirve un archivo inventado:
    objcopy tiene que poder leerlo."""
    for c in ("/bin/ls", "/usr/bin/ls", "/bin/cat", sys.executable):
        if c and os.path.isfile(c):
            with open(c, "rb") as f:
                if f.read(4) == b"\x7fELF":
                    return c
    return None


def main():
    print("== banco de pruebas del empaquetado v4 ==")
    vm_src = elf_real()
    print("  ELF de prueba (hace de vmlinux): %s" % vm_src)
    if not vm_src:
        print("  NO MEDIDO: no encontre un ELF para la prueba")
        return 2
    oc = shutil.which("llvm-objcopy") or shutil.which("objcopy")
    print("  objcopy disponible: %s" % (oc or "AUSENTE"))

    raiz = tempfile.mkdtemp(prefix="test-f004d61-")
    src = os.path.join(raiz, "ack")
    obj = os.path.join(raiz, "out-ocho")
    os.makedirs(os.path.join(src, "arch/arm64"))
    os.makedirs(os.path.join(obj, "arch/arm64/boot"))
    os.makedirs(os.path.join(obj, "drivers/net"))

    # ---- 1. leer OBJCOPYFLAGS_Image de la FUENTE ----
    print("\n-- 1. flags_objcopy_de_la_fuente --")
    mkf = os.path.join(src, "arch/arm64/Makefile")
    LINEA = ("OBJCOPYFLAGS_Image :=-O binary -R .note -R .note.gnu.build-id "
             "-R .comment -S")
    open(mkf, "w").write("# fake arch/arm64/Makefile\n%s\nall: Image\n" % LINEA)
    flags, crudo = B.flags_objcopy_de_la_fuente(src)
    caso("lee los flags del Makefile", flags is not None, repr(flags))
    caso("los flags traen -O binary", bool(flags) and "-O binary" in flags)
    caso("los flags traen -S", bool(flags) and flags.strip().endswith("-S"))
    caso("devuelve la linea cruda", crudo.strip() == LINEA)

    # CONTROL NEGATIVO: sin la linea, tiene que dar None y NO inventar nada
    open(mkf + ".vacio", "w").write("# nada\n")
    src2 = os.path.join(raiz, "ack-sin-linea")
    os.makedirs(os.path.join(src2, "arch/arm64"))
    open(os.path.join(src2, "arch/arm64/Makefile"), "w").write("# nada de nada\n")
    f2, c2 = B.flags_objcopy_de_la_fuente(src2)
    caso("CONTROL: sin la linea devuelve None", f2 is None, c2)
    f3, c3 = B.flags_objcopy_de_la_fuente(os.path.join(raiz, "no-existe"))
    caso("CONTROL: sin Makefile devuelve None", f3 is None, c3[:40])

    # ---- 2. el KAT ----
    print("\n-- 2. kat_objcopy --")
    vm = os.path.join(obj, "vmlinux")
    img = os.path.join(obj, B.IMAGE_REL)
    shutil.copy(vm_src, vm)
    if oc:
        r = subprocess.run(["bash", "-c", "%s %s %s %s" % (oc, flags, vm, img)],
                           capture_output=True, text=True)
        print("     objcopy rc=%d %s" % (r.returncode, r.stderr.strip()[:120]))
    if oc and os.path.isfile(img):
        k = B.kat_objcopy(src, obj, os.path.join(raiz, "rec-igual"))
        caso("KAT IDENTICO cuando Image sale del mismo vmlinux",
             k.get("kat") == "IDENTICO", k.get("kat"))
        caso("el sha256 del KAT tiene 64 hex",
             len(k.get("sha256_image", "")) == 64)

        # CONTROL NEGATIVO 1: Image corrupto -> el KAT DEBE decir DISTINTO
        with open(img, "r+b") as f:
            f.seek(0)
            f.write(b"\x00\x01\x02\x03")
        k2 = B.kat_objcopy(src, obj, os.path.join(raiz, "rec-corrupto"))
        caso("CONTROL: Image corrupto da DISTINTO",
             k2.get("kat") == "DISTINTO", k2.get("kat"))

        # CONTROL NEGATIVO 2: sin flags legibles -> NO MEDIDO, no rojo ni verde
        k3 = B.kat_objcopy(src2, obj, os.path.join(raiz, "rec-sin-flags"))
        caso("CONTROL: sin flags de la fuente da NO MEDIDO",
             str(k3.get("kat")).startswith("NO MEDIDO"), k3.get("kat"))
        caso("CONTROL: y kat_identico queda None, no False",
             k3.get("kat_identico") is None)
        # dejar el Image sano otra vez para la parte 3
        subprocess.run(["bash", "-c", "%s %s %s %s" % (oc, flags, vm, img)],
                       capture_output=True, text=True)
    else:
        print("  NO MEDIDO: sin objcopy no puedo probar el KAT en esta maquina")

    # ---- 3. la lista de miembros, que reemplaza al head -400 ----
    print("\n-- 3. lista_de_miembros: el tope silencioso --")
    N = 437  # a proposito MAS de 400: con el head del v3 se perdian 37
    for i in range(N):
        d = os.path.join(obj, "drivers/net") if i % 2 else os.path.join(obj, "drivers")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "mod%04d.ko" % i), "w").write("ko %d\n" % i)
    lst = os.path.join(raiz, "miembros.txt")
    kos = B.lista_de_miembros(obj, lst)
    caso("cuenta los %d modulos, sin tope" % N, len(kos) == N, str(len(kos)))
    lineas = open(lst).read().splitlines()
    caso("la lista arranca con vmlinux", lineas[0] == "vmlinux")
    caso("la lista trae el Image en segundo lugar", lineas[1] == B.IMAGE_REL)
    caso("la lista tiene 2 + %d lineas" % N, len(lineas) == N + 2, str(len(lineas)))
    # el defecto que se elimino, medido: cuantos perdia el head -400
    perdidos = max(0, N - 400)
    caso("CONTROL del defecto viejo: head -400 habria perdido %d" % perdidos,
         perdidos == 37, "%d" % perdidos)

    # ---- 4. el tar y sus guards ----
    print("\n-- 4. tar con -T y los guards de contenido --")
    if not shutil.which("zstd"):
        print("  NO MEDIDO: sin zstd no puedo armar el tarball igual que el v4")
    else:
        tb = os.path.join(raiz, "elf-ocho.tar.zst")
        r = subprocess.run(["bash", "-c", "cd %s && tar -c --zstd -f %s -T %s"
                            % (obj, tb, lst)], capture_output=True, text=True)
        caso("tar -T arma el tarball", r.returncode == 0 and os.path.isfile(tb),
             "rc=%d %s" % (r.returncode, r.stderr.strip()[:100]))
        if os.path.isfile(tb):
            r2 = subprocess.run(["bash", "-c", "tar -t --zstd -f %s" % tb],
                                capture_output=True, text=True)
            lista = r2.stdout
            tiene_vm = re.search(r"^\./?vmlinux$", lista, re.M) is not None
            tiene_img = re.search(r"^\./?%s$" % re.escape(B.IMAGE_REL),
                                  lista, re.M) is not None
            ko_dentro = len(re.findall(r"\.ko$", lista, re.M))
            caso("el tarball contiene vmlinux", tiene_vm)
            caso("el tarball contiene %s" % B.IMAGE_REL, tiene_img)
            caso("el tarball contiene los %d .ko" % N, ko_dentro == N,
                 str(ko_dentro))
            caso("la cuenta de la lista cierra con la del tarball",
                 ko_dentro == len(kos))
            # CONTROL NEGATIVO: un tarball SIN Image tiene que fallar el guard
            lst2 = os.path.join(raiz, "miembros-sin-image.txt")
            open(lst2, "w").write("vmlinux\n")
            tb2 = os.path.join(raiz, "elf-sin-image.tar.zst")
            subprocess.run(["bash", "-c", "cd %s && tar -c --zstd -f %s -T %s"
                            % (obj, tb2, lst2)], capture_output=True, text=True)
            r3 = subprocess.run(["bash", "-c", "tar -t --zstd -f %s" % tb2],
                                capture_output=True, text=True)
            sin_img = re.search(r"^\./?%s$" % re.escape(B.IMAGE_REL),
                                r3.stdout, re.M) is None
            caso("CONTROL: el guard detecta un tarball SIN Image", sin_img)

    # ---- 5. sha256 completo, no truncado ----
    print("\n-- 5. sha256_de: 64 hex y no 32 --")
    h = B.sha256_de(vm)
    caso("sha256_de devuelve 64 hex", len(h) == 64, h[:16] + "...")
    caso("y no 32 como el f004d61_stg.py", len(h) != 32)

    print("\n== RESULTADO: %d PASA, %d FALLA ==" % (len(OK), len(MAL)))
    for m in MAL:
        print("  FALLO: %s" % m)
    shutil.rmtree(raiz, ignore_errors=True)
    return 1 if MAL else 0


if __name__ == "__main__":
    sys.exit(main())
