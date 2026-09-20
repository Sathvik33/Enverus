import hashlib
from pathlib import Path

from app.schemas.document import ImageChunkSchema, ParsedElement, ElementType
from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


def _image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def _bbox_center_y(bbox: list[float]) -> float | None:
    if len(bbox) != 4:
        return None

    return (bbox[1] + bbox[3]) / 2.0


def _find_best_caption(
    image_bbox: list[float],
    captions: list[ParsedElement],
) -> str:
    """
    Find the closest caption to an image.

    Prefer captions physically below the image. If none exist,
    fall back to the nearest caption by vertical distance.
    """

    if not captions:
        return ""

    image_y = _bbox_center_y(image_bbox)

    if image_y is None:
        return captions[0].content

    candidates = []

    for caption in captions:
        caption_bbox = caption.metadata.get("bbox", [])
        caption_y = _bbox_center_y(caption_bbox)

        if caption_y is None:
            continue

        distance = caption_y - image_y

        # Prefer captions below the image.
        if distance >= 0:
            candidates.append((distance, caption.content))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    # No caption below the image.
    fallback = []

    for caption in captions:
        caption_bbox = caption.metadata.get("bbox", [])
        caption_y = _bbox_center_y(caption_bbox)

        if caption_y is not None:
            fallback.append(
                (
                    abs(caption_y - image_y),
                    caption.content,
                )
            )

    if fallback:
        fallback.sort(key=lambda x: x[0])
        return fallback[0][1]

    return captions[0].content


def _build_text_representation(
    caption: str,
    section: str,
    page: int,
) -> str:

    parts = []

    if caption:
        parts.append(caption)

    if section:
        parts.append(f"Section: {section}")

    parts.append(f"Page {page}")

    return ". ".join(parts)


def extract_and_save_images(
    document_id: str,
    parsed_data: dict,
    elements: list[ParsedElement],
) -> list[ImageChunkSchema]:

    settings = get_settings()

    image_dir = (
        Path(settings.IMAGE_DIR)
        / document_id
    )

    image_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    captions_by_page: dict[int, list[ParsedElement]] = {}

    for element in elements:
        if element.element_type == ElementType.CAPTION:
            captions_by_page.setdefault(
                element.page_number,
                [],
            ).append(element)

    section_by_page: dict[int, str] = {}

    for element in elements:
        if element.section:
            section_by_page[element.page_number] = (
                element.section
            )

    image_chunks = []

    images_by_page = parsed_data.get(
        "images_by_page",
        {},
    )

    seen_hashes: set[str] = set()

    for page_num, images in images_by_page.items():

        page_captions = captions_by_page.get(
            page_num,
            [],
        )

        section = section_by_page.get(
            page_num,
            "",
        )

        for idx, img_data in enumerate(images):

            width = img_data.get("width", 0)
            height = img_data.get("height", 0)

            # Ignore tiny decorative images.
            if width < 50 or height < 50:
                continue

            image_bytes = img_data.get(
                "image_bytes",
                b"",
            )

            if not image_bytes:
                continue

            digest = _image_hash(image_bytes)

            if digest in seen_hashes:
                continue

            seen_hashes.add(digest)

            ext = img_data.get(
                "ext",
                "png",
            )

            filename = (
                f"page{page_num}_img{idx}_{digest[:12]}.{ext}"
            )

            filepath = image_dir / filename

            try:
                with open(filepath, "wb") as file:
                    file.write(image_bytes)
            except OSError as exc:
                logger.warning(
                    "image_save_failed",
                    path=str(filepath),
                    error=str(exc),
                )
                continue

            caption = _find_best_caption(
                img_data.get("bbox", []),
                page_captions,
            )

            text_representation = _build_text_representation(
                caption=caption,
                section=section,
                page=page_num,
            )

            image_chunks.append(
                ImageChunkSchema(
                    document_id=document_id,
                    page_number=page_num,
                    section=section,
                    caption=caption,
                    image_path=str(filepath),
                    image_width=width,
                    image_height=height,
                    metadata={
                        "bbox": img_data.get(
                            "bbox",
                            [],
                        ),
                        "text_representation": (
                            text_representation
                        ),
                        "image_hash": digest,
                        "xref": img_data.get("xref"),
                    },
                )
            )

    logger.info(
        "images_extracted",
        count=len(image_chunks),
        document_id=document_id,
    )

    return image_chunks