from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import os
import stripe
import gc

# استيراد آمن لمكتبة إزالة الخلفية
try:
    from rembg import remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = os.getenv("STRIPE_API_KEY", "sk_test_your_stripe_secret_key_here")

PLATFORM_SPECS = {
    "redbubble": (5000, 5000),
    "teepublic": (5000, 5500),
    "merch": (4500, 5400)
}

PRICING_PLANS = {
    "single": {"name": "صورة واحدة (تجربة/فردي)", "amount": 150},
    "starter": {"name": "باقة 10 صور (تخفيض 20%)", "amount": 800},
    "pro": {"name": "باقة 50 صورة احترافية (الأفضل قيمة)", "amount": 2500}
}

@app.head("/", include_in_schema=False)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/create-checkout-session/")
async def create_checkout_session(request: Request, plan: str = Form("single")):
    try:
        selected_plan = PRICING_PLANS.get(plan, PRICING_PLANS["single"])
        base_url = str(request.base_url).rstrip("/")
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'POD Service - {selected_plan["name"]}',
                    },
                    'unit_amount': selected_plan["amount"],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{base_url}/?payment=success',
            cancel_url=f'{base_url}/?payment=cancel',
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-image/")
async def process_image(
    file: UploadFile = File(...),
    platform: str = Form("redbubble"),
    dpi: int = Form(300),
    remove_bg: bool = Form(False),
    custom_width: int = Form(None),
    custom_height: int = Form(None)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    try:
        image_bytes = await file.read()
        pil_img = Image.open(io.BytesIO(image_bytes))
        
        if pil_img.mode != 'RGBA' and pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGBA')
            
        original_size = pil_img.size
        
        # إزالة الخلفية إذا طلب المستخدم وكانت المتاحة
        if remove_bg and REMBG_AVAILABLE:
            pil_img = remove(pil_img)
            
        if custom_width and custom_height:
            target_width, target_height = custom_width, custom_height
        elif platform in PLATFORM_SPECS:
            target_width, target_height = PLATFORM_SPECS[platform]
        else:
            target_width, target_height = (5000, 5000)
            
        # تغيير الحجم بجودة عالية
        resized_pil = pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        output_filename = "ready_for_pod.png"
        resized_pil.save(output_filename, "PNG", dpi=(dpi, dpi))
        
        del image_bytes, pil_img, resized_pil
        gc.collect()
        
        return {
            "status": "success",
            "message": f"تمت معالجة الصورة وإزالة الخلفية بدقة {dpi} DPI وأبعاد {target_width}×{target_height} بنجاح!",
            "original_resolution": original_size,
            "optimized_resolution": [target_width, target_height],
            "applied_dpi": dpi
        }
        
    except Exception as e:
        gc.collect()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/")
async def download_image():
    file_path = "ready_for_pod.png"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png", filename="pod_ready_image.png")
    raise HTTPException(status_code=404, detail="Processed image not found.")
