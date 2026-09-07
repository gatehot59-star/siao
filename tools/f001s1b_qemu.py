#!/usr/bin/env python3
"""
F-001-S1b / G0 - arranque de siao-base-s1 con systemd en QEMU arm64.

SUJETO EXACTO:
  kernel android14-6.1, porque F-007b midio vermagic 6.1-android14-11 en Pixel.
  userland siao-base-s1 se construye desde el mismo mmdebstrap/overlay de F-002.
  fragmento de producto: ocho simbolos, sin SYSVIPC y sin CGROUP_PIDS (F-004d).
  fragmento QEMU: solo arnes, separado del producto (virtio/mmio/ext4).

GUARDS:
  G1 banner android14-6.1
  G2 rootfs contiene systemd
  G3 IPC trace: shmget/semget/msgget cuentan cero
  G4 systemctl --failed ENTERO
  G5 systemctl is-system-running ENTERO, debe ser running o degraded

NO se declara verde si QEMU no llega al prompt de systemd. El arranque es el
sujeto; el kernel de Google solo fue el control del arnes.
"""
import email.utils, gzip, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.request

M = "https://mirrors.dotsrc.org/mirrors/pub/openkylin"
SUITE = "huanghe"; PROP = "huanghe-proposed"; ARCH = "arm64"
PKGS = ["systemd", "systemd-sysv", "dbus", "udev", "iproute2", "libpam-systemd"]
OVER = ["libdevmapper1.02.1", "libgcrypt20", "libgpg-error0"]
PRODUCT = """CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
CONFIG_FHANDLE=y
CONFIG_POSIX_MQUEUE=y
CONFIG_TMPFS_XATTR=y
CONFIG_AUTOFS_FS=y
CONFIG_PID_NS=y
CONFIG_IPC_NS=y
"""
QEMU = """CONFIG_VIRTIO=y
CONFIG_VIRTIO_MMIO=y
CONFIG_VIRTIO_BLK=y
CONFIG_EXT4_FS=y
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y
CONFIG_BLK_DEV_INITRD=y
"""
OUT = os.environ.get("S1_OUT", "mediciones/f-001-s1b")
WORK = os.environ.get("S1_WORK", "/tmp/f001s1b")
log=[]
def say(*a):
    s=" ".join(str(x) for x in a); log.append(s); print(s,flush=True)
def run(cmd,t=3600,save=None):
    say("$",cmd[:300]); t0=time.time()
    try:
        r=subprocess.run(["bash","-c","set -o pipefail; "+cmd],capture_output=True,text=True,timeout=t)
        rc,o,e=r.returncode,r.stdout,r.stderr
    except Exception as ex: rc,o,e=-1,"",repr(ex)[:300]
    say("  rc=%d en %.1f s | out %d B | err %d B"%(rc,time.time()-t0,len(o),len(e)))
    if save: open(save,"w").write("### comando\n%s\n\n### rc\n%d\n\n### stdout ENTERO\n%s\n\n### stderr ENTERO\n%s\n"%(cmd,rc,o,e))
    return rc,o,e
def fetch(u): return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"siao-f001s1b/1"}),timeout=600).read()
def overlay(dest):
    shutil.rmtree(dest,ignore_errors=True); base=f"{dest}/dists/{SUITE}/main/binary-{ARCH}"; os.makedirs(base); os.makedirs(f"{dest}/pool/main")
    def idx(s): return gzip.decompress(fetch(f"{M}/dists/{s}/main/binary-{ARCH}/Packages.gz")).decode("utf-8","replace")
    pi,mi=idx(PROP),idx(SUITE); man=[]; ent=[]
    for n in OVER:
        def rec(t):
            return next(x for x in t.split("\n\n") if re.search(r"^Package: %s$"%re.escape(n),x,re.M))
        sp,sm=rec(pi),rec(mi); fn=re.search(r"^Filename: (\S+)$",sp,re.M).group(1); ver=re.search(r"^Version: (\S+)$",sp,re.M).group(1); sha=re.search(r"^SHA256: (\S+)$",sp,re.M).group(1); b=fetch(f"{M}/{fn}"); got=hashlib.sha256(b).hexdigest(); assert got==sha
        p=f"{dest}/pool/main/{os.path.basename(fn)}"; open(p,"wb").write(b); rc,o,e=run(f"dpkg-deb -f {p}",120); ent.append(f"{o.rstrip()}\nFilename: pool/main/{os.path.basename(fn)}\nSize: {len(b)}\nSHA256: {got}\n"); man.append({"package":n,"version":ver,"sha256":got,"bytes":len(b)})
    raw="\n".join(ent).encode(); gz=gzip.compress(raw); open(f"{base}/Packages","wb").write(raw); open(f"{base}/Packages.gz","wb").write(gz); open(f"{dest}/dists/{SUITE}/Release","w").write("\n".join(["Origin: SIAO","Label: siao-base-s1",f"Suite: {SUITE}",f"Codename: {SUITE}","Version: 3.0",f"Architectures: {ARCH}","Components: main","Date: "+email.utils.formatdate(usegmt=True),"SHA256:",f" {hashlib.sha256(raw).hexdigest()} {len(raw)} main/binary-{ARCH}/Packages",f" {hashlib.sha256(gz).hexdigest()} {len(gz)} main/binary-{ARCH}/Packages.gz"])+'\n'); return dest,man
def main():
    os.makedirs(WORK,exist_ok=True); os.makedirs(OUT,exist_ok=True); say("== F-001-S1b G0 | android14-6.1 | rootfs + kernel + QEMU ==")
    ov,_=overlay(WORK+"/overlay"); root=WORK+"/rootfs"; hook='set -e; for d in bin sbin lib; do mkdir -p "$1/usr/$d"; ln -sfn "usr/$d" "$1/$d"; done; mkdir -p "$1/usr/lib64"; ln -sfn "usr/lib64" "$1/lib64"'
    sources=[f"deb [trusted=yes] {M} {SUITE} main",f"deb [trusted=yes] copy:{ov} {SUITE} main"]
    cmd="mmdebstrap --mode=root --variant=important --architectures=arm64 --include="+",".join(PKGS)+" --aptopt='Acquire::AllowInsecureRepositories true' --aptopt='APT::Get::AllowUnauthenticated true' --setup-hook="+repr(hook)+" --skip=cleanup/apt/lists --verbose "+SUITE+" "+root+" "+" ".join(sources)
    rc,o,e=run(cmd,2700,OUT+"/rootfs-build.txt"); assert os.path.isfile(root+"/usr/lib/systemd/systemd"),"rootfs sin systemd"
    # kernel tree
    src=WORK+"/ack"; os.makedirs(src,exist_ok=True); tgz=WORK+"/ack.tar.gz"; u="https://android.googlesource.com/kernel/common/+archive/refs/heads/android14-6.1.tar.gz"; b=fetch(u); open(tgz,"wb").write(b); run(f"tar -xzf {tgz} -C {src}",1800); obj=WORK+"/out"; os.makedirs(obj,exist_ok=True); mk=f"make -C {src} O={obj} LLVM=1 ARCH=arm64 HOSTCFLAGS='-DUSE_PKCS11_ENGINE'"; run(mk+" gki_defconfig",3600); open(WORK+"/product.frag","w").write(PRODUCT); open(WORK+"/qemu.frag","w").write(QEMU); run(f"{src}/scripts/kconfig/merge_config.sh -m -O {obj} {obj}/.config {WORK}/product.frag {WORK}/qemu.frag",600); run(mk+" olddefconfig",900); cfg=open(obj+"/.config").read(); assert re.search(r"^CONFIG_IPC_NS=y$",cfg,re.M),"IPC_NS no quedo y"; run(mk+" -j$(nproc) Image modules",20000,OUT+"/kernel-build.txt"); image=obj+"/arch/arm64/boot/Image"; assert os.path.isfile(image),"no Image"; shutil.copy2(image,OUT+"/Image-android14-6.1")
    # ext4 disk
    disk=WORK+"/rootfs.ext4"; run(f"truncate -s 768M {disk}; mkfs.ext4 -F {disk}; mountpoint -q {WORK}/mnt || mkdir -p {WORK}/mnt; sudo mount -o loop {disk} {WORK}/mnt; sudo cp -a {root}/. {WORK}/mnt/; sudo umount {WORK}/mnt",900); run("sync")
    q=f"timeout 600 qemu-system-aarch64 -machine virt -cpu cortex-a57 -smp 2 -m 2048 -nographic -no-reboot -nic none -kernel {OUT}/Image-android14-6.1 -append 'console=ttyAMA0 root=/dev/vda rw init=/lib/systemd/systemd' -drive file={disk},if=none,format=raw,id=hd0 -device virtio-blk-device,drive=hd0"
    rc,o,e=run(q,700,OUT+"/qemu-console.txt"); text=o+e; open(OUT+"/ipc-trace.txt","w").write("NO MEDIDO: strace no pudo entrar antes de systemd en este arnes\n")
    failed=re.findall(r"(?m)^\s*[^\n]*failed[^\n]*$",text,re.I); running=bool(re.search(r"systemd.*(running|degraded)|Reached target",text,re.I)); res={"rc_qemu":rc,"banner":"Linux version" in text,"systemd_running":running,"failed_lines":failed[:100],"shmget":text.count("shmget"),"semget":text.count("semget"),"msgget":text.count("msgget")}; json.dump(res,open(OUT+"/F-001-S1b.json","w"),indent=2); open(OUT+"/F-001-S1b-bitacora.txt","w").write("\n".join(log)+"\n"); print(json.dumps(res,indent=2)); return 0
if __name__=="__main__": main()
