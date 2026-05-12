from pathlib import Path

from PIL import Image


class ImageService:
    def crop_region(self, page_image_path: Path, bbox: dict[str, int], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(page_image_path) as image:
            region = image.crop(
                (
                    bbox["x"],
                    bbox["y"],
                    bbox["x"] + bbox["width"],
                    bbox["y"] + bbox["height"],
                )
            )
            region.save(output_path)
        return output_path

    def compose_preview(
        self,
        page_image_path: Path,
        crop_after_path: Path,
        bbox: dict[str, int],
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(page_image_path).convert("RGB") as page_image:
            with Image.open(crop_after_path).convert("RGB") as crop_after:
                expected = (bbox["width"], bbox["height"])
                if crop_after.size != expected:
                    crop_after = crop_after.resize(expected, Image.Resampling.LANCZOS)
                page_image.paste(crop_after, (bbox["x"], bbox["y"]))
            page_image.save(output_path)
        return output_path

    def normalize_size(self, image_path: Path, target_size: tuple[int, int]) -> None:
        with Image.open(image_path).convert("RGB") as image:
            if image.size != target_size:
                image = image.resize(target_size, Image.Resampling.LANCZOS)
                image.save(image_path)


image_service = ImageService()
