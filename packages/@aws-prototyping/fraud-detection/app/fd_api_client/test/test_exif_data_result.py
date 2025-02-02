# coding: utf-8

"""
    Fraud Detection API

    An API for providing fraud detection capabilities.

    The version of the OpenAPI document: 0.0.1
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


import unittest

from fd_api_client.models.exif_data_result import ExifDataResult

class TestExifDataResult(unittest.TestCase):
    """ExifDataResult unit test stubs"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def make_instance(self, include_optional) -> ExifDataResult:
        """Test ExifDataResult
            include_optional is a boolean, when False only required
            params are included, when True both required and
            optional params are included """
        # uncomment below to create an instance of `ExifDataResult`
        """
        model = ExifDataResult()
        if include_optional:
            return ExifDataResult(
                latitude = 1.337,
                longitude = 1.337,
                timestamp = datetime.datetime.strptime('2013-10-20 19:20:30.00', '%Y-%m-%d %H:%M:%S.%f')
            )
        else:
            return ExifDataResult(
        )
        """

    def testExifDataResult(self):
        """Test ExifDataResult"""
        # inst_req_only = self.make_instance(include_optional=False)
        # inst_req_and_optional = self.make_instance(include_optional=True)

if __name__ == '__main__':
    unittest.main()
