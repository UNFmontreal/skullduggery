import json
import bids
from pathlib import Path
from nireports.assembler.report import Report
import nireports.assembler.report
from nireports.assembler import data as nr_data

from nibabel.spatialimages import SpatialImage

from nireports.interfaces.reporting.base import compose_view
from nireports.reportlets.mosaic import plot_segs

bids_config_path = nr_data.load("nipreps.json")
bids_config = json.loads(bids_config_path.read_bytes())


class DefaceReport(Report):
    def __init__(self, subject, session=None):
        super().__init__(subject, session)
        self.subject = subject

    def _load_config(self, config):
        self.sections = [
            {
                "name": "Registration",
                "reportlets": [{"pattern": "**/sub-{subject}_ses-{session}_*desc-reg_*.svg"}],
            },
            {
                "name": "Defacing",
                "reportlets": [{"pattern": "**/sub-{subject}_ses-{session}_*desc-mask_*.svg"}],
            },
        ]


def generate_deface_mosaic_report(masked_image: SpatialImage, warped_mask: SpatialImage, output_path: Path):
    """
    Generates a mosaic illustrating the results of the deface
    registration showing the defaced image against the warped mask.
    """

    compose_view(
        plot_segs(
            image_nii=masked_image,
            seg_niis=[warped_mask],
            bbox_nii=warped_mask,
            masked=True,
        ),
        fg_svgs=None,
        out_file=output_path,
    )



def generate_figure_path(layout: bids.BIDSLayout, series: bids.layout.BIDSFile, desc: str) -> Path:
    entities = series.get_entities(metadata=False)
    entities["datatype"] = "figures"
    entities["desc"] = desc
    return bids.layout.layout.build_path(
        entities,
        path_patterns=bids_config['default_path_patterns']
    )
