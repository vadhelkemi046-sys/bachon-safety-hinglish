# Bachon ke liye Online Safety (Hinglish)

Parent ke daale hue suspicious message ko check karke batata hai ki wo
scam, grooming, bullying ya inappropriate jaisa lagta hai ya nahi.
Hinglish aur Indian languages ke liye.

Status: Week 1, data aur test set bana rahe hain.
## Baseline results (prompt v1)

Model: gemini-3.1-flash-lite

| Test set | Rows | Correct | Accuracy |
|---|---|---|---|
| test | 25 | 25 | 100% |
| test_hard | 40 | 40 | 100% |
| test_perturbed | 76 | 75 | 98.68% |
| test_fresh (Claude-labelled) | 50 | 49 | 98.00% |

- False-positive rate: 0.00%, Danger recall: 100% (test_perturbed par).
- Ek galti: h030_p2 (grooming ko scam bola), typo wale SMS-style text par.
- Dhyan rakhein: test_perturbed, test_hard se bana hai, isliye ye sirf typing ki robustness check karta hai. Naye messages par generalization ka test abhi baaki hai.
## Demo

![Demo](image.png)

Parent koi suspicious message paste karta hai, aur app label, risk, ek line ka kaaran aur agle kadam batati hai. Ye AI ka andaza hai, galat bhi ho sakta hai.

Chalane ke liye: `streamlit run app.py`