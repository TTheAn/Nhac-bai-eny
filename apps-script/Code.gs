/**
 * NHAC BAI - Apps Script dong vai "dong ho": moi ngay goi GitHub chay workflow.
 * Sua phan CONFIG ben duoi, bam Luu (Ctrl+S). Rieng HOUR/MINUTE: sua xong
 * phai chay lai ham setupTrigger 1 lan.
 */
const CONFIG = {
  GITHUB_OWNER: "TTheAn",      // ten tai khoan GitHub
  GITHUB_REPO: "Nhac-bai",     // ten repo
  WORKFLOW_FILE: "daily.yml",
  BRANCH: "main",

  HOUR: 7,          // gio nhac (0-23), gio Viet Nam
  MINUTE: 0,        // phut (Apps Script co the lech +-15 phut)
  COUNT: 3,         // so doan nhac moi ngay
  MAX_REPEAT: 1,    // so doan cu (da tung nhac) toi da moi ngay

  TIMEZONE: "Asia/Ho_Chi_Minh",
};

/** Chay 1 lan (va chay lai moi khi doi HOUR/MINUTE) de dat lich hang ngay. */
function setupTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "triggerWorkflow") ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger("triggerWorkflow")
    .timeBased()
    .everyDays(1)
    .atHour(CONFIG.HOUR)
    .nearMinute(CONFIG.MINUTE)
    .inTimezone(CONFIG.TIMEZONE)
    .create();
  Logger.log("Da dat lich: moi ngay khoang " + CONFIG.HOUR + ":" +
    ("0" + CONFIG.MINUTE).slice(-2) + " (" + CONFIG.TIMEZONE + ")");
}

/** Ham duoc lich goi moi ngay. Cung co the bam Run de chay thu ngay. */
function triggerWorkflow() {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty("GH_TOKEN");
  if (!token) throw new Error("Thieu Script Property GH_TOKEN");

  const url = "https://api.github.com/repos/" + CONFIG.GITHUB_OWNER + "/" +
    CONFIG.GITHUB_REPO + "/actions/workflows/" + CONFIG.WORKFLOW_FILE + "/dispatches";
  const options = {
    method: "post",
    contentType: "application/json",
    muteHttpExceptions: true,
    headers: {
      Authorization: "Bearer " + token,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    payload: JSON.stringify({
      ref: CONFIG.BRANCH,
      inputs: {
        count: String(CONFIG.COUNT),
        max_repeat: String(CONFIG.MAX_REPEAT),
      },
    }),
  };

  let last = "";
  for (let i = 1; i <= 3; i++) {
    try {
      const r = UrlFetchApp.fetch(url, options);
      if (r.getResponseCode() === 204) return; // thanh cong
      last = "GitHub " + r.getResponseCode() + ": " + r.getContentText().slice(0, 200);
    } catch (e) {
      last = String(e);
    }
    Utilities.sleep(5000 * i);
  }
  notifyZalo_("❌ Apps Script không kích hoạt được workflow nhắc bài: " + last);
  throw new Error(last);
}

function notifyZalo_(text) {
  try {
    const p = PropertiesService.getScriptProperties();
    const token = p.getProperty("ZALO_BOT_TOKEN");
    const chat = p.getProperty("ZALO_CHAT_ID");
    if (!token || !chat) return;
    UrlFetchApp.fetch("https://bot-api.zaloplatforms.com/bot" + token + "/sendMessage", {
      method: "post",
      contentType: "application/json",
      muteHttpExceptions: true,
      payload: JSON.stringify({ chat_id: chat, text: text }),
    });
  } catch (e) {}
}
