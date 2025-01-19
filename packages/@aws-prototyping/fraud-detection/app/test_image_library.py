import os
import sys
import unittest
from PIL import Image
from image_library import S3ImageLibrary
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class TestS3ImageLibrary(unittest.TestCase):

    def setUp(self):
        self.library = S3ImageLibrary()

    def test_add_image(self):
        # Create a test image
        image = Image.new('RGB', (500, 500), color='red')
        filename = 'test_image.png'

        # Add the image to the library
        added_image = self.library.add_image(image, filename)

        # Check if the image was added successfully
        self.assertIsNotNone(added_image.id)
        self.assertEqual(added_image.filename, filename)
        # self.assertEqual(added_image.size, image.size[0] * image.size[1] * 3)

        # Check if the image can be retrieved from the library
        retrieved_image = self.library.get_image(added_image.id)
        self.assertEqual(retrieved_image.id, added_image.id)
        self.assertEqual(retrieved_image.filename, added_image.filename)
        self.assertEqual(retrieved_image.size, added_image.size)

        # Clean up: delete the added image
        self.library.delete_image(added_image.id)
        deleted_image = self.library.get_image(added_image.id)
        self.assertIsNone(deleted_image)

    def test_search_images(self):
        # Create a test query image
        query_image = Image.new('RGB', (500, 500), color='blue')

        # Add the query image to the library
        added_query_image = self.library.add_image(
            query_image, 'query_image.png')

        # Search for similar images
        similar_images = self.library.search_images(query_image)
        print(similar_images)
        # Check if the query image is in the list of similar images
        self.assertIn(added_query_image.id, [
                      x.image.id for x in similar_images])

        # Clean up: delete the query image
        self.library.delete_image(added_query_image.id)
        deleted_query_image = self.library.get_image(added_query_image.id)
        self.assertIsNone(deleted_query_image)


if __name__ == '__main__':
    unittest.main()
