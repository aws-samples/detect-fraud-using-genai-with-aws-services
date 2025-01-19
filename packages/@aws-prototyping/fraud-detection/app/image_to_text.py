from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration


def image_to_text(raw_image: Image):
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

    # img_url = 'https://storage.googleapis.com/sfr-vision-language-research/BLIP/demo.jpg'
    # raw_image = Image.open(requests.get(img_url, stream=True).raw).convert('RGB')

    # conditional image captioning
    text = "a photography of"
    inputs = processor(raw_image, text, return_tensors="pt")

    out = model.generate(**inputs)
    print(processor.decode(out[0], skip_special_tokens=True))
    # >>> a photography of a woman and her dog

    # unconditional image captioning
    inputs = processor(raw_image, return_tensors="pt")

    out = model.generate(**inputs)
    image_text = processor.decode(out[0], skip_special_tokens=True)

    print(image_text)

    return image_text
