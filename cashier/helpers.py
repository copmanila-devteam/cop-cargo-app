import hashlib





def get_image_hash(image_file):

    sha256 = hashlib.sha256()

    for chunk in image_file.chunks():

        sha256.update(chunk)

    return sha256.hexdigest()

