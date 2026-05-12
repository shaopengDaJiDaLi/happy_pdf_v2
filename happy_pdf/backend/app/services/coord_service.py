from app.schemas.api import BBox, Size


class CoordService:
    def map_display_to_image(
        self,
        display_bbox: BBox,
        display_size: Size,
        image_width: int,
        image_height: int,
    ) -> dict[str, int]:
        if display_size.width <= 0 or display_size.height <= 0:
            raise ValueError("display_size must be positive")

        scale_x = image_width / display_size.width
        scale_y = image_height / display_size.height

        x1 = round(display_bbox.x * scale_x)
        y1 = round(display_bbox.y * scale_y)
        x2 = round((display_bbox.x + display_bbox.width) * scale_x)
        y2 = round((display_bbox.y + display_bbox.height) * scale_y)

        x1 = max(0, min(image_width - 1, x1))
        y1 = max(0, min(image_height - 1, y1))
        x2 = max(x1 + 1, min(image_width, x2))
        y2 = max(y1 + 1, min(image_height, y2))

        width = x2 - x1
        height = y2 - y1
        if width < 4 or height < 4:
            raise ValueError("selected region is too small")

        return {"x": x1, "y": y1, "width": width, "height": height}


coord_service = CoordService()
