from __future__ import annotations

import os

import nibabel as nb
import numpy as np


# generates the mask on the fly from the template image, using hard-coded markers
# the mask image is larger that the template to include the full face and allow processing
# of images with larger FoV (eg. cspine acquisitions)
def generate_deface_ear_mask(mni, resolution=1):

    deface_ear_mask = np.ones(np.asarray(mni.shape) * (1, 1, 2), dtype=np.uint8)
    affine_ext = mni.affine.copy()
    affine_ext[2, -1] -= mni.shape[-1]

    above_eye_marker = np.asarray([218, 240]) // resolution
    jaw_marker = np.asarray([130, 182]) // resolution
    ear_marker = np.asarray([26, 160]) // resolution
    ear_marker2 = np.asarray([6, 260]) // resolution

    # remove face
    deface_ear_mask[:, jaw_marker[0] :, : jaw_marker[1]] = 0
    y_coords = np.round(
        np.linspace(
            jaw_marker[0], above_eye_marker[0], above_eye_marker[1] - jaw_marker[1]
        )
    ).astype(np.int32)
    for z, y in zip(range(jaw_marker[1], above_eye_marker[1]), y_coords):
        deface_ear_mask[:, y:, z] = 0

    # remove ears
    deface_ear_mask[: ear_marker[0], :, : ear_marker[1]] = 0
    deface_ear_mask[-ear_marker[0] :, :, : ear_marker[1]] = 0
    x_coords = np.round(
        np.linspace(ear_marker[0], ear_marker2[0], ear_marker2[1] - ear_marker[1])
    ).astype(np.int32)
    for z, x in zip(range(ear_marker[1], ear_marker2[1]), x_coords):
        deface_ear_mask[:x, :, z] = 0
        deface_ear_mask[-x:, :, z] = 0

    # remove data on the image size where the body doesn't extend
    deface_ear_mask[-1] = 0
    deface_ear_mask[0] = 0
    deface_ear_mask[:, 0, :] = 0
    deface_ear_mask[:, -1, :] = 0
    deface_ear_mask[:, :, -1] = 0
    deface_ear_mask[:, :, :mni.shape[2]] = deface_ear_mask[:, :, mni.shape[2], np.newaxis]
    return nb.Nifti1Image(deface_ear_mask, affine_ext)

MODEL_CACHE = {}

def synthstrip_load_model(modelfile, cuda_devices=None):
    global MODEL_CACHE

    if not modelfile:
        fshome = os.environ.get('FREESURFER_HOME')
        modelfile = os.path.join(fshome, 'models', f'synthstrip.1.pt')

    import torch
    import torch.nn as nn

    from .external.synthstrip import StripModel

    # configure device
    gpu = os.environ.get('CUDA_VISIBLE_DEVICES', '0')
    if cuda_devices:
        os.environ['CUDA_VISIBLE_DEVICES'] = gpu
        device = torch.device('cuda')
        device_name = 'GPU'
    else:
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        device = torch.device('cpu')
        device_name = 'CPU'
#        if args.threads is not None:
#            torch.set_num_threads(args.threads)

    if modelfile in MODEL_CACHE:
        return MODEL_CACHE[modelfile], device

    with torch.no_grad():
        model = StripModel()
        model.to(device)
        model.eval()

    checkpoint = torch.load(modelfile, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    MODEL_CACHE[modelfile] = model
    return model, device

def synthstrip_mask(image_path, modelfile="", border=1):
    model, device = synthstrip_load_model(modelfile)

    import surfa as sf
    import torch

    from .external.synthstrip import extend_sdt

    image = sf.load_volume(image_path)

    for f in range(image.nframes):
        print(f + 1, end=' ', flush=True)
        frame = image.new(image.framed_data[..., f])

        # conform, fit to shape with factors of 64
        conformed = frame.conform(voxsize=1.0, dtype='float32', method='nearest', orientation='LIA').crop_to_bbox()
        target_shape = np.clip(np.ceil(np.array(conformed.shape[:3]) / 64).astype(int) * 64, 192, 320)
        conformed = conformed.reshape(target_shape)

        # normalize
        conformed -= conformed.min()
        conformed = (conformed / conformed.percentile(99)).clip(0, 1)

        # predict the sdt
        with torch.no_grad():
            input_tensor = torch.from_numpy(conformed.data[np.newaxis, np.newaxis]).to(device)
            sdt = model(input_tensor).cpu().numpy().squeeze()

        # extend the sdt if needed, unconform
        sdt = extend_sdt(conformed.new(sdt), border=border)
        sdt = sdt.resample_like(image, fill=100)

        # extract mask, find largest CC to be safe
        yield sdt, (sdt < border).connected_component_mask(k=1, fill=True)
