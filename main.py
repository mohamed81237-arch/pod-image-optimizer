from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import os
import stripe
import gc

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

# واجهة SaaS عصرية وفخمة جداً بتأثيرات الزجاج المعشي (Glassmorphism)
LUXURY_HTML_UI = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة تجهيز وتحسين تصاميم الطباعة عند الطلب (POD)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; }
        .glass-panel {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }
        .pricing-card.selected {
            border-color: #3b82f6;
            background: rgba(30, 58, 138, 0.4);
            box-shadow: 0 0 25px rgba(59, 130, 246, 0.25);
        }
    </style>
</head>
<body class="bg-[#090d16] bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))] text-slate-100 min-h-screen py-12 px-4">

    <div class="max-w-4xl mx-auto">
        <!-- ترويسة الموقع الفخمة -->
        <header class="text-center mb-12">
            <div class="inline-block px-4 py-1.5 mb-4 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold tracking-wide">
                منصة احترافية مدعومة بالذكاء الاصطناعي ⚡
            </div>
            <h1 class="text-4xl md:text-6xl font-extrabold tracking-tight mb-4 bg-gradient-to-r from-white via-slate-200 to-blue-400 bg-clip-text text-transparent">
                تجهيز تصاميم الطباعة (POD)
            </h1>
            <p class="text-slate-400 text-base md:text-lg max-w-2xl mx-auto">
                أزل الخلفية بدقة فائقة واضبط الأبعاد لـ Redbubble و Amazon بضغطة زر واحدة في بيئة عمل عصرية.
            </p>
        </header>

        <!-- صندوق التنبيهات -->
        <div id="paymentAlert" class="hidden p-4 rounded-2xl mb-6 text-center font-bold shadow-lg"></div>

        <!-- صندوق العمل الرئيسي (Glass Panel) -->
        <div class="glass-panel rounded-3xl p-6 md:p-10">
            <form id="uploadForm" class="space-y-8">
                
                <!-- منطقة رفع الملفات العائمة (Dropzone) -->
                <div>
                    <label class="block text-sm font-semibold mb-3 text-slate-200">اختر أو اسحب ملف التصميم (صورة عالية الدقة):</label>
                    <div class="border-2 border-dashed border-slate-700 hover:border-blue-500/80 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 bg-slate-900/50 hover:bg-slate-900/80 relative group">
                        <input type="file" id="imageFile" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" required onchange="updateFileName(this)">
                        <div id="fileLabelText" class="space-y-2">
                            <div class="w-12 h-12 mx-auto rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:scale-110 transition duration-300">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                            </div>
                            <div class="text-slate-300 font-medium">
                                <span class="text-blue-400 font-semibold underline underline-offset-4">انقر لرفع الصورة</span> أو اسحبها وأفلتها هنا
                            </div>
                            <p class="text-xs text-slate-500">PNG, JPG, WEBP بجودة عالية</p>
                        </div>
                    </div>
                </div>

                <!-- إعدادات المنصة والدقة -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label for="platform" class="block text-sm font-semibold mb-2 text-slate-300">المنصة المستهدفة:</label>
                        <select id="platform" onchange="toggleCustomDims()" class="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 text-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition">
                            <option value="redbubble">Redbubble (5000 × 5000 px)</option>
                            <option value="teepublic">Teepublic (5000 × 5500 px)</option>
                            <option value="merch">Merch by Amazon (4500 × 5400 px)</option>
                            <option value="custom">مقاس مخصص</option>
                        </select>
                        <div class="custom-dims hidden grid-cols-2 gap-3 mt-3" id="customDims">
                            <input type="number" id="customWidth" placeholder="العرض (px)" class="bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 outline-none focus:border-blue-500">
                            <input type="number" id="customHeight" placeholder="الارتفاع (px)" class="bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 outline-none focus:border-blue-500">
                        </div>
                    </div>

                    <div>
                        <label for="dpiSelect" class="block text-sm font-semibold mb-2 text-slate-300">دقة الطباعة المطلوبة:</label>
                        <select id="dpiSelect" class="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 text-slate-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition">
                            <option value="300" selected>300 DPI (قياسي واحترافي للطباعة)</option>
                            <option value="150">150 DPI (متوسط)</option>
                        </select>
                    </div>
                </div>

                <!-- خيار إزالة الخلفية الفاخر -->
                <div class="flex items-center gap-3 bg-slate-900/60 p-4 rounded-2xl border border-slate-700/60">
                    <input type="checkbox" id="removeBg" class="w-5 h-5 accent-blue-600 rounded cursor-pointer" checked>
                    <label for="removeBg" class="text-sm font-medium text-slate-200 cursor-pointer select-none">
                        إزالة الخلفية وجعلها شفافة بالذكاء الاصطناعي (AI Background Removal) ✨
                    </label>
                </div>

                <!-- بطاقات التسعير المتناسقة -->
                <div>
                    <label class="block text-sm font-semibold mb-3 text-slate-300">اختر باقة التسعير للحصول على الجودة الكاملة (300 DPI):</label>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4" dir="ltr">
                        <div onclick="selectPlan('pro')" id="card-pro" class="pricing-card border border-slate-700/80 bg-slate-900/60 rounded-2xl p-5 cursor-pointer transition hover:border-blue-500 text-center">
                            <div class="text-xs font-semibold text-slate-400 mb-1 uppercase tracking-wider">الباقة الاحترافية</div>
                            <div class="text-2xl font-black text-blue-400 mb-2">$25.00</div>
                            <div class="text-xs text-slate-300">50 صورة جاهزة للطباعة</div>
                        </div>
                        <div onclick="selectPlan('starter')" id="card-starter" class="pricing-card border border-slate-700/80 bg-slate-900/60 rounded-2xl p-5 cursor-pointer transition hover:border-blue-500 text-center">
                            <div class="text-xs font-semibold text-slate-400 mb-1 uppercase tracking-wider">باقة المبتدئين</div>
                            <div class="text-2xl font-black text-blue-400 mb-2">$8.00</div>
                            <div class="text-xs text-slate-300">10 صور (تخفيض 20%)</div>
                        </div>
                        <div onclick="selectPlan('single')" id="card-single" class="pricing-card selected border border-slate-700/80 bg-slate-900/60 rounded-2xl p-5 cursor-pointer transition hover:border-blue-500 text-center">
                            <div class="text-xs font-semibold text-slate-400 mb-1 uppercase tracking-wider">فردي</div>
                            <div class="text-2xl font-black text-blue-400 mb-2">$1.50</div>
                            <div class="text-xs text-slate-300">صورة واحدة مجربة</div>
                        </div>
                    </div>
                    <input type="hidden" id="pricingPlan" value="single">
                </div>

                <!-- زر الإرسال -->
                <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-4 rounded-2xl shadow-xl shadow-blue-600/20 transition duration-300 text-lg">
                    معالجة ومعاينة التصميم مجانًا ⚡
                </button>
            </form>

            <!-- مؤشر التحميل -->
            <div class="loader hidden text-center my-8">
                <div class="inline-block animate-spin rounded-full h-10 w-10 border-4 border-blue-500 border-t-transparent"></div>
                <p class="text-sm text-blue-400 mt-3 font-medium">جاري معالجة الصورة وإزالة الخلفية بالذكاء الاصطناعي...</p>
            </div>

            <div id="status" class="mt-6 text-center text-sm font-medium"></div>

            <!-- معاينة الجودة المنخفضة المجانية -->
            <div class="text-center mt-6 p-5 bg-slate-900/80 rounded-2xl border border-slate-700/60 hidden shadow-inner" id="previewContainer">
                <p class="text-xs text-amber-400 mb-3 font-bold bg-amber-500/10 py-1.5 px-3 rounded-full inline-block border border-amber-500/20">
                    ⚠️ معاينة مجانية بجودة منخفضة (غير صالحة للطباعة المباشرة)
                </p>
                <div class="p-4 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] rounded-xl border border-slate-800">
                    <img id="imagePreview" src="" alt="معاينة الصورة" class="max-h-72 mx-auto rounded-lg shadow-2xl object-contain">
                </div>
            </div>

            <!-- الأزرار النهائية (دفع وتحميل) -->
            <div class="mt-8 space-y-4">
                <button type="button" id="stripeBtn" class="w-full bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold py-4 rounded-2xl shadow-xl shadow-indigo-600/20 transition duration-300 hidden text-lg flex items-center justify-center gap-2">
                    <span>إتمام الدفع لتحميل الملف الأصلي (300 DPI)</span> 💳
                </button>
                <a href="#" id="downloadBtn" class="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-4 rounded-2xl shadow-xl shadow-emerald-600/20 transition duration-300 text-center block text-lg">
                    تحميل الصورة الأصلية للطباعة بجودتها الكاملة 📥
                </a>
            </div>
        </div>
    </div>

<script>
    let isPaid = false;
    const API_BASE = window.location.origin;

    function selectPlan(planKey) {
        document.getElementById('pricingPlan').value = planKey;
        document.querySelectorAll('.pricing-card').forEach(card => card.classList.remove('selected'));
        document.getElementById(`card-${planKey}`).classList.add('selected');
    }

    function updateFileName(input) {
        if(input.files && input.files[0]) {
            document.getElementById('fileLabelText').innerHTML = `
                <div class="w-12 h-12 mx-auto rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                </div>
                <div class="text-slate-200 font-medium mt-2">
                    تم اختيار الملف: <span class="font-bold text-emerald-400">${input.files[0].name}</span>
                </div>`;
        }
    }

    window.onload = function() {
        const urlParams = new URLSearchParams(window.location.search);
        const paymentStatus = urlParams.get('payment');
        const alertBox = document.getElementById('paymentAlert');
        
        if (paymentStatus === 'success') {
            isPaid = true;
            alertBox.classList.remove('hidden');
            alertBox.classList.add('bg-emerald-950/80', 'text-emerald-300', 'border', 'border-emerald-700/50');
            alertBox.innerText = '✨ تم الدفع بنجاح! زر تحميل الملف الأصلي عالي الدقة متاح الآن في الأسفل.';
            
            const downloadBtn = document.getElementById('downloadBtn');
            downloadBtn.href = `${API_BASE}/download/`;
            downloadBtn.style.display = 'block';
            document.getElementById('stripeBtn').style.display = 'none';
        } else if (paymentStatus === 'cancel') {
            alertBox.classList.remove('hidden');
            alertBox.classList.add('bg-rose-950/80', 'text-rose-300', 'border', 'border-rose-700/50');
            alertBox.innerText = '❌ تم إلغاء عملية الدفع.';
        }
    };

    function toggleCustomDims() {
        const platform = document.getElementById('platform').value;
        document.getElementById('customDims').style.display = platform === 'custom' ? 'grid' : 'none';
    }

    document.getElementById('uploadForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const fileInput = document.getElementById('imageFile');
        if (!fileInput.files.length) {
            alert('الرجاء اختيار صورة أولاً!');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('platform', document.getElementById('platform').value);
        formData.append('dpi', document.getElementById('dpiSelect').value);
        formData.append('remove_bg', document.getElementById('removeBg').checked);

        if (document.getElementById('platform').value === 'custom') {
            const w = document.getElementById('customWidth').value;
            const h = document.getElementById('customHeight').value;
            if (w) formData.append('custom_width', w);
            if (h) formData.append('custom_height', h);
        }

        const loader = document.querySelector('.loader');
        const status = document.getElementById('status');
        const previewContainer = document.getElementById('previewContainer');
        const previewImg = document.getElementById('imagePreview');
        const stripeBtn = document.getElementById('stripeBtn');
        const downloadBtn = document.getElementById('downloadBtn');

        loader.style.display = 'block';
        status.innerText = '';
        downloadBtn.style.display = 'none';
        stripeBtn.style.display = 'none';
        previewContainer.style.display = 'none';

        try {
            const response = await fetch(`${API_BASE}/process-image/`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            loader.style.display = 'none';
            if (response.ok) {
                status.className = "mt-6 text-center text-sm font-semibold text-emerald-400";
                status.innerText = `${data.message} | معاينة الأبعاد: ${data.preview_resolution[0]}×${data.preview_resolution[1]}`;
                
                previewImg.src = `${API_BASE}/preview-image/?t=` + new Date().getTime();
                previewContainer.style.display = 'block';

                if (!isPaid) {
                    stripeBtn.style.display = 'flex';
                    stripeBtn.onclick = payWithStripe;
                } else {
                    downloadBtn.href = `${API_BASE}/download/`;
                    downloadBtn.style.display = 'block';
                }
            } else {
                status.className = "mt-6 text-center text-sm font-semibold text-rose-400";
                status.innerText = `حدث خطأ: ${data.detail}`;
            }
        } catch (err) {
            loader.style.display = 'none';
            status.className = "mt-6 text-center text-sm font-semibold text-rose-400";
            status.innerText = 'تعذر الاتصال بالسيرفر. تأكد من عمل الشبكة.';
        }
    });

    async function payWithStripe() {
        const status = document.getElementById('status');
        const selectedPlan = document.getElementById('pricingPlan').value;
        status.className = "mt-6 text-center text-sm font-semibold text-blue-400";
        status.innerText = 'جاري التحويل إلى بوابة الدفع الآمنة Stripe...';
        
        try {
            const formData = new FormData();
            formData.append('plan', selectedPlan);

            const response = await fetch(`${API_BASE}/create-checkout-session/`, { 
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.checkout_url) {
                window.location.href = data.checkout_url;
            } else {
                status.className = "mt-6 text-center text-sm font-semibold text-rose-400";
                status.innerText = 'تأكد من إعداد مفتاح Stripe API في إعدادات المنصة.';
            }
        } catch (err) {
            status.className = "mt-6 text-center text-sm font-semibold text-rose-400";
            status.innerText = 'خطأ في الاتصال ببوابة الدفع.';
        }
    }
</script>

</body>
</html>
"""

@app.head("/", include_in_schema=False)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return LUXURY_HTML_UI

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
                    'unit_amount': int(selected_plan["amount"]),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{base_url}/?payment=success',
            cancel_url=f'{base_url}/?payment=cancel',
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe Error: {str(e)}")

@app.post("/process-image/")
async def process_image(
    file: UploadFile = File(...),
    platform: str = Form("redbubble"),
    dpi: int = Form(300),
    custom_width: int = Form(None),
    custom_height: int = Form(None)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    try:
        image_bytes = await file.read()
        with Image.open(io.BytesIO(image_bytes)) as img:
            original_size = img.size
            # استخدام RGB إذا لم تكن الصورة تحتوي على شفافية لتوفير 25% من الذاكرة
            mode = 'RGBA' if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info) else 'RGB'
            pil_img = img.convert(mode)
        
        del image_bytes
        gc.collect()
            
        if custom_width and custom_height:
            target_width, target_height = custom_width, custom_height
        elif platform in PLATFORM_SPECS:
            target_width, target_height = PLATFORM_SPECS[platform]
        else:
            target_width, target_height = (5000, 5000)
            
        # 1. إنشاء وحفظ نسخة المعاينة أولاً (سريعة وخفيفة)
        preview_width = 600
        preview_height = int(target_height * (preview_width / target_width))
        preview_img = pil_img.resize((preview_width, preview_height), Image.Resampling.BILINEAR)
        preview_img.save("preview_pod.png", "PNG", compress_level=1)
        del preview_img
        gc.collect()

        # 2. حفظ الملف الأصلي عالي الجودة مع تسريع الضغط لتفادي Timeout
        full_res_img = pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        del pil_img
        gc.collect()
        
        full_res_img.save("ready_for_pod.png", "PNG", dpi=(dpi, dpi), compress_level=1)
        del full_res_img
        gc.collect()
        
        return {
            "status": "success",
            "message": "تمت معالجة الصورة بنجاح! شاهد المعاينة المجانية أدناه.",
            "original_resolution": original_size,
            "optimized_resolution": [target_width, target_height],
            "preview_resolution": [preview_width, preview_height]
        }
        
    except Exception as e:
        gc.collect()
        raise HTTPException(status_code=500, detail=str(e))

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
