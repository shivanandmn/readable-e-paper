import json
from os import remove, environ
from os.path import isdir, join, isfile, dirname
from shutil import which, rmtree
from subprocess import call, DEVNULL, check_output
from enum import Enum


class FigureType(Enum):
    figure = 1
    table = 2

    def __str__(self):
        if self.name == "figure":
            return "Figure"
        else:
            return "Table"


def fig_type_to_str(figure_type):
    if figure_type == FigureType.figure:
        return "Figure"
    elif figure_type == FigureType.table:
        return "Table"
    else:
        raise ValueError("%s is not a valid figure type" % str(figure_type))


def str_to_fig_type(string):
    if string == "Figure":
        return FigureType.figure
    elif string == "Table":
        return FigureType.table
    else:
        raise ValueError("%s is not a valid figure type string" % string)


class Figure(object):
    @staticmethod
    def from_dict(data):
        return Figure(
            str_to_fig_type(data["figure_type"]),
            data["name"],
            data["page"],
            data["dpi"],
            data["caption"],
            data["page_height"],
            data["page_width"],
            data["caption_bb"],
            data["region_bb"],
        )

    def as_dict(self):
        data = {}
        data.update(self.__dict__)
        data["figure_type"] = fig_type_to_str(data["figure_type"])
        return data

    def get_id(self):
        return self.figure_type, self.name, self.page

    def __init__(
        self,
        figure_type,
        name,
        page,
        dpi,
        caption,
        page_height=None,
        page_width=None,
        caption_bb=None,
        region_bb=None,
    ):
        if not isinstance(figure_type, FigureType):
            raise ValueError()
        if (
            page_width is None
            and page_height is not None
            or page_height is None
            and page_width is not None
        ):
            raise ValueError()
        if page_width is not None and page_width <= 0:
            raise ValueError()
        if page_height is not None and page_height <= 0:
            raise ValueError()
        if (caption_bb is not None or region_bb is not None) and dpi is None:
            raise ValueError()
        if page is not None and page <= 0:
            raise ValueError()
        if caption is not None and not isinstance(caption, str):
            raise ValueError("Initialized with caption of type %s" % type(caption))
        if not isinstance(name, str):
            raise ValueError("Name was not a string")

        self.name = name
        self.figure_type = figure_type
        self.page = page
        self.page_height = page_height
        self.page_width = page_width
        self.dpi = dpi
        self.caption = caption
        self.caption_bb = caption_bb
        self.region_bb = region_bb

    def __str__(self):
        if self.page_width is not None:
            return (
                "%s%s:<page=%d, caption=%s, " + "caption_bb=%s, region_bb=%s, dpi=%d>"
            ) % (
                "F" if self.figure_type == FigureType.figure else "T",
                self.name,
                self.page,
                self.caption[:20],
                str(self.caption_bb),
                str(self.region_bb),
                self.dpi,
            )
        else:
            return "%s:<page=%s, caption=%s>" % (
                self.name,
                str(self.page),
                self.caption[:20],
            )

    def __eq__(self, other):
        return isinstance(other, Figure) and self.__dict__ == other.__dict__


class PDFFigures2(object):
    """
    The new scala based extractor. Environment variable "PDFFIGURES2_HOME" can be used to point
    towards the home directory of the figure extractor. For example:
    PDFFIGURES2_HOME=/Users/chris/pdffigures2/
    Otherwise the the extractor is look for in the parent directory of this file
    """

    NAME = "pdffigures2"
    ENVIRON_VAR = "PDFFIGURES2_HOME"

    def __init__(self):
        if self.ENVIRON_VAR not in environ:
            self.extractor_home = dirname(dirname(__file__))
        else:
            self.extractor_home = environ[self.ENVIRON_VAR]
        if not isdir(self.extractor_home):
            raise ValueError(
                "Figure extractor home (%s) not found" % self.extractor_home
            )

    def load_json(self, output_file):
        figs = []
        if isfile(output_file):
            with open(output_file) as f:
                loaded_figs = json.load(f)
            for fig in loaded_figs["figures"] + loaded_figs["regionless-captions"]:
                if "regionBoundary" in fig:
                    caption = fig["caption"]
                    bb = fig["regionBoundary"]
                    region_bb = [bb["x1"], bb["y1"], bb["x2"], bb["y2"]]
                    bb = fig["captionBoundary"]
                    caption_bb = [bb["x1"], bb["y1"], bb["x2"], bb["y2"]]
                else:
                    bb = fig["boundary"]
                    caption_bb = [bb["x1"], bb["y1"], bb["x2"], bb["y2"]]
                    caption = fig["text"]
                    region_bb = None
                # For some reason (maybe due to text location issues in PDFBox?) the caption bounding box
                # is consistently just a little too small relative to our annotated caption bounding box.
                # It seems fair to account for this by fractionally expanding the returned bounding box
                caption_bb[1] -= 3
                caption_bb[0] -= 3
                caption_bb[2] += 3
                caption_bb[3] += 3
                figs.append(
                    Figure(
                        figure_type=str_to_fig_type(fig["figType"]),
                        name=fig["name"],
                        page=fig["page"] + 1,
                        dpi=72.0,
                        caption=caption,
                        caption_bb=caption_bb,
                        region_bb=region_bb,
                    )
                )
        return figs


def scale_figure(figure, dpi):
    """Returns the caption and region bbox of a `figure` when scaled to `dpi`"""
    rescaling = dpi / figure.dpi
    if figure.caption_bb is not None:
        caption_box = [x * rescaling for x in figure.caption_bb]
    else:
        caption_box = None
    if figure.region_bb is not None:
        region_box = [x * rescaling for x in figure.region_bb]
    else:
        region_box = None
    return caption_box, region_box
