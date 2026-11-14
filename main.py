from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from rembg import remove, new_session
import io
import os
import stripe
import cv2
import numpy as np
import gc

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = os.getenv("STRIPE_API_KEY", "sk_test_your_stripe_secret_key_here")

# استخدام النموذج الخفيف u2netp لتوفير الذاكرة في الاستضافة المجانية
rembg_session = new_session("u2netp")

PLATFORM_SPECS = {
    "redbubble": (5000, 5000),
    "teepublic": (5000, 5500),
    "merch": (4500, 5400)
}

# جدول الأسعار الاقتصادية والباقات
PRICING_PLANS = {
    "single": {"name": "صورة واحدة (تجربة/فردي)", "amount": 150},
    "starter": {"name": "باقة 10 صور (تخفيض 20%)", "amount": 800},
    "pro": {"name": "باقة 50 صورة احترافية (الأفضل قيمة)", "amount": 2500}
}

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
    remove_bg: bool = Form(False),
    dpi: int = Form(300),
    custom_width: int = Form(None),
    custom_height: int = Form(None)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    try:
        image_bytes = await file.read()
        
        if remove_bg:
            image_bytes = remove(image_bytes, session=rembg_session)
            
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        
        original_size = (img_cv.shape[1], img_cv.shape[0])
        
        if custom_width and custom_height:
            target_width, target_height = custom_width, custom_height
        elif platform in PLATFORM_SPECS:
            target_width, target_height = PLATFORM_SPECS[platform]
        else:
            target_width, target_height = (5000, 5000)
            
        resized_cv = cv2.resize(img_cv, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
        
        if len(resized_cv.shape) == 3 and resized_cv.shape[2] == 4:
            b, g, r, a = cv2.split(resized_cv)
            rgb = cv2.merge([b, g, r])
            smoothed_rgb = cv2.bilateralFilter(rgb, d=5, sigmaColor=50, sigmaSpace=50)
            resized_cv = cv2.merge([smoothed_rgb[:,:,0], smoothed_rgb[:,:,1], smoothed_rgb[:,:,2], a])
        else:
            resized_cv = cv2.bilateralFilter(resized_cv, d=5, sigmaColor=50, sigmaSpace=50)

        output_filename = "ready_for_pod.png"
        
        success, encoded_image = cv2.imencode('.png', resized_cv)
        if success:
            pil_img = Image.open(io.BytesIO(encoded_image.tobytes()))
            pil_img.save(output_filename, "PNG", dpi=(dpi, dpi))
        
        del img_cv, resized_cv, nparr, image_bytes
        gc.collect()
        
        return {
            "status": "success",
            "message": f"تمت المعالجة بدقة {dpi} DPI وأبعاد {target_width}×{target_height} بنجاح!",
            "original_resolution": original_size,
            "optimized_resolution": [target_width, target_height],
            "applied_dpi": dpi,
            "background_removed": remove_bg
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
