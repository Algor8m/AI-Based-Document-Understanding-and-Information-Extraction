from io import BytesIO
import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def png_bytes():
    image = Image.new("RGB", (240, 90), "white")
    ImageDraw.Draw(image).text((12, 20), "Attendance: 85%", fill="black")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@pytest.fixture
def jpeg_bytes():
    image = Image.new("RGB", (180, 80), "white")
    ImageDraw.Draw(image).text((10, 15), "Marks: 90", fill="black")
    output = BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()
