import streamlit as st
from pymongo import MongoClient

client = MongoClient(st.secrets["MONGO_URI"])
client.admin.command("ping")

db = client["food_delivery_analytics"]
st.success("MongoDB connected successfully!")