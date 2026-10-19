import json
import os
import re

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompt import LABELS, build_system as make_prompt, load_train

load_dotenv()

MODEL = os.getenv("MODEL", "gemini-3.1-flash-lite")

INFO = {
    "scam": ("🚩", "Scam jaisa lagta hai", [
        "Link na kholein aur OTP, password ya card details kisi ko na dein.",
        "Bachche ko samjhayein ki free inaam ya paisa maangne wale messages dhokha hote hain.",
        "Paisa chala gaya ho to cybercrime.gov.in par ya 1930 par report karein.",
    ]),
    "grooming": ("🚨", "Grooming jaisa lagta hai (gambhir)", [
        "Bachche ko daantein nahi. Shaanti se poochhein ki ye kaun hai aur kab se baat ho rahi hai.",
        "Chat ke screenshot save kar lein, phir us account ko block aur report karein.",
        "Madad ke liye Childline 1098 ya cybercrime.gov.in par sampark karein.",
    ]),
    "bullying": ("⚠️", "Bullying jaisa lagta hai", [
        "Bachche se pyaar se baat karein, use batayein ki isme uski galti nahi hai.",
        "Screenshot save karein aur zaroorat ho to school ko batayein.",
        "Bhejne wale ko block karein aur platform par report karein.",
    ]),
    "inappropriate": ("⚠️", "Bachche ke liye unfit content", [
        "Bachche se baat karein ki wo ye kahan se aaya aur kaisa laga.",
        "Parental controls aur group settings dekhein.",
    ]),
    "safe": ("✅", "Safe lagta hai", [
        "Is message mein khatre ka koi saaf nishaan nahi dikha.",
    ]),
}


@st.cache_resource
def get_client():
    return genai.Client()


@st.cache_data
def build_system():
    return make_prompt(load_train())


def classify(text):
    config = types.GenerateContentConfig(
        system_instruction=build_system(),
        temperature=0,
        max_output_tokens=300,
        response_mime_type="application/json",
    )
    try:
        resp = get_client().models.generate_content(
            model=MODEL,
            contents=f"<message>{text}</message>",
            config=config,
        )
        match = re.search(r"\{.*\}", resp.text or "", re.DOTALL)
        out = json.loads(match.group(0))
        if out.get("label") not in LABELS:
            return None
        return out
    except Exception as e:
        print("ERROR:", repr(e))
        return None


st.set_page_config(page_title="Bachon ki Online Safety", page_icon="🛡️")
st.title("🛡️ Bachon ki Online Safety")
st.caption("Suspicious message paste karein, AI batayega ki wo scam, grooming, "
           "bullying ya gandi baat jaisa lagta hai ya nahi.")

with st.sidebar:
    st.subheader("Dhyan dein")
    st.write("Ye abhi ek demo hai. Yahan kisi bachche ki asli chat na daalein, "
             "sirf sample messages try karein.")
    st.write("Ye app message ko save nahi karta, par jaanch ke liye use "
             "Google Gemini AI service ko bheja jaata hai.")

text = st.text_area("Message ya chat ka hissa yahan paste karein",
                    height=150, max_chars=1500)

if st.button("Check karein", type="primary"):
    if not text.strip():
        st.warning("Pehle koi message paste karein.")
    else:
        with st.spinner("Check ho raha hai..."):
            out = classify(text.strip())
        if out is None:
            st.error("Abhi jawab nahi mil paya. Thodi der baad dobara try karein.")
        else:
            label = out["label"]
            emoji, title, steps = INFO[label]
            box = st.success if label == "safe" else (
                st.error if out.get("risk") == "high" else st.warning)
            box(f"{emoji} {title}  |  Risk: {out.get('risk', '-')}")
            st.write(f"**Kyun:** {out.get('reason', '')}")
            st.markdown("**Aap kya kar sakte hain:**")
            for s in steps:
                st.markdown(f"- {s}")
            st.info("Ye AI ka andaza hai, galat bhi ho sakta hai. "
                    "Kripya khud confirm karein.")