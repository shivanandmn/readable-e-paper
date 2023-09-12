"""
Copyright (c) Meta Platforms, Inc. and affiliates.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""
import sys
from pathlib import Path
import logging
import re
import argparse
import re
from functools import partial
import torch
from torch.utils.data import ConcatDataset
from tqdm import tqdm
from nougat import NougatModel
from nougat.utils.dataset import LazyDataset
from nougat.utils.checkpoint import get_checkpoint
from nougat.postprocessing import markdown_compatible
import fitz

import json


BATCH_SIZE = 1


def combine_figures(text, merge_figures):
    text_list = text.split("\n")
    out = ""
    for txt in tqdm(text_list, leave=False):
        if txt.strip().startswith("Figure"):
            image_loc = None
            for fig in merge_figures:
                if txt.split(": ")[0] == fig["caption"].split(": ")[0]:
                    image_loc = f"\n![img]({fig['fig_path']})\n"
                    out = out + "\n" + image_loc + txt + "\n"
                    break
        else:
            out += txt + "\n"

    return out


def predict(pdf, model, merge_figures, out, markdown=False):
    pdf = Path(pdf)
    if model is None:
        checkpoint = get_checkpoint(None)
        model = NougatModel.from_pretrained(checkpoint).to(torch.bfloat16)
        if torch.cuda.is_available():
            model.to("cuda")
        model.eval()
    if not pdf.exists():
        ValueError()
    out_file = Path(out)
    if out:
        out_path = out_file / pdf.with_suffix(".md").name
        if out_path.exists():
            logging.info(
                f"Skipping {pdf.name}, already computed. Run with --recompute to convert again."
            )
            ValueError()
    try:
        dataset = LazyDataset(
            pdf, partial(model.encoder.prepare_input, random_padding=False)
        )
    except fitz.fitz.FileDataError:
        logging.info(f"Could not load file {str(pdf)}.")
        ValueError()

    dataloader = torch.utils.data.DataLoader(
        ConcatDataset([dataset]),
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=LazyDataset.ignore_none_collate,
    )

    predictions = []
    page_num = 0
    for i, (sample, is_last_page) in enumerate(tqdm(dataloader)):
        model_output = model.inference(image_tensors=sample)
        # check if model output is faulty
        for j, output in enumerate(model_output["predictions"]):
            if page_num == 0:
                logging.info(
                    "Processing file %s with %i pages" % (dataset.name, dataset.size)
                )
            page_num += 1
            if output.strip() == "[MISSING_PAGE_POST]":
                # uncaught repetitions -- most likely empty page
                predictions.append(f"\n\n[MISSING_PAGE_EMPTY:{page_num}]\n\n")
                continue
            if model_output["repeats"][j] is not None:
                if model_output["repeats"][j] > 0:
                    # If we end up here, it means the output is most likely not complete and was truncated.
                    logging.warning(f"Skipping page {page_num} due to repetitions.")
                    predictions.append(f"\n\n[MISSING_PAGE_FAIL:{page_num}]\n\n")
                else:
                    # If we end up here, it means the document page is too different from the training domain.
                    # This can happen e.g. for cover pages.
                    predictions.append(
                        f"\n\n[MISSING_PAGE_EMPTY:{i*BATCH_SIZE+j+1}]\n\n"
                    )
            else:
                if markdown:
                    output = markdown_compatible(output)
                if merge_figures is not None:
                    output = combine_figures(output, merge_figures)

                predictions.append(output)
            if is_last_page[j]:
                out = "".join(predictions).strip()
                out = re.sub(r"\n{3,}", "\n\n", out).strip()
                if out_file:
                    out_path = out_file / Path(is_last_page[j]).with_suffix(".md").name
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(out, encoding="utf-8")
                    print("out_path :", out_path)
                else:
                    print(out, "\n\n")
                predictions = []
                page_num = 0
    return out_path


if __name__ == "__main__":
    predict()
