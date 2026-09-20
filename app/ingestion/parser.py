import pymupdf
import pymupdf4llm
from pathlib import Path
from app.core.logging import get_logger

logger = get_logger(__name__)


def parse_pdf(pdf_path: str) -> dict:
    """Parse PDF into structured page chunks with layout awareness."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info("parsing_pdf", path=str(path))

    doc = pymupdf.open(str(path))
    page_count = len(doc)

    page_chunks = pymupdf4llm.to_markdown(str(path), page_chunks=True, write_images=False)

    images_by_page = {}
    for page_num in range(page_count):
        page = doc[page_num]
        images_by_page[page_num + 1] = []

        for img_index, img_info in enumerate(page.get_images(full=True)):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if base_image and base_image.get("image"):
                    img_data = {
                        "xref": xref,
                        "image_bytes": base_image["image"],
                        "ext": base_image.get("ext", "png"),
                        "width": base_image.get("width", 0),
                        "height": base_image.get("height", 0),
                    }

                    rects = page.get_image_rects(xref)
                    if rects:
                        rect = rects[0]
                        img_data["bbox"] = [rect.x0, rect.y0, rect.x1, rect.y1]
                    else:
                        img_data["bbox"] = []

                    images_by_page[page_num + 1].append(img_data)
            except Exception as e:
                logger.warning("image_extraction_failed", page=page_num + 1, xref=xref, error=str(e))

    doc.close()

    logger.info("pdf_parsed", pages=page_count, chunks=len(page_chunks))

    return {
        "page_count": page_count,
        "page_chunks": page_chunks,
        "images_by_page": images_by_page,
    }
