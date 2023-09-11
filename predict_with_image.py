from nougat.dataset.pdffigures import call_pdffigures
from PIL import Image, ImageDraw
import json
from pdftoimage import COLOR_IMAGE_DPI, get_images
from pdffigure2 import PDFFigures2, scale_figure
from predict import predict
from pathlib import Path
from subprocess import call


def get_annotations(annotation_file):
    pdffig = PDFFigures2()
    figures = pdffig.load_json(annotation_file)
    return figures


def double_digit(d):
    if len(d) == 1:
        return "0" + d
    else:
        return d


def create_save_dir(name):
    p = "output" / Path(name)
    for d in ["pages", "figs", "caps"]:
        out = p / d
        out.mkdir(parents=True, exist_ok=True)


def dump_cropped_images(pdf_file):
    pdf_name = pdf_file.split("/")[-1][:-4]
    create_save_dir(pdf_name)
    pages_dir = f"output/{pdf_name}/pages"
    figs_dir = f"output/{pdf_name}/figs"
    caps_dir = f"output/{pdf_name}/caps"
    get_images(pdf_file, pages_dir, COLOR_IMAGE_DPI)

    fig_meta_file = call_pdffigures(pdf_file, "output/" + pdf_name)
    figures = get_annotations(fig_meta_file)
    loaded_figs = {"figures": []}
    for figure in figures:
        fig_page = str(figure.page)
        fig_name = figure.name
        image = Image.open(
            f"{pages_dir}/{pdf_name}-page-" + double_digit(fig_page) + ".jpg"
        )
        capt, region = scale_figure(figure, COLOR_IMAGE_DPI)
        region = image.crop(region)
        capt = image.crop(capt)
        save_fig = Path(
            f"{figs_dir}/page-" + fig_page + "-fig-" + str(fig_name) + ".jpg"
        )
        caption_fig = Path(
            f"{caps_dir}/page-" + fig_page + "-fig-" + str(fig_name) + ".jpg"
        )
        region.save(save_fig)
        capt.save(caption_fig)
        fig = figure.as_dict()
        parent = Path(f"output/{pdf_name}")
        fig["fig_path"] = str(save_fig.relative_to(parent))
        fig["cap_path"] = str(caption_fig.relative_to(parent))
        loaded_figs["figures"].append(fig)
    json.dump(loaded_figs, open(fig_meta_file, "w"))
    return fig_meta_file


def predict_save():
    pdf_file = "pdf_dir/2308.13418.pdf"
    pdf_name = pdf_file.split("/")[-1][:-4]
    loaded_figs = dump_cropped_images(pdf_file)
    merge_figures = json.load(open(loaded_figs))["figures"]
    out_file = predict(
        pdf_file,
        checkpoint=None,
        merge_figures=merge_figures,
        out="output/" + pdf_name,
        markdown=False,
    )
    call(["md-to-pdf", str(out_file)])


if __name__ == "__main__":
    predict_save()
