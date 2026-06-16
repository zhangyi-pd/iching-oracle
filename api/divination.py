import os
import json
import random
import hashlib
import hmac
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEXAGRAM_DATA = None
data_path = os.path.join(os.path.dirname(__file__), "..", "iching_data.json")
if os.path.exists(data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        HEXAGRAM_DATA = json.load(f)["hexagrams"]

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
GUMROAD_SECRET = os.environ.get("GUMROAD_SECRET", "")

# TRIGRAM MAPPING: 3 coin tosses -> trigram
# heads=2, tails=3 (or heads=3, tails=2 depending on tradition)
# We use: heads=3 (yang), tails=2 (yin)
TRIGRAM_MAP = {
    (6, "old_yin"): 0,    # 3 tails (changing yin)
    (7, "young_yang"): 1,  # 2 tails 1 head (young yang)
    (8, "young_yin"): 2,  # 1 tail 2 heads (young yin)
    (9, "old_yang"): 3,   # 3 heads (changing yang)
}

# King Wen sequence trigram-to-hex lookup
# (lower_trigram, upper_trigram) -> hexagram_number
HEX_LOOKUP = {
    (7,7):1, (0,0):2, (4,7):3, (2,7):4, (2,0):5,   # 1-5
    (7,2):6, (0,2):7, (1,2):8, (7,6):9, (6,7):10,
    (6,0):11, (0,7):12, (5,7):13, (7,5):14, (1,0):15,
    (0,4):16, (4,6):17, (1,4):18, (6,0):19, (0,5):20,
    (4,5):21, (5,1):22, (1,0):23, (0,4):24, (7,4):25,
    (1,7):26, (4,1):27, (6,4):28, (2,2):29, (5,5):30,
    (6,1):31, (4,6):32, (7,1):33, (4,7):34, (0,5):35,
    (5,0):36, (5,4):37, (6,5):38, (1,2):39, (2,4):40,
    (6,1):41, (4,6):42, (6,7):43, (7,6):44, (6,0):45,
    (0,4):46, (6,2):47, (2,6):48, (5,6):49, (5,4):50,
    (4,4):51, (1,1):52, (1,4):53, (6,4):54, (5,4):55,
    (1,5):56, (4,3):57, (6,6):58, (2,3):59, (6,2):60,
    (6,4):61, (1,4):62, (2,5):63, (5,2):64
}

def coin_toss():
    """Simulate one coin toss: odd=True (heads/yang), even=False (tails/yin)"""
    return random.randint(0, 1) == 1

def cast_hexagram():
    """Cast 6 lines (from bottom to top), returns line values 6-9"""
    lines = []
    line_changes = []
    for i in range(6):
        tosses = [coin_toss() for _ in range(3)]
        heads = sum(tosses)
        if heads == 3:
            lines.append(9)   # old yang (changing)
            line_changes.append(True)
        elif heads == 2:
            lines.append(8)   # young yin
            line_changes.append(False)
        elif heads == 1:
            lines.append(7)   # young yang
            line_changes.append(False)
        else:
            lines.append(6)   # old yin (changing)
            line_changes.append(True)
    return lines, line_changes

def lines_to_trigram_value(lines):
    """Convert 3 lines to a trigram index (0-7)"""
    value = 0
    for i, line in enumerate(lines):
        if line % 2 == 1:  # yang line (7 or 9)
            value |= (1 << (2 - i))
    return value

def get_hexagram_number(lines):
    """Get hexagram number from 6 lines (bottom to top)"""
    lower = lines_to_trigram_value(lines[:3])
    upper = lines_to_trigram_value(lines[3:])
    return HEX_LOOKUP.get((lower, upper), 1)

def get_changing_lines_info(lines):
    """Get the positions and info of changing lines"""
    changes = []
    for i, val in enumerate(lines):
        if val == 6 or val == 9:
            change_to = "yin (open)" if val == 9 else "yang (solid)"
            changes.append({
                "position": i + 1,
                "from": "old yang" if val == 9 else "old yin",
                "changes_to": change_to
            })
    return changes

def hexagram_to_binary_lines(num):
    """Return 6 lines (top to bottom) for a hexagram number"""
    for (lower, upper), hnum in HEX_LOOKUP.items():
        if hnum == num:
            lines = []
            for i in range(3):
                lines.append(7 if (lower >> (2 - i)) & 1 else 8)
            for i in range(3):
                lines.append(7 if (upper >> (2 - i)) & 1 else 8)
            return lines
    return [7,7,7,7,7,7]

def build_yijing_lines_display(lines):
    """Build ASCII art of lines"""
    result = []
    for val in reversed(lines):
        if val % 2 == 1:  # yang
            result.append("═══════" if val == 7 else "x══════")
        else:
            result.append("╌╌╌╌╌╌╌" if val == 8 else "o╌╌╌╌╌╌")
    return result

@app.get("/")
async def root():
    return {"status": "I Ching Oracle API is running"}

@app.get("/api/cast")
async def api_cast(question: str = ""):
    """Cast hexagram and return free preview"""
    lines, line_changes = cast_hexagram()
    hex_num = get_hexagram_number(lines)
    changing_lines = get_changing_lines_info(lines)
    has_changes = any(c["position"] for c in changing_lines)
    
    hex_data = HEXAGRAM_DATA.get(str(hex_num), {})
    hex_name = hex_data.get("name", "Unknown")
    
    # Get resulting hexagram if there are changing lines
    result_hex = None
    if has_changes:
        result_lines = lines[:]
        for i in range(6):
            if lines[i] == 6:
                result_lines[i] = 7
            elif lines[i] == 9:
                result_lines[i] = 8
        result_num = get_hexagram_number(result_lines)
        result_hex = {
            "number": result_num,
            "name": HEXAGRAM_DATA.get(str(result_num), {}).get("name", "Unknown")
        }
    
    return {
        "hexagram_number": hex_num,
        "hexagram_name": hex_name,
        "hexagram_symbol": hex_data.get("symbol", ""),
        "judgment": hex_data.get("judgment", ""),
        "lines": lines,
        "line_display": build_yijing_lines_display(lines),
        "changing_lines": changing_lines,
        "resulting_hexagram": result_hex,
        "has_changes": has_changes,
        "preview": f"Your hexagram is **{hex_name}** (#{hex_num}). {hex_data.get('judgment', '')}",
        "requires_payment": True
    }

@app.post("/api/full-reading")
async def full_reading(request: Request):
    """Generate full AI reading after payment"""
    body = await request.json()
    question = body.get("question", "")
    hexagram_number = body.get("hexagram_number")
    lines = body.get("lines", [])
    changing_lines = body.get("changing_lines", [])
    result_hex = body.get("resulting_hexagram")
    
    if not DEEPSEEK_API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "AI API key not configured"}
        )
    
    hex_data = HEXAGRAM_DATA.get(str(hexagram_number), {})
    
    prompt = f"""You are an experienced I Ching (易经) divination master. Translate the wisdom of the ancient Chinese Book of Changes into practical, compassionate guidance for a modern English speaker.

User's question: "{question}"

Cast hexagram: {hex_data.get('name', 'Unknown')} (#{hexagram_number})
Hexagram symbol: {hex_data.get('symbol', '')}
Judgment: {hex_data.get('judgment', '')}

Line values (from bottom to top): {lines}
Changing lines: {changing_lines}
Resulting hexagram: {result_hex}

Please provide a reading in English with these sections:
1. **The Hexagram** — Name, symbol, and its essential meaning
2. **The Judgment** — What the hexagram text says about the situation
3. **The Changing Lines** — Analysis of each changing line and its meaning for the question
4. **The Transformation** — What the resulting hexagram reveals about the future direction
5. **Guidance** — 2-3 actionable pieces of advice

Keep the tone warm, wise, and practical. Write in natural, native-level English. Do not mention that you are an AI."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
            )
            result = resp.json()
            reading = result["choices"][0]["message"]["content"]
            return {"reading": reading}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"AI generation failed: {str(e)}"}
        )

@app.post("/api/verify-payment")
async def verify_payment(request: Request):
    """Verify Gumroad payment via webhook"""
    body = await request.json()
    license_key = body.get("license_key", "")
    
    if not license_key:
        raise HTTPException(status_code=400, detail="Missing license key")
    
    # Verify with Gumroad API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.gumroad.com/v2/licenses/verify",
                data={
                    "product_permalink": "iching-oracle",
                    "license_key": license_key
                }
            )
            result = resp.json()
            if result.get("success"):
                return {"verified": True, "sale": result.get("sale", {})}
            return {"verified": False}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Verification failed: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
