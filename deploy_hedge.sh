#!/bin/bash
set -e
GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  HEDGEΣSIGNAL — Crypto Fund Engine  ${NC}"
echo -e "${CYAN}══════════════════════════════════════${NC}"

# 1. Deps
echo -e "${CYAN}[1/5] Installing nginx + node...${NC}"
apt-get update -qq
apt-get install -y nginx curl nodejs npm 2>/dev/null | tail -2

# 2. App dir
mkdir -p /var/www/hedgesignal

# 3. Build React → static HTML using CDN (no build step needed)
echo -e "${CYAN}[2/5] Creating app...${NC}"

cat > /var/www/hedgesignal/index.html << 'HTML'
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#050508">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<title>HedgeΣSignal</title>
<link rel="manifest" href="/manifest.json">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=Syne:wght@700;800;900&display=swap');
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;background:#050508;overflow-x:hidden}
body{font-family:'IBM Plex Mono',monospace;color:#e2e8f0;max-width:480px;margin:0 auto}
button{font-family:'IBM Plex Mono',monospace}
button:active{transform:scale(0.97)}
::-webkit-scrollbar{width:2px}
::-webkit-scrollbar-thumb{background:#1a1a2e}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@keyframes glitch{0%,100%{transform:none}92%{transform:skewX(-1deg)}94%{transform:skewX(1deg)}96%{transform:none}}
/* CRT scanlines */
body::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:999;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.04) 2px,rgba(0,0,0,.04) 4px)}
/* Layout */
header{background:#030305;border-bottom:1px solid #1a1a2e;padding:12px 14px;position:sticky;top:0;z-index:50}
.hdr{display:flex;align-items:center;justify-content:space-between}
.brand{font-family:'Syne',sans-serif;font-size:17px;font-weight:900;color:#00ff88;letter-spacing:2px;animation:glitch 8s infinite}
.brand-sub{font-size:8px;color:#1a1a2e;letter-spacing:3px;margin-top:2px}
.hdr-r{text-align:right}
.live-row{display:flex;align-items:center;gap:6px;justify-content:flex-end}
.live-dot{width:5px;height:5px;border-radius:50%;animation:pulse 1.5s infinite}
.live-txt{font-size:9px;color:#2d3748;letter-spacing:1px}
.btn-ref{background:none;border:1px solid #1a1a2e;border-radius:2px;color:#4a5568;font-size:10px;padding:2px 7px;cursor:pointer}
.upd-txt{font-size:8px;color:#1a1a2e;margin-top:3px}
/* Ticker */
.ticker{overflow:hidden;background:#030305;border-bottom:1px solid #0f0f1a;padding:5px 0;white-space:nowrap}
.ticker-inner{display:inline-block;animation:marquee 40s linear infinite;font-size:10px;color:#2d3748;letter-spacing:0.5px}
/* Tabs */
.tabs{display:flex;background:#030305;border-bottom:1px solid #1a1a2e;position:sticky;top:65px;z-index:40}
.tab{flex:1;padding:9px 0;background:none;border:none;border-bottom:2px solid transparent;
  color:#2d3748;font-size:11px;font-weight:700;cursor:pointer;letter-spacing:2px;transition:all .15s}
.tab.active{color:#00ff88;border-bottom-color:#00ff88}
/* Content */
.content{padding:14px;padding-bottom:80px}
/* Cards */
.card{border:1px solid #1a1a2e;border-radius:4px;background:#080810;overflow:hidden;margin-bottom:12px}
.card-hdr{padding:8px 12px;background:#080810;border-bottom:1px solid #1a1a2e;
  display:flex;justify-content:space-between;align-items:center}
.card-lbl{font-size:9px;color:#2d3748;letter-spacing:2px}
/* Asset list */
.asset-row{display:flex;align-items:center;padding:10px 14px;gap:12px;
  border-bottom:1px solid #0a0a12;cursor:pointer;transition:all .15s;
  border-left:2px solid transparent}
.asset-row.sel{background:#050510}
.asset-sym{font-size:13px;font-weight:700;width:36px}
.asset-price{font-size:14px;color:#e2e8f0;flex:1}
.asset-chg{font-size:12px;font-weight:700;font-family:'IBM Plex Mono',monospace}
.asset-vol{font-size:10px;color:#2d3748;margin-top:1px;text-align:right}
.chevron{font-size:12px;color:#2d3748;transition:transform .2s}
/* Exchange sub-rows */
.exc-body{padding:0 14px 12px;border-top:1px solid #0f0f1a;animation:fadeIn .3s ease}
.exc-sublbl{font-size:9px;color:#2d3748;letter-spacing:2px;margin:10px 0 8px}
.exc-row{display:flex;align-items:center;margin-bottom:5px;gap:8px}
.exc-nm{font-size:10px;color:#4a5568;width:56px}
.exc-bar{flex:1;height:1px;background:#1a1a2e}
.exc-pr{font-size:11px;color:#a0aec0;width:92px;text-align:right}
.exc-v{font-size:9px;color:#2d3748;width:55px;text-align:right}
.spread-badge{margin-top:8px;font-size:10px;font-family:'IBM Plex Mono',monospace}
/* FG */
.fg-wrap{display:flex;align-items:center;gap:12px;padding:12px 14px}
.fg-num{font-size:22px;font-weight:700}
.fg-lbl{font-size:11px;margin-top:2px}
.fg-bars{display:flex;gap:3px;margin-top:6px}
.fg-b{width:8px;border-radius:1px}
/* Signal btn */
.btn-signal{width:100%;margin-top:14px;border-radius:3px;padding:14px;
  font-size:12px;font-weight:700;cursor:pointer;letter-spacing:2px;
  display:flex;align-items:center;justify-content:center;gap:8px;transition:all .2s}
.btn-signal.ready{border:1px solid #00ff88;background:#00ff8808;color:#00ff88;box-shadow:0 0 20px #00ff8815}
.btn-signal.busy{border:1px solid #1a1a2e;background:#080810;color:#2d3748;cursor:not-allowed}
.hint{text-align:center;font-size:9px;color:#1a1a2e;margin-top:6px;letter-spacing:1px}
/* Agents */
.agent-card{border:1px solid #1a1a2e;border-radius:4px;background:#080810;transition:border-color .3s;margin-bottom:8px;animation:fadeIn .4s ease}
.agent-row{display:flex;align-items:center;gap:10px;padding:11px 13px;cursor:pointer}
.a-ico{font-size:16px;flex-shrink:0}
.a-nm{font-size:11px;font-weight:700;letter-spacing:1px}
.a-desc{font-size:10px;color:#2d3748;margin-top:1px}
.sig-badge{border-radius:2px;padding:2px 8px;font-size:10px;font-weight:700;border:1px solid}
.dots{display:flex;gap:3px}
.dot{width:4px;height:4px;border-radius:50%;animation:pulse 1.2s infinite}
.agent-body{border-top:1px solid;padding:12px 13px;animation:fadeIn .3s ease}
.a-sum{font-size:11px;color:#718096;line-height:1.7;margin-bottom:10px}
.bullet{display:flex;gap:7px;margin-bottom:5px}
.b-dot{font-size:10px;margin-top:2px;flex-shrink:0}
.b-txt{font-size:11px;color:#a0aec0;line-height:1.6}
/* Final signal */
.final-card{border-radius:4px;padding:16px;margin-top:12px;animation:fadeIn .5s ease;
  background:linear-gradient(135deg,#080810,transparent)}
.f-header{font-size:9px;letter-spacing:3px;margin-bottom:14px}
.f-inner{display:flex;align-items:center;gap:14px}
.f-ring{position:relative;width:88px;height:88px;flex-shrink:0}
.f-ring svg{transform:rotate(-90deg);position:absolute}
.f-ring-info{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.f-conf{font-size:11px;font-weight:700}
.f-tag{font-size:9px;color:#475569;letter-spacing:2px;margin-bottom:4px}
.f-sig{font-family:'Syne',sans-serif;font-size:32px;font-weight:900;letter-spacing:2px;line-height:1}
.f-tf{font-size:10px;color:#4a5568;margin-top:4px}
.f-sum{font-size:11px;color:#718096;line-height:1.7;margin-top:14px;padding-top:12px}
.f-levels{display:flex;gap:8px;margin-top:12px}
.f-level{flex:1;border-radius:3px;padding:7px 9px;text-align:center}
.f-lvl-lbl{font-size:9px;color:#4a5568;margin-bottom:3px}
.f-lvl-val{font-size:12px;font-weight:700}
.f-risks{margin-top:10px;padding:8px 10px;border-radius:3px}
.f-rlbl{font-size:9px;letter-spacing:2px;margin-bottom:5px}
.f-ri{font-size:10px;line-height:1.6}
.f-disc{font-size:9px;color:#1a1a2e;margin-top:10px;text-align:center}
/* Flow bars */
.flow-row{padding:9px 12px;border-bottom:1px solid #0a0a12;display:flex;align-items:center;gap:10px}
.flow-ex{font-size:10px;color:#4a5568;width:52px}
.flow-bar{flex:1;height:2px;background:#0f0f1a;border-radius:1px;overflow:hidden}
.flow-fill{height:100%;border-radius:1px;transition:width .6s ease}
.flow-pr{font-size:11px;color:#e2e8f0;width:90px;text-align:right}
.flow-v{font-size:9px;color:#2d3748;width:58px;text-align:right}
/* Empty */
.empty{text-align:center;padding:50px 20px}
.empty-ico{font-size:36px;color:#1a1a2e;font-family:'Syne',sans-serif;font-weight:900;margin-bottom:8px}
.empty-txt{font-size:10px;color:#2d3748;letter-spacing:2px}
.btn-back{margin-top:16px;background:none;border:1px solid #1a1a2e;border-radius:2px;
  padding:8px 16px;color:#4a5568;font-size:10px;cursor:pointer;letter-spacing:1px}
.btn-rerun{width:100%;margin-top:12px;background:none;border:1px solid #1a1a2e;
  border-radius:3px;padding:11px;color:#4a5568;font-size:10px;cursor:pointer;letter-spacing:2px}
.hidden{display:none!important}
.spn{border-radius:50%;border-style:solid;animation:spin .8s linear infinite;flex-shrink:0}
</style>
</head>
<body>
<header>
  <div class="hdr">
    <div>
      <div class="brand">HEDGE<span style="color:#ff3366">Σ</span>SIGNAL</div>
      <div class="brand-sub">CRYPTO FUND ENGINE v2.0</div>
    </div>
    <div class="hdr-r">
      <div class="live-row">
        <div class="live-dot" id="ldot" style="background:#10b981"></div>
        <span class="live-txt">LIVE</span>
        <button class="btn-ref" onclick="loadMarket()">↻</button>
      </div>
      <div class="upd-txt" id="upd"></div>
    </div>
  </div>
</header>

<div class="ticker"><div class="ticker-inner" id="ticker">Loading market data...</div></div>

<div class="tabs">
  <button class="tab active" id="tab-market" onclick="sw('market')">MKT</button>
  <button class="tab" id="tab-signal" onclick="sw('signal')">SIG</button>
  <button class="tab" id="tab-flow" onclick="sw('flow')">FLOW</button>
</div>

<div class="content">

  <!-- MKT -->
  <div id="pane-market">
    <!-- F&G -->
    <div class="card" id="fg-card">
      <div class="card-hdr"><span class="card-lbl">FEAR &amp; GREED INDEX</span><span id="fg-age" class="card-lbl"></span></div>
      <div class="fg-wrap">
        <div style="position:relative;width:64px;height:64px;flex-shrink:0">
          <svg width="64" height="64" style="transform:rotate(-90deg);position:absolute">
            <circle cx="32" cy="32" r="28" fill="none" stroke="#1a1a2e" stroke-width="5"/>
            <circle id="fg-arc" cx="32" cy="32" r="28" fill="none" stroke="#ffaa00" stroke-width="5"
              stroke-dasharray="0 175.9" stroke-linecap="round"
              style="transition:stroke-dasharray 1s ease"/>
          </svg>
          <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center">
            <span id="fg-num" class="fg-num" style="color:#ffaa00">—</span>
          </div>
        </div>
        <div>
          <div id="fg-lbl" class="fg-lbl" style="color:#ffaa00">LOADING...</div>
          <div class="fg-bars" id="fg-bars"></div>
          <div style="font-size:9px;color:#1a1a2e;margin-top:3px;letter-spacing:1px">7-DAY</div>
        </div>
      </div>
    </div>
    <!-- Assets -->
    <div class="card">
      <div class="card-hdr"><span class="card-lbl">ASSET</span><span class="card-lbl">PRICE · 24H · VOL</span></div>
      <div id="asset-list"></div>
    </div>
    <button class="btn-signal ready" id="bgo" onclick="runSignal()">▲ RUN SIGNAL ENGINE</button>
    <div class="hint">MACRO · ON-CHAIN · NEWS · QUANT · AI SYNTHESIS</div>
  </div>

  <!-- SIGNAL -->
  <div id="pane-signal" class="hidden">
    <div id="sig-empty" class="empty">
      <div class="empty-ico">NO SIGNAL</div>
      <div class="empty-txt">RUN ENGINE TO GENERATE</div>
      <button class="btn-back" onclick="sw('market')">← MARKET</button>
    </div>
    <div id="sig-run" class="hidden">
      <div class="card-lbl" id="sig-status" style="margin-bottom:12px;color:#00ff88">◉ PROCESSING</div>
      <div id="agent-list"></div>
      <div id="final-wrap"></div>
      <button class="btn-rerun hidden" id="btn-rerun" onclick="runSignal()">↻ REFRESH SIGNAL</button>
    </div>
  </div>

  <!-- FLOW -->
  <div id="pane-flow" class="hidden">
    <div class="card-lbl" style="margin-bottom:12px">EXCHANGE FLOW MONITOR</div>
    <div id="flow-btc" class="card">
      <div class="card-hdr"><span class="card-lbl" style="color:#f7931a">BTC</span><span id="btc-spread" class="card-lbl"></span></div>
      <div id="flow-btc-rows"></div>
    </div>
    <div id="flow-eth" class="card">
      <div class="card-hdr"><span class="card-lbl" style="color:#7b8cde">ETH</span><span id="eth-spread" class="card-lbl"></span></div>
      <div id="flow-eth-rows"></div>
    </div>
    <div class="card" id="fg-hist-card">
      <div class="card-hdr"><span class="card-lbl">FEAR &amp; GREED HISTORY</span></div>
      <div id="fg-hist"></div>
    </div>
  </div>

</div>

<script>
/* ══ STATE ══ */
const ASSETS=[
  {sym:"BTC",id:"bitcoin",   color:"#f7931a"},
  {sym:"ETH",id:"ethereum",  color:"#7b8cde"},
  {sym:"XRP",id:"ripple",    color:"#00b4d8"},
  {sym:"SOL",id:"solana",    color:"#9945ff"},
  {sym:"BNB",id:"binancecoin",color:"#f3ba2f"},
  {sym:"XAU",id:"gold",      color:"#ffd700"},
];
const AGENTS=[
  {id:"macro",  label:"MACRO",    icon:"◈",color:"#ff6b6b",desc:"Геополитика · ФРС · ЦБ"},
  {id:"onchain",label:"ON-CHAIN", icon:"⬡",color:"#ffd166",desc:"Whale · Flow · Institutions"},
  {id:"news",   label:"NEWS",     icon:"◉",color:"#06d6a0",desc:"Новости · Инсайды · Sentiment"},
  {id:"quant",  label:"QUANT",    icon:"◆",color:"#118ab2",desc:"RSI · OI · Funding · Volume"},
  {id:"signal", label:"SIGNAL",   icon:"▲",color:"#00ff88",desc:"Финальный торговый сигнал"},
];
let prices={},excData={},fgData=[],running=false,aResults={};

/* ══ UTILS ══ */
function f$(n,d=2){if(n==null)return"—";if(n>=1e9)return"$"+(n/1e9).toFixed(2)+"B";if(n>=1e6)return"$"+(n/1e6).toFixed(1)+"M";return"$"+n.toLocaleString("en",{minimumFractionDigits:d,maximumFractionDigits:d})}
function pct(n){return n==null?"—":(n>=0?"+":"")+n.toFixed(2)+"%"}
function pc(n){return n>0?"#00ff88":n<0?"#ff3366":"#4a5568"}
function sc(s){return s==="LONG"?"#00ff88":s==="SHORT"?"#ff3366":"#ffaa00"}
function sb(s){return s==="LONG"?"#00ff8815":s==="SHORT"?"#ff336615":"#ffaa0015"}
function spn(c="#00ff88",s=14){return`<div class="spn" style="width:${s}px;height:${s}px;border-width:2px;border-color:${c}30;border-top-color:${c}"></div>`}

/* ══ TAB ══ */
function sw(t){
  ["market","signal","flow"].forEach(x=>{
    document.getElementById("pane-"+x).classList.toggle("hidden",x!==t);
    document.getElementById("tab-"+x).classList.toggle("active",x===t);
  });
}

/* ══ MARKET DATA ══ */
async function loadMarket(){
  document.getElementById("ldot").style.background="#ffaa00";
  await Promise.all([loadPrices(),loadFG(),loadExchanges()]);
  document.getElementById("ldot").style.background="#00ff88";
  document.getElementById("upd").textContent=new Date().toLocaleTimeString("ru");
}

async function loadPrices(){
  try{
    const r=await fetch("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple,solana,binancecoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true");
    prices=await r.json();
  }catch{}
  renderAssets();
  renderTicker();
}

async function loadFG(){
  try{
    const r=await fetch("https://api.alternative.me/fng/?limit=7");
    const d=await r.json();
    fgData=d.data||[];
  }catch{}
  renderFG();
}

async function loadExchanges(){
  const [b,e]=await Promise.all([getExc("BTC"),getExc("ETH")]);
  excData={BTC:b,ETH:e};
  renderAssets();
  renderFlow();
}

async function getExc(sym){
  const out={};
  try{const r=await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${sym}USDT`);const d=await r.json();if(d.lastPrice)out.Binance={p:+d.lastPrice,v:+d.quoteVolume,ch:+d.priceChangePercent};}catch{}
  try{const r=await fetch(`https://api.bybit.com/v5/market/tickers?category=spot&symbol=${sym}USDT`);const d=await r.json();const i=d.result?.list?.[0];if(i?.lastPrice)out.Bybit={p:+i.lastPrice,v:+i.turnover24h,ch:+i.price24hPcnt*100};}catch{}
  try{const ks=sym==="BTC"?"XBTUSD":`${sym}USD`;const r=await fetch(`https://api.kraken.com/0/public/Ticker?pair=${ks}`);const d=await r.json();const k=Object.keys(d.result||{})[0];if(k)out.Kraken={p:+d.result[k].c[0],v:+d.result[k].v[1]};}catch{}
  return out;
}

/* ══ RENDERS ══ */
function renderTicker(){
  const items=ASSETS.filter(a=>prices[a.id]?.usd).map(a=>{
    const p=prices[a.id];
    const ch=p.usd_24h_change;
    return`${a.sym} ${f$(p.usd)} ${ch!=null?(ch>=0?"+":"")+ch.toFixed(2)+"%":""}`;
  }).join("  ·  ")+"  ·  ";
  const t=document.getElementById("ticker");
  t.textContent=items.repeat(4);
}

function renderFG(){
  if(!fgData.length)return;
  const cur=fgData[0];
  const v=parseInt(cur.value);
  const color=v>75?"#ff3366":v>55?"#ffaa00":v>45?"#e2e8f0":"#00ff88";
  const CIRC=2*Math.PI*28;
  document.getElementById("fg-num").textContent=v;
  document.getElementById("fg-num").style.color=color;
  document.getElementById("fg-lbl").textContent=cur.value_classification?.toUpperCase();
  document.getElementById("fg-lbl").style.color=color;
  setTimeout(()=>{
    document.getElementById("fg-arc").style.stroke=color;
    document.getElementById("fg-arc").style.strokeDasharray=`${(v/100)*CIRC} ${CIRC}`;
  },100);
  // 7-day bars
  const bars=document.getElementById("fg-bars");
  bars.innerHTML=fgData.slice(0,7).map(d=>{
    const dv=parseInt(d.value);
    const dc=dv>55?"#ff3366":dv>45?"#ffaa00":"#00ff88";
    return`<div class="fg-b" style="height:${12+dv/10}px;background:${dc}60;border-bottom:2px solid ${dc}"></div>`;
  }).join("");
}

let openAsset=null;
function renderAssets(){
  const list=document.getElementById("asset-list");
  list.innerHTML=ASSETS.map(a=>{
    const d=a.id==="gold"?null:prices[a.id];
    const exc=excData[a.sym]||{};
    const excArr=Object.values(exc);
    const ps=excArr.map(e=>e.p).filter(Boolean);
    const spread=ps.length>1?((Math.max(...ps)-Math.min(...ps))/Math.min(...ps)*100).toFixed(3):null;
    const minP=ps.length?Math.min(...ps):0;
    const maxP=ps.length?Math.max(...ps):1;
    const isOpen=openAsset===a.sym;
    const ch=d?.usd_24h_change;
    const excHtml=Object.keys(exc).length?`
      <div class="exc-body" style="border-top-color:${a.color}20${isOpen?""};display:${isOpen?"block":"none"}" id="exc-${a.sym}">
        <div class="exc-sublbl">EXCHANGE PRICES</div>
        ${Object.entries(exc).map(([ex,ed])=>`
          <div class="exc-row">
            <span class="exc-nm">${ex}</span>
            <div class="exc-bar" style="position:relative">
              <div style="height:100%;width:${ps.length>1?Math.min(100,((ed.p-minP)/(maxP-minP))*100):50}%;background:${a.color};transition:width .6s ease"></div>
            </div>
            <span class="exc-pr">${f$(ed.p)}</span>
            ${ed.v?`<span class="exc-v">${f$(ed.v)}</span>`:""}
          </div>`).join("")}
        ${spread?`<div class="spread-badge" style="color:${parseFloat(spread)>0.1?"#ffaa00":"#2d3748"}">
          ${parseFloat(spread)>0.1?"⚠ ":""}SPREAD: ${spread}%
        </div>`:""}
      </div>`:"";
    return`<div class="asset-row${openAsset===a.sym?" sel":""}" style="border-left-color:${openAsset===a.sym?a.color:"transparent"}" onclick="toggleAsset('${a.sym}','${a.color}')">
      <span class="asset-sym" style="color:${a.color}">${a.sym}</span>
      <div style="flex:1">
        ${d?.usd?`<div class="asset-price">${f$(d.usd)}</div>`:spn(a.color,14)}
      </div>
      <div style="text-align:right">
        ${ch!=null?`<div class="asset-chg" style="color:${pc(ch)}">${pct(ch)}</div>`:""}
        ${d?.usd_24h_vol?`<div class="asset-vol">${f$(d.usd_24h_vol)}</div>`:""}
      </div>
      <div class="chevron" style="transform:${isOpen?"rotate(180deg)":"none"}">▾</div>
    </div>${excHtml}`;
  }).join("");
}

function toggleAsset(sym,color){
  openAsset=openAsset===sym?null:sym;
  renderAssets();
}

function renderFlow(){
  ["BTC","ETH"].forEach(sym=>{
    const exc=excData[sym]||{};
    const arr=Object.entries(exc);
    const ps=arr.map(([,d])=>d.p).filter(Boolean);
    const minP=ps.length?Math.min(...ps):0,maxP=ps.length?Math.max(...ps):1;
    const spread=ps.length>1?((maxP-minP)/minP*100).toFixed(3):"0";
    const color=sym==="BTC"?"#f7931a":"#7b8cde";
    document.getElementById(`${sym.toLowerCase()}-spread`).textContent=
      `${parseFloat(spread)>0.1?"⚠ ":""}SPREAD ${spread}%`;
    document.getElementById(`${sym.toLowerCase()}-spread`).style.color=
      parseFloat(spread)>0.1?"#ffaa00":"#2d3748";
    const rows=document.getElementById(`flow-${sym.toLowerCase()}-rows`);
    if(!arr.length){rows.innerHTML=`<div style="padding:14px;text-align:center;font-size:10px;color:#2d3748;letter-spacing:1px">${sym} DATA LOADING...</div>`;return;}
    rows.innerHTML=arr.map(([ex,d])=>`
      <div class="flow-row">
        <span class="flow-ex">${ex}</span>
        <div class="flow-bar"><div class="flow-fill" style="width:${ps.length>1?Math.min(100,((d.p-minP)/(maxP-minP))*100):50}%;background:${color}"></div></div>
        <span class="flow-pr">${f$(d.p)}</span>
        ${d.v?`<span class="flow-v">${f$(d.v)}</span>`:""}
      </div>`).join("");
  });
  // FG history
  const hist=document.getElementById("fg-hist");
  hist.innerHTML=fgData.slice(0,7).map((d,i)=>{
    const v=parseInt(d.value);
    const c=v>75?"#ff3366":v>55?"#ffaa00":v>45?"#e2e8f0":"#00ff88";
    return`<div class="flow-row">
      <span class="flow-ex" style="color:#2d3748">D-${i}</span>
      <div class="flow-bar"><div class="flow-fill" style="width:${v}%;background:${c}"></div></div>
      <span style="font-size:10px;color:${c};font-weight:700;width:28px;text-align:right">${v}</span>
      <span style="font-size:9px;color:#2d3748;width:80px;text-align:right">${d.value_classification}</span>
    </div>`;
  }).join("");
}

/* ══ CLAUDE API ══ */
async function callClaude(sys,prompt,search=true){
  const body={model:"claude-sonnet-4-20250514",max_tokens:1000,system:sys,messages:[{role:"user",content:prompt}]};
  if(search)body.tools=[{type:"web_search_20250305",name:"web_search"}];
  const r=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const d=await r.json();
  const txt=(d.content||[]).filter(c=>c.type==="text").map(c=>c.text).join("");
  try{return JSON.parse(txt.replace(/```json|```/g,"").trim());}
  catch{return{raw:txt.slice(0,600)};}
}

/* ══ AGENT RENDER ══ */
function renderAgent(id,status,result){
  const a=AGENTS.find(x=>x.id===id);
  const isDone=status==="done";
  const isRun=status==="running";
  const tc=isDone?a.color:isRun?"#2d3748":"#1a1a2e";
  const sig=result?.signal||result?.recommendation;
  const sigC=sc(sig);
  let body="";
  if(isDone&&result){
    body=`<div class="agent-body" id="ab-${id}" style="border-top-color:${a.color}25;display:none">
      ${sig?`<div class="sig-badge" style="background:${sb(sig)};border-color:${sigC};color:${sigC};display:inline-block;margin-bottom:10px">${sig}</div>`:""}
      ${result.summary?`<div class="a-sum">${result.summary}</div>`:""}
      ${(result.bullets||[]).map(b=>`<div class="bullet"><span class="b-dot" style="color:${a.color}">▸</span><span class="b-txt">${b}</span></div>`).join("")}
      ${result.raw?`<div style="font-size:10px;color:#4a5568;line-height:1.6;white-space:pre-wrap">${result.raw.slice(0,500)}</div>`:""}
    </div>`;
  }
  const html=`<div class="agent-card" id="ac-${id}" style="border-color:${isDone?a.color+"40":"#1a1a2e"}">
    <div class="agent-row" onclick="toggleAgent('${id}','${a.color}')">
      <span class="a-ico" style="color:${tc}">${a.icon}</span>
      <div style="flex:1"><div class="a-nm" style="color:${tc}">${a.label}</div><div class="a-desc">${a.desc}</div></div>
      ${isRun?`<div class="dots">${[0,1,2].map(i=>`<div class="dot" style="background:${a.color};animation-delay:${i*0.2}s"></div>`).join("")}</div>`:""}
      ${isDone&&sig?`<div class="sig-badge" style="background:${sb(sig)};border-color:${sigC};color:${sigC}">${sig}</div>`:""}
      ${isDone&&result?`<span id="chv-${id}" style="color:#2d3748;font-size:12px;transition:transform .2s">▾</span>`:""}
    </div>
    ${body}
  </div>`;
  const ex=document.getElementById("ac-"+id);
  if(ex)ex.outerHTML=html;
  else document.getElementById("agent-list").insertAdjacentHTML("beforeend",html);
}

function toggleAgent(id){
  const b=document.getElementById("ab-"+id);
  const ch=document.getElementById("chv-"+id);
  if(!b)return;
  const open=b.style.display!=="none";
  b.style.display=open?"none":"block";
  if(ch)ch.style.transform=open?"none":"rotate(180deg)";
}

function renderFinalSignal(r){
  if(!r)return;
  const sig=r.signal||r.recommendation||"HOLD";
  const conf=r.confidence||50;
  const color=sc(sig);
  const CIRC=2*Math.PI*38;
  document.getElementById("final-wrap").innerHTML=`
    <div class="final-card" style="border:1px solid ${color}80;box-shadow:0 0 30px ${color}15">
      <div class="f-header" style="color:${color}">── HEDGE FUND SIGNAL ──</div>
      <div class="f-inner">
        <div class="f-ring">
          <svg width="88" height="88">
            <circle cx="44" cy="44" r="38" fill="none" stroke="#1a1a2e" stroke-width="5"/>
            <circle cx="44" cy="44" r="38" fill="none" stroke="${color}" stroke-width="5"
              stroke-linecap="round" stroke-dasharray="${(conf/100)*CIRC} ${CIRC}"
              style="filter:drop-shadow(0 0 4px ${color})"/>
          </svg>
          <div class="f-ring-info"><span class="f-conf" style="color:${color}">${conf}%</span></div>
        </div>
        <div>
          <div class="f-tag">AI SIGNAL</div>
          <div class="f-sig" style="color:${color};text-shadow:0 0 20px ${color}60">${sig}</div>
          <div class="f-tf">${r.timeframe||"SHORT-TERM"}</div>
          <div style="font-size:10px;color:#2d3748;margin-top:2px">CONFIDENCE: ${conf}/100</div>
        </div>
      </div>
      ${r.thesis?`<div style="font-size:11px;color:${color}80;margin-top:12px;padding:8px 10px;border:1px solid ${color}20;border-radius:3px;letter-spacing:0.5px">"${r.thesis}"</div>`:""}
      ${r.summary?`<div class="f-sum" style="border-top-color:${color}20">${r.summary}</div>`:""}
      ${r.levels?.length?`<div class="f-levels">${r.levels.map(l=>`<div class="f-level" style="border:1px solid ${l.type==="target"?"#00ff8840":"#ff336640"}">
        <div class="f-lvl-lbl">${l.label}</div>
        <div class="f-lvl-val" style="color:${l.type==="target"?"#00ff88":"#ff3366"}">${l.value}</div>
      </div>`).join("")}</div>`:""}
      ${r.risks?.length?`<div class="f-risks" style="background:#ff336608;border:1px solid #ff336620">
        <div class="f-rlbl" style="color:#ff3366">RISK FACTORS</div>
        ${r.risks.map(x=>`<div class="f-ri" style="color:#ff336680">► ${x}</div>`).join("")}
      </div>`:""}
      <div class="f-disc">NOT FINANCIAL ADVICE · DYOR · AI-GENERATED SIGNALS</div>
    </div>`;
}

/* ══ SIGNAL ENGINE ══ */
async function runSignal(){
  if(running)return;
  running=true; aResults={};
  sw("signal");
  document.getElementById("sig-empty").classList.add("hidden");
  document.getElementById("sig-run").classList.remove("hidden");
  document.getElementById("sig-status").textContent="◉ PROCESSING...";
  document.getElementById("sig-status").style.color="#ffaa00";
  document.getElementById("agent-list").innerHTML="";
  document.getElementById("final-wrap").innerHTML="";
  document.getElementById("btn-rerun").classList.add("hidden");
  const b=document.getElementById("bgo");
  b.className="btn-signal busy";
  b.innerHTML=spn("#2d3748",12)+" ANALYZING...";
  AGENTS.forEach(a=>renderAgent(a.id,"waiting",null));

  const sys="You are a quantitative crypto analyst at a top hedge fund. Respond ONLY with valid JSON, no markdown.";
  const p=prices,fg0=fgData[0];
  const ctx=`BTC $${p.bitcoin?.usd?.toFixed(0)||"?"} (${p.bitcoin?.usd_24h_change?.toFixed(1)||"?"}% 24h), ETH $${p.ethereum?.usd?.toFixed(0)||"?"}, XRP $${p.ripple?.usd?.toFixed(4)||"?"}, SOL $${p.solana?.usd?.toFixed(1)||"?"}, BNB $${p.binancecoin?.usd?.toFixed(1)||"?"}, Fear&Greed ${fg0?.value||"?"}(${fg0?.value_classification||"?"})`;

  async function agent(id,prompt,search=true){
    renderAgent(id,"running",null);
    try{
      const r=await callClaude(sys,prompt,search);
      aResults[id]=r; renderAgent(id,"done",r); return r;
    }catch(e){const r={raw:"Error: "+e.message};aResults[id]=r;renderAgent(id,"done",r);return r;}
  }

  const macro=await agent("macro",`Search right now for active geopolitical events, wars, military conflicts, Fed/ECB decisions, sanctions that are affecting crypto markets TODAY. Context: ${ctx}
JSON: {"signal":"LONG|SHORT|HOLD","summary":"2-3 sentences","bullets":["event1","event2","event3"],"risk_level":"HIGH|MEDIUM|LOW","key_event":"most important event right now"}`);

  const onchain=await agent("onchain",`Search for latest whale movements, large BTC/ETH on-chain transactions, exchange net flows, institutional activity, ETF flows in last 24h. Who is buying/selling big? Context: ${ctx}
JSON: {"signal":"LONG|SHORT|HOLD","summary":"2-3 sentences","bullets":["whale1","flow2","institutional3"],"net_flow":"ACCUMULATION|DISTRIBUTION|NEUTRAL","whale_bias":"BULLISH|BEARISH|NEUTRAL"}`);

  const news=await agent("news",`Search breaking crypto news RIGHT NOW: regulation, hacks, exchange news, protocol launches, key influencer sentiment, insider leaks. Context: ${ctx}
JSON: {"signal":"LONG|SHORT|HOLD","summary":"2-3 sentences","bullets":["news1","news2","news3"],"sentiment":"BULLISH|BEARISH|NEUTRAL","breaking":"single most important breaking news"}`);

  const quant=await agent("quant",`Search current BTC/ETH technicals: RSI, funding rates, open interest, volume anomalies, key support/resistance levels. Exchange data BTC: ${JSON.stringify(excData.BTC||{})}. Context: ${ctx}
JSON: {"signal":"LONG|SHORT|HOLD","summary":"2-3 sentences","bullets":["rsi","funding","volume"],"trend":"BULLISH|BEARISH|SIDEWAYS","support":"$N","resistance":"$N","rsi":50}`);

  const final=await agent("signal",`You are the Chief Investment Officer synthesizing all analyst reports into ONE final trading signal.
MACRO ANALYST: ${macro?.signal||"?"} | Risk: ${macro?.risk_level||"?"} | Key: ${macro?.key_event||""}
ON-CHAIN ANALYST: ${onchain?.signal||"?"} | Flow: ${onchain?.net_flow||"?"} | Whales: ${onchain?.whale_bias||"?"}
NEWS ANALYST: ${news?.signal||"?"} | Sentiment: ${news?.sentiment||"?"} | Breaking: ${news?.breaking||""}
QUANT ANALYST: ${quant?.signal||"?"} | Trend: ${quant?.trend||"?"} | RSI: ${quant?.rsi||"?"} | Support: ${quant?.support||"?"} | Resistance: ${quant?.resistance||"?"}
Live Market: ${ctx}
JSON: {"signal":"LONG|SHORT|HOLD","confidence":0-100,"timeframe":"4H|1D|3D|1W","thesis":"one killer bull or bear thesis","summary":"3-4 sentence deep analysis","levels":[{"label":"TARGET","value":"$N","type":"target"},{"label":"STOP","value":"$N","type":"stop"}],"risks":["risk1","risk2"]}`,false);

  renderFinalSignal(final);
  document.getElementById("sig-status").textContent="◉ SIGNAL READY";
  document.getElementById("sig-status").style.color="#00ff88";
  document.getElementById("btn-rerun").classList.remove("hidden");
  b.className="btn-signal ready";
  b.innerHTML="▲ RUN SIGNAL ENGINE";
  running=false;
}

/* ══ INIT ══ */
loadMarket();
setInterval(loadMarket,90000);
</script>
</body>
</html>
HTML

# 4. PWA Manifest
cat > /var/www/hedgesignal/manifest.json << 'MANIFEST'
{
  "name": "HedgeΣSignal",
  "short_name": "HedgeSig",
  "description": "Crypto Hedge Fund Signal Engine",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#050508",
  "theme_color": "#050508",
  "orientation": "portrait",
  "icons": [
    {"src": "/icon.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/icon.png", "sizes": "512x512", "type": "image/png"}
  ]
}
MANIFEST

# Generate a simple icon using Python
python3 -c "
import struct, zlib
def png(sz,r,g,b):
  def ch(n,d):
    c=zlib.crc32(n+d)&0xffffffff
    return struct.pack('>I',len(d))+n+d+struct.pack('>I',c)
  rows=b''
  for _ in range(sz):
    row=b'\x00'
    for _ in range(sz):
      row+=bytes([r,g,b])
    rows+=row
  d=b'\x89PNG\r\n\x1a\n'
  d+=ch(b'IHDR',struct.pack('>IIBBBBB',sz,sz,8,2,0,0,0))
  d+=ch(b'IDAT',zlib.compress(rows))
  d+=ch(b'IEND',b'')
  return d
with open('/var/www/hedgesignal/icon.png','wb') as f:
  f.write(png(192,5,5,8))
print('Icon OK')
"

# 5. Nginx
echo -e "${CYAN}[3/5] Configuring nginx...${NC}"
cat > /etc/nginx/sites-available/hedgesignal << 'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/hedgesignal;
    index index.html;
    charset utf-8;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header X-Frame-Options "SAMEORIGIN";
    gzip on;
    gzip_types text/html text/css application/javascript application/json;
    location / { try_files $uri $uri/ /index.html; }
}
NGINX

ln -sf /etc/nginx/sites-available/hedgesignal /etc/nginx/sites-enabled/hedgesignal
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo -e "${CYAN}[4/5] Starting nginx...${NC}"
systemctl enable nginx
systemctl restart nginx

echo -e "${CYAN}[5/5] Done!${NC}"
IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅  HedgeΣSignal DEPLOYED!             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo -e ""
echo -e "  Browser:  ${GREEN}http://${IP}${NC}"
echo -e ""
echo -e "  ${CYAN}На телефоне:${NC}"
echo -e "  1. Chrome → http://${IP}"
echo -e "  2. ⋮ → 'Добавить на главный экран'"
echo -e "  3. Иконка появится как приложение!"
