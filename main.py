from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import os
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

PLATFORM_SPECS = {
    "redbubble": (5000, 5000),
    "teepublic": (5000, 5500),
    "merch": (4500, 5400)
}

# واجهة SaaS مع جمع البريد الإلكتروني وزر الدعم الاختياري (Buy Me a Coffee)
COMMUNITY_HTML_UI = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>منصة تجهيز وتحسين تصاميم الطباعة عند الطلب (POD Master Studio)</title>
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
        .checkerboard {
            background-image: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAMUlEQVQ4T2NkYGAQYcAP3uCTZhw1gGGYhAGBZIA/nYDCgBDAm9BGDWAAJyRCgLaBCAAgXwixzAS0pgAAAABJRU5ErkJggg==");
        }
    </style>
</head>
<body class="bg-[#090d16] bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))] text-slate-100 min-h-screen py-12 px-4">

    <div class="max-w-4xl mx-auto">
        <!-- ترويسة الموقع الفخمة -->
        <header class="text-center mb-12">
            <div class="inline-block px-4 py-1.5 mb-4 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold tracking-wide">
                أداة مجتمعية مجانية للمصممين ⚡
            </div>
            <h1 class="text-4xl md:text-6xl font-extrabold tracking-tight mb-4 bg-gradient-to-r from-white via-slate-200 to-emerald-400 bg-clip-text text-transparent">
                تجهيز تصاميم الطباعة (POD)
            </h1>
            <p class="text-slate-400 text-base md:text-lg max-w-2xl mx-auto">
                أزل الخلفية بدقة فائقة واضبط الأبعاد لـ Redbubble و Amazon بضغطة زر ومجاناً تماماً.
            </p>
        </header>

        <!-- صندوق العمل الرئيسي (Glass Panel) -->
        <div class="glass-panel rounded-3xl p-6 md:p-10">
            <form id="uploadForm" class="space-y-8">
                
                <!-- منطقة رفع الملفات العائمة (Dropzone) -->
                <div>
                    <label class="block text-sm font-semibold mb-3 text-slate-200">اختر أو اسحب ملف التصميم (صورة عالية الدقة):</label>
                    <div class="border-2 border-dashed border-slate-700 hover:border-emerald-500/80 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 bg-slate-900/50 hover:bg-slate-900/80 relative group">
                        <input type="file" id="imageFile" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" required onchange="handleFileSelect(this)">
                        <div id="fileLabelText" class="space-y-2">
                            <div class="w-12 h-12 mx-auto rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition duration-300">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                            </div>
                            <div class="text-slate-300 font-medium">
                                <span class="text-emerald-400 font-semibold underline underline-offset-4">انقر لرفع الصورة</span> أو اسحبها وأفلتها هنا
                            </div>
                            <p class="text-xs text-slate-500">PNG, JPG, WEBP بجودة عالية</p>
                        </div>
                    </div>
                </div>

                <!-- 🌟 معاينة فورية (Live Local Preview) مع أزرار فحص الخلفيات -->
                <div id="instantPreviewContainer" class="hidden p-4 rounded-2xl bg-slate-950/60 border border-slate-800 transition-all">
                    <div class="flex items-center justify-between mb-3">
                        <span class="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            معاينة الملف الأصلي قبل المعالجة
                        </span>
                        <span id="originalDimensionsBadge" class="text-xs bg-slate-900 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-800">
                            جاري قراءة الأبعاد...
                        </span>
                    </div>
                    
                    <!-- أزرار تبديل الخلفية (QA Background Switcher) -->
                    <div class="flex items-center justify-center gap-2 mb-3">
                        <span class="text-xs text-slate-400 ml-1">فحص على لون المنتج:</span>
                        <button type="button" onclick="changePreviewBg('instantPreviewBox', 'checker')" class="w-6 h-6 rounded-full border-2 border-slate-600 checkerboard focus:ring-2 ring-emerald-500" title="خلفية شفافة"></button>
                        <button type="button" onclick="changePreviewBg('instantPreviewBox', 'black')" class="w-6 h-6 rounded-full border-2 border-slate-600 bg-black focus:ring-2 ring-emerald-500" title="تيشرت أسود"></button>
                        <button type="button" onclick="changePreviewBg('instantPreviewBox', 'navy')" class="w-6 h-6 rounded-full border-2 border-slate-600 bg-[#0f172a] focus:ring-2 ring-emerald-500" title="تيشرت كحلي"></button>
                        <button type="button" onclick="changePreviewBg('instantPreviewBox', 'white')" class="w-6 h-6 rounded-full border-2 border-slate-600 bg-white focus:ring-2 ring-emerald-500" title="تيشرت أبيض"></button>
                    </div>

                    <div id="instantPreviewBox" class="relative w-full h-56 rounded-xl overflow-hidden flex items-center justify-center checkerboard transition-colors duration-300">
                        <img id="instantPreviewImg" src="" alt="Instant Preview" class="max-h-48 max-w-full object-contain drop-shadow-md" />
                    </div>
                </div>

                <!-- إعدادات المنصة والدقة -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label for="platform" class="block text-sm font-semibold mb-2 text-slate-300">المنصة المستهدفة:</label>
                        <select id="platform" onchange="toggleCustomDims()" class="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 text-slate-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none transition">
                            <option value="redbubble">Redbubble (5000 × 5000 px)</option>
                            <option value="teepublic">Teepublic (5000 × 5500 px)</option>
                            <option value="merch">Merch by Amazon (4500 × 5400 px)</option>
                            <option value="custom">مقاس مخصص</option>
                        </select>
                        <div class="custom-dims hidden grid-cols-2 gap-3 mt-3" id="customDims">
                            <input type="number" id="customWidth" placeholder="العرض (px)" class="bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 outline-none focus:border-emerald-500">
                            <input type="number" id="customHeight" placeholder="الارتفاع (px)" class="bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 outline-none focus:border-emerald-500">
                        </div>
                    </div>

                    <div>
                        <label for="dpiSelect" class="block text-sm font-semibold mb-2 text-slate-300">دقة الطباعة المطلوبة:</label>
                        <select id="dpiSelect" class="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 text-slate-200 focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none transition">
                            <option value="300" selected>300 DPI (قياسي واحترافي للطباعة)</option>
                            <option value="150">150 DPI (متوسط)</option>
                        </select>
                    </div>
                </div>

                <!-- خيار إزالة الخلفية الفاخر -->
                <div class="flex items-center gap-3 bg-slate-900/60 p-4 rounded-2xl border border-slate-700/60">
                    <input type="checkbox" id="removeBg" class="w-5 h-5 accent-emerald-600 rounded cursor-pointer" checked>
                    <label for="removeBg" class="text-sm font-medium text-slate-200 cursor-pointer select-none">
                        إزالة الخلفية وجعلها شفافة بالذكاء الاصطناعي (AI Background Removal) ✨
                    </label>
                </div>

                <!-- زر الإرسال المجاني -->
                <button type="submit" class="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-4 rounded-2xl shadow-xl shadow-emerald-600/20 transition duration-300 text-lg">
                    معالجة وتحميل التصميم مجانًا ⚡
                </button>
            </form>

            <!-- مؤشر التحميل -->
            <div class="loader hidden text-center my-8">
                <div class="inline-block animate-spin rounded-full h-10 w-10 border-4 border-emerald-500 border-t-transparent"></div>
                <p class="text-sm text-emerald-400 mt-3 font-medium">جاري معالجة الصورة وضبطها لجودة 300 DPI...</p>
            </div>

            <div id="status" class="mt-6 text-center text-sm font-medium"></div>

            <!-- معاينة النتيجة وجمع البريد الإلكتروني -->
            <div class="text-center mt-6 p-5 bg-slate-900/80 rounded-2xl border border-slate-700/60 hidden shadow-inner" id="previewContainer">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-xs text-emerald-400 font-bold bg-emerald-500/10 py-1.5 px-3 rounded-full border border-emerald-500/20">
                        ✨ النتيجة جاهزة للطباعة بجودة 300 DPI
                    </span>
                    
                    <div class="flex items-center gap-2 bg-slate-950/80 px-3 py-1.5 rounded-xl border border-slate-800">
                        <span class="text-xs text-slate-400 ml-1">فحص النتيجة:</span>
                        <button type="button" onclick="changePreviewBg('processedPreviewBox', 'checker')" class="w-5 h-5 rounded-full border border-slate-600 checkerboard" title="شفاف"></button>
                        <button type="button" onclick="changePreviewBg('processedPreviewBox', 'black')" class="w-5 h-5 rounded-full border border-slate-600 bg-black" title="أسود"></button>
                        <button type="button" onclick="changePreviewBox('processedPreviewBox', 'navy')" class="w-5 h-5 rounded-full border border-slate-600 bg-[#0f172a]" title="كحلي"></button>
                        <button type="button" onclick="changePreviewBox('processedPreviewBox', 'white')" class="w-5 h-5 rounded-full border border-slate-600 bg-white" title="أبيض"></button>
                    </div>
                </div>

                <div id="processedPreviewBox" class="p-4 checkerboard rounded-xl border border-slate-800 transition-colors duration-300">
                    <img id="imagePreview" src="" alt="معاينة الصورة" class="max-h-72 mx-auto rounded-lg shadow-2xl object-contain">
                </div>

                <!-- 🌟 صندوق جمع البريد الإلكتروني الاختياري (Newsletter / Lead Magnet) -->
                <div class="mt-6 p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-right">
                    <label class="block text-xs font-semibold text-slate-300 mb-1">احصل على دليل استراتيجيات زيادة مبيعات Redbubble مجاناً:</label>
                    <div class="flex gap-2">
                        <input type="email" id="userEmail" placeholder="أدخل بريدك الإلكتروني (اختياري)" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500">
                        <button type="button" onclick="saveEmail()" class="bg-slate-800 hover:bg-slate-700 text-emerald-400 font-semibold px-4 py-2.5 rounded-xl text-sm transition">حفظ</button>
                    </div>
                    <p id="emailMsg" class="text-xs text-emerald-400 mt-2 hidden">✨ شكراً لك! تم تسجيل بريدك بنجاح.</p>
                </div>

                <!-- زر التحميل المباشر المجاني -->
                <div class="mt-6">
                    <a href="#" id="downloadBtn" class="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-4 rounded-2xl shadow-xl shadow-emerald-600/20 transition duration-300 text-center block text-lg">
                        تحميل الصورة الأصلية للطباعة بجودتها الكاملة 300 DPI مجاناً 📥
                    </a>
                </div>

                <!-- 🌟 زر التبرع الاختياري (Buy Me a Coffee / Support) -->
                <div class="mt-6 pt-4 border-t border-slate-800 text-center">
                    <p class="text-xs text-slate-400 mb-2">هل أعجبتك الأداة وساعدت عملك؟ يمكنك دعم استمرار السيرفر:</p>
                    <a href="https://buymeacoffee.com/your-username" target="_blank" class="inline-flex items-center gap-2 bg-[#ffdd00] hover:bg-[#f2d100] text-slate-950 font-bold px-6 py-2.5 rounded-xl text-xs transition shadow-md">
                        <span>☕ ادعمني بقهوة (Buy Me a Coffee)</span>
                    </a>
                </div>
            </div>
        </div>

        <!-- قسم دليل البائعين الإرشادي -->
        <section class="mt-16">
            <div class="text-center mb-10">
                <h2 class="text-2xl font-bold text-white mb-3">دليل تجهيز التصاميم للطباعة حسب الطلب (POD)</h2>
                <p class="text-slate-400 text-sm max-w-xl mx-auto">قواعد فحص الجودة الأساسية لضمان قبول تصاميمك وظهورها بأعلى دقة على التيشرتات والأكواب.</p>
            </div>

            <div class="grid md:grid-cols-3 gap-6">
                <div class="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
                    <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-xl mb-4">👕</div>
                    <h3 class="text-base font-bold text-white mb-2">الفحص على الألوان الداكنة</h3>
                    <p class="text-slate-400 text-xs leading-relaxed">اختبر تصميمك دائماً على خلفية سوداء أو كحلية لكشف أي حواف بيضاء غير مرغوب فيها قبل رفعها للمتجر.</p>
                </div>

                <div class="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
                    <div class="w-10 h-10 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center text-xl mb-4">📐</div>
                    <h3 class="text-base font-bold text-white mb-2">معيار 300 DPI</h3>
                    <p class="text-slate-400 text-xs leading-relaxed">تأكد من تصدير ملفك بالأبعاد والمقاسات الصحيحة للمنصة المستهدفة لتفادي بهتان الطباعة.</p>
                </div>

                <div class="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
                    <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-xl mb-4">✨</div>
                    <h3 class="text-base font-bold text-white mb-2">نسخ مخصصة لكل منتج</h3>
                    <p class="text-slate-400 text-xs leading-relaxed">التصاميم ذات النصوص الفاتحة تتطلب عناية خاصة عند طباعتها على منتجات بيضاء أو سوداء.</p>
                </div>
            </div>
        </section>
    </div>

<script>
    const API_BASE = window.location.origin;

    function handleFileSelect(input) {
        if (input.files && input.files[0]) {
            const file = input.files[0];
            const reader = new FileReader();
            
            reader.onload = function(e) {
                document.getElementById('instantPreviewImg').src = e.target.result;
                document.getElementById('instantPreviewContainer').classList.remove('hidden');

                const tempImg = new Image();
                tempImg.onload = function() {
                    document.getElementById('originalDimensionsBadge').textContent = `الأبعاد: ${this.width} × ${this.height} px`;
                };
                tempImg.src = e.target.result;
            }
            reader.readAsDataURL(file);

            document.getElementById('fileLabelText').innerHTML = `
                <div class="w-12 h-12 mx-auto rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                </div>
                <div class="text-slate-200 font-medium mt-2">
                    تم اختيار الملف: <span class="font-bold text-emerald-400">${file.name}</span>
                </div>`;
        }
    }

    function changePreviewBg(boxId, bgType) {
        const box = document.getElementById(boxId);
        box.classList.remove('bg-black', 'bg-white', 'bg-[#0f172a]', 'checkerboard');

        if (bgType === 'checker') {
            box.classList.add('checkerboard');
        } else if (bgType === 'black') {
            box.classList.add('bg-black');
        } else if (bgType === 'navy') {
            box.classList.add('bg-[#0f172a]');
        } else if (bgType === 'white') {
            box.classList.add('bg-white');
        }
    }

    function toggleCustomDims() {
        const platform = document.getElementById('platform').value;
        document.getElementById('customDims').style.display = platform === 'custom' ? 'grid' : 'none';
    }

    function saveEmail() {
        const email = document.getElementById('userEmail').value;
        if(email && email.includes('@')) {
            document.getElementById('emailMsg').classList.remove('hidden');
            // هنا يمكنك لاحقاً ربطه بـ Backend لحفظ البريد في ملف أو قاعدة بيانات
        } else {
            alert('الرجاء إدخال بريد إلكتروني صحيح!');
        }
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
        const downloadBtn = document.getElementById('downloadBtn');

        loader.style.display = 'block';
        status.innerText = '';
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
                status.innerText = `${data.message} | الأبعاد الجديدة: ${data.optimized_resolution[0]}×${data.optimized_resolution[1]}`;
                
                previewImg.src = `${API_BASE}/preview-image/?t=` + new Date().getTime();
                previewContainer.style.display = 'block';

                downloadBtn.href = `${API_BASE}/download/`;
                previewContainer.scrollIntoView({ behavior: 'smooth' });
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
</script>

</body>
</html>
"""

@app.head("/", include_in_schema=False)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return COMMUNITY_HTML_UI

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

        if remove_bg and REMBG_AVAILABLE:
            try:
                pil_img = remove(pil_img)
            except Exception:
                pass
            
        if custom_width and custom_height:
            target_width, target_height = custom_width, custom_height
        elif platform in PLATFORM_SPECS:
            target_width, target_height = PLATFORM_SPECS[platform]
        else:
            target_width, target_height = (5000, 5000)
            
        # 1. المعاينة
        preview_width = 600
        preview_height = int(target_height * (preview_width / target_width))
        preview_img = pil_img.resize((preview_width, preview_height), Image.Resampling.BILINEAR)
        preview_img.save("preview_pod.png", "PNG", compress_level=1)
        del preview_img
        gc.collect()

        # 2. الصورة الأصلية عالية الجودة
        full_res_img = pil_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        del pil_img
        gc.collect()
        
        full_res_img.save("ready_for_pod.png", "PNG", dpi=(dpi, dpi), compress_level=1)
        del full_res_img
        gc.collect()
        
        return {
            "status": "success",
            "message": "تمت معالجة الصورة بنجاح وتجهيزها للطباعة!",
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
