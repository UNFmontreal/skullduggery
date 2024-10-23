from __future__ import annotations

import nibabel as nb


def output_debug_images(ref, moving, affine):
    moving_nb = moving.get_image()
    moving_suffix = moving.entities["suffix"]
    moving_reg_path = moving.path.replace(
        f"_{moving_suffix}", f"_space-MNIlinreg_{moving_suffix}"
    )
    moving_reg = affine.transform(
        moving_nb.get_fdata(),
        image_grid2world=moving_nb.affine,
        sampling_grid_shape=ref.shape,
        sampling_grid2world=ref.affine,
    )
    logging.info(
        f"writing reference serie linearly warped to MNI template: {moving_reg_path}"
    )
    nb.Nifti1Image(moving_reg, ref.affine).to_filename(moving_reg_path)

    ref_inv_path = moving.path.replace(
        f"_{moving_suffix}", f"_mod-{moving_suffix}_MNIlinreg"
    )
    ref_inv = affine.transform_inverse(
        ref.get_fdata(),
        image_grid2world=ref.affine,
        sampling_grid_shape=moving_nb.shape,
        sampling_grid2world=moving_nb.affine,
    )
    logging.info(
        f"writing MNI template image linearly warped to the reference serie: {ref_inv_path}"
    )
    nb.Nifti1Image(ref_inv, moving_nb.affine).to_filename(ref_inv_path)
