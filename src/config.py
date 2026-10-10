MODEL_ID = "wambugu71/crop_leaf_diseases_vit"   # A may swap after size/licence check
SUPPORTED_CROPS = ["rice", "wheat", "corn"]

USABLE_THRESHOLD = 0.80      # score >= this -> usable
UNCERTAIN_THRESHOLD = 0.50   # between USABLE and this -> uncertain; below -> rejected

MAX_UPLOAD_MB = 5
MIN_IMAGE_SIZE = (100, 100)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

DISCLAIMER = "Possible issue, not a confirmed diagnosis. Consult your local agriculture extension officer."
