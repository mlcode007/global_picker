const fs = require('fs');
const path = require('path');
const { minify } = require('terser');
const archiver = require('archiver');

const SRC_DIR = path.join(__dirname);
const DIST_DIR = path.join(__dirname, 'dist');
const MANIFEST_FILE = path.join(SRC_DIR, 'manifest.json');

// 需要压缩的 JS 文件
const JS_FILES = [
  'background.js',
  'content.js',
  'popup.js',
  'sync-inject.js',
];

// 不需要压缩的文件/目录
const SKIP_FILES = [
  'package.json',
  'package-lock.json',
  'build.js',
  'node_modules',
  'dist',
];

async function minifyJS() {
  console.log('🔧 开始压缩 JavaScript 文件...\n');

  for (const file of JS_FILES) {
    const srcPath = path.join(SRC_DIR, file);
    const distPath = path.join(DIST_DIR, file);

    if (!fs.existsSync(srcPath)) {
      console.warn(`⚠️  跳过: ${file} 不存在`);
      continue;
    }

    const code = fs.readFileSync(srcPath, 'utf-8');

    try {
      const result = await minify(code, {
        compress: {
          drop_console: false,  // 保留 console 用于调试
          drop_debugger: true,
          pure_funcs: [],
        },
        mangle: {
          toplevel: true,
          properties: {
            regex: /^_/  // 只混淆以 _ 开头的属性
          }
        },
        output: {
          comments: false,
          beautify: false,
        },
        sourceMap: false,
      });

      fs.writeFileSync(distPath, result.code, 'utf-8');

      const originalSize = Buffer.byteLength(code, 'utf-8');
      const minifiedSize = Buffer.byteLength(result.code, 'utf-8');
      const savings = ((1 - minifiedSize / originalSize) * 100).toFixed(1);

      console.log(`✅ ${file}`);
      console.log(`   原始: ${(originalSize / 1024).toFixed(1)} KB → 压缩: ${(minifiedSize / 1024).toFixed(1)} KB (节省 ${savings}%)`);
    } catch (error) {
      console.error(`❌ ${file} 压缩失败:`, error.message);
    }
  }

  console.log('\n✨ JavaScript 压缩完成\n');
}

function copyStaticFiles() {
  console.log('📦 复制静态文件...\n');

  // 复制 manifest.json
  const manifestSrc = path.join(SRC_DIR, 'manifest.json');
  const manifestDist = path.join(DIST_DIR, 'manifest.json');
  fs.copyFileSync(manifestSrc, manifestDist);
  console.log('✅ manifest.json');

  // 复制 popup.html
  const popupSrc = path.join(SRC_DIR, 'popup.html');
  const popupDist = path.join(DIST_DIR, 'popup.html');
  if (fs.existsSync(popupSrc)) {
    fs.copyFileSync(popupSrc, popupDist);
    console.log('✅ popup.html');
  }

  // 复制 icons 目录
  const iconsSrc = path.join(SRC_DIR, 'icons');
  const iconsDist = path.join(DIST_DIR, 'icons');
  if (fs.existsSync(iconsSrc)) {
    fs.mkdirSync(iconsDist, { recursive: true });
    const iconFiles = fs.readdirSync(iconsSrc);
    for (const icon of iconFiles) {
      fs.copyFileSync(path.join(iconsSrc, icon), path.join(iconsDist, icon));
    }
    console.log(`✅ icons/ (${iconFiles.length} 个文件)`);
  }

  console.log('\n✨ 静态文件复制完成\n');
}

function createZip() {
  return new Promise((resolve, reject) => {
    console.log('️  创建 ZIP 压缩包...\n');

    const version = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8')).version;
    const zipName = `tiktok-shop-collector-v${version}.zip`;
    const zipPath = path.join(SRC_DIR, zipName);

    const output = fs.createWriteStream(zipPath);
    const archive = archiver('zip', {
      zlib: { level: 9 }  // 最高压缩级别
    });

    output.on('close', () => {
      const size = (archive.pointer() / 1024).toFixed(1);
      console.log(`✅ 压缩包创建成功: ${zipName}`);
      console.log(`   大小: ${size} KB`);
      console.log(`   路径: ${zipPath}`);
      resolve();
    });

    archive.on('error', (err) => {
      reject(err);
    });

    archive.pipe(output);
    archive.directory(DIST_DIR, false);
    archive.finalize();
  });
}

async function build() {
  console.log('🚀 开始构建 Chrome 扩展...\n');
  console.log('='.repeat(50));

  // 清理 dist 目录
  if (fs.existsSync(DIST_DIR)) {
    fs.rmSync(DIST_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(DIST_DIR, { recursive: true });

  // 压缩 JS 文件
  await minifyJS();

  // 复制静态文件
  copyStaticFiles();

  // 如果需要创建 ZIP
  const shouldZip = process.argv.includes('--zip');
  if (shouldZip) {
    await createZip();
  }

  console.log('='.repeat(50));
  console.log('🎉 构建完成!');
  console.log(`\n📁 输出目录: ${DIST_DIR}`);
  if (shouldZip) {
    const version = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8')).version;
    console.log(`📦 ZIP 文件: tiktok-shop-collector-v${version}.zip`);
  }
  console.log('\n💡 使用方法:');
  console.log('   1. 打开 chrome://extensions/');
  console.log('   2. 开启"开发者模式"');
  console.log('   3. 点击"加载已解压的扩展程序"');
  console.log(`   4. 选择 ${DIST_DIR} 目录`);
  console.log('\n   或者上传 ZIP 文件到 Chrome Web Store\n');
}

build().catch(console.error);
