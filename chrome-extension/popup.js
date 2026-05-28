/**
 * 弹出页面逻辑
 * 负责显示用户状态、采集配额、手动同步登录等
 */

const loginStatusEl = document.getElementById('loginStatus');
const loginTextEl = document.getElementById('loginText');
const usernameEl = document.getElementById('username');
const pointsEl = document.getElementById('points');
const quotaTextEl = document.getElementById('quotaText');
const quotaBarEl = document.getElementById('quotaBar');
const remainingQuotaEl = document.getElementById('remainingQuota');
const syncButton = document.getElementById('syncButton');
const syncButtonText = document.getElementById('syncButtonText');
const messageEl = document.getElementById('message');
const alibaba1688Card = document.getElementById('alibaba1688Card');
const alibaba1688StatusEl = document.getElementById('alibaba1688Status');
const alibaba1688StatusTextEl = document.getElementById('alibaba1688StatusText');
const alibaba1688ProgressEl = document.getElementById('alibaba1688Progress');
const alibaba1688ProgressBarEl = document.getElementById('alibaba1688ProgressBar');

function showMessage(text, type = 'info') {
  messageEl.innerHTML = text;
  messageEl.className = `message ${type}`;
  setTimeout(() => { messageEl.className = 'message'; }, 5000);
}

function updateLoginStatus(isLoggedIn, user = null) {
  if (isLoggedIn && user) {
    loginStatusEl.className = 'status-badge success';
    loginTextEl.textContent = '已登录';
    usernameEl.textContent = user.display_name || user.username || user.phone || '-';
  } else {
    loginStatusEl.className = 'status-badge error';
    loginTextEl.textContent = '未登录';
    usernameEl.textContent = '-';
    pointsEl.textContent = '-';
  }
}

function updatePoints(points) {
  pointsEl.textContent = points != null ? points : '-';
}

function updateQuota(todayCount, dailyLimit) {
  const remaining = dailyLimit - todayCount;
  const percentage = (todayCount / dailyLimit) * 100;

  quotaTextEl.textContent = `${todayCount} / ${dailyLimit}`;
  remainingQuotaEl.textContent = remaining;
  quotaBarEl.style.width = `${Math.min(percentage, 100)}%`;

  if (percentage >= 90) {
    quotaBarEl.className = 'progress-fill error';
  } else if (percentage >= 70) {
    quotaBarEl.className = 'progress-fill warning';
  } else {
    quotaBarEl.className = 'progress-fill';
  }
}

function updateAlibaba1688Status(status, current, total) {
  if (!alibaba1688Card) return;

  alibaba1688Card.style.display = 'block';

  if (status === 'collecting') {
    alibaba1688StatusEl.className = 'status-badge warning';
    alibaba1688StatusTextEl.textContent = '采集中';
  } else if (status === 'completed') {
    alibaba1688StatusEl.className = 'status-badge success';
    alibaba1688StatusTextEl.textContent = '已完成';
  } else if (status === 'stopped') {
    alibaba1688StatusEl.className = 'status-badge error';
    alibaba1688StatusTextEl.textContent = '已停止';
  } else {
    alibaba1688StatusEl.className = 'status-badge';
    alibaba1688StatusTextEl.textContent = '未开始';
  }

  if (current != null && total != null) {
    alibaba1688ProgressEl.textContent = `${current} / ${total}`;
    const percentage = total > 0 ? (current / total) * 100 : 0;
    alibaba1688ProgressBarEl.style.width = `${Math.min(percentage, 100)}%`;
  }
}

function resetSyncButton() {
  syncButton.disabled = false;
  syncButtonText.textContent = '同步登录状态';
}

async function syncLoginStatus() {
  syncButton.disabled = true;
  syncButtonText.innerHTML = '<span class="loading"></span> 同步中...';

  chrome.runtime.sendMessage({ type: 'SYNC_AUTH' }, (response) => {
    if (chrome.runtime.lastError) {
      showMessage('同步失败: ' + chrome.runtime.lastError.message, 'error');
      resetSyncButton();
      return;
    }

    if (response && response.success) {
      showMessage('登录状态同步成功', 'success');
      loadStatus();
    } else {
      const errorMsg = response?.error?.message || '网页未登录，请先在 <a href="http://www.globalpicker.com" target="_blank" style="color:inherit;text-decoration:underline;">Global Picker</a> 平台登录';
      showMessage(errorMsg, 'error');
    }

    resetSyncButton();
  });
}

async function loadStatus() {
  chrome.runtime.sendMessage({ type: 'GET_STATUS' }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('获取状态失败:', chrome.runtime.lastError);
      return;
    }

    if (response && response.success) {
      const data = response.data;
      updateLoginStatus(data.isLoggedIn, data.user);
      if (data.isLoggedIn && data.user) {
        updatePoints(data.points);
      }
      updateQuota(data.todayCount, data.dailyLimit);
    }
  });
}

syncButton.addEventListener('click', syncLoginStatus);

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'UPDATE_1688_STATUS') {
    updateAlibaba1688Status(message.data.status, message.data.current, message.data.total);
  }
});

document.addEventListener('DOMContentLoaded', () => {
  loadStatus();
});
