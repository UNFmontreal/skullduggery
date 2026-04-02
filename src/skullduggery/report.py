import bids
from pathlib import Path
from nireports.interfaces.reporting.masks import SimpleShowMaskRPT
from nireports.assembler.report import Report


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


def generate_deface_mosaic_report(
    masked_image_path: Path,
    warped_mask_path: Path,
    output_path: Path):
    """
    Generates a mosaic illustrating the results of the deface
    registration showing the defaced image against the warped mask.
    """

    mosaic = SimpleShowMaskRPT(
        background_file=str(masked_image_path),
        mask_file=str(warped_mask_path),
        out_report=str(output_path),
    )
    mosaic.run()

def generate_figure_path(series: bids.BIDSImageFile, desc: str)-> pathlib.Path:
    entities = series.entities.copy()
    entities['datatype'] = 'figures'
    entities['desc'] = desc
    bids.
