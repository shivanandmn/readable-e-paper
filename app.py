"""
Copyright (c) Meta Platforms, Inc. and affiliates.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""
import os
import sys
from functools import partial
from http import HTTPStatus
from fastapi import FastAPI, File, UploadFile
from PIL import Image
from pathlib import Path
import hashlib
from fastapi.middleware.cors import CORSMiddleware
import fitz
import torch
from nougat import NougatModel
from nougat.postprocessing import markdown_compatible, close_envs
from nougat.utils.dataset import ImageDataset
from nougat.utils.checkpoint import get_checkpoint
from nougat.dataset.rasterize import rasterize_paper
from predict_with_image import predict_save

SAVE_DIR = Path("./pdf_dir")
BATCHSIZE = os.environ.get("NOUGAT_BATCHSIZE", 6)
NOUGAT_CHECKPOINT = get_checkpoint()
if NOUGAT_CHECKPOINT is None:
    print(
        "Set environment variable 'NOUGAT_CHECKPOINT' with a path to the model checkpoint!."
    )
    sys.exit(1)

app = FastAPI(title="Nougat API")
origins = ["http://localhost", "http://127.0.0.1"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
model = None


@app.on_event("startup")
async def load_model(
    checkpoint: str = NOUGAT_CHECKPOINT,
):
    global model
    if model is None:
        model = NougatModel.from_pretrained(checkpoint).to(torch.bfloat16)
        if torch.cuda.is_available():
            model.to("cuda")
        model.eval()


@app.get("/")
def root():
    """Health check."""
    response = {
        "status-code": HTTPStatus.OK,
        "data": {},
    }
    return response


@app.post("/predict/")
async def predict(
    file: UploadFile = File(...)
) -> dict:
    """
    Perform predictions on a PDF document and return the extracted text in Markdown format.

    Args:
        file (UploadFile): The uploaded PDF file to process.

    Returns:
        dict: 
    """
    pdfbin = file.file.read()
    pdf = fitz.open("pdf", pdfbin)
    print("pdf_dir/" + str(pdf.name))
    pdf.save("pdf_dir/2308.13418.pdf")
    

    global model

    pdf_file_path = "pdf_dir/2308.13418.pdf"#predict_save(model)
    response = {
        "status_ code": HTTPStatus.OK,
        "data": {"file":pdf_file_path},
    }
    return response


def main():
    import uvicorn

    uvicorn.run("app:app", port=5000)


if __name__ == "__main__":
    main()
