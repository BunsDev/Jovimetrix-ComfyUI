"""
Jovimetrix - http://www.github.com/amorano/jovimetrix
Creation
"""

import torch
from PIL import ImageFont

from loguru import logger

import comfy
# from server import PromptServer

from Jovimetrix import WILDCARD, JOVImageSimple, JOVImageMultiple, \
    JOV_HELP_URL, MIN_IMAGE_SIZE

from Jovimetrix.sup.lexicon import Lexicon

from Jovimetrix.sup.util import parse_tuple, \
    parse_number, zip_longest_fill, EnumTupleType

from Jovimetrix.sup.image import batch_extract, channel_solid, cv2tensor_full, \
    image_grayscale, image_mask_add, image_matte, image_rotate, image_stereogram, \
    image_translate, pil2cv, pixel_eval, tensor2cv, shape_ellipse, shape_polygon, \
    shape_quad, EnumEdge, EnumImageType

from Jovimetrix.sup.text import font_all, font_all_names, text_autosize, text_draw, \
    EnumAlignment, EnumJustify, EnumShapes

# =============================================================================

JOV_CATEGORY = "JOVIMETRIX 🔺🟩🔵/CREATE"

# =============================================================================

class ConstantNode(JOVImageMultiple):
    NAME = "CONSTANT (JOV) 🟪"
    CATEGORY = JOV_CATEGORY
    DESCRIPTION = "Create a single RGBA block of color. Useful for masks, overlays and general filtering."

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {"tooltip":"Optional Image to Matte with Selected Color"}),
            Lexicon.RGBA_A: ("VEC4", {"default": (0, 0, 0, 255), "step": 1,
                                      "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A],
                                      "rgb": True, "tooltip": "Constant Color to Output"}),
            Lexicon.WH: ("VEC2", {"default": (512, 512), "step": 1,
                                  "label": [Lexicon.W, Lexicon.H],
                                  "tooltip": "Desired Width and Height of the Color Output"})
        }}
        return Lexicon._parse(d, JOV_HELP_URL + "/CREATE#-constant")

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor]:
        pA = kw.get(Lexicon.PIXEL, None)
        pA = [None] if pA is None else batch_extract(pA)
        wihi = parse_tuple(Lexicon.WH, kw, default=(MIN_IMAGE_SIZE, MIN_IMAGE_SIZE,), clip_min=1)
        matte = parse_tuple(Lexicon.RGBA_A, kw, default=(0, 0, 0, 255), clip_min=0, clip_max=255)
        images = []
        params = [tuple(x) for x in zip_longest_fill(pA, wihi, matte)]
        pbar = comfy.utils.ProgressBar(len(params))
        for idx, (pA, wihi, matte) in enumerate(params):
            width, height = wihi
            matte = pixel_eval(matte, EnumImageType.BGRA)
            if pA is None:
                pA = channel_solid(width, height, matte, EnumImageType.BGRA)
            else:
                pA = tensor2cv(pA)
            images.append(cv2tensor_full(pA, matte))
            pbar.update_absolute(idx)
        return list(zip(*images))

class ShapeNode(JOVImageMultiple):
    NAME = "SHAPE GENERATOR (JOV) ✨"
    CATEGORY = JOV_CATEGORY
    DESCRIPTION = "Generate polyhedra for masking or texture work."

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.SHAPE: (EnumShapes._member_names_, {"default": EnumShapes.CIRCLE.name}),
            Lexicon.SIDES: ("INT", {"default": 3, "min": 3, "max": 100, "step": 1}),
            Lexicon.RGBA_A: ("VEC4", {"default": (255, 255, 255, 255), "step": 1,
                                      "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A],
                                      "rgb": True, "tooltip": "Main Shape Color"}),
            Lexicon.MATTE: ("VEC4", {"default": (0, 0, 0, 255), "step": 1,
                                     "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A],
                                     "rgb": True, "tooltip": "Background Color"}),
            Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE),
                                  "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.ANGLE: ("FLOAT", {"default": 0, "min": -180, "max": 180,
                                      "step": 0.01, "precision": 4, "round": 0.00001}),
            Lexicon.SIZE: ("VEC2", {"default": (1., 1.), "step": 0.01, "precision": 4,
                                    "round": 0.00001, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.EDGE: (EnumEdge._member_names_, {"default": EnumEdge.CLIP.name}),
        }}
        d = Lexicon._parse(d, JOV_HELP_URL + "/CREATE#-shape-generator")
        return d

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor]:
        shape = kw.get(Lexicon.SHAPE, EnumShapes.CIRCLE)
        sides = kw.get(Lexicon.SIDES, 3)
        angle = kw.get(Lexicon.ANGLE, 0)
        edge = kw.get(Lexicon.EDGE, EnumEdge.CLIP)
        size = parse_tuple(Lexicon.SIZE, kw, EnumTupleType.FLOAT, default=(1., 1.,))
        wihi = parse_tuple(Lexicon.WH, kw, default=(MIN_IMAGE_SIZE, MIN_IMAGE_SIZE,))
        color = parse_tuple(Lexicon.RGBA_A, kw, default=(255, 255, 255, 255))
        matte = parse_tuple(Lexicon.MATTE, kw, default=(0, 0, 0, 255))
        params = [tuple(x) for x in zip_longest_fill(shape, sides, angle, edge,
                                                     size, wihi, color, matte)]
        images = []
        pbar = comfy.utils.ProgressBar(len(params))
        for idx, (shape, sides, angle, edge, size, wihi, color, matte) in enumerate(params):
            width, height = wihi
            sizeX, sizeY = size
            edge = EnumEdge[edge]
            shape = EnumShapes[shape]
            match shape:
                case EnumShapes.SQUARE:
                    img = shape_quad(width, height, sizeX, sizeX, fill=color, back=matte)
                    mask = shape_quad(width, height, sizeX, sizeX, fill=color[3])

                case EnumShapes.ELLIPSE:
                    img = shape_ellipse(width, height, sizeX, sizeY, fill=color, back=matte)
                    mask = shape_ellipse(width, height, sizeX, sizeY, fill=color[3])

                case EnumShapes.RECTANGLE:
                    img = shape_quad(width, height, sizeX, sizeY, fill=color, back=matte)
                    mask = shape_quad(width, height, sizeX, sizeY, fill=color[3])

                case EnumShapes.POLYGON:
                    img = shape_polygon(width, height, sizeX, sides, fill=color, back=matte)
                    mask = shape_polygon(width, height, sizeX, sides, fill=color[3])

                case EnumShapes.CIRCLE:
                    img = shape_ellipse(width, height, sizeX, sizeX, fill=color, back=matte)
                    mask = shape_ellipse(width, height, sizeX, sizeX, fill=color[3])

            img = pil2cv(img)
            mask = pil2cv(mask)
            mask = image_grayscale(mask)
            img = image_mask_add(img, mask)
            img = image_rotate(img, angle, edge=edge)
            matte = pixel_eval(matte, EnumImageType.BGRA)
            img = cv2tensor_full(img, matte)
            images.append(img)
            pbar.update_absolute(idx)
        return list(zip(*images))

class TextNode(JOVImageMultiple):
    NAME = "TEXT GENERATOR (JOV) 📝"
    CATEGORY = JOV_CATEGORY
    DESCRIPTION = "Use any system font with auto-fit or manual placement."
    FONT_NAMES = font_all_names()
    FONTS = font_all()

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.STRING: ("STRING", {"default": "", "multiline": True,
                                        "dynamicPrompts": False,
                                        "tooltip": "Your Message"}),
            Lexicon.FONT: (cls.FONT_NAMES, {"default": cls.FONT_NAMES[0]}),
            Lexicon.LETTER: ("BOOLEAN", {"default": False}),
            Lexicon.AUTOSIZE: ("BOOLEAN", {"default": False}),
            Lexicon.RGBA_A: ("VEC3", {"default": (255, 255, 255, 255), "step": 1,
                                      "label": [Lexicon.R, Lexicon.G, Lexicon.B, Lexicon.A],
                                      "rgb": True, "tooltip": "Color of the letters"}),
            Lexicon.MATTE: ("VEC3", {"default": (0, 0, 0), "step": 1,
                                     "label": [Lexicon.R, Lexicon.G, Lexicon.B], "rgb": True}),
            Lexicon.COLUMNS: ("INT", {"default": 0, "min": 0, "step": 1}),
            # if auto on, hide these...
            Lexicon.FONT_SIZE: ("INT", {"default": 16, "min": 1, "step": 1}),
            Lexicon.ALIGN: (EnumAlignment._member_names_, {"default": EnumAlignment.CENTER.name}),
            Lexicon.JUSTIFY: (EnumJustify._member_names_, {"default": EnumJustify.CENTER.name}),
            Lexicon.MARGIN: ("INT", {"default": 0, "min": -1024, "max": 1024}),
            Lexicon.SPACING: ("INT", {"default": 25, "min": -1024, "max": 1024}),
            Lexicon.WH: ("VEC2", {"default": (MIN_IMAGE_SIZE, MIN_IMAGE_SIZE),
                                  "step": 1, "label": [Lexicon.W, Lexicon.H]}),
            Lexicon.XY: ("VEC2", {"default": (0, 0,), "step": 0.01, "precision": 4,
                                  "round": 0.00001, "label": [Lexicon.X, Lexicon.Y]}),
            Lexicon.ANGLE: ("FLOAT", {"default": 0, "min": -180, "max": 180,
                                      "step": 0.01, "precision": 4, "round": 0.00001}),
            Lexicon.EDGE: (EnumEdge._member_names_, {"default": EnumEdge.CLIP.name}),
            Lexicon.INVERT: ("BOOLEAN", {"default": False, "tooltip": "Invert the mask input"})
        }}
        return Lexicon._parse(d, JOV_HELP_URL + "/CREATE#-text-generator")

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor]:
        if len(full_text := kw.get(Lexicon.STRING, [""])) == 0:
            full_text = [""]
        font_idx = kw.get(Lexicon.FONT, self.FONT_NAMES[0])
        autosize = kw.get(Lexicon.AUTOSIZE, [False])
        letter = kw.get(Lexicon.LETTER, [False])
        color = parse_tuple(Lexicon.RGBA_A, kw, default=(255, 255, 255, 255))
        matte = parse_tuple(Lexicon.MATTE, kw, default=(0, 0, 0), clip_min=0, clip_max=255)
        columns = kw.get(Lexicon.COLUMNS, [0])
        font_size = kw.get(Lexicon.FONT_SIZE, [16])
        align = kw.get(Lexicon.ALIGN, [EnumAlignment.CENTER])
        justify = kw.get(Lexicon.JUSTIFY, [EnumJustify.CENTER])
        margin = kw.get(Lexicon.MARGIN, [0])
        line_spacing = kw.get(Lexicon.SPACING, [25])
        wihi = parse_tuple(Lexicon.WH, kw, default=(MIN_IMAGE_SIZE, MIN_IMAGE_SIZE,))
        pos = parse_tuple(Lexicon.XY, kw, EnumTupleType.FLOAT, (0, 0), -1, 1)
        angle = parse_number(Lexicon.ANGLE, kw, EnumTupleType.FLOAT, [0])
        edge = kw.get(Lexicon.EDGE, [EnumEdge.CLIP])
        images = []
        params = [tuple(x) for x in zip_longest_fill(full_text, font_idx, autosize,
                                                     letter, color, matte, columns,
                                                     font_size, align, justify,
                                                     margin, line_spacing, wihi,
                                                     pos, angle, edge)]
        pbar = comfy.utils.ProgressBar(len(params))
        for idx, (full_text, font_idx, autosize, letter, color, matte, columns,
                  font_size, align, justify, margin, line_spacing, wihi, pos,
                  angle, edge) in enumerate(params):

            width, height = wihi
            font_name = self.FONTS[font_idx]
            align = EnumAlignment[align]
            justify = EnumJustify[justify]
            edge = EnumEdge[edge]
            matte = pixel_eval(matte)
            wm = width-margin * 2
            hm = height-margin * 2 - line_spacing
            if letter:
                full_text = full_text.replace('\n', '')
                if autosize:
                    w, h = text_autosize(full_text, font_name, wm, hm)[2:]
                    w /= len(full_text) * 1.25 # kerning?
                    font_size = (w + h) * 0.5
                font_size *= 10
                font = ImageFont.truetype(font_name, font_size)
                for ch in full_text:
                    img = text_draw(ch, font, width, height, align, justify, color=color)
                    images.append(img)

            else:
                if autosize:
                    full_text, font_size = text_autosize(full_text, font_name, wm, hm)[:2]
                font = ImageFont.truetype(font_name, font_size)
                img = text_draw(full_text, font, width, height, align, justify,
                                margin, line_spacing, color)
                images.append(img)

        out = []
        for i in images:
            img = image_rotate(i, angle, edge=edge)
            img = image_translate(img, pos, edge=edge)
            img = cv2tensor_full(img, matte)
            out.append(img)
            pbar.update_absolute(idx)
        return list(zip(*out))

class StereogramNode(JOVImageSimple):
    NAME = "STEREOGRAM (JOV) 📻"
    CATEGORY = JOV_CATEGORY
    DESCRIPTION = "Make a magic eye stereograms."
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        d = {
        "required": {},
        "optional": {
            Lexicon.PIXEL: (WILDCARD, {}),
            Lexicon.DEPTH: (WILDCARD, {}),
            Lexicon.TILE: ("INT", {"default": 8, "min": 1}),
            Lexicon.NOISE: ("FLOAT", {"default": 0.33, "min": 0, "max": 1, "step": 0.01}),
            Lexicon.GAMMA: ("FLOAT", {"default": 0.33, "min": 0, "max": 1, "step": 0.01}),
            Lexicon.SHIFT: ("FLOAT", {"default": 1., "min": -1, "max": 1, "step": 0.01}),
        }}
        return Lexicon._parse(d, JOV_HELP_URL + "/CREATE#-stereogram")

    def run(self, **kw) -> tuple[torch.Tensor, torch.Tensor]:
        pA = kw.get(Lexicon.PIXEL, None)
        pA = [None] if pA is None else batch_extract(pA)
        depth = kw.get(Lexicon.DEPTH, [None])
        divisions = kw.get(Lexicon.TILE, [8])
        noise = kw.get(Lexicon.NOISE, [0.33])
        gamma = kw.get(Lexicon.VALUE, [0.33])
        shift = kw.get(Lexicon.SHIFT, [1])
        params = [tuple(x) for x in zip_longest_fill(pA, depth, divisions, noise,
                                                     gamma, shift)]
        images = []
        pbar = comfy.utils.ProgressBar(len(params))
        for idx, (pA, depth, divisions, noise, gamma, shift) in enumerate(params):
            if pA is None:
                pA = channel_solid(MIN_IMAGE_SIZE, MIN_IMAGE_SIZE, chan=EnumImageType.BGRA)
            else:
                pA = tensor2cv(pA)

            depth = tensor2cv(depth)
            pA = image_stereogram(pA, depth, divisions, noise, gamma, shift)
            images.append(cv2tensor_full(pA))
            pbar.update_absolute(idx)
        return list(zip(*images))
