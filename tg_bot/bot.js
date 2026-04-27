const https = require("https");

const BOT_TOKEN = "8672583953:AAFpMmJXruX917bygJqKJtVqa6bqNWsHBiA";
const API = `https://api.telegram.org/bot${BOT_TOKEN}`;

/* ── Telegram ── */
function tg(method, data) {
  return new Promise(resolve => {
    const body = JSON.stringify(data);
    const req = https.request({ hostname:"api.telegram.org", path:`/bot${BOT_TOKEN}/${method}`, method:"POST",
      headers:{"Content-Type":"application/json","Content-Length":Buffer.byteLength(body)} }, res => {
      let d=""; res.on("data",c=>d+=c); res.on("end",()=>{ try{resolve(JSON.parse(d));}catch{resolve({});} });
    });
    req.on("error",()=>resolve({})); req.write(body); req.end();
  });
}
const send  = (id,text,ex={}) => tg("sendMessage",{chat_id:id,text,parse_mode:"HTML",disable_web_page_preview:true,...ex});
const edit  = (id,mid,text,ex={}) => tg("editMessageText",{chat_id:id,message_id:mid,text,parse_mode:"HTML",disable_web_page_preview:true,...ex});
const answerCB = id => tg("answerCallbackQuery",{callback_query_id:id});

/* ── HTTP GET ── */
function get(url) {
  return new Promise(resolve => {
    https.get(url,{headers:{"User-Agent":"HedgeSigBot/2.0"}}, res => {
      let d=""; res.on("data",c=>d+=c);
      res.on("end",()=>{ try{resolve(JSON.parse(d));}catch{resolve({});} });
    }).on("error",()=>resolve({}));
  });
}

/* ── Market Data ── */
async function getPrices(ids="bitcoin,ethereum,ripple,solana,binancecoin,dogecoin,avalanche-2,chainlink,polkadot,cardano"){
  try{ return await get(`https://api.coingecko.com/api/v3/simple/price?ids=${ids}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true`); }
  catch{ return {}; }
}
async function getTopCoins(order="price_change_percentage_24h_desc",limit=8){
  try{ const d=await get(`https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=${order}&per_page=${limit}&page=1`); return Array.isArray(d)?d:[];}
  catch{ return []; }
}
async function getFG(){
  try{ const d=await get("https://api.alternative.me/fng/?limit=1"); return d.data?.[0]||{value:50,value_classification:"Neutral"}; }
  catch{ return {value:50,value_classification:"Neutral"}; }
}
async function getBinance(sym){ try{ const d=await get(`https://api.binance.com/api/v3/ticker/24hr?symbol=${sym}USDT`); return d.lastPrice?{price:+d.lastPrice,vol:+d.quoteVolume,change:+d.priceChangePercent}:null; }catch{return null;} }
async function getBybit(sym){ try{ const d=await get(`https://api.bybit.com/v5/market/tickers?category=spot&symbol=${sym}USDT`); const i=d.result?.list?.[0]; return i?{price:+i.lastPrice,vol:+i.turnover24h,change:+(+i.price24hPcnt*100).toFixed(2)}:null; }catch{return null;} }
async function getKraken(sym){ try{ const ks=sym==="BTC"?"XBTUSD":`${sym}USD`; const d=await get(`https://api.kraken.com/0/public/Ticker?pair=${ks}`); const k=Object.keys(d.result||{})[0]; return k?{price:+d.result[k].c[0],vol:+d.result[k].v[1]}:null; }catch{return null;} }

/* ── Claude API ── */
function claude(system,prompt,search=true){
  return new Promise(resolve=>{
    const body=JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:900,system,messages:[{role:"user",content:prompt}],
      ...(search?{tools:[{type:"web_search_20250305",name:"web_search"}]}:{})});
    const req=https.request({hostname:"api.anthropic.com",path:"/v1/messages",method:"POST",
      headers:{"Content-Type":"application/json","Content-Length":Buffer.byteLength(body)}}, res=>{
      let d=""; res.on("data",c=>d+=c);
      res.on("end",()=>{ try{ const j=JSON.parse(d); const txt=(j.content||[]).filter(c=>c.type==="text").map(c=>c.text).join(""); try{resolve(JSON.parse(txt.replace(/```json|```/g,"").trim()));}catch{resolve({raw:txt.slice(0,500)});} }catch{resolve({raw:"error"});} });
    });
    req.on("error",()=>resolve({raw:"network error"})); req.write(body); req.end();
  });
}

/* ── Formatters ── */
const f$=(n,d=2)=>!n&&n!==0?"—":n>=1e9?`$${(n/1e9).toFixed(2)}B`:n>=1e6?`$${(n/1e6).toFixed(1)}M`:`$${Number(n).toLocaleString("en",{minimumFractionDigits:d,maximumFractionDigits:d})}`;
const fp=n=>n==null?"—":`${n>=0?"+":""}${Number(n).toFixed(2)}%`;
const fge=v=>v>75?"🔴":v>55?"🟡":v>45?"⚪":v>25?"🟢":"💚";
const se=s=>s==="LONG"?"🟢":s==="SHORT"?"🔴":"🟡";
const sw=s=>s==="LONG"?"ЛОНГ ▲":s==="SHORT"?"ШОРТ ▼":"ЖДАТЬ ◆";
const ts=()=>new Date().toLocaleString("ru",{timeZone:"Europe/Moscow"})+" МСК";

/* ── Menu ── */
const MENU={inline_keyboard:[
  [{text:"🎯 Полный Signal Engine",  callback_data:"signal"}],
  [{text:"⚡ Быстрый сигнал",        callback_data:"quick"},{text:"📊 Цены",          callback_data:"prices"}],
  [{text:"📰 Новости",               callback_data:"news"}, {text:"🐋 Киты",          callback_data:"whale"}],
  [{text:"🚀 Топ растущих",          callback_data:"top_up"},{text:"📉 Топ падающих", callback_data:"top_down"}],
  [{text:"🪙 Альткоины",             callback_data:"alts"}, {text:"🌍 Fear & Greed",  callback_data:"fg"}],
  [{text:"🏦 Сравнение бирж",        callback_data:"exchanges"}],
  [{text:"💼 Мой портфель",          callback_data:"portfolio"},{text:"🔔 Алерт на цену",callback_data:"alert"}],
  [{text:"⏰ Авто-сигнал каждые 4ч", callback_data:"auto"}],
]};

/* ── State ── */
const autoTimers={}, portfolios={}, alertList={}, waitingFor={}, alertTmp={};

/* ── Alert Checker (every 5 min) ── */
async function checkAlerts(){
  const chats=Object.keys(alertList);
  if(!chats.length) return;
  const p=await getPrices("bitcoin,ethereum,ripple,solana,binancecoin");
  const map={BTC:p.bitcoin?.usd,ETH:p.ethereum?.usd,XRP:p.ripple?.usd,SOL:p.solana?.usd,BNB:p.binancecoin?.usd};
  for(const chatId of chats){
    const remaining=[];
    for(const al of alertList[chatId]||[]){
      const cur=map[al.sym];
      if(!cur){remaining.push(al);continue;}
      const hit=al.dir==="above"?cur>=al.targetPrice:cur<=al.targetPrice;
      if(hit){
        await send(+chatId,
          `${al.dir==="above"?"🚀":"📉"} <b>АЛЕРТ СРАБОТАЛ!</b>\n\n`+
          `<b>${al.sym}</b> достиг <code>${f$(cur)}</code>\n`+
          `Цель: <code>${f$(al.targetPrice)}</code>\n\n<code>${ts()}</code>`,{reply_markup:MENU});
      } else { remaining.push(al); }
    }
    alertList[chatId]=remaining;
  }
}

/* ── Full Signal Engine ── */
async function runSignal(chatId,msgId){
  const SYS="You are a crypto hedge fund quant analyst. Respond ONLY with valid JSON, no markdown.";
  const [p,fg]=await Promise.all([getPrices("bitcoin,ethereum,ripple,solana,binancecoin"),getFG()]);
  const ctx=`BTC $${p.bitcoin?.usd?.toFixed(0)||"?"} (${p.bitcoin?.usd_24h_change?.toFixed(1)||"?"}% 24h), ETH $${p.ethereum?.usd?.toFixed(0)||"?"}, XRP $${p.ripple?.usd?.toFixed(4)||"?"}, SOL $${p.solana?.usd?.toFixed(1)||"?"}, F&G ${fg.value}(${fg.value_classification})`;
  const agents=[
    {id:"macro",  label:"MACRO",    q:`Search active geopolitical events, wars, Fed/ECB/sanctions affecting crypto RIGHT NOW. Context:${ctx}\nJSON:{"signal":"LONG|SHORT|HOLD","summary":"2 sentences","bullets":["...","...","..."],"risk":"HIGH|MEDIUM|LOW"}`},
    {id:"onchain",label:"ON-CHAIN", q:`Search whale movements, exchange flows, ETF inflows, institutional buying/selling last 24h. Context:${ctx}\nJSON:{"signal":"LONG|SHORT|HOLD","summary":"2 sentences","bullets":["...","...","..."],"flow":"ACCUMULATION|DISTRIBUTION|NEUTRAL"}`},
    {id:"news",   label:"NEWS",     q:`Search breaking crypto news RIGHT NOW: regulation, hacks, listings, major events. Context:${ctx}\nJSON:{"signal":"LONG|SHORT|HOLD","summary":"2 sentences","bullets":["...","...","..."],"sentiment":"BULLISH|BEARISH|NEUTRAL"}`},
    {id:"quant",  label:"QUANT",    q:`Search BTC/ETH technicals: RSI, funding rates, open interest, key support/resistance levels. Context:${ctx}\nJSON:{"signal":"LONG|SHORT|HOLD","summary":"2 sentences","trend":"BULLISH|BEARISH|SIDEWAYS","support":"$N","resistance":"$N","rsi":50}`},
  ];
  const res={};
  for(const ag of agents){
    const status=agents.map(a=>res[a.id]?`${se(res[a.id].signal)} ${a.label} ✓`:a.id===ag.id?`🔄 ${a.label} анализирую...`:`⏳ ${a.label}`).join("\n");
    await edit(chatId,msgId,`⚙️ <b>HEDGE SIGNAL ENGINE</b>\n\n${status}\n\n<i>AI + веб-поиск в реальном времени...</i>`);
    try{res[ag.id]=await claude(SYS,ag.q,true);}catch{res[ag.id]={signal:"HOLD",summary:"Ошибка агента"};}
  }
  await edit(chatId,msgId,`⚙️ <b>HEDGE SIGNAL ENGINE</b>\n\n✅ MACRO\n✅ ON-CHAIN\n✅ NEWS\n✅ QUANT\n🔄 Синтезирую финальный сигнал...`);
  const m=res.macro,o=res.onchain,n=res.news,q=res.quant;
  const fin=await claude(SYS,
    `CIO synthesizing all analysts into ONE final trading signal.\nMACRO:${m?.signal||"?"} risk:${m?.risk||"?"}\nONCHAIN:${o?.signal||"?"} flow:${o?.flow||"?"}\nNEWS:${n?.signal||"?"} sentiment:${n?.sentiment||"?"}\nQUANT:${q?.signal||"?"} trend:${q?.trend||"?"} rsi:${q?.rsi||"?"} support:${q?.support||"?"} resistance:${q?.resistance||"?"}\nMarket:${ctx}\nJSON:{"signal":"LONG|SHORT|HOLD","confidence":0-100,"timeframe":"4H|1D|3D","thesis":"one-line thesis","summary":"3-4 sentence analysis","target":"$N","stop":"$N","risks":["risk1","risk2"]}`,false);
  const sig=fin?.signal||"HOLD",conf=fin?.confidence||50;
  const bar="█".repeat(Math.round(conf/10))+"░".repeat(10-Math.round(conf/10));
  let msg=`${se(sig)} <b>HEDGE FUND SIGNAL</b> ${se(sig)}\n<code>${ts()}</code>\n\n`;
  msg+=`━━━━━━━━━━━━━━━━━━━━\n`;
  msg+=`📌 <b>СИГНАЛ:</b>  <code>${sw(sig)}</code>\n`;
  msg+=`⏱ <b>Горизонт:</b> <code>${fin?.timeframe||"1D"}</code>\n`;
  msg+=`🎯 <b>Уверенность:</b> <code>${conf}%  ${bar}</code>\n`;
  msg+=`━━━━━━━━━━━━━━━━━━━━\n\n`;
  if(fin?.thesis) msg+=`💡 <i>"${fin.thesis}"</i>\n\n`;
  if(fin?.summary) msg+=`📋 ${fin.summary}\n\n`;
  msg+=`<b>Агенты:</b>\n`;
  msg+=`${se(m?.signal)} MACRO — ${m?.signal||"?"} | Риск: ${m?.risk||"?"}\n`;
  msg+=`${se(o?.signal)} ON-CHAIN — ${o?.signal||"?"} | ${o?.flow||"?"}\n`;
  msg+=`${se(n?.signal)} NEWS — ${n?.signal||"?"} | ${n?.sentiment||"?"}\n`;
  msg+=`${se(q?.signal)} QUANT — RSI:${q?.rsi||"?"} | ${q?.trend||"?"}\n\n`;
  if(fin?.target||fin?.stop){ msg+=`<b>📍 Уровни BTC:</b>\n`; if(fin.target) msg+=`🟢 Цель: <code>${fin.target}</code>\n`; if(fin.stop) msg+=`🔴 Стоп: <code>${fin.stop}</code>\n`; msg+="\n"; }
  if(fin?.risks?.length){ msg+=`⚠️ <b>Риски:</b>\n`; fin.risks.forEach(r=>{msg+=`• ${r}\n`;}); msg+="\n"; }
  msg+=`━━━━━━━━━━━━━━━━━━━━\n<i>⚠️ Не финансовый совет. DYOR.</i>`;
  await edit(chatId,msgId,msg,{reply_markup:MENU});
}

/* ── Quick Signal ── */
async function runQuick(chatId){
  const w=await send(chatId,"⚡ <b>Быстрый сигнал...</b>\n\n<i>~15 секунд</i>");
  const [p,fg]=await Promise.all([getPrices("bitcoin,ethereum,solana"),getFG()]);
  const ctx=`BTC $${p.bitcoin?.usd?.toFixed(0)||"?"} (${p.bitcoin?.usd_24h_change?.toFixed(1)||"?"}% 24h), ETH $${p.ethereum?.usd?.toFixed(0)||"?"}, SOL $${p.solana?.usd?.toFixed(1)||"?"}, F&G ${fg.value}(${fg.value_classification})`;
  const r=await claude("You are a crypto quant trader. Respond ONLY valid JSON.",
    `Search latest crypto news and quickly analyze market. Context:${ctx}\nJSON:{"signal":"LONG|SHORT|HOLD","confidence":0-100,"timeframe":"4H|1D","reason":"2-3 sentences","target":"$N","stop":"$N"}`,true);
  const sig=r?.signal||"HOLD",conf=r?.confidence||50;
  const bar="█".repeat(Math.round(conf/10))+"░".repeat(10-Math.round(conf/10));
  let msg=`⚡ <b>БЫСТРЫЙ СИГНАЛ</b>\n<code>${ts()}</code>\n\n`;
  msg+=`${se(sig)} <b>${sw(sig)}</b>  <code>${conf}% ${bar}</code>\n⏱ ${r?.timeframe||"1D"}\n\n`;
  if(r?.reason) msg+=`📋 ${r.reason}\n\n`;
  msg+=`<b>Рынок:</b>\n₿ BTC <code>${f$(p.bitcoin?.usd)}</code>  ${fp(p.bitcoin?.usd_24h_change)}\nΞ ETH <code>${f$(p.ethereum?.usd)}</code>  ${fp(p.ethereum?.usd_24h_change)}\n◎ SOL <code>${f$(p.solana?.usd)}</code>  ${fp(p.solana?.usd_24h_change)}\n`;
  if(r?.target||r?.stop){ msg+=`\n📍 <b>Уровни BTC:</b>\n`; if(r.target) msg+=`🟢 Цель: <code>${r.target}</code>\n`; if(r.stop) msg+=`🔴 Стоп: <code>${r.stop}</code>\n`; }
  msg+=`\n<i>⚠️ Не финансовый совет. DYOR.</i>`;
  await edit(chatId,w.result.message_id,msg,{reply_markup:MENU});
}

/* ── Prices ── */
async function showPrices(chatId){
  const [p,fg]=await Promise.all([getPrices("bitcoin,ethereum,ripple,solana,binancecoin"),getFG()]);
  const coins=[["₿","BTC","bitcoin"],["Ξ","ETH","ethereum"],["✕","XRP","ripple"],["◎","SOL","solana"],["⬡","BNB","binancecoin"]];
  let m=`📊 <b>ЦЕНЫ КРИПТО</b>\n<code>${ts()}</code>\n\n`;
  for(const [ico,sym,id] of coins){
    const d=p[id]; if(!d?.usd) continue;
    const ch=d.usd_24h_change, arr=ch>0?"▲":ch<0?"▼":"–";
    m+=`${ico} <b>${sym}</b>  <code>${f$(d.usd)}</code>  ${arr}<code>${fp(ch)}</code>\n`;
    if(d.usd_24h_vol) m+=`   Vol: <code>${f$(d.usd_24h_vol)}</code>\n`;
  }
  const v=parseInt(fg.value), bar="█".repeat(Math.round(v/10))+"░".repeat(10-Math.round(v/10));
  m+=`\n${fge(v)} F&G: <code>${v} — ${fg.value_classification}</code>\n<code>${bar}</code>`;
  await send(chatId,m,{reply_markup:MENU});
}

/* ── Top Movers ── */
async function showTop(chatId,dir){
  const order=dir==="up"?"price_change_percentage_24h_desc":"price_change_percentage_24h_asc";
  const w=await send(chatId,dir==="up"?"🚀 Ищу топ растущих...":"📉 Ищу топ падающих...");
  const coins=await getTopCoins(order,8);
  const emoji=dir==="up"?"🚀":"📉", title=dir==="up"?"ТОП РАСТУЩИХ 24Ч":"ТОП ПАДАЮЩИХ 24Ч";
  let m=`${emoji} <b>${title}</b>\n<code>${ts()}</code>\n\n`;
  if(!coins.length){ m+="Данные временно недоступны"; }
  else { for(const [i,c] of coins.entries()){ const ch=c.price_change_percentage_24h; m+=`${i+1}. <b>${c.symbol?.toUpperCase()}</b>  <code>${f$(c.current_price)}</code>  ${ch>0?"▲":"▼"}<code>${fp(ch)}</code>\n   Vol: <code>${f$(c.total_volume)}</code>\n`; } }
  await edit(chatId,w.result.message_id,m,{reply_markup:MENU});
}

/* ── Alts ── */
async function showAlts(chatId){
  const w=await send(chatId,"🪙 Загружаю альткоины...");
  const p=await getPrices("dogecoin,avalanche-2,chainlink,polkadot,cardano,uniswap,near");
  const alts=[["🐕","DOGE","dogecoin"],["🔺","AVAX","avalanche-2"],["⬡","LINK","chainlink"],["🟣","DOT","polkadot"],["♠","ADA","cardano"],["🦄","UNI","uniswap"],["🔮","NEAR","near"]];
  let m=`🪙 <b>АЛЬТКОИНЫ</b>\n<code>${ts()}</code>\n\n`;
  for(const [ico,sym,id] of alts){ const d=p[id]; if(!d?.usd) continue; const ch=d.usd_24h_change; m+=`${ico} <b>${sym}</b>  <code>${f$(d.usd)}</code>  ${ch>0?"▲":"▼"}<code>${fp(ch)}</code>\n`; }
  await edit(chatId,w.result.message_id,m,{reply_markup:MENU});
}

/* ── Exchanges ── */
async function showExchanges(chatId){
  const w=await send(chatId,"🏦 Сравниваю биржи...");
  let m=`🏦 <b>СРАВНЕНИЕ БИРЖ</b>\n<code>${ts()}</code>\n\n`;
  for(const sym of["BTC","ETH","SOL"]){
    const [bin,bbt,kra]=await Promise.all([getBinance(sym),getBybit(sym),getKraken(sym)]);
    m+=`<b>${sym}</b>\n`;
    const ps=[];
    if(bin){m+=`  Binance: <code>${f$(bin.price)}</code>  ${fp(bin.change)}\n`;ps.push(bin.price);}
    if(bbt){m+=`  Bybit:   <code>${f$(bbt.price)}</code>  ${fp(bbt.change)}\n`;ps.push(bbt.price);}
    if(kra){m+=`  Kraken:  <code>${f$(kra.price)}</code>\n`;ps.push(kra.price);}
    if(ps.length>1){ const sp=((Math.max(...ps)-Math.min(...ps))/Math.min(...ps)*100).toFixed(3); m+=`  ${parseFloat(sp)>0.05?"⚠️":"✅"} Спред: <code>${sp}%</code>\n`; }
    m+="\n";
  }
  await edit(chatId,w.result.message_id,m,{reply_markup:MENU});
}

/* ── News ── */
async function showNews(chatId){
  const w=await send(chatId,"📰 Ищу свежие новости...");
  const r=await claude("You are a crypto news analyst. Respond ONLY valid JSON.",
    `Search latest crypto news RIGHT NOW. JSON:{"headlines":["h1","h2","h3","h4","h5"],"sentiment":"BULLISH|BEARISH|NEUTRAL","breaking":"top breaking news","summary":"2-3 sentences"}`,true);
  let m=`📰 <b>КРИПТО-НОВОСТИ</b>\n<code>${ts()}</code>\n\n`;
  if(r.breaking) m+=`🔥 <b>Главное:</b> ${r.breaking}\n\n`;
  if(r.headlines?.length){ m+=`<b>Заголовки:</b>\n`; r.headlines.forEach((h,i)=>{m+=`${i+1}. ${h}\n`;}); m+="\n"; }
  if(r.summary) m+=`📋 ${r.summary}\n\n`;
  if(r.sentiment) m+=`Настроение: ${r.sentiment==="BULLISH"?"🟢 БЫЧЬЕ":r.sentiment==="BEARISH"?"🔴 МЕДВЕЖЬЕ":"🟡 НЕЙТРАЛЬНОЕ"}`;
  await edit(chatId,w.result.message_id,m,{reply_markup:MENU});
}

/* ── Whale ── */
async function showWhale(chatId){
  const w=await send(chatId,"🐋 Отслеживаю движения китов...");
  const r=await claude("You are a crypto on-chain analyst. Respond ONLY valid JSON.",
    `Search whale transactions, large BTC/ETH/SOL movements, exchange flows, institutional activity last 24h. JSON:{"transactions":["t1","t2","t3","t4"],"net_flow":"ACCUMULATION|DISTRIBUTION|NEUTRAL","whale_sentiment":"BULLISH|BEARISH|NEUTRAL","summary":"2-3 sentences","key_alert":"single most important whale event"}`,true);
  let m=`🐋 <b>ДВИЖЕНИЯ КИТОВ</b>\n<code>${ts()}</code>\n\n`;
  if(r.key_alert) m+=`🚨 <b>Главное:</b> ${r.key_alert}\n\n`;
  if(r.transactions?.length){ m+=`<b>Крупные сделки:</b>\n`; r.transactions.forEach(t=>{m+=`• ${t}\n`;}); m+="\n"; }
  if(r.summary) m+=`📋 ${r.summary}\n\n`;
  const fl=r.net_flow||"NEUTRAL"; m+=`Поток: ${fl==="ACCUMULATION"?"🟢 НАКОПЛЕНИЕ":fl==="DISTRIBUTION"?"🔴 РАСПРОДАЖА":"🟡 НЕЙТРАЛЬНЫЙ"}\n`;
  const ws=r.whale_sentiment||"NEUTRAL"; m+=`Настроение китов: ${ws==="BULLISH"?"🟢 БЫЧЬЕ":ws==="BEARISH"?"🔴 МЕДВЕЖЬЕ":"🟡 НЕЙТРАЛЬНОЕ"}`;
  await edit(chatId,w.result.message_id,m,{reply_markup:MENU});
}

/* ── Fear & Greed ── */
async function showFG(chatId){
  const fg=await getFG(); const v=parseInt(fg.value);
  const bar="█".repeat(Math.round(v/10))+"░".repeat(10-Math.round(v/10));
  let m=`${fge(v)} <b>Fear &amp; Greed Index</b>\n<code>${ts()}</code>\n\n`;
  m+=`<b>Значение:</b> <code>${v}/100</code>\n<b>Зона:</b> <code>${fg.value_classification}</code>\n\n<code>${bar}</code>\n\n`;
  m+=v>75?"🔴 <b>Extreme Greed</b> — рынок перегрет, риск коррекции":v>55?"🟡 <b>Greed</b> — осторожно, возможна коррекция":v>45?"⚪ <b>Neutral</b> — неопределённость":v>25?"🟢 <b>Fear</b> — хорошая зона для покупок":"💚 <b>Extreme Fear</b> — исторически лучшее время для входа";
  await send(chatId,m,{reply_markup:MENU});
}

/* ── Portfolio ── */
const SYM_MAP={BTC:"bitcoin",ETH:"ethereum",XRP:"ripple",SOL:"solana",BNB:"binancecoin",DOGE:"dogecoin",AVAX:"avalanche-2",LINK:"chainlink",DOT:"polkadot",ADA:"cardano"};

async function calcPortfolio(chatId,input){
  const w=await send(chatId,"💼 Считаю портфель...");
  const holdings=[];
  for(const part of input.toUpperCase().split(/[,\n]+/)){ const m=part.trim().match(/([A-Z]+)\s+([\d.]+)/); if(m&&SYM_MAP[m[1]]) holdings.push({sym:m[1],id:SYM_MAP[m[1]],amount:parseFloat(m[2])}); }
  if(!holdings.length){ await edit(chatId,w.result.message_id,"❌ Не могу распознать. Пример:\n<code>BTC 0.5, ETH 2, SOL 10</code>",{reply_markup:MENU}); return; }
  const p=await getPrices(holdings.map(h=>h.id).join(","));
  let total=0, m=`💼 <b>МОЙ ПОРТФЕЛЬ</b>\n<code>${ts()}</code>\n\n`;
  for(const h of holdings){ const d=p[h.id]; if(!d?.usd) continue; const val=d.usd*h.amount; total+=val; m+=`<b>${h.sym}</b> ×${h.amount}\n  ${f$(d.usd)} × ${h.amount} = <code>${f$(val)}</code>  ${fp(d.usd_24h_change)}\n\n`; }
  m+=`━━━━━━━━━━━━━━━━━━━━\n💰 <b>Итого: <code>${f$(total)}</code></b>`;
  portfolios[chatId]=input;
  await edit(chatId,w.result.message_id,m,{reply_markup:MENU});
}

/* ── Handler ── */
async function handle(upd){
  try{
    const isCallback=!!upd.callback_query;
    const msg=upd.message||upd.callback_query?.message;
    if(!msg) return;
    const chatId=msg.chat.id;
    const text=upd.message?.text||"";
    const cb=upd.callback_query?.data||"";
    const cmd=text.split(" ")[0].toLowerCase();
    if(isCallback) await answerCB(upd.callback_query.id);

    /* Waiting for text input */
    if(upd.message&&waitingFor[chatId]){
      const wf=waitingFor[chatId];
      if(wf==="portfolio"){ delete waitingFor[chatId]; await calcPortfolio(chatId,text); return; }
      if(wf==="alert_sym"){
        const sym=text.toUpperCase().trim();
        if(!SYM_MAP[sym]){ await send(chatId,`❌ Неизвестная монета. Введите: <code>BTC</code>, <code>ETH</code>, <code>SOL</code> и т.д.`); return; }
        alertTmp[chatId]={sym}; waitingFor[chatId]="alert_price";
        await send(chatId,`🔔 Монета: <b>${sym}</b>\n\nВведите целевую цену (просто число):\n<code>95000</code>`); return;
      }
      if(wf==="alert_price"){
        const price=parseFloat(text.replace(/[$,\s]/g,""));
        if(isNaN(price)||price<=0){ await send(chatId,"❌ Введите число, например: <code>95000</code>"); return; }
        const sym=alertTmp[chatId]?.sym; if(!sym){delete waitingFor[chatId];return;}
        const p=await getPrices(SYM_MAP[sym]); const cur=p[SYM_MAP[sym]]?.usd||0;
        const dir=price>cur?"above":"below";
        if(!alertList[chatId]) alertList[chatId]=[];
        alertList[chatId].push({sym,targetPrice:price,dir});
        delete waitingFor[chatId]; delete alertTmp[chatId];
        await send(chatId,
          `✅ <b>Алерт создан!</b>\n\n<b>${sym}</b> сейчас <code>${f$(cur)}</code>\nАлерт сработает когда цена ${dir==="above"?"поднимется выше ▲":"опустится ниже ▼"} <code>${f$(price)}</code>\n\nПроверяю каждые 5 минут.`,{reply_markup:MENU}); return;
      }
    }

    if(cmd==="/start"||cb==="menu"){ await send(chatId,`📡 <b>HedgeΣSignal Bot v2</b>\n\nCrypto Hedge Fund Signal Engine\n\n🎯 AI анализ: геополитика · киты · новости · техника\n⚡ Быстрые сигналы LONG/SHORT/HOLD\n🚀 Топ растущих и падающих монет\n🏦 Сравнение бирж\n💼 Трекер портфеля\n🔔 Алерты на цену\n\nВыберите действие:`,{reply_markup:MENU}); return; }
    if(cmd==="/signal"||cb==="signal"){ const w=await send(chatId,"⚙️ <b>HEDGE SIGNAL ENGINE</b>\n\n⏳ Запускаю AI агентов...\n\n<i>~60 секунд</i>"); await runSignal(chatId,w.result.message_id); return; }
    if(cb==="quick"||cmd==="/quick"){ await runQuick(chatId); return; }
    if(cb==="prices"||cmd==="/prices"){ await showPrices(chatId); return; }
    if(cb==="news"||cmd==="/news"){ await showNews(chatId); return; }
    if(cb==="whale"||cmd==="/whale"){ await showWhale(chatId); return; }
    if(cb==="fg"||cmd==="/fg"){ await showFG(chatId); return; }
    if(cb==="top_up"){ await showTop(chatId,"up"); return; }
    if(cb==="top_down"){ await showTop(chatId,"down"); return; }
    if(cb==="alts"||cmd==="/alts"){ await showAlts(chatId); return; }
    if(cb==="exchanges"||cmd==="/exchanges"){ await showExchanges(chatId); return; }
    if(cb==="portfolio"||cmd==="/portfolio"){
      if(portfolios[chatId]){ await calcPortfolio(chatId,portfolios[chatId]); }
      else{ waitingFor[chatId]="portfolio"; await send(chatId,`💼 <b>МОЙ ПОРТФЕЛЬ</b>\n\nВведите монеты и количество:\n<code>BTC 0.5, ETH 2, SOL 10, XRP 500</code>`); }
      return;
    }
    if(cb==="alert"||cmd==="/alert"){ waitingFor[chatId]="alert_sym"; await send(chatId,`🔔 <b>АЛЕРТ НА ЦЕНУ</b>\n\nВведите символ монеты:\n<code>BTC</code>`); return; }
    if(cb==="auto"){
      if(autoTimers[chatId]){ clearInterval(autoTimers[chatId]); delete autoTimers[chatId]; await send(chatId,"⏹ Авто-сигнал <b>отключён</b>",{reply_markup:MENU}); }
      else{
        autoTimers[chatId]=setInterval(async()=>{ const w=await send(chatId,"⚙️ <b>Авто-сигнал (4ч)</b>\n\n⏳ Запускаю..."); await runSignal(chatId,w.result.message_id); },4*60*60*1000);
        await send(chatId,"✅ Авто-сигнал <b>включён</b> — каждые 4 часа",{reply_markup:MENU});
        const w=await send(chatId,"⚙️ <b>Первый сигнал</b>\n\n⏳ Запускаю..."); await runSignal(chatId,w.result.message_id);
      }
      return;
    }
    if(cmd==="/help"){ await send(chatId,`📡 <b>Команды:</b>\n/start — Меню\n/signal — Полный сигнал\n/quick — Быстрый сигнал\n/prices — Цены\n/news — Новости\n/whale — Киты\n/alts — Альткоины\n/exchanges — Биржи\n/portfolio — Портфель\n/alert — Алерт\n/help — Помощь`,{reply_markup:MENU}); }
  }catch(e){ console.error("Handler error:",e.message); }
}

/* ── Polling ── */
let lastId=0;
async function poll(){
  try{
    const d=await get(`${API}/getUpdates?offset=${lastId+1}&timeout=25&allowed_updates=["message","callback_query"]`);
    if(d.ok&&d.result?.length){ for(const u of d.result){lastId=u.update_id;handle(u);} }
  }catch(e){ console.error("Poll:",e.message); }
  setTimeout(poll,1000);
}

/* ── Start ── */
(async()=>{
  const me=await get(`${API}/getMe`);
  console.log(`✅ @${me.result?.username} started — HedgeΣSignal v2`);
  await tg("setMyCommands",{commands:[
    {command:"start",     description:"Главное меню"},
    {command:"signal",    description:"🎯 Полный AI-сигнал (~60 сек)"},
    {command:"quick",     description:"⚡ Быстрый сигнал (~15 сек)"},
    {command:"prices",    description:"📊 Цены всех монет"},
    {command:"news",      description:"📰 Свежие новости"},
    {command:"whale",     description:"🐋 Движения китов"},
    {command:"alts",      description:"🪙 Альткоины"},
    {command:"exchanges", description:"🏦 Сравнение бирж"},
    {command:"portfolio", description:"💼 Трекер портфеля"},
    {command:"alert",     description:"🔔 Алерт на цену"},
    {command:"help",      description:"Список команд"},
  ]});
  setInterval(checkAlerts,5*60*1000);
  poll();
})();
