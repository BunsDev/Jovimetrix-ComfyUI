"""
Jovimetrix - http://www.github.com/amorano/jovimetrix
Composition
"""

from enum import Enum
from typing import Any, List, Tuple

import cv2
import torch
import numpy as np

from loguru import logger

from comfy.utils import ProgressBar

from Jovimetrix import JOVBaseNode, WILDCARD
from Jovimetrix.sup.lexicon import Lexicon
from Jovimetrix.sup.util import parse_dynamic, parse_param, \
    zip_longest_fill, EnumConvertType
from Jovimetrix.sup.image import  channel_merge, \
    channel_solid, channel_swap, cv2tensor_full, image_convert, \
    image_crop, image_crop_center, image_crop_polygonal, image_grayscale, \
    image_mask, image_mask_add, image_matte, image_transform, \
    image_split, pixel_eval, tensor2cv, \
    image_edge_wrap, image_scalefit, cv2tensor, \
    image_stack, image_mirror, image_blend, \
    color_theory, remap_fisheye, remap_perspective, remap_polar, \
    remap_sphere, image_invert, \
    EnumImageType, EnumColorTheory, EnumProjection, \
    EnumScaleMode, EnumInterpolation, EnumBlendType, \
    EnumEdge, EnumMirrorMode, EnumOrientation, EnumPixelSwizzle, \
    MIN_IMAGE_SIZE

# =============================================================================

JOV_CATEGORY = "COMPOSE"

class EnumCropMode(Enum):
    CENTER = 20
    XY = 0
    FREE = 10

# =============================================================================

class TransformNode(JOVBaseNode):
    NAME = "TRANSFORM (JOV) 🏝️"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 0
    DESCRIPTION = """
Applies various geometric transformations to images, including translation, rotation, scaling, mirroring, tiling, perspective projection, and more. It offers extensive control over image manipulation to achieve desired visual effects.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
            Lexicon.XY: ("VEC2", {"default": (0, 0,), "step": 0.01, "precision": 4, "round": 0.00001, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.ANGLE: ("FLOAT", {"default": 0, "min": -180, "max": 180, "step": 0.01, "precision": 4, "round": 0.00001}),
            Lexicon.SIZE: ("VEC2", {"default": (1., 1.), "step": 0.01, "precision": 4, "round": 0.00001, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.TILE: ("VEC2", {"default": (1., 1.), "step": 0.1,  "precision": 4, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.EDGE: (EnumEdge._member_names_, {"default": EnumEdge.CLIP.name}),
            Lexicon.MIRROR: (EnumMirrorMode._member_names_, {"default": EnumMirrorMode.NONE.name}),
            Lexicon.PIVOT: ("VEC2", {"default": (0.5, 0.5), "step": 0.005, "precision": 4, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.PROJECTION: (EnumProjection._member_names_, {"default": EnumProjection.NORMAL.name}),
            Lexicon.TLTR: ("VEC4", {"default": (0, 0, 1, 0), "step": 0.005, "precision": 4, "label": [Lexicon.TOP, Lexicon.LEFT, Lexicon.TOP, Lexicon.RIGHT]}),
            Lexicon.BLBR: ("VEC4", {"default": (0, 1, 1, 1), "step": 0.005, "precision": 4, "label": [Lexicon.BOTTOM, Lexicon.LEFT, Lexicon.BOTTOM, Lexicon.RIGHT]}),
            Lexicon.STRENGTH: ("FLOAT", {"default": 1, "min": 0, "precision": 4, "step": 0.005}),
            Lexicon.MODE: (EnumScaleMode._member_names_, {"default": EnumScaleMode.NONE.name}),
            Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.SAMPLE: (EnumInterpolation._member_names_, {"default": EnumInterpolation.LANCZOS4.name}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw) -> Tuple[torch.Tensor, torch.Tensor]:
        pA = parse_param(kw, Lexicon.PIXEL, EnumConvertType.IMAGE, None)
        offset = parse_param(kw, Lexicon.XY, EnumConvertType.VEC2, (0, 0))
        angle = parse_param(kw, Lexicon.ANGLE, EnumConvertType.FLOAT, 0)
        size = parse_param(kw, Lexicon.SIZE, EnumConvertType.VEC2, (1, 1), zero=0.001)
        edge = parse_param(kw, Lexicon.EDGE, EnumConvertType.STRING, EnumEdge.CLIP.name)
        mirror = parse_param(kw, Lexicon.MIRROR, EnumConvertType.STRING, EnumMirrorMode.NONE.name)
        mirror_pivot = parse_param(kw, Lexicon.PIVOT, EnumConvertType.VEC2, (0.5, 0.5), 0, 1)
        tile_xy = parse_param(kw, Lexicon.TILE, EnumConvertType.VEC2INT, (1, 1), 1)
        proj = parse_param(kw, Lexicon.PROJECTION, EnumConvertType.STRING, EnumProjection.NORMAL.name)
        tltr = parse_param(kw, Lexicon.TLTR, EnumConvertType.VEC4, (0, 0, 1, 0), 0, 1)
        blbr = parse_param(kw, Lexicon.BLBR, EnumConvertType.VEC4, (0, 1, 1, 1), 0, 1)
        strength = parse_param(kw, Lexicon.STRENGTH, EnumConvertType.FLOAT, 1, 0, 1)
        mode = parse_param(kw, Lexicon.MODE, EnumConvertType.STRING, EnumScaleMode.NONE.name)
        wihi = parse_param(kw, Lexicon.WH, EnumConvertType.VEC2INT, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), MIN_IMAGE_SIZE)
        sample = parse_param(kw, Lexicon.SAMPLE, EnumConvertType.STRING, EnumInterpolation.LANCZOS4.name)
        matte = parse_param(kw, Lexicon.MATTE, EnumConvertType.VEC4INT, (0, 0, 0, 255), 0, 255)
        params = list(zip_longest_fill(pA, offset, angle, size, edge, tile_xy, mirror, mirror_pivot, proj, strength, tltr, blbr, mode, wihi, sample, matte))
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, offset, angle, size, edge, tile_xy, mirror, mirror_pivot, proj, strength, tltr, blbr, mode, wihi, sample, matte) in enumerate(params):
            pA = tensor2cv(pA) if pA is not None else channel_solid(chan=EnumImageType.BGRA)
            h, w = pA.shape[:2]
            edge = EnumEdge[edge]
            sample = EnumInterpolation[sample]
            pA = image_transform(pA, offset, angle, size, sample, edge)
            pA = image_crop_center(pA, w, h)

            mirror = EnumMirrorMode[mirror]
            if mirror != EnumMirrorMode.NONE:
                mpx, mpy = mirror_pivot
                pA = image_mirror(pA, mirror, mpx, mpy)
                pA = image_scalefit(pA, w, h, EnumScaleMode.FIT, sample)

            tx, ty = tile_xy
            if tx != 1. or ty != 1.:
                pA = image_edge_wrap(pA, tx / 2 - 0.5, ty / 2 - 0.5)
                pA = image_scalefit(pA, w, h, EnumScaleMode.FIT, sample)

            proj = EnumProjection[proj]
            match proj:
                case EnumProjection.PERSPECTIVE:
                    x1, y1, x2, y2 = tltr
                    x4, y4, x3, y3 = blbr
                    sh, sw = pA.shape[:2]
                    x1, x2, x3, x4 = map(lambda x: x * sw, [x1, x2, x3, x4])
                    y1, y2, y3, y4 = map(lambda y: y * sh, [y1, y2, y3, y4])
                    pA = remap_perspective(pA, [[x1, y1], [x2, y2], [x3, y3], [x4, y4]])
                case EnumProjection.SPHERICAL:
                    pA = remap_sphere(pA, strength)
                case EnumProjection.FISHEYE:
                    pA = remap_fisheye(pA, strength)
                case EnumProjection.POLAR:
                    pA = remap_polar(pA)

            if proj != EnumProjection.NORMAL:
                pA = image_scalefit(pA, w, h, EnumScaleMode.FIT, sample)

            mode = EnumScaleMode[mode]
            if mode != EnumScaleMode.NONE:
                w, h = wihi
                pA = image_scalefit(pA, w, h, mode, sample)
            images.append(cv2tensor_full(pA, matte))
            pbar.update_absolute(idx)
        return [torch.cat(i, dim=0) for i in list(zip(*images))]

class BlendNode(JOVBaseNode):
    NAME = "BLEND (JOV) ⚗️"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 10
    DESCRIPTION = """
Combines two input images using various blending modes, such as normal, screen, multiply, overlay, etc. It also supports alpha blending and masking to achieve complex compositing effects. This node is essential for creating layered compositions and adding visual richness to images.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL_A: (WILDCARD, {"tooltip": "Background Plate"}),
            Lexicon.PIXEL_B: (WILDCARD, {"tooltip": "Image to Overlay on Background Plate"}),
            Lexicon.MASK: (WILDCARD, {"tooltip": "Optional Mask to use for Alpha Blend Operation. If empty, will use the ALPHA of B"}),
            Lexicon.FUNC: (EnumBlendType._member_names_, {"default": EnumBlendType.NORMAL.name, "tooltip": "Blending Operation"}),
            Lexicon.A: ("FLOAT", {"default": 1, "min": 0, "max": 1, "step": 0.01, "tooltip": "Amount of Blending to Perform on the Selected Operation"}),
            Lexicon.FLIP: ("BOOLEAN", {"default": False}),
            Lexicon.INVERT: ("BOOLEAN", {"default": False, "tooltip": "Invert the mask input"}),
            Lexicon.MODE: (EnumScaleMode._member_names_, {"default": EnumScaleMode.NONE.name}),
            Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.SAMPLE: (EnumInterpolation._member_names_, {"default": EnumInterpolation.LANCZOS4.name}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw) -> Tuple[torch.Tensor, torch.Tensor]:
        pA = parse_param(kw, Lexicon.PIXEL_A, EnumConvertType.IMAGE, None)
        pB = parse_param(kw, Lexicon.PIXEL_B, EnumConvertType.IMAGE, None)
        mask = parse_param(kw, Lexicon.MASK, EnumConvertType.IMAGE, None)
        func = parse_param(kw, Lexicon.FUNC, EnumConvertType.STRING, EnumBlendType.NORMAL.name)
        alpha = parse_param(kw, Lexicon.A, EnumConvertType.FLOAT, 1, 0, 1)
        flip = parse_param(kw, Lexicon.FLIP, EnumConvertType.BOOLEAN, False)
        mode = parse_param(kw, Lexicon.MODE, EnumConvertType.STRING, EnumScaleMode.NONE.name)
        wihi = parse_param(kw, Lexicon.WH, EnumConvertType.VEC2INT, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), MIN_IMAGE_SIZE)
        sample = parse_param(kw, Lexicon.SAMPLE, EnumConvertType.STRING, EnumInterpolation.LANCZOS4.name)
        matte = parse_param(kw, Lexicon.MATTE, EnumConvertType.VEC3INT, (0, 0, 0), 0, 255)
        invert = parse_param(kw, Lexicon.INVERT, EnumConvertType.BOOLEAN, False)
        params = list(zip_longest_fill(pA, pB, mask, func, alpha, flip, mode, wihi, sample, matte, invert))
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, pB, mask, func, alpha, flip, mode, wihi, sample, matte, invert) in enumerate(params):
            if flip:
                pA, pB = pB, pA

            w, h = MIN_IMAGE_SIZE, MIN_IMAGE_SIZE
            if pA is not None:
                h, w = pA.shape[:2]
            elif pB is not None:
                h, w = pB.shape[:2]

            tmask = None
            if pA is None:
                pA = channel_solid(w, h, matte, chan=EnumImageType.BGRA)
            else:
                pA = tensor2cv(pA)
                matted = pixel_eval(matte, EnumImageType.BGRA)
                pA = image_matte(pA, matted)
                tmask = pA

            if pB is None:
                pB = channel_solid(w, h, matte, chan=EnumImageType.BGRA)
            else:
                pB = tensor2cv(pB)
                tmask = pB

            if mask is None:
                mask = channel_solid(w, h, (matte[3],), EnumImageType.GRAYSCALE) if tmask is None else image_mask(tmask)
            else:
                mask = tensor2cv(mask)

            if invert:
                mask = 255 - mask

            func = EnumBlendType[func]
            img = image_blend(pA, pB, mask, func, alpha)
            mode = EnumScaleMode[mode]
            if mode != EnumScaleMode.NONE:
                w, h = wihi
                sample = EnumInterpolation[sample]
                img = image_scalefit(img, w, h, mode, sample)
            img = cv2tensor_full(img, matte)
            images.append(img)
            pbar.update_absolute(idx)
        return [torch.cat(i, dim=0) for i in list(zip(*images))]

class PixelSplitNode(JOVBaseNode):
    NAME = "PIXEL SPLIT (JOV) 💔"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("MASK", "MASK", "MASK", "MASK",)
    RETURN_NAMES = (Lexicon.RI, Lexicon.GI, Lexicon.BI, Lexicon.MI)
    SORT = 40
    DESCRIPTION = """
Takes an input image and splits it into its individual color channels (red, green, blue), along with a mask channel. This node is useful for separating different color components of an image for further processing or analysis.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {})
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw) -> Tuple[torch.Tensor, torch.Tensor]:
        images = []
        pA = parse_param(kw, Lexicon.PIXEL, EnumConvertType.IMAGE, None)
        pbar = ProgressBar(len(pA))
        for idx, (pA,) in enumerate([pA]):
            pA = tensor2cv(pA) if pA is not None else channel_solid(chan=EnumImageType.BGRA)
            pA = image_mask_add(pA)
            pA = [cv2tensor(x) for x in image_split(pA)]
            images.append(pA)
            pbar.update_absolute(idx)
        return [torch.cat(i, dim=0) for i in list(zip(*images))]

class PixelMergeNode(JOVBaseNode):
    NAME = "PIXEL MERGE (JOV) 🫂"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 45
    DESCRIPTION = """
Combines individual color channels (red, green, blue) along with an optional mask channel to create a composite image. This node is useful for merging separate color components into a single image for visualization or further processing.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.R: (WILDCARD, {}),
            Lexicon.G: (WILDCARD, {}),
            Lexicon.B: (WILDCARD, {}),
            Lexicon.A: (WILDCARD, {}),
            Lexicon.MODE: (EnumScaleMode._member_names_, {"default": EnumScaleMode.NONE.name}),
            Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.SAMPLE: (EnumInterpolation._member_names_, {"default": EnumInterpolation.LANCZOS4.name}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw)  -> Tuple[torch.Tensor, torch.Tensor]:
        R = parse_param(kw, Lexicon.R, EnumConvertType.IMAGE, None)
        G = parse_param(kw, Lexicon.G, EnumConvertType.IMAGE, None)
        B = parse_param(kw, Lexicon.B, EnumConvertType.IMAGE, None)
        A = parse_param(kw, Lexicon.A, EnumConvertType.IMAGE, None)
        mode = parse_param(kw, Lexicon.MODE, EnumConvertType.STRING, EnumScaleMode.NONE.name)
        wihi = parse_param(kw, Lexicon.WH, EnumConvertType.VEC2INT, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), MIN_IMAGE_SIZE)
        sample = parse_param(kw, Lexicon.SAMPLE, EnumConvertType.STRING, EnumInterpolation.LANCZOS4.name)
        matte = parse_param(kw, Lexicon.MATTE, EnumConvertType.VEC3INT, (0, 0, 0), 0, 255)
        if len(R)+len(B)+len(G)+len(A) == 0:
            img = channel_solid(MIN_IMAGE_SIZE, MIN_IMAGE_SIZE, 0, EnumImageType.BGRA)
            return list(cv2tensor_full(img, matte))
        params = list(zip_longest_fill(R, G, B, A, mode, wihi, sample, matte))
        images = []
        pbar = ProgressBar(len(params))
        for idx, (r, g, b, a, mode, wihi, sample, matte) in enumerate(params):
            w, h = wihi
            ret = [channel_solid(w, h, chan=EnumImageType.GRAYSCALE) if x is None else image_grayscale(tensor2cv(x)) for x in (b, g, r, a)]
            h, w = ret[0].shape[:2]
            ret = [cv2.resize(r, (w, h)) for r in ret]
            img = channel_merge(ret)
            mode = EnumScaleMode[mode]
            if mode != EnumScaleMode.NONE:
                w, h = wihi
                sample = EnumInterpolation[sample]
                img = image_scalefit(img, w, h, mode, sample)
            images.append(cv2tensor_full(img, matte))
            pbar.update_absolute(idx)
        return [torch.cat(i, dim=0) for i in list(zip(*images))]

class PixelSwapNode(JOVBaseNode):
    NAME = "PIXEL SWAP (JOV) 🔃"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 48
    DESCRIPTION = """
Swap pixel values between two input images based on specified channel swizzle operations. Options include pixel inputs, swap operations for red, green, blue, and alpha channels, and constant values for each channel. The swap operations allow for flexible pixel manipulation by determining the source of each channel in the output image, whether it be from the first image, the second image, or a constant value.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL_A: (WILDCARD, {}),
            Lexicon.PIXEL_B: (WILDCARD, {}),
            Lexicon.SWAP_R: (EnumPixelSwizzle._member_names_,
                             {"default": EnumPixelSwizzle.RED_A.name}),
            Lexicon.R: ("INT", {"default": 0, "step": 1, "min": 0, "max": 255}),
            Lexicon.SWAP_G: (EnumPixelSwizzle._member_names_,
                             {"default": EnumPixelSwizzle.GREEN_A.name}),
            Lexicon.G: ("INT", {"default": 0, "step": 1, "min": 0, "max": 255}),
            Lexicon.SWAP_B: (EnumPixelSwizzle._member_names_,
                             {"default": EnumPixelSwizzle.BLUE_A.name}),
            Lexicon.B: ("INT", {"default": 0, "step": 1, "min": 0, "max": 255}),
            Lexicon.SWAP_A: (EnumPixelSwizzle._member_names_,
                             {"default": EnumPixelSwizzle.ALPHA_A.name}),
            Lexicon.A: ("INT", {"default": 0, "step": 1, "min": 0, "max": 255}),
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw)  -> Tuple[torch.Tensor, torch.Tensor]:
        pA = parse_param(kw, Lexicon.PIXEL_A, EnumConvertType.IMAGE, None)
        pB = parse_param(kw, Lexicon.PIXEL_B, EnumConvertType.IMAGE, None)
        swap_r = parse_param(kw, Lexicon.SWAP_R, EnumConvertType.STRING, EnumPixelSwizzle.RED_A.name)
        r = parse_param(kw, Lexicon.R, EnumConvertType.INT, 0, 0, 255)
        swap_g = parse_param(kw, Lexicon.SWAP_G, EnumConvertType.STRING, EnumPixelSwizzle.GREEN_A.name)
        g = parse_param(kw, Lexicon.G, EnumConvertType.INT, 0, 0, 255)
        swap_b = parse_param(kw, Lexicon.SWAP_B, EnumConvertType.STRING, EnumPixelSwizzle.BLUE_A.name)
        b = parse_param(kw, Lexicon.B, EnumConvertType.INT, 0, 0, 255)
        swap_a = parse_param(kw, Lexicon.SWAP_A, EnumConvertType.STRING, EnumPixelSwizzle.ALPHA_A.name)
        a = parse_param(kw, Lexicon.A, EnumConvertType.INT, 0, 0, 255)
        params = list(zip_longest_fill(pA, pB, r, swap_r, g, swap_g, b, swap_b, a, swap_a))
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, pB, r, swap_r, g, swap_g, b, swap_b, a, swap_a) in enumerate(params):
            pA = tensor2cv(pA) if pA is not None else channel_solid(chan=EnumImageType.BGRA)
            h, w = pA.shape[:2]
            pB = tensor2cv(pB) if pB is not None else channel_solid(w, h, chan=EnumImageType.BGRA)
            out = channel_solid(w, h, (r,g,b,a), EnumImageType.BGRA)

            if len(pA) < 2 or pA.shape[2] < 4:
                pA = image_convert(pA, 4)
            if len(pB) < 2 or pB.shape[2] < 4:
                pB = image_convert(pB, 4)

            # crop fit?
            pB = image_scalefit(pB, w, h, EnumScaleMode.CROP)

            def swapper(swap_out:EnumPixelSwizzle, swap_in:EnumPixelSwizzle) -> np.ndarray[Any]:
                target = out
                swap_in = EnumPixelSwizzle[swap_in]
                if swap_in in [EnumPixelSwizzle.RED_A, EnumPixelSwizzle.GREEN_A,
                            EnumPixelSwizzle.BLUE_A, EnumPixelSwizzle.ALPHA_A]:
                    target = pA
                elif swap_in in [EnumPixelSwizzle.RED_B, EnumPixelSwizzle.GREEN_B,
                            EnumPixelSwizzle.BLUE_B, EnumPixelSwizzle.ALPHA_B]:
                    target = pB
                elif swap_in != EnumPixelSwizzle.CONSTANT:
                    target = channel_swap(pA, swap_out, pB, swap_in)
                return target

            # logger.debug(swap_r, swap_g, swap_b, swap_a)
            out[:,:,0] = swapper(EnumPixelSwizzle.BLUE_A, swap_b)[:,:,0]
            out[:,:,1] = swapper(EnumPixelSwizzle.GREEN_A, swap_g)[:,:,1]
            out[:,:,2] = swapper(EnumPixelSwizzle.RED_A, swap_r)[:,:,2]
            out[:,:,3] = swapper(EnumPixelSwizzle.ALPHA_A, swap_a)[:,:,3]
            images.append(cv2tensor_full(out))
            pbar.update_absolute(idx)
        return [torch.cat(i, dim=0) for i in list(zip(*images))]

class StackNode(JOVBaseNode):
    NAME = "STACK (JOV) ➕"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 75
    DESCRIPTION = """
Merge multiple input images into a single composite image by stacking them along a specified axis. Options include axis, stride, scaling mode, width and height, interpolation method, and matte color. The axis parameter allows for horizontal, vertical, or grid stacking of images, while stride controls the spacing between them.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
            "required": {},
            "optional": {
                Lexicon.AXIS: (EnumOrientation._member_names_, {"default": EnumOrientation.GRID.name, "tooltip":"Choose the direction in which to stack the images. Options include horizontal, vertical, or a grid layout"}),
                Lexicon.STEP: ("INT", {"min": 1, "step": 1, "default": 1, "tooltip":"Specify the spacing between each stacked image. This determines how far apart the images are from each other"}),
                Lexicon.MODE: (EnumScaleMode._member_names_, {"default": EnumScaleMode.NONE.name}),
                Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
                Lexicon.SAMPLE: (EnumInterpolation._member_names_, {"default": EnumInterpolation.LANCZOS4.name}),
                Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
            }
        }
        return Lexicon._parse(d, cls)

    def run(self, **kw) -> Tuple[torch.Tensor, torch.Tensor]:
        images = parse_dynamic(kw, 0, EnumConvertType.IMAGE, None)
        if len(images) == 0:
            logger.warning("no images to stack")
            return
        axis = parse_param(kw, Lexicon.AXIS, EnumConvertType.STRING, EnumOrientation.GRID.name)[0]
        stride = parse_param(kw, Lexicon.STEP, EnumConvertType.INT, 1, 1)[0]
        mode = parse_param(kw, Lexicon.MODE, EnumConvertType.STRING, EnumScaleMode.NONE.name)[0]
        wihi = parse_param(kw, Lexicon.WH, EnumConvertType.VEC2INT, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), MIN_IMAGE_SIZE)[0]
        sample = parse_param(kw, Lexicon.SAMPLE, EnumConvertType.STRING, EnumInterpolation.LANCZOS4.name)[0]
        matte = parse_param(kw, Lexicon.MATTE, EnumConvertType.VEC4INT, (0, 0, 0, 255), 0, 255)[0]
        images = [tensor2cv(img) for img in images]
        axis = EnumOrientation[axis]
        img = image_stack(images, axis, stride, matte)
        mode = EnumScaleMode[mode]
        if mode != EnumScaleMode.NONE:
            w, h = wihi
            sample = EnumInterpolation[sample]
            img = image_scalefit(img, w, h, mode, sample)
        return cv2tensor_full(img, matte)

class CropNode(JOVBaseNode):
    NAME = "CROP (JOV) ✂️"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 5
    DESCRIPTION = """
Extract a portion of an input image or resize it. It supports various cropping modes, including center cropping, custom XY cropping, and freeform polygonal cropping. This node is useful for preparing image data for specific tasks or extracting regions of interest.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
            Lexicon.FUNC: (EnumCropMode._member_names_, {"default": EnumCropMode.CENTER.name}),
            Lexicon.XY: ("VEC2", {"default": (0, 0), "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.WH: ("VEC2", {"default": (512, 512), "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.TLTR: ("VEC4", {"default": (0, 0, 0, 1), "step": 0.01, "precision": 5, "round": 0.000001, "label": [Lexicon.TOP, Lexicon.LEFT, Lexicon.TOP, Lexicon.RIGHT]}),
            Lexicon.BLBR: ("VEC4", {"default": (1, 0, 1, 1), "step": 0.01, "precision": 5, "round": 0.000001, "label": [Lexicon.BOTTOM, Lexicon.LEFT, Lexicon.BOTTOM, Lexicon.RIGHT]}),
            Lexicon.RGB: ("VEC3", {"default": (0, 0, 0),  "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B], "rgb": True})
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw) -> Tuple[List[torch.Tensor], List[torch.Tensor]]:
        pA = parse_param(kw, Lexicon.PIXEL, EnumConvertType.IMAGE, None)
        func = parse_param(kw, Lexicon.FUNC, EnumConvertType.STRING, EnumCropMode.CENTER.name)
        # if less than 1 then use as scalar, over 1 = int(size)
        xy = parse_param(kw, Lexicon.XY, EnumConvertType.VEC2, (0, 0,), 1)
        wihi = parse_param(kw, Lexicon.WH, EnumConvertType.VEC2INT, (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE), MIN_IMAGE_SIZE)
        tltr = parse_param(kw, Lexicon.TLTR, EnumConvertType.VEC4, (0, 0, 0, 1,), 0, 1)
        blbr = parse_param(kw, Lexicon.BLBR, EnumConvertType.VEC4, (1, 0, 1, 1,), 0, 1)
        color = parse_param(kw, Lexicon.RGB, EnumConvertType.VEC3INT, (0, 0, 0,), 0, 255)
        params = list(zip_longest_fill(pA, func, xy, wihi, tltr, blbr, color))
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, func, xy, wihi, tltr, blbr, color) in enumerate(params):
            width, height = wihi
            pA = tensor2cv(pA) if pA is not None else channel_solid(width, height)
            func = EnumCropMode[func]
            if func == EnumCropMode.FREE:
                y1, x1, y2, x2 = tltr
                y4, x4, y3, x3 = blbr
                points = (x1 * width, y1 * height), (x2 * width, y2 * height), \
                    (x3 * width, y3 * height), (x4 * width, y4 * height)
                pA = image_crop_polygonal(pA, points)
            elif func == EnumCropMode.XY:
                pA = image_crop(pA, width, height, xy)
            else:
                pA = image_crop_center(pA, width, height)
            images.append(cv2tensor_full(pA, color))
            pbar.update_absolute(idx)
        return [torch.cat(i, dim=0) for i in list(zip(*images))]

class ColorTheoryNode(JOVBaseNode):
    NAME = "COLOR THEORY (JOV) 🛞"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = (Lexicon.C1, Lexicon.C2, Lexicon.C3, Lexicon.C4, Lexicon.C5)
    SORT = 100
    DESCRIPTION = """
Apply various color harmony schemes to an input image using the Color Theory Node, generating multiple color variants based on the selected scheme. Supported schemes include complimentary, analogous, triadic, tetradic, and more. Users can customize the angle of separation for color calculations, offering flexibility in color manipulation and exploration of different color palettes.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
            Lexicon.SCHEME: (EnumColorTheory._member_names_, {"default": EnumColorTheory.COMPLIMENTARY.name}),
            Lexicon.VALUE: ("INT", {"default": 45, "min": -90, "max": 90, "step": 1, "tooltip": "Custom angle of separation to use when calculating colors"}),
            Lexicon.INVERT: ("BOOLEAN", {"default": False})
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw) -> Tuple[List[torch.Tensor], List[torch.Tensor]]:
        pA = parse_param(kw, Lexicon.PIXEL, EnumConvertType.IMAGE, None)
        scheme = parse_param(kw, Lexicon.SCHEME, EnumConvertType.STRING, EnumColorTheory.COMPLIMENTARY.name)
        user = parse_param(kw, Lexicon.VALUE, EnumConvertType.INT, 0, -180, 180)
        invert = parse_param(kw, Lexicon.INVERT, EnumConvertType.BOOLEAN, False)
        params = list(zip_longest_fill(pA, scheme, user, invert))
        images = []
        pbar = ProgressBar(len(params))
        for idx, (img, target, user, invert) in enumerate(params):
            img = tensor2cv(img) if img is not None else channel_solid(chan=EnumImageType.BGRA)
            target = EnumColorTheory[target]
            img = color_theory(img, user, target)
            if invert:
                img = (image_invert(s, 1) for s in img)
            images.append([cv2tensor(a) for a in img])
            pbar.update_absolute(idx)
        return [torch.cat(i, dim=0) for i in list(zip(*images))]

class ImageFlatten(JOVBaseNode):
    NAME = "FLATTEN (JOV) ⬇️"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK")
    RETURN_NAMES = (Lexicon.IMAGE, Lexicon.RGB, Lexicon.MASK)
    SORT = 500
    DESCRIPTION = """
Combine multiple input images into a single image by summing their pixel values. This operation is useful for merging multiple layers or images into one composite image, such as combining different elements of a design or merging masks. Users can specify the blending mode and interpolation method to control how the images are combined. Additionally, a matte can be applied to adjust the transparency of the final composite image.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.MODE: (EnumScaleMode._member_names_, {"default": EnumScaleMode.NONE.name}),
            Lexicon.SAMPLE: (EnumInterpolation._member_names_, {"default": EnumInterpolation.LANCZOS4.name}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1, "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A], "rgb": True})
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw) -> torch.Tensor:
        pA = parse_dynamic(kw, 0, EnumConvertType.IMAGE, None)
        pA = [item for sublist in pA for item in sublist]
        if len(pA) == 0:
            logger.error("no images to flatten")
            return ()
        pA = [image_convert(tensor2cv(img), 4) for img in pA]
        mode = parse_param(kw, Lexicon.MODE, EnumConvertType.STRING, EnumScaleMode.NONE.name)
        sample = parse_param(kw, Lexicon.SAMPLE, EnumConvertType.STRING, EnumInterpolation.LANCZOS4.name)
        matte = parse_param(kw, Lexicon.MATTE, EnumConvertType.VEC4INT, (0, 0, 0, 255), 0, 255)
        images = []
        params = list(zip_longest_fill(mode, sample, matte))
        pbar = ProgressBar(len(params))
        for idx, (mode, sample, matte) in enumerate(params):
            current = pA[0]
            h, w = pA[0].shape[:2]
            mode = EnumScaleMode[mode]
            if len(pA) > 1:
                for x in pA[1:]:
                    if mode != EnumScaleMode.NONE:
                        x = image_scalefit(x, w, h, mode, sample)
                    x = image_scalefit(x, w, h, EnumScaleMode.CROP, sample)
                    #@TODO: ADD VARIOUS COMP OPS?
                    current = cv2.add(current, x)
            images.append(cv2tensor_full(current, matte))
            pbar.update_absolute(idx)
        return [torch.cat(i, dim=0) for i in list(zip(*images))]

'''
class HistogramNode(JOVImageSimple):
    NAME = "HISTOGRAM (JOV) 👁‍🗨"
    CATEGORY = f"JOVIMETRIX 🔺🟩🔵/{JOV_CATEGORY}"
        RETURN_TYPES = ("IMAGE", )
    RETURN_NAMES = (Lexicon.IMAGE,)
    SORT = 40
    DESCRIPTION = """
The Histogram Node generates a histogram representation of the input image, showing the distribution of pixel intensity values across different bins. This visualization is useful for understanding the overall brightness and contrast characteristics of an image. Additionally, the node performs histogram normalization, which adjusts the pixel values to enhance the contrast of the image. Histogram normalization can be helpful for improving the visual quality of images or preparing them for further image processing tasks.
"""

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
        }}
        return Lexicon._parse(d, cls)

    def run(self, **kw) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pA = parse_param(kw, Lexicon.PIXEL, None), EnumConvertType.IMAGE, None)
        params = list(zip_longest_fill(pA,))
        images = []
        pbar = ProgressBar(len(params))
        for idx, (pA, ) in enumerate(params):
            pA = image_histogram(pA)
            pA = image_histogram_normalize(pA)
            images.append(cv2tensor(pA))
            pbar.update_absolute(idx)
        return list(zip(*images))
'''
