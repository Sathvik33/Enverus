import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


_model = None
_processor = None
_device = None


def _load_model():
    global _model
    global _processor
    global _device

    if _model is None:

        settings = get_settings()

        _device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        logger.info(
            "loading_image_embedding_model",
            model=settings.IMAGE_EMBEDDING_MODEL,
            device=_device,
        )

        _processor = AutoProcessor.from_pretrained(
            settings.IMAGE_EMBEDDING_MODEL
        )

        _model = AutoModel.from_pretrained(
            settings.IMAGE_EMBEDDING_MODEL
        )

        _model = _model.to(_device)
        _model.eval()

    return (
        _model,
        _processor,
        _device,
    )


def _normalize(
    embeddings: torch.Tensor,
) -> torch.Tensor:

    return embeddings / embeddings.norm(
        p=2,
        dim=-1,
        keepdim=True,
    ).clamp_min(1e-12)


def embed_image(
    image_path: str,
) -> list[float]:

    model, processor, device = _load_model()

    image = Image.open(
        image_path
    ).convert("RGB")

    inputs = processor(
        images=image,
        return_tensors="pt",
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.inference_mode():

        if hasattr(model, "get_image_features"):
            features = model.get_image_features(
                **inputs
            )

        else:
            outputs = model.vision_model(
                pixel_values=inputs["pixel_values"]
            )

            features = outputs.pooler_output

    features = _normalize(features)

    return (
        features
        .detach()
        .cpu()
        .squeeze(0)
        .tolist()
    )


def embed_text_for_image_search(
    text: str,
) -> list[float]:

    if not text or not text.strip():
        return []

    model, processor, device = _load_model()

    inputs = processor(
        text=[text],
        return_tensors="pt",
        padding=True,
        truncation=True,
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.inference_mode():

        if hasattr(model, "get_text_features"):
            features = model.get_text_features(
                **inputs
            )

        else:
            outputs = model.text_model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs.get(
                    "attention_mask"
                ),
            )

            features = outputs.pooler_output

    features = _normalize(features)

    return (
        features
        .detach()
        .cpu()
        .squeeze(0)
        .tolist()
    )