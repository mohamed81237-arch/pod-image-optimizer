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

# الواجهة الأمامية بدون أي أزرار تبرعات أو دعم مادي
COMMUNITY_HTML_UI = """
<!DOCTYPE html>
<html lang="ar" dir="rtl" id="htmlRoot">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title id="pageTitle">POD Master Studio - أداة تجهيز وتحسين تصاميم الطباعة</title>
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
        <!-- ترويسة مع زر تغيير اللغة -->
        <div class="flex justify-between items-center mb-8">
            <div id="badgeText" class="px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold tracking-wide">
                أداة مجتمعية مجانية للمصممين ⚡
            </div>
            <button onclick="toggleLanguage()" class="bg-slate-800 hover:bg-slate-700 text-emerald-400 font-semibold px-4 py-2 rounded-xl text-xs border border-slate-700 transition">
                🌐 English / العربية
            </button>
        </div>

        <header class="text-center mb-12">
            <h1 id="mainTitle" class="text-4xl md:text-6xl font-extrabold tracking-tight mb-4 bg-gradient-to-r from-white via-slate-200 to-emerald-400 bg-clip-text text-transparent">
                تجهيز تصاميم الطباعة (POD)
            </h1>
            <p id="mainDesc" class="text-slate-400 text-base md:text-lg max-w-2xl mx-auto">
                إزالة الخلفية الفاتحة مع تنعيم الحواف بدقة وضبط الأبعاد لمنصات Redbubble و Amazon بضغطة زر.
            </p>
        </header>

        <div class="glass-panel rounded-3xl p-6 md:p-10">
            <form id="uploadForm" class="space-y-8">
                
                <div>
                    <label id="labelUpload" class="block text-sm font-semibold mb-3 text-slate-200">اختر أو اسحب ملف التصميم (صورة عالية الدقة):</label>
                    <div class="border-2 border-dashed border-slate-700 hover:border-emerald-500/80 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 bg-slate-900/50 hover:bg-slate-900/80 relative group">
                        <input type="file" id="imageFile" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" required onchange="handleFileSelect(this)">
                        <div id="fileLabelText" class="space-y-2">
                            <div class="w-12 h-12 mx-auto rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition duration-300">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                            </div>
                            <div class="text-slate-300 font-medium upload-text-inner">
                                <span class="text-emerald-400 font-semibold underline underline-offset-4">انقر لرفع الصورة</span> أو اسحبها وأفلتها هنا
                            </div>
                            <p class="text-xs text-slate-500">PNG, JPG, WEBP بجودة عالية</p>
                        </div>
                    </div>
                </div>

                <div id="instantPreviewContainer" class="hidden p-4 rounded-2xl bg-slate-950/60 border border-slate-800 transition-all">
                    <div class="flex items-center justify-between mb-3">
                        <span id="previewTitle" class="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            معاينة الملف الأصلي
                        </span>
                        <span id="originalDimensionsBadge" class="text-xs bg-slate-900 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-800">
                            جاري قراءة الأبعاد...
                        </span>
                    </div>
                    
                    <div class="flex items-center justify-center gap-2 mb-3">
                        <span id="bgColorLabel" class="text-xs text-slate-400 ml-1">فحص على لون المنتج:</span>
                        <button type="button" onclick="changePreviewBg('instantPreviewBox', 'checker')" class="w-6 h-6 rounded-full border-2 border-slate-600 checkerboard" title="شفاف"></button>
                        <button type="button" onclick="changePreviewBg('instantPreviewBox', 'black')" class="w-6 h-6 rounded-full border-2 border-slate-600 bg-black" title="أسود"></button>
                        <button type="button" onclick="changePreviewBg('instantPreviewBox', 'navy')" class="w-6 h-6 rounded-full border-2 border-slate-600 bg-[#0f172a]" title="كحلي"></button>
                        <button type="button" onclick="changePreviewBg('instantPreviewBox', 'white')" class="w-6 h-6 rounded-full border-2 border-slate-600 bg-white" title="أبيض"></button>
                    </div>

                    <div id="instantPreviewBox" class="relative w-full h-56 rounded-xl overflow-hidden flex items-center justify-center checkerboard transition-colors duration-300">
                        <img id="instantPreviewImg" src="" alt="Instant Preview" class="max-h-48 max-w-full object-contain drop-shadow-md" />
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label id="labelPlatform" class="block text-sm font-semibold mb-2 text-slate-300">المنصة المستهدفة:</label>
                        <select id="platform" onchange="toggleCustomDims()" class="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 text-slate-200 outline-none transition">
                            <option value="redbubble">Redbubble (5000 × 5000 px)</option>
                            <option value="teepublic">Teepublic (5000 × 5500 px)</option>
                            <option value="merch">Merch by Amazon (4500 × 5400 px)</option>
                            <option id="optCustom" value="custom">مقاس مخصص (Custom)</option>
                        </select>
                        <div class="custom-dims hidden grid-cols-2 gap-3 mt-3" id="customDims">
                            <input type="number" id="customWidth" placeholder="العرض (Width)" class="bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 outline-none">
                            <input type="number" id="customHeight" placeholder="الارتفاع (Height)" class="bg-slate-900 border border-slate-700 rounded-xl p-3 text-sm text-slate-100 outline-none">
                        </div>
                    </div>

                    <div>
                        <label id="labelDpi" class="block text-sm font-semibold mb-2 text-slate-300">دقة الطباعة:</label>
                        <select id="dpiSelect" class="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 text-slate-200 outline-none transition">
                            <option value="300" selected>300 DPI (قياسي واحترافي للطباعة)</option>
                            <option value="150">150 DPI (متوسط)</option>
                        </select>
                    </div>
                </div>

                <div class="flex items-center gap-3 bg-slate-900/60 p-4 rounded-2xl border border-slate-700/60">
                    <input type="checkbox" id="removeBg" class="w-5 h-5 accent-emerald-600 rounded cursor-pointer" checked>
                    <label id="labelRemoveBg" class="text-sm font-medium text-slate-200 cursor-pointer select-none">
                        إزالة الخلفية الفاتحة وتنعيم الحواف بذكاء (Smart Background Removal & Edge Smoothing) ✨
                    </label>
                </div>

                <button id="submitBtn" type="submit" class="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-4 rounded-2xl shadow-xl shadow-emerald-600/20 transition duration-300 text-lg">
                    معالجة وتحميل التصميم مجانًا ⚡
                </button>
            </form>

            <div class="loader hidden text-center my-8">
                <div class="inline-block animate-spin rounded-full h-10 w-10 border-4 border-emerald-500 border-t-transparent"></div>
                <p id="loaderText" class="text-sm text-emerald-400 mt-3 font-medium">جاري معالجة الصورة وتنعيم الحواف بجودة 300 DPI...</p>
            </div>

            <div id="status" class="mt-6 text-center text-sm font-medium"></div>

            <div class="text-center mt-6 p-5 bg-slate-900/80 rounded-2xl border border-slate-700/60 hidden shadow-inner" id="previewContainer">
                <div class="flex items-center justify-between mb-3">
                    <span id="resultBadge" class="text-xs text-emerald-400 font-bold bg-emerald-500/10 py-1.5 px-3 rounded-full border border-emerald-500/20">
                        ✨ النتيجة جاهزة للطباعة بجودة 300 DPI
                    </span>
                    
                    <div class="flex items-center gap-2 bg-slate-950/80 px-3 py-1.5 rounded-xl border border-slate-800">
                        <span id="checkResultLabel" class="text-xs text-slate-400 ml-1">فحص النتيجة:</span>
                        <button type="button" onclick="changePreviewBg('processedPreviewBox', 'checker')" class="w-5 h-5 rounded-full border border-slate-600 checkerboard" title="شفاف"></button>
                        <button type="button" onclick="changePreviewBg('processedPreviewBox', 'black')" class="w-5 h-5 rounded-full border border-slate-600 bg-black" title="أسود"></button>
                        <button type="button" onclick="changePreviewBg('processedPreviewBox', 'navy')" class="w-5 h-5 rounded-full border border-slate-600 bg-[#0f172a]" title="كحلي"></button>
                        <button type="button" onclick="changePreviewBg('processedPreviewBox', 'white')" class="w-5 h-5 rounded-full border border-slate-600 bg-white" title="أبيض"></button>
                    </div>
                </div>

                <div id="processedPreviewBox" class="p-4 checkerboard rounded-xl border border-slate-800 transition-colors duration-300">
                    <img id="imagePreview" src="" alt="معاينة الصورة" class="max-h-72 mx-auto rounded-lg shadow-2xl object-contain">
                </div>

                <div class="mt-6 p-4 rounded-2xl bg-slate-950/70 border border-slate-800 text-right" id="emailBoxContainer">
                    <label id="emailLabel" class="block text-xs font-semibold text-slate-300 mb-1">احصل على دليل استراتيجيات زيادة مبيعات Redbubble مجاناً:</label>
                    <div class="flex gap-2">
                        <input type="email" id="userEmail" placeholder="أدخل بريدك الإلكتروني" class="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500">
                        <button id="emailSaveBtn" type="button" onclick="saveEmail()" class="bg-slate-800 hover:bg-slate-700 text-emerald-400 font-semibold px-4 py-2.5 rounded-xl text-sm transition">حفظ</button>
                    </div>
                    <p id="emailMsg" class="text-xs text-emerald-400 mt-2 hidden">✨ شكراً لك! تم تسجيل بريدك بنجاح.</p>
                </div>

                <div class="mt-6">
                    <a href="#" id="downloadBtn" class="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-4 rounded-2xl shadow-xl shadow-emerald-600/20 transition duration-300 text-center block text-lg">
                        تحميل الصورة الأصلية للطباعة بجودتها الكاملة 300 DPI مجاناً 📥
                    </a>
                </div>
            </div>
        </div>
    </div>

<script>
    const API_BASE = window.location.origin;
    let currentLang = 'ar';

    const translations = {
        ar: {
            htmlLang: "ar", dir: "rtl",
            badge: "أداة مجتمعية مجانية للمصممين ⚡",
            title: "تجهيز تصاميم الطباعة (POD)",
            desc: "إزالة الخلفية الفاتحة مع تنعيم الحواف بدقة وضبط الأبعاد لمنصات Redbubble و Amazon بضغطة زر.",
            uploadLabel: "اختر أو اسحب ملف التصميم (صورة عالية الدقة):",
            uploadText: '<span class="text-emerald-400 font-semibold underline underline-offset-4">انقر لرفع الصورة</span> أو اسحبها وأفلتها هنا',
            subText: "PNG, JPG, WEBP بجودة عالية",
            previewTitle: "معاينة الملف الأصلي",
            bgColorLabel: "فحص على لون المنتج:",
            labelPlatform: "المنصة المستهدفة:",
            optCustom: "مقاس مخصص (Custom)",
            labelDpi: "دقة الطباعة:",
            labelRemoveBg: "إزالة الخلفية الفاتحة وتنعيم الحواف بذكاء (Smart Background Removal & Edge Smoothing) ✨",
            submitBtn: "معالجة وتحميل التصميم مجانًا ⚡",
            loaderText: "جاري معالجة الصورة وتنعيم الحواف بجودة 300 DPI...",
            resultBadge: "✨ النتيجة جاهزة للطباعة بجودة 300 DPI",
            checkResultLabel: "فحص النتيجة:",
            emailLabel: "احصل على دليل استراتيجيات زيادة مبيعات Redbubble مجاناً:",
            emailPlaceholder: "أدخل بريدك الإلكتروني",
            emailSaveBtn: "حفظ",
            downloadBtn: "تحميل الصورة الأصلية للطباعة بجودتها الكاملة 300 DPI مجاناً 📥"
        },
        en: {
            htmlLang: "en", dir: "ltr",
            badge: "Free Community Tool for Designers ⚡",
            title: "POD Design Optimizer",
            desc: "Smart background removal with edge smoothing and precise sizing for Redbubble, Teepublic & Amazon.",
            uploadLabel: "Choose or drag your design file (High-Res):",
            uploadText: '<span class="text-emerald-400 font-semibold underline underline-offset-4">Click to upload</span> or drag and drop here',
            subText: "PNG, JPG, WEBP in high quality",
            previewTitle: "Original File Preview",
            bgColorLabel: "Check on product color:",
            labelPlatform: "Target Platform:",
            optCustom: "Custom Size",
            labelDpi: "Print Resolution:",
            labelRemoveBg: "Smart Background Removal & Edge Smoothing ✨",
            submitBtn: "Process & Download Design Free ⚡",
            loaderText: "Processing image & smoothing edges at 300 DPI...",
            resultBadge: "✨ Ready for Print at 300 DPI",
            checkResultLabel: "Check result:",
            emailLabel: "Get the Free Redbubble Sales Strategy Guide:",
            emailPlaceholder: "Enter your email address",
            emailSaveBtn: "Save",
            downloadBtn: "Download Full-Res Print-Ready Image (300 DPI) 📥"
        }
    };

    function toggleLanguage() {
        currentLang = currentLang === 'ar' ? 'en' : 'ar';
        const t = translations[currentLang];
        
        document.getElementById('htmlRoot').setAttribute('lang', t.htmlLang);
        document.getElementById('htmlRoot').setAttribute('dir', t.dir);
        
        document.getElementById('badgeText').innerText = t.badge;
        document.getElementById('mainTitle').innerText = t.title;
        document.getElementById('mainDesc').innerText = t.desc;
        document.getElementById('labelUpload').innerText = t.uploadLabel;
        document.querySelector('.upload-text-inner').innerHTML = t.uploadText;
        document.getElementById('previewTitle').innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> ${t.previewTitle}`;
        document.getElementById('bgColorLabel').innerText = t.bgColorLabel;
        document.getElementById('labelPlatform').innerText = t.labelPlatform;
        document.getElementById('optCustom').innerText = t.optCustom;
        document.getElementById('labelDpi').innerText = t.labelDpi;
        document.getElementById('labelRemoveBg').innerText = t.labelRemoveBg;
        document.getElementById('submitBtn').innerText = t.submitBtn;
        document.getElementById('loaderText').innerText = t.loaderText;
        document.getElementById('resultBadge').innerText = t.resultBadge;
        document.getElementById('checkResultLabel').innerText = t.checkResultLabel;
        document.getElementById('emailLabel').innerText = t.emailLabel;
        document.getElementById('userEmail').placeholder = t.emailPlaceholder;
        document.getElementById('emailSaveBtn').innerText = t.emailSaveBtn;
        document.getElementById('downloadBtn').innerText = t.downloadBtn;
        
        const emailContainer = document.getElementById('emailBoxContainer');
        emailContainer.className = `mt-6 p-4 rounded-2xl bg-slate-950/70 border border-slate-800 ${t.dir === 'rtl' ? 'text-right' : 'text-left'}`; }  function handleFileSelect(input) { if (input.files && input.files[0]) { const file = input.files[0]; const reader = new FileReader(); reader.onload = function(e) { document.getElementById('instantPreviewImg').src = e.target.result; document.getElementById('instantPreviewContainer').classList.remove('hidden');  const tempImg = new Image(); tempImg.onload = function() { document.getElementById('originalDimensionsBadge').textContent = `${currentLang === 'ar' ? 'الأبعاد' : 'Dims'}: ${this.width} ×${this.height} px`;
                };
                tempImg.src = e.target.result;
            }
            reader.readAsDataURL(file);
            document.getElementById('fileLabelText').innerHTML = `
                <div class="w-12 h-12 mx-auto rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                </div>
                <div class="text-slate-200 font-medium mt-2">
                    ${currentLang === 'ar' ? 'تم اختيار الملف:' : 'Selected File:'} <span class="font-bold text-emerald-400">${file.name}</span>
                </div>`;
        }
    }

    function changePreviewBg(boxId, bgType) {
        const box = document.getElementById(boxId);
        box.classList.remove('bg-black', 'bg-white', 'bg-[#0f172a]', 'checkerboard');
        if (bgType === 'checker') box.classList.add('checkerboard');
        else if (bgType === 'black') box.classList.add('bg-black');
        else if (bgType === 'navy') box.classList.add('bg-[#0f172a]');
        else if (bgType === 'white') box.classList.add('bg-white');
    }

    function toggleCustomDims() {
        const platform = document.getElementById('platform').value;
        document.getElementById('customDims').style.display = platform === 'custom' ? 'grid' : 'none';
    }

    async function saveEmail() {
        const emailInput = document.getElementById('userEmail');
        const email = emailInput.value;
        const msgElement = document.getElementById('emailMsg');

        if (email && email.includes('@')) {
            try {
                const response = await fetch(`${API_BASE}/collect-email/`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: `email=${encodeURIComponent(email)}`
                });
                const data = await response.json();
                
                msgElement.classList.remove('hidden');
                if (response.ok) {
                    msgElement.className = "text-xs text-emerald-400 mt-2 font-medium";
                    msgElement.innerText = "✨ " + data.message;
                    emailInput.value = "";
                } else {
                    msgElement.className = "text-xs text-amber-400 mt-2 font-medium";
                    msgElement.innerText = "⚠️ " + (data.detail || data.message);
                }
            } catch (err) {
                alert('Connection error.');
            }
        } else {
            alert('Please enter a valid email address!');
        }
    }

    document.getElementById('uploadForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const fileInput = document.getElementById('imageFile');
        if (!fileInput.files.length) { alert('Please select an image first!'); return; }

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
            const response = await fetch(`${API_BASE}/process-image/`, { method: 'POST', body: formData }); const data = await response.json(); loader.style.display = 'none'; if (response.ok) { status.className = "mt-6 text-center text-sm font-semibold text-emerald-400"; status.innerText = `${data.message} | Size: ${data.optimized_resolution[0]}×${data.optimized_resolution[1]}`;
                previewImg.src = `${API_BASE}/preview-image/?t=` + new Date().getTime(); previewContainer.style.display = 'block'; downloadBtn.href = `${API_BASE}/download/`;
                previewContainer.scrollIntoView({ behavior: 'smooth' });
            } else {
                status.className = "mt-6 text-center text-sm font-semibold text-rose-400";
                status.innerText = `Error
