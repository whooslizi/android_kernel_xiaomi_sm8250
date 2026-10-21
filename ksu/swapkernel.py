#!/usr/bin/env python3
"""Replace only the kernel in an Android boot image (header v0-v2).
Everything else (ramdisk, second, recovery_dtbo, dtb, cmdline, offsets) is copied as-is.
usage: swapkernel.py boot-in.img Image boot-out.img
"""
import hashlib, struct, sys

src, kernel_path, dst = sys.argv[1:4]
data = open(src, "rb").read()
kernel = open(kernel_path, "rb").read()
assert data[:8] == b"ANDROID!", "not an Android boot image"

(ksize, kaddr, rsize, raddr, ssize, saddr, tags, page, hv, osv) = struct.unpack_from("<10I", data, 8)
assert hv <= 2, f"header v{hv} not supported"
pad = lambda n: (page - n % page) % page

off = page
sections = {}
for name, size in (("kernel", ksize), ("ramdisk", rsize), ("second", ssize)):
    sections[name] = data[off:off + size]
    off += size + pad(size)
if hv >= 1:
    s, = struct.unpack_from("<I", data, 1632)
    sections["recovery_dtbo"] = data[off:off + s]; off += s + pad(s)
if hv >= 2:
    s, = struct.unpack_from("<I", data, 1648)
    sections["dtb"] = data[off:off + s]; off += s + pad(s)

sections["kernel"] = kernel
hdr = bytearray(data[:page])
struct.pack_into("<I", hdr, 8, len(kernel))

order = ["kernel", "ramdisk", "second"] + (["recovery_dtbo"] if hv >= 1 else []) + (["dtb"] if hv >= 2 else [])
sha = hashlib.sha1()
for name in order:
    sha.update(sections[name]); sha.update(struct.pack("<I", len(sections[name])))
hdr[576:608] = sha.digest().ljust(32, b"\0")

out = bytearray(hdr)
for name in order:
    out += sections[name] + b"\0" * pad(len(sections[name]))
if len(out) <= len(data):
    out += b"\0" * (len(data) - len(out))
open(dst, "wb").write(out)
print(f"header v{hv}, page {page}: kernel {ksize} -> {len(kernel)} bytes, out {len(out)} bytes")
