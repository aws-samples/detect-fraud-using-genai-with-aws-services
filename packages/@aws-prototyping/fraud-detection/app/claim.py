import datetime

import streamlit as st

from dynamo import DynamoDBHandler

CLAIMS_TABLE_NAME = "Claims"


class Claim:

    def __init__(self, claim_number='', date_time=datetime.datetime.now(), latitude=0, longitude=0, fraud_score=0):
        self.claim_number = claim_number
        self.date_time = date_time
        self.latitude = latitude
        self.longitude = longitude
        self.fraud_score = fraud_score

    def __str__(self):
        return f"Claim Number: {self.claim_number}, Date/Time: {self.date_time}, Location: ({self.latitude}, {self.longitude})"

    def save(self):
        ddb_handler = DynamoDBHandler(CLAIMS_TABLE_NAME)
        ddb_handler.save_item(self)


def render_claim_table():
    ddb_handler = DynamoDBHandler(CLAIMS_TABLE_NAME)
    claims = ddb_handler.list_items()
    st.table(claims)
