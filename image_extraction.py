# pip install -q langchain langchain-openai pillow python-dotenv

import os, json, glob, base64
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
 
# --- Setup ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
# Vision model
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0,api_key= OPENAI_API_KEY ).bind(
    # Force valid JSON output (OpenAI "JSON mode")
    response_format={"type": "json_object"}
)

# --- Minimal helpers ---
def image_to_data_url(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

INSTRUCTIONS = (
    "You are an expert at visually parsing documents (invoices, receipts, forms, IDs, etc.). "
    "Look at the image and return a SINGLE JSON object that captures the content you see. "
    "Infer keys from the document itself (e.g., 'invoice_number', 'date', 'seller', 'buyer', "
    "'items', 'totals', 'tax', 'address', etc.)—only if they appear. "
    "If there are tables, represent them as arrays of row objects. "
    "If you see line items, include them as an array with fields derived from the column headers. "
    "Prefer numbers for numeric values. Use ISO date strings if clear. "
    "Do NOT add commentary. Do NOT wrap in markdown—return only JSON."
    "- If a field is missing, simply omit it (do not invent data)."
    "- Include important fields you can infer from text (seller, address, contact, invoice_no/date/due, line_items_summary, amounts, instructions).\n"
    "- Deduplicate and correct minor OCR spacing like 'HonkKong' -> 'Hong Kong', 'DueDate:' -> 'due date'."
    "- If bill is for travel get from and too locations." 
    "- If bill is for hotel get hotel name, location, check in check out and from and till."
    "- Tag currancy if possible (e.g., USD, EUR, GBP, INR)."
)


def extract_json_from_image(image_path: str, emp_id) -> dict:
    msg = HumanMessage(
        content=[
            {"type": "text", "text": INSTRUCTIONS},
            {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}},
        ]
    )
    resp = llm.invoke([msg])
    text = resp.content if isinstance(resp.content, str) else json.dumps(resp.content)
    j_res = json.loads(text)
    j_res["Employee ID"] = emp_id
    try:
        return j_res
    except Exception:
        # Fallback: try to salvage JSON between first { and last }
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:

            return json.loads(text[start:end+1])
        raise ValueError(f"Model did not return valid JSON:\n{text}")


def save_json(data, out_dir,image_name):
    out_dir = Path(out_dir)
    out_path = out_dir / (Path(image_name).stem + ".json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ {Path(out_path).name} -> {out_path}")


