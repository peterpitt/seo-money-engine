/* 公開假日時間軸（seoengine）：讀取 .holiday-timeline 內嵌的 JSON，畫出各國假日軌道並提供播放／拖曳。 */
(function () {
  "use strict";
  if (window.__seoTimeline) return;
  window.__seoTimeline = true;

  var SVGNS = "http://www.w3.org/2000/svg";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var T = {
    en: {
      play: "▶ Play", pause: "❚❚ Pause", bridges: "Show leave hacks", year: "Year", pick: "Pick a date",
      off: "Day off", offEst: "Day off (expected)", weekend: "Weekend", work: "Working day",
      breakDay: function (k, n) { return "day " + k + " of " + n + "-day break"; },
      longWeekend: function (n) { return n + "-day break"; }, plainWeekend: "Regular weekend",
      next: function (name, n) { return "Next: " + name + (n === 1 ? ", tomorrow" : ", in " + n + " days"); },
      none: "No later holiday in our data", full: "Full list →",
      leaveHack: function (k, n) { return "Take " + k + " day" + (k > 1 ? "s" : "") + " off for a " + n + "-day break"; },
      breakTip: function (n) { return n + "-day break"; }, takeOff: "Take off: ", moved: "Moved from ",
      expected: "Expected date, not yet announced",
      legend: ["Official holiday", "Expected date", "Break with no leave", "Break with leave days"],
      today: "Today", aria: "Public holiday timeline",
      month: function (m) { return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m]; },
      day: function (d) { return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }); },
      short: function (d) { return (d.getMonth() + 1) + "/" + d.getDate(); }
    },
    zh: {
      play: "▶ 播放", pause: "❚❚ 暫停", bridges: "顯示請假串連", year: "年份", pick: "選擇日期",
      off: "放假", offEst: "放假（預估）", weekend: "週末", work: "上班",
      breakDay: function (k, n) { return "連假第 " + k + "/" + n + " 天"; },
      longWeekend: function (n) { return "連假中 · 共 " + n + " 天"; }, plainWeekend: "一般週末",
      next: function (name, n) { return "下一個：" + name + "，" + (n === 1 ? "明天" : n + " 天後"); },
      none: "資料中沒有之後的假日", full: "完整假日表 →",
      leaveHack: function (k, n) { return "請 " + k + " 天假可連休 " + n + " 天"; },
      breakTip: function (n) { return "連假 " + n + " 天"; }, takeOff: "請假：", moved: "原日期 ",
      expected: "預估日期，官方尚未公告",
      legend: ["正式假日", "預估日期", "不用請假的連假", "請假可串連"],
      today: "今天", aria: "各國假日時間軸",
      month: function (m) { return (m + 1) + "月"; },
      day: function (d) { return (d.getMonth() + 1) + "/" + d.getDate() + "（" + "日一二三四五六"[d.getDay()] + "）"; },
      short: function (d) { return (d.getMonth() + 1) + "/" + d.getDate(); }
    }
  };

  function el(tag, attrs, parent, text) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  }
  function h(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function parse(s) { var p = s.split("-"); return new Date(+p[0], p[1] - 1, +p[2]); }
  function iso(d) { return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function doy(d) { return Math.round((d - new Date(d.getFullYear(), 0, 1)) / 864e5); }
  function daysIn(y) { return new Date(y, 1, 29).getMonth() === 1 ? 366 : 365; }

  function init(root, index) {
    var dataNode = root.querySelector(".ht-data");
    if (!dataNode || root.__ready) return;
    root.__ready = true;
    var D = JSON.parse(dataNode.textContent);
    var t = T[(D.lang || "").indexOf("zh") === 0 ? "zh" : "en"];
    var focus = D.focus, cursor = 0, playing = false, raf = 0;
    var W = 760, L = 78, R = 10, TOP = 30, LANE = 42;

    // ---- 介面骨架
    var bar = h("div", "ht-toolbar");
    var seg = h("div", "ht-seg"); seg.setAttribute("role", "group"); seg.setAttribute("aria-label", t.year);
    var bridgeLabel = h("label", "ht-check"), bridgeBox = h("input");
    bridgeBox.type = "checkbox"; bridgeBox.checked = true; bridgeBox.id = "ht-bridges-" + index;
    bridgeLabel.appendChild(bridgeBox); bridgeLabel.appendChild(document.createTextNode(" " + t.bridges));
    var playBtn = h("button", "ht-play", t.play); playBtn.type = "button";
    bar.appendChild(seg); bar.appendChild(bridgeLabel); bar.appendChild(playBtn);

    var scrub = h("div", "ht-scrub"), readout = h("output", "ht-readout"), range = h("input");
    range.type = "range"; range.min = 0; range.id = "ht-day-" + index; range.setAttribute("aria-label", t.pick);
    scrub.appendChild(readout); scrub.appendChild(range);

    var board = h("div", "ht-board");
    var wrap = h("div", "ht-chart"), svg = el("svg", { role: "img", "aria-label": t.aria }), tip = h("div", "ht-tip");
    tip.hidden = true; wrap.appendChild(svg); wrap.appendChild(tip);
    var legend = h("div", "ht-legend");
    ["solid", "est", "brk", "brg"].forEach(function (kind, i) {
      var s = h("span"), sw = h("i", "ht-sw ht-sw-" + kind);
      s.appendChild(sw); s.appendChild(document.createTextNode(t.legend[i])); legend.appendChild(s);
    });
    [bar, scrub, board, wrap, legend].forEach(function (n) { root.appendChild(n); });

    D.countries.forEach(function (c) {
      var card = h("div", "ht-card"); card.style.setProperty("--c", c.color);
      var who = h("div", "ht-who"), dot = h("span", "ht-dot");
      dot.style.background = c.color;
      who.appendChild(dot); who.appendChild(h("strong", null, c.name)); who.appendChild(h("span", "ht-pill"));
      card.appendChild(who); card.appendChild(h("div", "ht-state"));
      if (c.page) { var a = h("a", "ht-link", t.full); a.href = c.page; card.appendChild(a); }
      board.appendChild(card);
    });

    D.years.forEach(function (y) {
      var b = h("button", null, String(y)); b.type = "button";
      b.setAttribute("aria-pressed", String(y === focus));
      b.addEventListener("click", function () {
        stop(); focus = y;
        Array.prototype.forEach.call(seg.children, function (n) { n.setAttribute("aria-pressed", String(n.textContent === String(y))); });
        cursor = startDay(); draw(true);
      });
      seg.appendChild(b);
    });

    function x(i, total) { return L + (i / total) * (W - L - R); }
    function startDay() {
      var now = new Date(); now.setHours(0, 0, 0, 0);
      return now.getFullYear() === focus ? doy(now) : 0;
    }
    function pop(node, delay, frames) {
      if (reduce || !node.animate) return;
      node.animate(frames || [{ transform: "scale(0)", opacity: 0 }, { transform: "scale(1)", opacity: 1 }],
        { duration: 460, delay: delay, easing: "cubic-bezier(.2,.9,.25,1.35)", fill: "backwards" });
    }

    function draw(animate) {
      var y = focus, total = daysIn(y), H = TOP + D.countries.length * LANE + 14, marks = [];
      svg.setAttribute("viewBox", "0 0 " + W + " " + H);
      svg.textContent = "";
      for (var m = 0; m < 12; m++) {
        var mx = x(doy(new Date(y, m, 1)), total);
        el("line", { x1: mx, x2: mx, y1: TOP - 6, y2: H - 10, class: "ht-grid" }, svg);
        el("text", { x: mx + 3, y: 16, class: "ht-month" }, svg, t.month(m));
      }
      D.countries.forEach(function (c, i) {
        var cy = TOP + i * LANE + LANE / 2;
        el("rect", { x: L, y: cy - 15, width: W - L - R, height: 30, rx: 6, class: "ht-lane" }, svg);
        el("text", { x: 4, y: cy + 4, class: "ht-lane-label" }, svg, c.name);
        (c.breaks[String(y)] || []).forEach(function (b) {
          if (b.leave && !bridgeBox.checked) return;
          var s = parse(b.start), e = parse(b.end);
          if (s.getFullYear() < y) s = new Date(y, 0, 1);
          if (e.getFullYear() > y) e = new Date(y, 11, 31);
          var x1 = x(doy(s), total), x2 = x(doy(e) + 1, total);
          var r = el("rect", { x: x1, y: cy - 11, width: x2 - x1, height: 22, rx: 5,
            class: b.leave ? "ht-bridge ht-bar" : "ht-break ht-bar", style: "--c:" + c.color }, svg);
          r.dataset.tip = (b.leave ? t.leaveHack(b.leave, b.length) : t.breakTip(b.length)) + "\n" +
            t.day(parse(b.start)) + " – " + t.day(parse(b.end)) +
            (b.leave ? "\n" + t.takeOff + b.leave_dates.map(function (z) { return t.day(parse(z)); }).join(", ") : "") +
            "\n" + b.names.join(" + ");
          marks.push({ n: r, d: doy(s), bar: true });
        });
        c.holidays.forEach(function (hd) {
          var s = parse(hd.start), e = parse(hd.end);
          if (s.getFullYear() !== y) return;
          var est = hd.status === "estimated", n;
          if (hd.start === hd.end) {
            n = el("circle", { cx: x(doy(s) + 0.5, total), cy: cy, r: 5.5, class: "ht-mark" + (est ? " ht-est" : ""), style: "--c:" + c.color }, svg);
          } else {
            var x1 = x(doy(s), total), x2 = x(doy(e) + 1, total);
            n = el("rect", { x: x1, y: cy - 5.5, width: Math.max(9, x2 - x1), height: 11, rx: 5.5,
              class: "ht-mark" + (est ? " ht-est" : ""), style: "--c:" + c.color }, svg);
          }
          n.dataset.tip = hd.name + (hd.local ? " · " + hd.local : "") + "\n" + t.day(s) +
            (hd.end !== hd.start ? " – " + t.day(e) : "") +
            (hd.actual && hd.actual !== hd.start ? "\n" + t.moved + t.day(parse(hd.actual)) : "") +
            (est ? "\n" + t.expected : "");
          marks.push({ n: n, d: doy(s), bar: false });
        });
      });
      var now = new Date(); now.setHours(0, 0, 0, 0);
      if (now.getFullYear() === y) {
        var tx = x(doy(now) + 0.5, total);
        el("line", { x1: tx, x2: tx, y1: TOP - 6, y2: H - 10, class: "ht-today" }, svg);
        el("text", { x: tx + 3, y: H - 1, class: "ht-month" }, svg, t.today);
      }
      var g = el("g", { class: "ht-cursor" }, svg);
      el("line", { x1: 0, x2: 0, y1: 22, y2: H - 10, class: "ht-cursor-line" }, g);
      el("rect", { x: -24, y: 2, width: 48, height: 17, rx: 4, class: "ht-cursor-tag" }, g);
      el("text", { x: 0, y: 14.5, "text-anchor": "middle", class: "ht-cursor-text" }, g);
      if (animate) marks.forEach(function (m) {
        var delay = 120 + (m.d / total) * 1400;
        pop(m.n, m.bar ? delay + 100 : delay, m.bar ? [{ transform: "scaleX(0)", opacity: 0 }, { transform: "scaleX(1)", opacity: 1 }] : null);
      });
      range.max = total - 1;
      set(cursor);
    }

    function covering(c, s) {
      for (var i = 0; i < c.holidays.length; i++) if (c.holidays[i].start <= s && s <= c.holidays[i].end) return c.holidays[i];
      return null;
    }
    function naturalBreak(c, d) {
      var s = iso(d), list = c.breaks[String(d.getFullYear())] || [];
      for (var i = 0; i < list.length; i++) if (!list[i].leave && list[i].start <= s && s <= list[i].end) return list[i];
      return null;
    }
    function nextHoliday(c, d) {
      var s = iso(d);
      for (var i = 0; i < c.holidays.length; i++) if (c.holidays[i].start > s) {
        return t.next(c.holidays[i].name, Math.round((parse(c.holidays[i].start) - d) / 864e5));
      }
      return t.none;
    }

    function set(i) {
      var total = daysIn(focus);
      cursor = Math.max(0, Math.min(total - 1, i));
      var whole = Math.round(cursor), d = new Date(focus, 0, 1 + whole);
      var g = svg.querySelector(".ht-cursor");
      if (g) { g.setAttribute("transform", "translate(" + x(cursor + 0.5, total) + ",0)"); g.querySelector(".ht-cursor-text").textContent = t.short(d); }
      range.value = whole;
      readout.textContent = focus + " · " + t.day(d);
      var s = iso(d);
      D.countries.forEach(function (c, k) {
        var card = board.children[k], hd = covering(c, s), wk = c.weekend.indexOf((d.getDay() + 6) % 7) >= 0, br = naturalBreak(c, d);
        var pill = card.querySelector(".ht-pill"), state = card.querySelector(".ht-state");
        card.classList.toggle("is-off", !!(hd || (wk && br)));
        if (hd) {
          pill.textContent = hd.status === "estimated" ? t.offEst : t.off;
          var start = br ? parse(br.start) : null;
          if (start && start.getFullYear() < focus) start = new Date(focus, 0, 1);
          state.textContent = hd.name + (br ? " · " + t.breakDay(Math.round((d - start) / 864e5) + 1, br.length) : "");
        } else if (wk) {
          pill.textContent = t.weekend;
          state.textContent = br ? t.longWeekend(br.length) : t.plainWeekend;
        } else {
          pill.textContent = t.work;
          state.textContent = nextHoliday(c, d);
        }
      });
    }

    function stop() { playing = false; cancelAnimationFrame(raf); playBtn.textContent = t.play; }
    function play() {
      var total = daysIn(focus);
      if (cursor >= total - 1) cursor = 0;
      if (reduce) { set(cursor + 7); return; }
      playing = true; playBtn.textContent = t.pause;
      var last = performance.now();
      function step(now) {
        if (!playing) return;
        var next = cursor + (now - last) / 1000 * 26; last = now;
        set(Math.min(next, total - 1));
        if (next >= total - 1) { stop(); return; }
        raf = requestAnimationFrame(step);
      }
      raf = requestAnimationFrame(step);
    }

    playBtn.addEventListener("click", function () { playing ? stop() : play(); });
    range.addEventListener("input", function () { stop(); set(+range.value); });
    bridgeBox.addEventListener("change", function () { draw(false); });
    svg.addEventListener("pointermove", function (e) {
      var target = e.target.closest ? e.target.closest("[data-tip]") : null;
      if (!target) { tip.hidden = true; return; }
      tip.textContent = "";
      target.dataset.tip.split("\n").forEach(function (line, i) { tip.appendChild(h(i ? "div" : "strong", null, line)); });
      tip.hidden = false;
      var r = wrap.getBoundingClientRect(), left = e.clientX - r.left + wrap.scrollLeft + 12;
      if (left + 230 > wrap.scrollLeft + r.width) left -= 250;
      tip.style.left = left + "px"; tip.style.top = (e.clientY - r.top + 12) + "px";
    });
    svg.addEventListener("pointerleave", function () { tip.hidden = true; });

    cursor = startDay();
    draw(true);
  }

  function boot() { Array.prototype.forEach.call(document.querySelectorAll(".holiday-timeline"), init); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
