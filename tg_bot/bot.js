const https = require("https");

/* ═══════ CONFIG ═══════ */
const BOT_TOKEN = process.env.BOT_TOKEN || "8672583953:AAFpMmJXruX917bygJqKJtVqa6bqNWsHBiA";
const API = `https://api.telegram.org/bot${BOT_TOKEN}`;

/* ═══════ TELEGRAM ═════ */
function tg(method, data) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(data);
    const req = https.request({
      hostname: "api.telegram.org",
      path: `/bot${BOT_TOKEN}/${method}`,
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
    }, res => {
      let d = ""; res.on("data", c => d += c);
      res.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    });
    req.on("error", reject); req.write(body); req.end();
  });
}
const send  = (id, text, extra={}) => tg("sendMessage",    { chat_id:id, text, parse_mode:"HTML", ...extra });
const edit  = (id, mid, text, extra={}) => tg("editMessageText", { chat_id:id, message_id:mid, text, parse_mode:"HTML", ...extra });
const answer= (id) => tg("answerCallbackQuery", { callback_query_id:id });

/* ═══════ HTTP GET ══════ */
function get(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers:{"User-Agent":"HedgeSigBot/1.0"} }, res => {
      let d = ""; res.on("data", c => d += c);
      res.on("end", () => { try { resolve(JSON.parse(d)); } catch { resolve({}); } });
    }).on("error", reject);
  });
}

/* ═══════ MARKET DATA ══ */
async function getPrices() {
  try {
    return await get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple,solana,binancecoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true");
  } catch { return {}; }
}
async function getFG() {
  try { const d = await get("https://api.alternative.me/fng/?limit=1"); return d.data?.[0] || {value:50,value_classification:"Neutral"}; }
  catch { return {value:50,value_classification:"Neutral"}; }
}

/* ═══════ CLAUDE API ═══ */
function claude(system, prompt, search=true) {
  return new Promise((resolve) => {
    const body = JSON.stringify({
      model: "claude-sonnet-4-20250514", max_tokens: 800, system,
      messages: [{ role:"user", content:prompt }],
      ...(search ? { tools:[{type:"web_search_20250305",name:"web_search"}] } : {}),
    });
    const req = https.request({
      hostname:"api.anthropic.com", path:"/v1/messages", method:"POST",
      headers:{"Content-Type":"application/json","Content-Length":Buffer.byteLength(body)},
    }, res => {
      let d = ""; res.on("data", c => d += c);
      res.on("end", () => {
        try {
          const j = JSON.parse(d);
          const txt = (j.content||[]).filter(c=>c.type==="text").map(c=>c.text).join("");
          try { resolve(JSON.parse(txt.replace(/```json|```/g,"").trim())); }
          catch { resolve({ raw: txt.slice(0,400) }); }
        } catch { resolve({raw:"error"}); }
      });
    });
    req.on("error", () => resolve({raw:"network error"}));
    req.write(body); req.end();
  });
}

/* ═══════ FORMATTERS ═══ */
const f$ = (n,d=2) => !n?"—": n>=1e9?`$${(n/1e9).toFixed(2)}B`: n>=1e6?`$${(n/1e6).toFixed(1)}M`:`$${n.toLocaleString("en",{minimumFractionDigits:d,maximumFractionDigits:d})}`;
const fp  = n => n==null?"—":`${n>=0?"+":""}${n.toFixed(2)}%`;
const fge = v => v>75?"🔴":v>55?"🟡":v>45?"⚪":v>25?"🟢":"💚";
const se  = s => s==="LONG"?"🟢":s==="SHORT"?"🔴":"🟡";
const sw  = s => s==="LONG"?"ЛОНГ ▲":s==="SHORT"?"ШОРТ ▼":"ЖДАТЬ ◆";

function pricesMsg(p, fg) {
  const coins = [
    ["₿","BTC","bitcoin"],["Ξ","ETH","ethereum"],
    ["✕","XRP","ripple"],["◎","SOL","solana"],["⬡","BNB","binancecoin"],
  ];
  let m = "📡 <b>HEDGE SIGNAL — РЫНОК</b>\n";
  m += `<code>${new Date().toLocaleString("ru",{timeZone:"Europe/Moscow"})} МСК</code>\n\n`;
  for(const [ico,sym,id] of coins){
    const d=p[id]; if(!d?.usd) continue;
    const ch=d.usd_24h_change, arr=ch>0?"▲":ch<0?"▼":"–";
    m+=`${ico} <b>${sym}</b>  <code>${f$(d.usd)}</code>  ${arr} <code>${fp(ch)}</code>\n`;
  }
  if(fg){
    const v=parseInt(fg.value);
    const bar="█".repeat(Math.round(v/10))+"░".repeat(10-Math.round(v/10));
    m+=`\n${fge(v)} <b>Fear &amp; Greed:</b> <code>${v} — ${fg.value_classification}</code>\n<code>${bar}</code>\n`;
  }
  return m;
}

/* ═══════ SIGNAL ENGINE ═ */
async function runSignal(chatId, msgId) {
  const SYS = "You are a crypto hedge fund quant analyst. Respond ONLY with valid JSON, no markdown.";
  const [prices, fg] = await Promise.all([getPrices(), getFG()]);
  const p = prices;
  const ctx = `BTC $${p.bitcoin?.usd?.toFixed(0)||"?"} (${p.bitcoin?.usd_24h_change?.toFixed(1)||"?"}% 24h), ETH $${p.ethereum?.usd?.toFixed(0)||"?"}, XRP $${p.ripple?.usd?.toFixed(4)||"?"}, SOL $${p.solana?.usd?.toFixed(1)||"?"}, F&G ${fg.value}(${fg.value_classification})`;

  const agents = [
    { id:"macro",   emoji:"🌍", label:"MACRO",
      q:`Search geopolitical events, wars, Fed/ECB decisions affecting crypto RIGHT NOW. Context:${ctx}
JSON:{"signal":"LONG|SHORT|HOLD","summary":"2 sentences","bullets":["...","...","..."],"risk":"HIGH|MEDIUM|LOW"}` },
    { id:"onchain", emoji:"🐋", label:"ON-CHAIN",
      q:`Search whale movements, exchange flows, institutional activity, ETF flows 24h. Context:${ctx}
JSON:{"signal":"LONG|SHORT|HOLD","summary":"2 sentences","bullets":["...","...","..."],"flow":"ACCUMULATION|DISTRIBUTION|NEUTRAL"}` },
    { id:"news",    emoji:"📰", label:"NEWS",
      q:`Search breaking crypto news right now: regulation, hacks, listings, sentiment. Context:${ctx}
JSON:{"signal":"LONG|SHORT|HOLD","summary":"2 sentences","bullets":["...","...","..."],"sentiment":"BULLISH|BEARISH|NEUTRAL"}` },
    { id:"quant",   emoji:"📊", label:"QUANT",
      q:`Search BTC/ETH technicals: RSI, funding rates, open interest, key levels. Context:${ctx}
JSON:{"signal":"LONG|SHORT|HOLD","summary":"2 sentences","trend":"BULLISH|BEARISH|SIDEWAYS","support":"$N","resistance":"$N","rsi":50}` },
  ];

  const res = {};
  for(const ag of agents){
    const status = agents.map(a =>
      res[a.id] ? `${se(res[a.id].signal)} ${a.label} ✓`
      : a.id===ag.id ? `🔄 ${a.label} анализирую...`
      : `⏳ ${a.label}`
    ).join("\n");
    await edit(chatId, msgId, `⚙️ <b>HEDGE SIGNAL ENGINE</b>\n\n${status}\n\n<i>AI + веб-поиск...</i>`);
    try { res[ag.id] = await claude(SYS, ag.q, true); }
    catch { res[ag.id] = {signal:"HOLD",summary:"Ошибка"}; }
  }

  await edit(chatId, msgId,
    `⚙️ <b>HEDGE SIGNAL ENGINE</b>\n\n✅ MACRO\n✅ ON-CHAIN\n✅ NEWS\n✅ QUANT\n🔄 СИНТЕЗ...\n\n<i>Формирую финальный сигнал...</i>`);

  const m=res.macro, o=res.onchain, n=res.news, q=res.quant;
  const fin = await claude(SYS,
    `CIO synthesizing all analysts into ONE final signal.
MACRO:${m?.signal||"?"} risk:${m?.risk||"?"}
ONCHAIN:${o?.signal||"?"} flow:${o?.flow||"?"}
NEWS:${n?.signal||"?"} sentiment:${n?.sentiment||"?"}
QUANT:${q?.signal||"?"} trend:${q?.trend||"?"} rsi:${q?.rsi||"?"} sup:${q?.support||"?"} res:${q?.resistance||"?"}
Market:${ctx}
JSON:{"signal":"LONG|SHORT|HOLD","confidence":0-100,"timeframe":"4H|1D|3D","thesis":"one-line thesis","summary":"3-4 sentence analysis","target":"$N","stop":"$N","risks":["risk1","risk2"]}`, false);

  const sig=fin?.signal||"HOLD", conf=fin?.confidence||50;
  const bar="█".repeat(Math.round(conf/10))+"░".repeat(10-Math.round(conf/10));

  let msg = `${se(sig)} <b>HEDGE FUND SIGNAL</b> ${se(sig)}\n`;
  msg += `<code>${new Date().toLocaleString("ru",{timeZone:"Europe/Moscow"})} МСК</code>\n\n`;
  msg += `━━━━━━━━━━━━━━━━━━\n`;
  msg += `📌 <b>СИГНАЛ:</b>  <code>${sw(sig)}</code>\n`;
  msg += `⏱ <b>Горизонт:</b> <code>${fin?.timeframe||"1D"}</code>\n`;
  msg += `🎯 <b>Уверенность:</b> <code>${conf}%  ${bar}</code>\n`;
  msg += `━━━━━━━━━━━━━━━━━━\n\n`;
  if(fin?.thesis) msg+=`💡 <i>"${fin.thesis}"</i>\n\n`;
  if(fin?.summary) msg+=`📋 ${fin.summary}\n\n`;
  msg+=`<b>Агенты:</b>\n`;
  msg+=`${se(m?.signal)} MACRO — ${m?.signal||"?"} | Риск: ${m?.risk||"?"}\n`;
  msg+=`${se(o?.signal)} ON-CHAIN — ${o?.signal||"?"} | ${o?.flow||"?"}\n`;
  msg+=`${se(n?.signal)} NEWS — ${n?.signal||"?"} | ${n?.sentiment||"?"}\n`;
  msg+=`${se(q?.signal)} QUANT — RSI:${q?.rsi||"?"} | ${q?.trend||"?"}\n\n`;
  if(fin?.target||fin?.stop){
    msg+=`<b>📍 Уровни BTC:</b>\n`;
    if(fin.target) msg+=`🟢 Цель: <code>${fin.target}</code>\n`;
    if(fin.stop)   msg+=`🔴 Стоп: <code>${fin.stop}</code>\n`;
    msg+="\n";
  }
  if(fin?.risks?.length){
    msg+=`⚠️ <b>Риски:</b>\n`;
    fin.risks.forEach(r => { msg+=`• ${r}\n`; });
    msg+="\n";
  }
  msg+=`━━━━━━━━━━━━━━━━━━\n`;
  msg+=`<i>⚠️ Не финансовый совет. DYOR.</i>`;
  await edit(chatId, msgId, msg);
}

/* ═══════ MENU ══════════ */
const MENU = {
  inline_keyboard:[
    [{text:"🎯 Signal Engine (LONG/SHORT/HOLD)", callback_data:"signal"}],
    [{text:"📊 Цены сейчас", callback_data:"prices"},{text:"🌍 Fear & Greed", callback_data:"fg"}],
    [{text:"📰 Новости BTC", callback_data:"news"},{text:"🐋 Активность китов", callback_data:"whale"}],
    [{text:"⏰ Авто-сигнал каждые 4ч", callback_data:"auto_toggle"}],
  ]
};

/* ═══════ STATE ══════════ */
const auto = {};

/* ═══════ HANDLER ════════ */
async function handle(upd) {
  try {
    const isCallback = !!upd.callback_query;
    const msg   = upd.message || upd.callback_query?.message;
    if(!msg) return;
    const chatId  = msg.chat.id;
    const text    = upd.message?.text || "";
    const cbData  = upd.callback_query?.data || "";
    const cmd     = text.split(" ")[0].toLowerCase();

    if(isCallback) await answer(upd.callback_query.id);

    // /start or menu button
    if(cmd==="/start"){
      await send(chatId,
        `📡 <b>HedgeΣSignal</b> — Crypto Fund Engine\n\n` +
        `Анализирую рынок как хедж-фонд:\n` +
        `• Геополитика и макро\n• Движения китов\n• Свежие новости\n• Технический анализ\n\n` +
        `Выберите действие:`, {reply_markup:MENU});
      return;
    }

    // Signal
    if(cmd==="/signal" || cbData==="signal"){
      const w = await send(chatId, "⚙️ <b>HEDGE SIGNAL ENGINE</b>\n\n⏳ Запускаю AI агентов...\n\n<i>~60 секунд</i>");
      await runSignal(chatId, w.result.message_id);
      return;
    }

    // Prices
    if(cmd==="/prices" || cbData==="prices"){
      const [p,fg] = await Promise.all([getPrices(), getFG()]);
      await send(chatId, pricesMsg(p, fg));
      return;
    }

    // Fear & Greed
    if(cbData==="fg"){
      const fg = await getFG();
      const v = parseInt(fg.value);
      const bar = "█".repeat(Math.round(v/10))+"░".repeat(10-Math.round(v/10));
      await send(chatId,
        `${fge(v)} <b>Fear &amp; Greed Index</b>\n\n` +
        `<b>Значение:</b> <code>${v}/100</code>\n` +
        `<b>Зона:</b> <code>${fg.value_classification}</code>\n\n` +
        `<code>${bar}</code>\n\n` +
        `${v>75?"🔴 Extreme Greed — рынок перегрет":v>55?"🟡 Greed — осторожно":v>45?"⚪ Neutral":v>25?"🟢 Fear — хорошая зона для покупок":"💚 Extreme Fear — исторически лучшее время"}`,
        {reply_markup:MENU});
      return;
    }

    // News
    if(cbData==="news"){
      const w = await send(chatId, "📰 Ищу свежие крипто-новости...");
      const r = await claude(
        "You are a crypto news analyst. Respond ONLY with valid JSON.",
        `Search the latest crypto news RIGHT NOW. JSON:{"headlines":["h1","h2","h3","h4","h5"],"sentiment":"BULLISH|BEARISH|NEUTRAL","breaking":"top breaking news","summary":"2-3 sentences"}`,
        true
      );
      let txt = "📰 <b>Крипто-новости</b>\n\n";
      if(r.breaking) txt+=`🔥 <b>Главное:</b> ${r.breaking}\n\n`;
      if(r.headlines?.length){ txt+="<b>Заголовки:</b>\n"; r.headlines.forEach((h,i)=>{ txt+=`${i+1}. ${h}\n`; }); txt+="\n"; }
      if(r.summary) txt+=`📋 ${r.summary}\n\n`;
      if(r.sentiment) txt+=`Настроение: ${r.sentiment==="BULLISH"?"🟢 БЫЧЬЕ":r.sentiment==="BEARISH"?"🔴 МЕДВЕЖЬЕ":"🟡 НЕЙТРАЛЬНОЕ"}`;
      await edit(chatId, w.result.message_id, txt);
      return;
    }

    // Whale
    if(cbData==="whale"){
      const w = await send(chatId, "🐋 Отслеживаю движения китов...");
      const r = await claude(
        "You are a crypto on-chain analyst. Respond ONLY with valid JSON.",
        `Search whale transactions, large BTC/ETH movements, exchange flows last 24h, institutional activity. JSON:{"transactions":["t1","t2","t3"],"net_flow":"ACCUMULATION|DISTRIBUTION|NEUTRAL","whale_sentiment":"BULLISH|BEARISH|NEUTRAL","summary":"2-3 sentences","key_alert":"top whale event"}`,
        true
      );
      let txt = "🐋 <b>Активность китов</b>\n\n";
      if(r.key_alert) txt+=`🚨 <b>Главное:</b> ${r.key_alert}\n\n`;
      if(r.transactions?.length){ txt+="<b>Крупные сделки:</b>\n"; r.transactions.forEach(t=>{ txt+=`• ${t}\n`; }); txt+="\n"; }
      if(r.summary) txt+=`📋 ${r.summary}\n\n`;
      if(r.net_flow) txt+=`Поток: ${r.net_flow==="ACCUMULATION"?"🟢 НАКОПЛЕНИЕ":r.net_flow==="DISTRIBUTION"?"🔴 РАСПРОДАЖА":"🟡 НЕЙТРАЛЬНЫЙ"}\n`;
      if(r.whale_sentiment) txt+=`Настроение китов: ${r.whale_sentiment==="BULLISH"?"🟢 БЫЧЬЕ":r.whale_sentiment==="BEARISH"?"🔴 МЕДВЕЖЬЕ":"🟡 НЕЙТРАЛЬНОЕ"}`;
      await edit(chatId, w.result.message_id, txt);
      return;
    }

    // Auto signal toggle
    if(cbData==="auto_toggle"){
      if(auto[chatId]){
        clearInterval(auto[chatId]);
        delete auto[chatId];
        await send(chatId, "⏹ Авто-сигнал <b>отключён</b>", {reply_markup:MENU});
      } else {
        auto[chatId] = setInterval(async()=>{
          const w = await send(chatId, "⚙️ <b>Авто-сигнал (4ч)</b>\n\n⏳ Запускаю...");
          await runSignal(chatId, w.result.message_id);
        }, 4*60*60*1000);
        await send(chatId, "✅ Авто-сигнал <b>включён</b> — каждые 4 часа\n\nНажмите снова чтобы выключить.", {reply_markup:MENU});
        // First signal immediately
        const w = await send(chatId, "⚙️ <b>Первый сигнал</b>\n\n⏳ Запускаю...");
        await runSignal(chatId, w.result.message_id);
      }
      return;
    }

    if(cmd==="/help"){
      await send(chatId,
        `📡 <b>HedgeΣSignal — Команды</b>\n\n/start — Меню\n/signal — Полный AI-сигнал\n/prices — Цены\n/help — Помощь`,
        {reply_markup:MENU});
    }

  } catch(e) { console.error("Handle error:", e.message); }
}

/* ═══════ POLLING ════════ */
let lastId = 0;
async function poll(){
  try {
    const d = await get(`${API}/getUpdates?offset=${lastId+1}&timeout=25&allowed_updates=["message","callback_query"]`);
    if(d.ok && d.result?.length){
      for(const u of d.result){ lastId=u.update_id; handle(u); }
    }
  } catch(e){ console.error("Poll:", e.message); }
  setTimeout(poll, 1000);
}

/* ═══════ START ══════════ */
(async()=>{
  const me = await get(`${API}/getMe`);
  console.log(`✅ @${me.result?.username} started`);
  await tg("setMyCommands",{ commands:[
    {command:"start",  description:"Главное меню"},
    {command:"signal", description:"🎯 AI-сигнал LONG/SHORT/HOLD"},
    {command:"prices", description:"📊 Текущие цены"},
    {command:"help",   description:"Помощь"},
  ]});
  poll();
})();
