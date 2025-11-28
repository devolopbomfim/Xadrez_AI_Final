from setuptools import setup, Extension

bitops = Extension(
    "core.native.bitops",
    sources=["core/native/bitops.c"],
    extra_compile_args=["-O3", "-march=native"]
)

setup(
    name="xadrez_native",
    version="0.1",
    ext_modules=[bitops],
)
