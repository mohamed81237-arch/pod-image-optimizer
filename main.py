from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageFilter
import io
import os
import gc
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PLATFORM_SPECS = {
    "redbubble": (5000, 5000),
    "teepublic": (5000, 5500),
    "merch": (4500, 5400)
}

# قراءة الواجهة من ملف index.html الخارجي (يمنع أي أخطاء SyntaxError نهائياً)
@app.head("/", include_in_schema=False)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    file_path = "index.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>index.html not found! Please create the frontend file.</h3>"

@app.post("/collect-email/")
async def collect_email(email: str = Form(...)):
    if not email or "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    
    clean_email = email.strip().lower()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path = "emails.txt"
    
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            if clean_email in f.read():
                return {"status": "exists", "message": "This email is already registered!"}
    
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {clean_email}\n")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save email.")
        
    return {"status": "success", "message": "Email saved successfully!"}

@app.get("/admin/download-emails-txt/")
async def download_emails_txt(secret_key: str):
    ADMIN_SECRET = "MY_SECRET_ADMIN_KEY"
    if secret_key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized access.")
    
    file_path = "emails.txt"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/plain", filename="subscribers_emails.txt")
    raise HTTPException(status_code=404, detail="No emails registered yet.")

def smart_remove_bg_and_smooth(pil_img: Image.Image) -> Image.Image:
    pil_img = pil_img.convert("RGBA")
    datas = pil_img.getdata()
    
    new_data = []
    for item in datas:
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
            
    pil_img.putdata(new_data)
    
    alpha = pil_img.split()[3]
    alpha = alpha.filter(ImageFilter.SMOOTH_MORE)
    pil_img.putalpha(alpha)
    
    return pil_img

@app.post("/process-image/")
async def process_image(
    file: UploadFile = File(...),
    platform: str = Form("redbubble"),
    dpi: int = Form(300),
    custom_width: int = Form(None),
    custom_height: int = Form(None),
    remove_bg: bool = Form(True)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    try:
        image_bytes = await file.read()
        with Image.open(io.BytesIO(image_bytes)) as img:
            original_size = img.size
            mode = 'RGBA' if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info) else 'RGB'
            pil_img = img.convert(mode)
        
        del image_bytes
        gc.collect()

        if remove_bg:
            try:
                pil_img = smart_remove_bg_and_smooth(pil_img)
            except Exception as e:
                print(f"Background removal notice: {e}")
            
        if custom_width and custom_height:
            target_width, target_height = custom_width, custom_height
        elif platform in PLATFORM_SPECS:
            target_width, target_height = PLATFORM_SPECS[platform]
        else:
            target_width, target_height = (5000, 5000)
            
        preview_width = 600
        preview_height = int(target_height * (preview_width / target_width))
        preview_img = pil_img.resize((preview_width, preview_height), Image.Resampling.BILINEAR)
        preview_img.save("preview_pod.png", "PNG", compress_level=1)
        del preview_img
        gc.collect()

        full_res_img = pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        del pil_img
        gc.collect()
        
        full_res_img.save("ready_for_pod.png", "PNG", dpi=(dpi, dpi), compress_level=1)
        del full_res_img
        gc.collect()
        
        return {
            "status": "success",
            "message": "Processed & Edges Smoothed Successfully!",
            "original_resolution": original_size,
            "optimized_resolution": [target_width, target_height],
            "preview_resolution": [preview_width, preview_height]
        }
        
    except Exception as e:
        gc.collect()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/preview-image/")
async def preview_image():
    file_path = "preview_pod.png"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Preview image not found.")

@app.get("/download/")
async def download_image():
    file_path = "ready_for_pod.png"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png", filename="pod_ready_image_300dpi.png")
    raise HTTPException(status_code=404, detail="Processed image not found.")
