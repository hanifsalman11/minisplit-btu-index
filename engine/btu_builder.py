import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/minisplit-btu-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2").strip()
CUSTOM_SYSTEM = os.environ.get("CUSTOM_SYSTEM", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_systems.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (System/Room Name, Nominal BTU, SEER2 Rating, Voltage, Max Breaker Amps, Ideal Sq Ft, Category)
SEED_SYSTEMS = [
    ("MRCOOL DIY 4th Gen 12000 BTU 22 SEER2", 12000, 22.0, 115, 20, 500, "Single-Zone DIY Heat Pump"),
    ("MRCOOL DIY 4th Gen 18000 BTU 20.5 SEER2", 18000, 20.5, 230, 20, 750, "Single-Zone DIY Heat Pump"),
    ("MRCOOL DIY 4th Gen 24000 BTU 20.5 SEER2", 24000, 20.5, 230, 25, 1000, "Large Garage & Workshop"),
    ("MRCOOL DIY 4th Gen 36000 BTU Multi-Zone", 36000, 21.5, 230, 35, 1500, "Whole-Home Multi-Zone"),
    ("Senville LETO 12000 BTU Alexa Mini Split", 12000, 20.0, 115, 20, 500, "Budget Smart Heat Pump"),
    ("Senville AURA 18000 BTU Extreme Cold -22F", 18000, 22.0, 230, 20, 750, "Arctic Cold-Climate Hyper Heat"),
    ("Senville AURA 24000 BTU Arctic Heat Pump", 24000, 21.0, 230, 25, 1000, "Cold-Climate Garage & Basement"),
    ("Pioneer Diamante Ultra 12000 BTU 20 SEER2", 12000, 20.0, 115, 20, 500, "Bedroom & Home Office"),
    ("Pioneer Diamante Pro 18000 BTU 230V", 18000, 20.5, 230, 20, 750, "Living Room & Studio"),
    ("Pioneer Hyperformance 24000 BTU 21.5 SEER2", 24000, 21.5, 230, 25, 1000, "Commercial & Workshop"),
    ("Cooper & Hunter Sophia 12000 BTU 22.5 SEER2", 12000, 22.5, 230, 15, 500, "High-Efficiency Inverter"),
    ("Cooper & Hunter Hyper Heat 18000 BTU -22F", 18000, 21.5, 230, 20, 750, "Sub-Zero Heating & Cooling"),
    ("Della Optima 12000 BTU WiFi Inverter", 12000, 20.0, 115, 20, 500, "Plug-and-Play Smart HVAC"),
    ("Della Vario 18000 BTU 19 SEER2 230V", 18000, 19.0, 230, 20, 750, "Mid-Size Room & Garage"),
    ("TOSOT Muse 12000 BTU 22 SEER2 Gree Inverter", 12000, 22.0, 230, 15, 500, "Ultra-Quiet Bedroom HVAC"),
    ("TOSOT Apex 24000 BTU Ultra-Heat -22F", 24000, 20.5, 230, 25, 1000, "Northern Climate Heat Pump"),
    ("Mitsubishi M-Series MUZ-FS12NA 12000 BTU", 12000, 23.1, 230, 15, 550, "Flagship Hyper-Heating INVERTER"),
    ("Mitsubishi MXZ-3C24NAHZ4 24000 BTU 3-Zone", 24000, 20.0, 230, 30, 1100, "Multi-Zone Hyper-Heat"),
    ("Daikin ENTRA 12000 BTU 18 SEER2 Wall Mount", 12000, 18.0, 230, 15, 500, "Reliable Single-Zone Inverter"),
    ("Daikin AURORA 18000 BTU Cold Climate", 18000, 20.0, 230, 20, 750, "Low-Ambient Heating"),
    ("Fujitsu Halcyon 12LZAS1 12000 BTU 29.4 SEER2", 12000, 29.4, 230, 15, 550, "Ultra-High SEER2 Flagship"),
    ("LG Art Cool Mirror 12000 BTU Dual Inverter", 12000, 22.0, 230, 15, 500, "Designer Living Room HVAC"),
    ("Gree Sapphire 12000 BTU 28 SEER2 Extreme", 12000, 28.0, 230, 15, 550, "Sub-Zero Flagship Heat Pump"),
    ("Costway 9000 BTU 19 SEER2 115V Mini Split", 9000, 19.0, 115, 15, 350, "Small Bedroom & Office"),
    ("ROVUS / RovSun 18000 BTU 230V Split AC", 18000, 19.0, 230, 20, 750, "Budget Garage & ADU"),
    ("EG4 Hybrid Solar 12000 BTU AC/DC Mini Split", 12000, 22.0, 115, 20, 500, "Off-Grid Solar Direct HVAC"),
    ("EG4 Hybrid Solar 24000 BTU Off-Grid Heat Pump", 24000, 21.0, 230, 25, 1000, "Solar Cabin & Homestead"),
    ("Two-Car Garage Workshop (600 Sq Ft)", 18000, 20.5, 230, 20, 600, "Garage & Man-Cave Sizing"),
    ("Three-Car Insulated Shop (950 Sq Ft)", 24000, 20.5, 230, 25, 950, "Large Shop HVAC Sizing"),
    ("Four-Season Sunroom & Enclosed Patio (400 Sq Ft)", 15000, 21.0, 230, 20, 400, "High Solar-Gain Glass Room")
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=12000.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_hvac_queries():
    """Mengambil kueri model Mini-Split & ukuran BTU ruangan dari Google Autocomplete US."""
    discovered = []
    seeds = [
        "mrcool diy ",
        "senville mini split ",
        "pioneer mini split ",
        "what size mini split for "
    ]
    for seed in seeds:
        try:
            q = f"{seed}btu" if "what size" not in seed else seed
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(q)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|cost|manual|specs|review|reddit)\b",
                        "",
                        suggestion,
                        flags=re.IGNORECASE
                    ).strip()
                    if 5 <= len(cleaned) <= 44:
                        btu_match = re.search(r"(9000|12000|18000|24000|36000|9k|12k|18k|24k|36k)", cleaned, flags=re.IGNORECASE)
                        btu_val = 18000
                        if btu_match:
                            raw_b = btu_match.group(1).lower().replace("k", "000")
                            btu_val = int(raw_b)
                        sqft_val = int(round(btu_val / 25.0))
                        volt_val = 115 if btu_val <= 12000 else 230
                        brk_val = 20 if btu_val <= 18000 else 25
                        discovered.append((cleaned.title(), btu_val, 20.5, volt_val, brk_val, sqft_val, "Ductless Mini-Split Sizing"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_hvac_data(sys_tuple):
    """Mesin Fisika Termal ACCA Manual-J & SEER2 Kelistrikan (100% bebas gagal)."""
    sys_name, btu, seer2, volts, breaker_a, ideal_sqft, category = sys_tuple

    tons = round(btu / 12000.0, 1)
    running_watts = int(round(btu / seer2))
    # Estimasi pemakaian rata-rata 8 jam/hari x 30 hari x faktor modulasi inverter 65%
    monthly_kwh = int(round((running_watts * 8 * 30 * 0.65) / 1000.0))
    monthly_cost_usd = round(monthly_kwh * 0.16, 2)

    if breaker_a <= 15:
        wire_awg = "14/2 or 12/2 AWG Copper NM-B / THHN"
    elif breaker_a <= 20:
        wire_awg = "12/2 AWG Copper THHN in Liquidtight Whip"
    elif breaker_a <= 25:
        wire_awg = "10/2 AWG Copper THHN in Liquidtight Whip"
    else:
        wire_awg = "8/2 AWG Copper THHN in 3/4-Inch Conduit"

    return {
        "system_name": sys_name,
        "category": category,
        "seo_title": f"{sys_name} BTU Sizing, SEER2 Power Cost & Breaker Calculator (2026)",
        "meta_description": f"Calculate room coverage ({ideal_sqft} sq ft), monthly SEER2 electricity cost (${monthly_cost_usd}/mo), running watts ({running_watts}W), and NEC breaker size ({breaker_a}A {volts}V) for the {sys_name}.",
        "specs": {
            "nominal_btu": btu,
            "tonnage": tons,
            "seer2_rating": seer2,
            "voltage": volts,
            "max_breaker_amps": breaker_a,
            "recommended_wire_awg": wire_awg,
            "ideal_sqft": ideal_sqft,
            "avg_running_watts": running_watts
        },
        "engineering_verdict": f"Rated at {btu:,} BTU/hr ({tons} Tons) with a {seer2} SEER2 variable-speed DC inverter compressor, the {sys_name} is engineered for spaces around {ideal_sqft} sq ft (with standard 8 ft ceilings). It draws approximately {running_watts}W during active cooling/heating (~${monthly_cost_usd}/month at $0.16/kWh) and requires a dedicated {volts}V {breaker_a}-Amp circuit wired with {wire_awg}.",
        "hardware_bundle": [
            {
                "badge": f"{tons}-Ton Heat Pump Kit",
                "title": f"{sys_name} Ductless Mini-Split Inverter System",
                "price_range": "$699 - $2,299",
                "amazon_query": f"{sys_name} Mini Split Heat Pump",
                "hvac_note": f"Delivers {btu:,} BTU/hr cooling and heating at {seer2} SEER2 efficiency for rooms up to {ideal_sqft} sq ft."
            },
            {
                "badge": "NEC Disconnect & Whip",
                "title": f"60A 240V Non-Fused AC Disconnect Box + 1/2\" Liquidtight Whip & HVAC Surge Suppressor",
                "price_range": "$59 - $129",
                "amazon_query": "Mini Split Disconnect Box Electrical Whip Kit HVAC Surge Protector",
                "hvac_note": "NEC Article 440 requires a visible, lockable disconnect switch within sight of the outdoor condenser unit, plus Type 1/2 surge protection for the inverter board."
            },
            {
                "badge": "Mounting & Line-Set Shield",
                "title": "Heavy-Duty 450-Lb Condenser Wall Bracket / Pad + 3\" PVC Line-Set Cover Kit",
                "price_range": "$54 - $109",
                "amazon_query": "Mini Split Wall Mounting Bracket 3 Inch Line Set Cover Kit",
                "hvac_note": "Elevates the outdoor heat pump above winter snowdrifts and protects copper refrigerant insulation from UV degradation."
            },
            {
                "badge": "Vacuum & Flare Tool Kit",
                "title": "4.5 CFM Single-Stage HVAC Rotary Vacuum Pump, R410A/R454B Gauges & Eccentric Flaring Tool",
                "price_range": "$99 - $199",
                "amazon_query": "HVAC Vacuum Pump Manifold Gauge Set R410A Mini Split Adapter",
                "hvac_note": "Essential for pulling non-precharged copper line sets down below 500 microns and performing nitrogen/vacuum decay leak checks."
            }
        ],
        "installation_checklist": [
            f"Size your dedicated circuit breaker to the unit's MOP (Maximum Overcurrent Protection) nameplate rating: {breaker_a}A at {volts}V using {wire_awg}.",
            "Install an inline HVAC Surge Protector (such as ICM517 or AG3000) directly at the outdoor disconnect box; variable-speed inverter PCBs are highly sensitive to grid voltage spikes.",
            "Maintain at least 12 to 20 inches of unobstructed airflow clearance behind the outdoor condenser coil and elevate the base above local snow accumulation levels.",
            "Torque brass flare nuts using a calibrated digital flare torque wrench (e.g., 1/4\" line at 14–18 ft-lbs, 3/8\" line at 25–30 ft-lbs, 1/2\" line at 36–45 ft-lbs) with Nylog Blue thread sealant."
        ],
        "faqs": [
            {
                "q": f"How many square feet will the {sys_name} cool and heat?",
                "a": f"With {btu:,} BTU/hr ({tons} Tons) of capacity, it comfortably conditions {ideal_sqft} sq ft in well-insulated rooms with 8-foot ceilings, or around {int(round(ideal_sqft * 0.78))} sq ft in sunrooms, uninsulated garages, or rooms with 10–12 ft vaulted ceilings."
            },
            {
                "q": f"How much electricity does the {sys_name} use per month?",
                "a": f"At {seer2} SEER2, average continuous draw is ~{running_watts} watts ({round(running_watts / volts, 1)} Amps at {volts}V). Running 8 hours a day with inverter modulation consumes roughly {monthly_kwh} kWh per month, costing about ${monthly_cost_usd}/month at the $0.16/kWh US average rate."
            },
            {
                "q": f"What size breaker and wire do I need for the {sys_name}?",
                "a": f"Install a dedicated {breaker_a}-Amp {volts}V circuit breaker feeding an outdoor non-fused 60A disconnect box using {wire_awg} copper conductors."
            }
        ]
    }


def generate_hvac_data(sys_tuple):
    """Memanggil Gemini 2.5 Flash API; jika gagal otomatis memakai Deterministic Manual-J Engine."""
    if not GEMINI_API_KEY:
        return build_deterministic_hvac_data(sys_tuple)

    sys_name, btu, seer2, volts, breaker_a, ideal_sqft, category = sys_tuple
    tons = round(btu / 12000.0, 1)
    running_watts = int(round(btu / seer2))

    prompt = f"""
You are a Senior Licensed HVAC Mechanical Engineer (ACCA Manual-J & NEC Article 440 Specialist). Create an accurate 2026 room BTU sizing, SEER2 power consumption, and electrical breaker guide for: "{sys_name}".
Baseline reference specs: Nominal Capacity={btu} BTU/hr ({tons} Tons), Efficiency={seer2} SEER2, Voltage={volts}V, Breaker={breaker_a}A, Ideal Area={ideal_sqft} sq ft, Running Watts={running_watts}W.
Return ONLY a valid JSON object matching this exact schema:
{{
  "system_name": "{sys_name}",
  "category": "{category}",
  "seo_title": "{sys_name} BTU Sizing, SEER2 Power Cost & Breaker Calculator (2026)",
  "meta_description": "Calculate exact room square footage coverage, monthly SEER2 electricity bill, running watts, and NEC breaker size for the {sys_name}.",
  "specs": {{
    "nominal_btu": {btu},
    "tonnage": {tons},
    "seer2_rating": {seer2},
    "voltage": {volts},
    "max_breaker_amps": {breaker_a},
    "recommended_wire_awg": "12/2 AWG Copper THHN",
    "ideal_sqft": {ideal_sqft},
    "avg_running_watts": {running_watts}
  }},
  "engineering_verdict": "3-sentence technical summary stating BTU/tonnage, SEER2 rating, square footage coverage, running watts, and required voltage/breaker.",
  "hardware_bundle": [
    {{
      "badge": "Mini-Split Heat Pump",
      "title": "{sys_name}",
      "price_range": "$749 - $2,199",
      "amazon_query": "{sys_name} Mini Split",
      "hvac_note": "1-sentence thermal performance note"
    }},
    {{
      "badge": "Disconnect & Whip Kit",
      "title": "60A 240V AC Disconnect Box + Liquidtight Electrical Whip & Surge Protector",
      "price_range": "$59 - $129",
      "amazon_query": "Mini Split Disconnect Box Whip Kit Surge Protector",
      "hvac_note": "1-sentence NEC Article 440 safety note"
    }},
    {{
      "badge": "Bracket & Line-Set Cover",
      "title": "Heavy-Duty Wall Mounting Bracket + 3-Inch PVC Line-Set Cover Kit",
      "price_range": "$54 - $109",
      "amazon_query": "Mini Split Wall Bracket Line Set Cover Kit",
      "hvac_note": "1-sentence outdoor condenser protection note"
    }},
    {{
      "badge": "Vacuum & Manifold Kit",
      "title": "4.5 CFM HVAC Vacuum Pump, Micron Gauge & R410A/R454B Manifold Set",
      "price_range": "$99 - $199",
      "amazon_query": "HVAC Vacuum Pump Manifold Gauge Set Mini Split",
      "hvac_note": "1-sentence 500-micron evacuation note"
    }}
  ],
  "installation_checklist": [
    "Step 1 regarding MCA/MOP breaker and AWG wire sizing",
    "Step 2 regarding HVAC surge protector installation",
    "Step 3 regarding condenser clearance and condensate drain slope",
    "Step 4 regarding flare nut torque and vacuum micron decay test"
  ],
  "faqs": [
    {{"q": "How many square feet will the {sys_name} cover?", "a": "Exact sq ft for insulated rooms vs garages/sunrooms."}},
    {{"q": "How much electricity does the {sys_name} use per month?", "a": "Exact running watts, kWh per month, and dollar cost."}},
    {{"q": "What size breaker and wire do I need for the {sys_name}?", "a": "Exact voltage, breaker amperage, and AWG copper wire."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{sys_name}': {e}")

    return build_deterministic_hvac_data(sys_tuple)


def build_hvac_html_page(data, slug, mon_cfg):
    sys_name = data.get("system_name", "Mini-Split Heat Pump")
    sp = data.get("specs", {})
    btu = int(safe_float(sp.get("nominal_btu", 12000), 12000))
    tons = round(btu / 12000.0, 1)
    seer2 = round(safe_float(sp.get("seer2_rating", 20.5), 20.5), 1)
    volts = int(safe_float(sp.get("voltage", 230), 230))
    breaker_a = int(safe_float(sp.get("max_breaker_amps", 20), 20))
    wire_awg = sp.get("recommended_wire_awg", "12/2 AWG Copper THHN")
    ideal_sqft = int(safe_float(sp.get("ideal_sqft", 500), 500))
    run_watts = int(safe_float(sp.get("avg_running_watts", int(btu / seer2)), 600))

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "DIY+Ductless+Mini+Split+Heat+Pump"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{sys_name} BTU Room Sizing & SEER2 Cost Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Mini Split Heat Pump")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-orange-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'HVAC Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$59+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">❄️ {item.get('hvac_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-orange-500 hover:bg-orange-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Room Size & BTU Reference Matrix
    btu_tiers = [
        ("250 – 400 Sq Ft", "9,000 BTU (0.75 Ton)", "115V / 230V (15A Breaker)", "14/2 AWG Copper", "~410W"),
        ("400 – 550 Sq Ft", "12,000 BTU (1.0 Ton)", "115V / 230V (15A–20A)", "12/2 AWG Copper", "~545W"),
        ("550 – 800 Sq Ft", "18,000 BTU (1.5 Ton)", "230V (20A Breaker)", "12/2 AWG Copper", "~860W"),
        ("800 – 1,100 Sq Ft", "24,000 BTU (2.0 Ton)", "230V (25A Breaker)", "10/2 AWG Copper", "~1,150W"),
        ("1,100 – 1,500 Sq Ft", "36,000 BTU (3.0 Ton)", "230V (35A–40A)", "8/2 AWG Copper", "~1,710W")
    ]
    matrix_rows_html = ""
    for area_s, btu_s, elec_s, awg_s, watt_s in btu_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{area_s}</td>
          <td class="py-3 px-4 font-bold text-orange-400">{btu_s}</td>
          <td class="py-3 px-4 text-slate-300">{elec_s}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{awg_s}</td>
          <td class="py-3 px-4 text-xs text-slate-400">{watt_s} Avg Draw</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("installation_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-orange-500 rounded cursor-pointer hvac-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', sys_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', sys_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-orange-500 text-slate-950 px-2 py-0.5 rounded font-black">BTU</span>SizingIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop DIY Mini-Splits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-orange-500 text-slate-950 px-3 py-1 rounded-full">{btu:,} BTU ({tons} Ton)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Efficiency: {seer2} SEER2 (~{run_watts}W)</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">{volts}V | {breaker_a}A Breaker | {wire_awg}</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', sys_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-orange-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>ACCA Manual-J & Electrical Summary:</strong> {data.get('engineering_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE BTU LOAD, SEER2 MONTHLY COST & BREAKER CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {sys_name} BTU Load & SEER2 Bill Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your room square footage, ceiling height, insulation quality, and daily runtime to calculate required BTU capacity, monthly electricity cost, and NEC breaker size.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="sqftSlider" class="text-slate-300">Room or Garage Floor Area (Sq Ft)</label>
              <span class="text-orange-400 font-bold"><span id="sqftVal">{ideal_sqft}</span> sq ft</span>
            </div>
            <input id="sqftSlider" type="range" min="150" max="1600" step="25" value="{ideal_sqft}" class="w-full accent-orange-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="ceilingSelect" class="block text-xs font-medium text-slate-400 mb-1">Ceiling Height</label>
              <select id="ceilingSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="1.00" selected>8 ft Standard Ceiling</option>
                <option value="1.15">9 – 10 ft High Ceiling</option>
                <option value="1.30">12+ ft Vaulted / Shop</option>
              </select>
            </div>
            <div>
              <label for="insulSelect" class="block text-xs font-medium text-slate-400 mb-1">Insulation & Sun Load</label>
              <select id="insulSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="22">Well Insulated (R-19+)</option>
                <option value="25" selected>Average Room / Insulated Garage</option>
                <option value="32">Poor Insulation / Sunroom / Hot Climate</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="hrsSlider" class="text-slate-300">Daily Active Operation (Hours/Day @ $0.16/kWh)</label>
              <span class="text-orange-400 font-bold"><span id="hrsVal">8</span> hrs/day</span>
            </div>
            <input id="hrsSlider" type="range" min="2" max="24" step="1" value="8" class="w-full accent-orange-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-orange-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-orange-400 font-bold">Required HVAC Capacity</span>
            <div class="text-xl sm:text-2xl font-black text-white mt-1"><span id="btuOut">{btu:,}</span> <span class="text-xs font-normal text-slate-400">BTU</span></div>
            <p id="tonOut" class="text-xs text-orange-400 font-semibold mt-1">Recommended: {tons} Ton Unit</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Est. Monthly Power Bill</span>
            <div class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">$<span id="billOut">0.00</span><span class="text-xs font-normal text-slate-400">/mo</span></div>
            <p id="kwhOut" class="text-xs text-slate-400 mt-1">At {seer2} SEER2 Inverter</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-orange-950/40 border border-orange-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="hvacAdviceBanner" class="text-sm text-orange-100 font-medium"></div>
        <a id="dynamicUnitBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-orange-500 hover:bg-orange-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Mini-Split on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {sys_name} Installation & Electrical Kit</h2>
        <span class="text-xs text-slate-400">NEC Article 440 & AHRI Certified</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- ROOM SIZE & BTU MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Mini-Split BTU, Tonnage & Electrical Wire Sizing Chart</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Floor Area (Sq Ft)</th>
              <th class="py-3.5 px-4 text-orange-400">Recommended BTU / Ton</th>
              <th class="py-3.5 px-4">Voltage & Breaker</th>
              <th class="py-3.5 px-4 text-emerald-400">Copper Whip Wire</th>
              <th class="py-3.5 px-4">Inverter Power Draw</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- INSTALLATION CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">DIY & Master HVAC Technician Installation Checklist</h2>
        <span id="hvacBadge" class="text-xs font-bold bg-slate-800 text-orange-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({sys_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} BTUSizingIndex. Independent HVAC Thermal Load & SEER2 Engineering Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const unitSeer2 = {seer2};
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const sqftSlider = document.getElementById('sqftSlider');
    const ceilingSelect = document.getElementById('ceilingSelect');
    const insulSelect = document.getElementById('insulSelect');
    const hrsSlider = document.getElementById('hrsSlider');
    const sqftVal = document.getElementById('sqftVal');
    const hrsVal = document.getElementById('hrsVal');
    const btuOut = document.getElementById('btuOut');
    const tonOut = document.getElementById('tonOut');
    const billOut = document.getElementById('billOut');
    const kwhOut = document.getElementById('kwhOut');
    const hvacAdviceBanner = document.getElementById('hvacAdviceBanner');
    const dynamicUnitBtn = document.getElementById('dynamicUnitBtn');

    function recalculateHvac() {{
      const sqft = parseInt(sqftSlider.value, 10);
      const ceilFactor = parseFloat(ceilingSelect.value);
      const btuPerSqft = parseFloat(insulSelect.value);
      const hrs = parseInt(hrsSlider.value, 10);

      sqftVal.textContent = sqft.toLocaleString();
      hrsVal.textContent = hrs;

      const rawBtu = sqft * btuPerSqft * ceilFactor;
      let recTierBtu = 9000;
      let recTon = "0.75 Ton (9K BTU)";
      let breakerSpec = "15A Breaker (14/2 AWG)";

      if (rawBtu <= 10000) {{
        recTierBtu = 9000;
        recTon = "0.75 Ton (9,000 BTU)";
        breakerSpec = "115V/230V 15A Breaker (14/2 AWG)";
      }} else if (rawBtu <= 14500) {{
        recTierBtu = 12000;
        recTon = "1.0 Ton (12,000 BTU)";
        breakerSpec = "115V/230V 20A Breaker (12/2 AWG)";
      }} else if (rawBtu <= 20500) {{
        recTierBtu = 18000;
        recTon = "1.5 Ton (18,000 BTU)";
        breakerSpec = "230V 20A Breaker (12/2 AWG)";
      }} else if (rawBtu <= 28000) {{
        recTierBtu = 24000;
        recTon = "2.0 Ton (24,000 BTU)";
        breakerSpec = "230V 25A Breaker (10/2 AWG)";
      }} else {{
        recTierBtu = 36000;
        recTon = "3.0 Ton (36,000 BTU)";
        breakerSpec = "230V 35A Breaker (8/2 AWG)";
      }}

      const estWatts = Math.round((recTierBtu / unitSeer2) * 0.65);
      const monthlyKwh = Math.round((estWatts * hrs * 30) / 1000.0);
      const monthlyCost = monthlyKwh * 0.16;

      btuOut.textContent = Math.round(rawBtu).toLocaleString();
      tonOut.textContent = `Match: ${{recTon}}`;
      billOut.textContent = monthlyCost.toFixed(2);
      kwhOut.textContent = `~${{monthlyKwh}} kWh/mo (${{estWatts}}W avg)`;

      hvacAdviceBanner.innerHTML = `❄️ <strong>Manual-J Sizing Spec:</strong> A ${{sqft}} sq ft space requires <strong>${{recTon}}</strong> wired to a <strong>${{breakerSpec}}</strong> outdoor disconnect.`;
      dynamicUnitBtn.href = `https://${{amzDomain}}/s?k=${{recTierBtu}}+BTU+DIY+Ductless+Mini+Split+Heat+Pump+SEER2&tag=${{amzTag}}`;
    }}

    sqftSlider.addEventListener('input', recalculateHvac);
    ceilingSelect.addEventListener('change', recalculateHvac);
    insulSelect.addEventListener('change', recalculateHvac);
    hrsSlider.addEventListener('input', recalculateHvac);
    recalculateHvac();

    const checks = document.querySelectorAll('.hvac-check');
    const badge = document.getElementById('hvacBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "DIY+Ductless+Mini+Split+Heat+Pump"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-orange-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-orange-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('btu', 12000):,} BTU | {item.get('seer2', 20.5)} SEER2</span>
            <span class="text-xs text-slate-400">Up to {item.get('sqft', 500)} Sq Ft</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-orange-400 transition">{item['system_name']} BTU & Cost Calculator</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-orange-400">Calculate Room BTU & SEER2 Bill →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BTUSizingIndex — Mini-Split Heat Pump BTU Room Sizing & SEER2 Cost Calculator (2026)</title>
  <meta name="description" content="Calculate exact ductless mini-split BTU capacity, room square footage, monthly SEER2 electricity bill, and NEC breaker wire size for MRCOOL, Senville, Pioneer, Mitsubishi, and Daikin systems.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="BTUSizingIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-orange-500 text-slate-950 px-2 py-0.5 rounded font-black">BTU</span>SizingIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop DIY Mini-Splits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Mini-Split Heat Pump BTU & SEER2 Cost Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select any ductless mini-split model or room type below to calculate required BTU/tonnage, monthly SEER2 power consumption, and NEC 240V whip/breaker specs.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search model or room (e.g. MRCOOL 18000 BTU, Senville Aura, Pioneer, Garage, Sunroom...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-orange-500">
      </div>
    </div>

    <div id="hvacGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} BTUSizingIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('hvacGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>BTUSizingIndex Mini-Split HVAC Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Ductless Mini-Split BTU Room Sizing & SEER2 Electricity Cost Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_SYSTEM:
        candidates.append((CUSTOM_SYSTEM.strip(), 18000, 20.5, 230, 20, 750, "Ductless Mini-Split Sizing"))
    candidates.extend(SEED_SYSTEMS)
    candidates.extend(discover_google_hvac_queries())

    new_urls = []
    count = 0

    for sys_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        sys_name = sys_tuple[0]
        slug = slugify(f"{sys_name}-btu-cost-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating HVAC BTU & SEER2 calculator for: {sys_name}...")
        try:
            data = generate_hvac_data(sys_tuple)
            build_hvac_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "system_name": data.get("system_name", sys_name),
                "slug": slug,
                "title": data.get("seo_title", f"{sys_name} BTU Calculator"),
                "description": data.get("meta_description", ""),
                "btu": int(safe_float(sp.get("nominal_btu", sys_tuple[1]), sys_tuple[1])),
                "seer2": round(safe_float(sp.get("seer2_rating", sys_tuple[2]), sys_tuple[2]), 1),
                "sqft": int(safe_float(sp.get("ideal_sqft", sys_tuple[5]), sys_tuple[5])),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {sys_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new Mini-Split BTU calculator pages.")


if __name__ == "__main__":
    main()
