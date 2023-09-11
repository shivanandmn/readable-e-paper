import argparse
from os import listdir, mkdir
from os.path import join, isdir
from subprocess import call
import sys
import datasets
from shutil import which

COLOR_IMAGE_DPI = 300
from pathlib import Path

"""
Script to use pdftoppm to turn the pdfs into single images per page
"""


def get_images(pdfname, output_dir, dpi):
    if which("pdftoppm") is None:
        raise ValueError("Requires executable pdftopmm to be on the PATH")

    if not isdir(output_dir):
        print("Making %s to store rasterized PDF pages" % output_dir)
        Path(output_dir).mkdir(parents=True)

    if not pdfname.endswith(".pdf"):
        raise ValueError()
    doc_id = pdfname.split("/")[-1][:-4]
    args = [
        "pdftoppm",
        "-jpeg",
        "-r",
        str(dpi),
        "-cropbox",
        pdfname,
        join(output_dir, doc_id + "-page"),
    ]
    retcode = call(args)
    if retcode != 0:
        raise ValueError("Bad return code for <%s> (%d)", " ".join(args), retcode)


if __name__ == "__main__":
    get_images("result/pdfs/", "result/pdfs", COLOR_IMAGE_DPI)
