"""Collect each library's .exs instruments and samples into one flat folder per library.
Only libraries whose zip is still in libraries/ are staged.

work/stage/<lib>/ gets hard links (no extra disk space) to:
  * every .exs under "Sampler Instruments/" of the library's v1.3.1 release, and
  * every .wav under its "Samples/" folder.
The older "EXS24 Hun-DEMO" and "EXS24 JangGu-DEMO" releases go to hun_legacy/ and
janggu_legacy/. Files with the same name in different sub-folders are bit-identical copies;
the second one is linked as "<name> (1).wav".
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACT = os.path.join(ROOT, "work", "extract")
STAGE = os.path.join(ROOT, "work", "stage")
LIBRARIES = os.path.join(ROOT, "libraries")
LEGACY = {"hun": "EXS24 Hun-DEMO", "janggu": "EXS24 JangGu-DEMO"}


def sources():
    for lib in sorted(os.listdir(EXTRACT)):
        d = os.path.join(EXTRACT, lib)
        if not os.path.isdir(d) or not os.path.exists(os.path.join(LIBRARIES, f"{lib} exs24.zip")):
            continue
        for ver in sorted(os.listdir(d)):
            if "v.1.3.1" in ver:
                yield lib, os.path.join(d, ver)
            elif LEGACY.get(lib) == ver:
                yield lib + "_legacy", os.path.join(d, ver)


def link(src, folder):
    name = os.path.basename(src)
    dst = os.path.join(folder, name)
    n = 1
    while os.path.exists(dst):
        base, ext = os.path.splitext(name)
        dst = os.path.join(folder, f"{base} ({n}){ext}")
        n += 1
    os.link(src, dst)


def main():
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    count = 0
    for lib, top in sources():
        folder = os.path.join(STAGE, lib)
        os.makedirs(folder)
        n_exs = n_wav = 0
        for dp, dns, fns in os.walk(top):
            dns.sort()
            if ".logicx" in dp:
                continue
            parts = dp.split(os.sep)
            for fn in sorted(fns):
                p = os.path.join(dp, fn)
                if fn.endswith(".exs") and "Sampler Instruments" in parts:
                    link(p, folder); n_exs += 1
                elif fn.lower().endswith(".wav") and "Samples" in parts:
                    link(p, folder); n_wav += 1
        if not n_exs:
            sys.exit(f"no .exs instruments found for {lib} in {top}")
        count += 1
        print(f"   {lib}: {n_exs} instruments, {n_wav} samples")
    print(f"   staged {count} library folders")


if __name__ == "__main__":
    main()
