// ===== 1688 请求拦截测试脚本 =====
// 在 air.1688.com 的 iframe 控制台中执行

(function() {
  'use strict';
  
  console.log('=== 1688 请求拦截器启动 ===');
  
  // 保存原始方法
  const originalFetch = window.fetch;
  const originalXHR = window.XMLHttpRequest;
  
  // 拦截 Fetch
  window.fetch = async function(...args) {
    const url = args[0];
    const urlString = typeof url === 'string' ? url : (url && url.url ? url.url : '');
    
    console.log('📡 [Fetch拦截] URL:', urlString.substring(0, 200));
    
    // 检查是否是1688插件列表请求
    if (urlString.includes('mtop.1688.pc.plugin.imagesearch.plugin.search')) {
      console.log('🎯 [命中] 拦截到1688插件列表请求!');
      console.log(' [完整URL]', urlString);
    }
    
    try {
      const response = await originalFetch.apply(this, args);
      
      // 如果是目标请求，打印响应数据
      if (urlString.includes('mtop.1688.pc.plugin.imagesearch.plugin.search')) {
        console.log('📦 [响应] 开始读取响应数据...');
        
        const clonedResponse = response.clone();
        clonedResponse.json().then(data => {
          console.log('✅ [响应数据] 成功解析JSON');
          console.log('📊 [数据结构]', JSON.stringify(data).substring(0, 1000));
          
          // 检查数据结构
          if (data && data.data) {
            console.log(' [data.data]', JSON.stringify(data.data).substring(0, 500));
            
            if (data.data.offerExtend) {
              const productCount = Object.keys(data.data.offerExtend).length;
              console.log('🎉 [商品数量]', productCount, '个商品');
              console.log('📋 [商品ID列表]', Object.keys(data.data.offerExtend));
            }
          }
        }).catch(e => {
          console.log('⚠️ [响应] 不是JSON格式:', e.message);
        });
      }
      
      return response;
    } catch (error) {
      console.error('❌ [Fetch错误]', error);
      throw error;
    }
  };
  
  console.log('✅ Fetch 拦截器已安装');
  
  // 拦截 XHR
  const origOpen = originalXHR.prototype.open;
  const origSend = originalXHR.prototype.send;
  
  originalXHR.prototype.open = function(method, url) {
    this._url = url;
    return origOpen.apply(this, arguments);
  };
  
  originalXHR.prototype.send = function() {
    const xhr = this;
    
    if (xhr._url && xhr._url.includes('mtop.1688.pc.plugin.imagesearch.plugin.search')) {
      console.log(' [XHR命中] 拦截到1688插件列表请求!');
      console.log('📋 [XHR URL]', xhr._url.substring(0, 200));
      
      const origOnReadyStateChange = xhr.onreadystatechange;
      
      xhr.onreadystatechange = function() {
        if (xhr.readyState === 4 && xhr.status === 200) {
          console.log('📦 [XHR响应] 状态200，开始解析...');
          
          try {
            const data = JSON.parse(xhr.responseText);
            console.log('✅ [XHR响应数据] 成功解析JSON');
            console.log('📊 [数据结构]', JSON.stringify(data).substring(0, 1000));
            
            if (data && data.data && data.data.offerExtend) {
              const productCount = Object.keys(data.data.offerExtend).length;
              console.log(' [商品数量]', productCount, '个商品');
            }
          } catch (e) {
            console.log('⚠️ [XHR响应] 解析失败:', e.message);
          }
        }
        
        if (origOnReadyStateChange) {
          origOnReadyStateChange.apply(xhr, arguments);
        }
      };
    }
    
    return origSend.apply(this, arguments);
  };
  
  console.log('✅ XHR 拦截器已安装');
  console.log('=== 拦截器就绪，等待1688插件加载商品列表 ===');
})();
