"""國定假日行事曆：從資料檔產生假日表、連假攻略（含請假建議）與倒數工具。

資料檔：<站>/data/holidays/<code>.yaml
  country: Japan            # 英文國名
  country_zh: 日本          # 中文國名（選填）
  code: jp                  # 必須與檔名相同
  weekend: [sat, sun]       # 週末（預設六日）
  sources: [{name: ..., url: ...}]
  holidays:
    - date: 2027-05-03      # 放假日（區間的第一天）
      end: 2027-05-05       # 選填：連續多天的最後一天
      actual: 2027-07-04    # 選填：節日原本日期（放假日被移動時）
      name: Constitution Day
      name_zh: 憲法紀念日   # 選填
      local: 憲法記念日      # 選填：當地語言名稱
      status: official      # official | estimated（依月相等尚未公告）
      note: ...             # 選填
      note_zh: ...          # 選填

短碼：[[holidays:jp:2027]]  [[longweekends:jp:2027]]  [[countdown:jp]]
      [[remaining:jp:2026]]（該年度還沒過的假日；建置當天算一次，瀏覽器端每天再自動更新）
      [[timeline]] 或 [[timeline:us,ae,it,jp]]（給訪客的互動時間軸）  [[holidaystats:2027]]（各國統計比較表）
選填欄位：short（英文短國名）、pages（各語言的國家文章網址，例如 {en: /japan-public-holidays/}）
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import yaml

_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_ZH_WEEKDAYS = "一二三四五六日"
_CODE = re.compile(r"^[a-z]{2,3}$")
_SHORTCODE = re.compile(r"\[\[(holidays|longweekends|countdown|remaining):([a-z0-9]+)(?::(\d{4}))?\]\]")
_TIMELINE = re.compile(r"\[\[timeline(?::([a-z0-9,]+))?\]\]")
_STATS = re.compile(r"\[\[holidaystats:(\d{4})(?::([a-z0-9,]+))?\]\]")
_COUNTRY_COLORS = {"us": "#3b6ff0", "ae": "#12a37e", "it": "#e0733a", "jp": "#e0306f",
                   "de": "#c08a00", "fr": "#7c3aed", "gb": "#0891b2", "au": "#65a30d", "tw": "#dc2626"}
_FALLBACK_COLORS = ["#8b5cf6", "#0ea5c6", "#b8860b", "#64748b", "#d946ef", "#16a34a"]
_STATUSES = ("official", "estimated")


class CalendarError(ValueError):
    pass


def _date(value, label: str) -> dt.date:
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError as exc:
        raise CalendarError(f"invalid date for {label}: {value!r}") from exc


def _is_zh(lang: str) -> bool:
    return lang.lower().startswith("zh")


def fmt_date(day: dt.date, lang: str) -> str:
    if _is_zh(lang):
        return f"{day.month}/{day.day}（{_ZH_WEEKDAYS[day.weekday()]}）"
    return f"{day:%a}, {day:%b} {day.day}"


def fmt_span(start: dt.date, end: dt.date, lang: str) -> str:
    if start == end:
        return fmt_date(start, lang)
    return f"{fmt_date(start, lang)} – {fmt_date(end, lang)}"


@dataclass(frozen=True)
class HolidayEntry:
    start: dt.date
    end: dt.date
    name: str
    name_zh: str = ""
    local: str = ""
    actual: dt.date | None = None
    status: str = "official"
    note: str = ""
    note_zh: str = ""

    @property
    def days(self) -> list[dt.date]:
        return [self.start + dt.timedelta(n) for n in range((self.end - self.start).days + 1)]

    def display_name(self, lang: str) -> str:
        return (self.name_zh or self.name) if _is_zh(lang) else self.name


@dataclass
class Calendar:
    code: str
    country: str
    country_zh: str = ""
    short: str = ""
    language: str = ""
    timezone: str = ""          # IANA 時區，例如 Asia/Tokyo；行事曆頁面用來顯示當地時間
    city: str = ""              # 顯示當地時間用的城市（英文）
    city_zh: str = ""
    pages: dict = field(default_factory=dict)
    weekend: tuple[int, ...] = (5, 6)
    entries_all: list[HolidayEntry] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping) -> "Calendar":
        code = str(data.get("code") or "")
        if not _CODE.match(code):
            raise CalendarError(f"calendar code {code!r} must be 2–3 lowercase letters")
        weekend_names = [str(w).lower()[:3] for w in (data.get("weekend") or ["sat", "sun"])]
        if any(w not in _WEEKDAYS for w in weekend_names):
            raise CalendarError(f"{code}: invalid weekend {weekend_names}")
        entries = []
        for raw in data.get("holidays") or []:
            start = _date(raw.get("date"), f"{code} holiday")
            end = _date(raw.get("end"), f"{code} holiday end") if raw.get("end") else start
            if end < start:
                raise CalendarError(f"{code}: end {end} is before start {start}")
            status = str(raw.get("status") or "official")
            if status not in _STATUSES:
                raise CalendarError(f"{code}: status must be one of {_STATUSES}, got {status!r}")
            entries.append(HolidayEntry(
                start=start, end=end, name=str(raw.get("name") or "").strip(),
                name_zh=str(raw.get("name_zh") or ""), local=str(raw.get("local") or ""),
                actual=_date(raw["actual"], f"{code} actual") if raw.get("actual") else None,
                status=status, note=str(raw.get("note") or ""), note_zh=str(raw.get("note_zh") or ""),
            ))
        entries.sort(key=lambda e: e.start)
        timezone = str(data.get("timezone") or "")
        if timezone:
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
            try:
                ZoneInfo(timezone)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise CalendarError(f"{code}: unknown timezone {timezone!r}（請用 IANA 名稱，例如 Asia/Tokyo）") from exc
        return cls(
            code=code, country=str(data.get("country") or code.upper()),
            country_zh=str(data.get("country_zh") or ""),
            short=str(data.get("short") or ""),
            language=str(data.get("language") or ""),
            timezone=timezone, city=str(data.get("city") or ""), city_zh=str(data.get("city_zh") or ""),
            pages={str(k): str(v) for k, v in (data.get("pages") or {}).items()},
            weekend=tuple(_WEEKDAYS.index(w) for w in weekend_names),
            entries_all=entries, sources=list(data.get("sources") or []),
        )

    def display_country(self, lang: str) -> str:
        return (self.country_zh or self.country) if _is_zh(lang) else (self.short or self.country)

    def page_for(self, lang: str) -> str:
        if lang in self.pages:
            return self.pages[lang]
        prefix = "zh" if _is_zh(lang) else "en"
        return next((v for k, v in self.pages.items() if k.lower().startswith(prefix)), "")

    def entries(self, year: int) -> list[HolidayEntry]:
        return [e for e in self.entries_all if e.start.year == year]

    def years(self) -> set[int]:
        return {e.start.year for e in self.entries_all}

    def holiday_days(self, year: int | None = None) -> set[dt.date]:
        pool = self.entries_all if year is None else self.entries(year)
        return {d for e in pool for d in e.days}

    def is_off(self, day: dt.date, holiday_days: set[dt.date]) -> bool:
        return day.weekday() in self.weekend or day in holiday_days


def load_calendars(project_dir: str | Path) -> dict[str, Calendar]:
    folder = Path(project_dir) / "data" / "holidays"
    if not folder.is_dir():
        return {}
    calendars = {}
    for path in sorted(folder.glob("*.yaml")):
        if path.name == "i18n.yaml" or path.name.startswith("_"):
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cal = Calendar.from_mapping(data)
        if cal.code != path.stem:
            raise CalendarError(f"{path.name}: code '{cal.code}' must match the file name")
        calendars[cal.code] = cal
    return calendars


# ---------------------------------------------------------------- long breaks
@dataclass(frozen=True)
class LongBreak:
    start: dt.date
    end: dt.date
    leave_dates: tuple[dt.date, ...]
    holidays: tuple[str, ...]

    @property
    def length(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def leave_days(self) -> int:
        return len(self.leave_dates)


def _blocks(cal: Calendar, year: int) -> list[tuple[dt.date, dt.date]]:
    holidays = cal.holiday_days()
    day, last = dt.date(year, 1, 1) - dt.timedelta(10), dt.date(year, 12, 31) + dt.timedelta(10)
    blocks, run_start = [], None
    while day <= last:
        if cal.is_off(day, holidays):
            run_start = run_start or day
        elif run_start:
            blocks.append((run_start, day - dt.timedelta(1)))
            run_start = None
        day += dt.timedelta(1)
    if run_start:
        blocks.append((run_start, last))
    return blocks


def _names_in(cal: Calendar, start: dt.date, end: dt.date, lang: str = "en") -> tuple[str, ...]:
    names = []
    for e in cal.entries_all:
        if e.start <= end and e.end >= start and e.display_name(lang) not in names:
            names.append(e.display_name(lang))
    return tuple(names)


def long_breaks(
    cal: Calendar, year: int, max_leave: int = 2, min_length: int = 3, lang: str = "en", min_ratio: int = 3
) -> list[LongBreak]:
    """自然連假（不用請假 ≥3 天）＋ 請 1–2 天假可串起的長假（每請 1 天至少換到 min_ratio 天）。"""
    blocks = _blocks(cal, year)
    out: list[LongBreak] = []
    for start, end in blocks:
        names = _names_in(cal, start, end, lang)
        if names and (end - start).days + 1 >= min_length and year in (start.year, end.year):
            out.append(LongBreak(start, end, (), names))
    for (a_start, a_end), (b_start, b_end) in zip(blocks, blocks[1:]):
        gap = [a_end + dt.timedelta(n) for n in range(1, (b_start - a_end).days)]
        names = _names_in(cal, a_start, b_end, lang)
        total = (b_end - a_start).days + 1
        if (names and 1 <= len(gap) <= max_leave and total >= min_ratio * len(gap)
                and year in (a_start.year, b_end.year)):
            out.append(LongBreak(a_start, b_end, tuple(gap), names))
    return sorted(out, key=lambda b: (b.start, b.leave_days))


# ---------------------------------------------------------------- rendering
_T = {
    "en": {"date": "Date", "holiday": "Holiday", "notes": "Notes", "expected": "Expected",
           "moved": "Moved from {d}", "break": "Break", "dates": "Dates", "length": "Days off",
           "leave": "Leave needed", "none": "None", "days": "{n} days", "day": "{n} day",
           "take": "{n} ({dates})"},
    "zh": {"date": "日期", "holiday": "假日", "notes": "備註", "expected": "預估",
           "moved": "原日期 {d}，放假日調整", "break": "連假", "dates": "日期", "length": "天數",
           "leave": "需請假", "none": "免請假", "days": "{n} 天", "day": "{n} 天",
           "take": "{n}（{dates}）"},
}


def _t(lang: str) -> dict[str, str]:
    return _T["zh" if _is_zh(lang) else "en"]


def _days_label(n: int, lang: str) -> str:
    t = _t(lang)
    return (t["day"] if n == 1 else t["days"]).format(n=n)


def render_holiday_table(cal: Calendar, year: int, lang: str) -> str:
    entries = cal.entries(year)
    if not entries:
        raise CalendarError(f"no {cal.code} holiday data for {year}")
    return _holiday_table(cal, year, entries, lang)


def _holiday_table(cal: Calendar, year: int, entries: list[HolidayEntry], lang: str, mark_end: bool = False) -> str:
    """假日表格。mark_end=True 時每列帶 data-end（假日最後一天），讓瀏覽器端能把已過的列收起來。"""
    t, e_ = _t(lang), html.escape
    rows = []
    for e in entries:
        notes = []
        if e.status == "estimated":
            notes.append(f'<span class="badge badge-est">{t["expected"]}</span>')
        if e.actual and e.actual != e.start:
            notes.append(e_(t["moved"].format(d=fmt_date(e.actual, lang))))
        extra = e.note_zh if _is_zh(lang) and e.note_zh else e.note
        if extra:
            notes.append(e_(extra))
        local = f'<span class="local-name">{e_(e.local)}</span>' if e.local else ""
        end = f' data-end="{e.end.isoformat()}"' if mark_end else ""
        rows.append(
            f'<tr class="status-{e.status}"{end}><td class="hd-date">{e_(fmt_span(e.start, e.end, lang))}</td>'
            f'<td>{e_(e.display_name(lang))}{local}</td><td>{" · ".join(notes)}</td></tr>'
        )
    return (
        f'<div class="table-wrap"><table class="holiday-table" data-country="{cal.code}" data-year="{year}">'
        f'<thead><tr><th>{t["date"]}</th><th>{t["holiday"]}</th><th>{t["notes"]}</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


_REMAINING_T = {
    "en": {"note": "Holidays still to come in {year}:", "sep": " of ", "asof": "(as of {d})",
           "done": "All {year} holidays have passed."},
    "zh": {"note": "{year} 年還沒過的假日：", "sep": " / ", "asof": "（統計至 {d}）",
           "done": "{year} 年的假日已全部過完。"},
}

# 靜態頁面建置後不會自己變：瀏覽器端每天把已過的假日列收起來並更新數字，敘述才不會過期
_REMAINING_JS = """<script>(function(){if(window.__hdRemaining)return;window.__hdRemaining=1;
function run(){var t=new Date();t.setHours(0,0,0,0);
document.querySelectorAll('.holiday-remaining').forEach(function(box){
var c=box.querySelector('.hr-count');if(!c)return;var left=0;
box.querySelectorAll('tr[data-end]').forEach(function(r){var p=r.getAttribute('data-end').split('-');
var past=new Date(+p[0],p[1]-1,+p[2])<t;r.hidden=past;if(!past)left++});
var a=box.querySelector('.hr-asof');if(a)a.hidden=true;
if(!left){box.querySelector('.hr-note').textContent=box.getAttribute('data-done');
var w=box.querySelector('.table-wrap');if(w)w.hidden=true;return}
c.textContent=left+c.getAttribute('data-sep')+c.getAttribute('data-total')})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run()})();</script>"""


def render_remaining(cal: Calendar, year: int, lang: str, today: dt.date | None = None) -> str:
    """該年度「還沒過」的假日（最後一天 >= today）：一句統計＋只含剩餘假日的表格。"""
    entries = cal.entries(year)
    if not entries:
        raise CalendarError(f"no {cal.code} holiday data for {year}")
    today = today or dt.date.today()
    t, e_ = _REMAINING_T["zh" if _is_zh(lang) else "en"], html.escape
    done = t["done"].format(year=year)
    left = [e for e in entries if e.end >= today]
    if not left:
        return f'<div class="holiday-remaining" data-lang="{e_(lang)}"><p class="hr-note">{e_(done)}</p></div>'
    day = f"{today.year}/{fmt_date(today, lang)}" if _is_zh(lang) else f"{fmt_date(today, lang)}, {today.year}"
    return (
        f'<div class="holiday-remaining" data-lang="{e_(lang)}" data-done="{e_(done)}">'
        f'<p class="hr-note">{e_(t["note"].format(year=year))} '
        f'<strong class="hr-count" data-total="{len(entries)}" data-sep="{t["sep"]}">{len(left)}{t["sep"]}{len(entries)}</strong> '
        f'<span class="hr-asof">{e_(t["asof"].format(d=day))}</span></p>'
        f"{_holiday_table(cal, year, left, lang, mark_end=True)}</div>\n{_REMAINING_JS}"
    )


def render_long_breaks(cal: Calendar, year: int, lang: str) -> str:
    if not cal.entries(year):
        raise CalendarError(f"no {cal.code} holiday data for {year}")
    t, e_ = _t(lang), html.escape
    rows = []
    for b in long_breaks(cal, year, lang=lang):
        if b.leave_days:
            dates = "、".join(fmt_date(d, lang) for d in b.leave_dates) if _is_zh(lang) else ", ".join(
                fmt_date(d, lang) for d in b.leave_dates)
            leave = t["take"].format(n=_days_label(b.leave_days, lang), dates=dates)
        else:
            leave = t["none"]
        rows.append(
            f'<tr class="{"bridge" if b.leave_days else "natural"}">'
            f'<td>{e_(" + ".join(b.holidays))}</td><td>{e_(fmt_span(b.start, b.end, lang))}</td>'
            f'<td class="hd-len">{_days_label(b.length, lang)}</td><td>{e_(leave)}</td></tr>'
        )
    return (
        f'<div class="table-wrap"><table class="holiday-table long-breaks" data-country="{cal.code}">'
        f'<thead><tr><th>{t["break"]}</th><th>{t["dates"]}</th><th>{t["length"]}</th><th>{t["leave"]}</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


_COUNTDOWN_JS = """<script>(function(){if(window.__hdCountdown)return;window.__hdCountdown=1;
function run(){document.querySelectorAll('.holiday-countdown').forEach(function(el){
var zh=(el.dataset.lang||'').indexOf('zh')===0,list=[];try{list=JSON.parse(el.dataset.holidays)}catch(e){}
var t=new Date();t.setHours(0,0,0,0);
var next=list.map(function(h){var p=h.date.split('-');return{d:new Date(+p[0],p[1]-1,+p[2]),n:h.name}})
.filter(function(h){return h.d>=t})[0];var out=el.querySelector('.hc-text');
if(!next){out.textContent=zh?'資料中沒有即將到來的假日':'No upcoming holiday in our data yet.';return}
var days=Math.round((next.d-t)/864e5),w=zh?'日一二三四五六'[next.d.getDay()]:next.d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});
out.innerHTML='';var s=document.createElement('strong');s.textContent=next.n;
if(zh){out.append('下一個假日：',s,'（'+(next.d.getMonth()+1)+'/'+next.d.getDate()+' 週'+w+'）'+(days?'，還有 '+days+' 天':'，就是今天！'))}
else{out.append('Next holiday: ',s,' — '+w+(days?' · in '+days+' day'+(days>1?'s':''):' · today!'))}})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run()})();</script>"""


def render_countdown(cal: Calendar, lang: str) -> str:
    payload = [{"date": e.start.isoformat(), "name": e.display_name(lang)} for e in cal.entries_all]
    data = json.dumps(payload, ensure_ascii=False).replace("&", "&amp;").replace("'", "&#39;")
    fallback = "下一個假日請見下方表格" if _is_zh(lang) else "See the table below for the next holiday."
    return (
        f'<div class="holiday-countdown" data-lang="{html.escape(lang)}" data-holidays=\'{data}\'>'
        f'<p class="hc-text">{fallback}</p></div>\n{_COUNTDOWN_JS}'
    )


def _pick(calendars: Mapping[str, Calendar], codes: list[str] | None) -> list[Calendar]:
    codes = codes or list(calendars)
    for code in codes:
        if code not in calendars:
            raise CalendarError(f"unknown holiday calendar '{code}' (add data/holidays/{code}.yaml)")
    return [calendars[c] for c in codes]


def _focus_year(years: list[int]) -> int:
    limit = dt.date.today().year + 1
    eligible = [y for y in years if y <= limit]
    return max(eligible) if eligible else years[0]


def _safe_json(data) -> str:
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def render_timeline(calendars: Mapping[str, Calendar], codes: list[str] | None, lang: str) -> str:
    """給訪客的互動時間軸：資料內嵌在頁面，動畫由 /timeline.js 執行；不支援 JS 時顯示靜態清單。"""
    chosen = _pick(calendars, codes)
    years = sorted({y for cal in chosen for y in cal.years()})
    if not years:
        raise CalendarError("timeline needs holiday data")
    spare = iter(_FALLBACK_COLORS)
    countries = []
    for cal in chosen:
        countries.append({
            "code": cal.code,
            "name": cal.display_country(lang),
            "color": _COUNTRY_COLORS.get(cal.code) or next(spare, "#64748b"),
            "weekend": list(cal.weekend),
            "page": cal.page_for(lang),
            "holidays": [
                {"start": e.start.isoformat(), "end": e.end.isoformat(), "name": e.display_name(lang),
                 "local": e.local, "status": e.status, "actual": e.actual.isoformat() if e.actual else None}
                for e in cal.entries_all
            ],
            "breaks": {
                str(y): [{"start": b.start.isoformat(), "end": b.end.isoformat(), "length": b.length,
                          "leave": b.leave_days, "leave_dates": [d.isoformat() for d in b.leave_dates],
                          "names": list(b.holidays)}
                         for b in long_breaks(cal, y, lang=lang)]
                for y in years
            },
        })
    focus = _focus_year(years)
    payload = {"lang": lang, "years": years, "focus": focus, "countries": countries}
    fallback = "".join(
        f"<li><strong>{html.escape(cal.display_country(lang))}</strong>: "
        + "; ".join(f"{html.escape(e.display_name(lang))} ({fmt_span(e.start, e.end, lang)})" for e in cal.entries(focus))
        + "</li>"
        for cal in chosen
    )
    return (
        f'<div class="holiday-timeline" data-lang="{html.escape(lang)}">'
        f'<script type="application/json" class="ht-data">{_safe_json(payload)}</script>'
        f"<noscript><ul>{fallback}</ul></noscript>"
        '<script src="/timeline.js" defer></script></div>'
    )


def holiday_stats(cal: Calendar, year: int) -> dict:
    entries = cal.entries(year)
    days = cal.holiday_days(year)
    breaks = [b for b in long_breaks(cal, year) if b.start.year == year or b.end.year == year]
    natural = [b for b in breaks if not b.leave_days]
    bridges = [b for b in breaks if b.leave_days]
    return {
        "entries": len(entries),
        "weekday_days": sum(1 for d in days if d.weekday() not in cal.weekend),
        "longest": max(natural, key=lambda b: (b.length, -b.start.toordinal()), default=None),
        "best_bridge": max(bridges, key=lambda b: (b.length / b.leave_days, b.length, -b.start.toordinal()), default=None),
        "estimated": sum(1 for e in entries if e.status == "estimated"),
    }


_STATS_T = {
    "en": ("Country", "Holidays", "Weekday days off", "Longest break, no leave", "Best leave hack",
           "{n}-day break for {k} leave day", "{n}-day break for {k} leave days", "{n} expected"),
    "zh": ("國家", "假日", "落在平日的天數", "最長連假（免請假）", "最划算的請假",
           "請 {k} 天休 {n} 天", "請 {k} 天休 {n} 天", "{n} 筆預估"),
}


def render_holiday_stats(calendars: Mapping[str, Calendar], year: int, lang: str, codes: list[str] | None = None) -> str:
    t = _STATS_T["zh" if _is_zh(lang) else "en"]
    rows = []
    for cal in _pick(calendars, codes):
        if not cal.entries(year):
            raise CalendarError(f"no {cal.code} holiday data for {year}")
        s = holiday_stats(cal, year)
        name = html.escape(cal.display_country(lang))
        page = cal.page_for(lang)
        country = f'<a href="{html.escape(page)}">{name}</a>' if page else name
        count = str(s["entries"]) + (f' <span class="badge badge-est">{t[7].format(n=s["estimated"])}</span>' if s["estimated"] else "")
        longest = (f'{fmt_span(s["longest"].start, s["longest"].end, lang)}<br><span class="local-name">'
                   f'{_days_label(s["longest"].length, lang)}</span>') if s["longest"] else "—"
        b = s["best_bridge"]
        bridge = (f'{fmt_span(b.start, b.end, lang)}<br><span class="local-name">'
                  f'{(t[5] if b.leave_days == 1 else t[6]).format(n=b.length, k=b.leave_days)}</span>') if b else "—"
        rows.append(f"<tr><td>{country}</td><td>{count}</td><td>{s['weekday_days']}</td><td>{longest}</td><td>{bridge}</td></tr>")
    head = "".join(f"<th>{h}</th>" for h in t[:5])
    return (f'<div class="table-wrap"><table class="holiday-table holiday-stats" data-year="{year}">'
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


def expand_calendar_shortcodes(md_text: str, calendars: Mapping[str, Calendar], lang: str,
                               today: dt.date | None = None) -> str:
    def replace(m: re.Match) -> str:
        kind, code, year = m.group(1), m.group(2), m.group(3)
        if code not in calendars:
            raise CalendarError(f"unknown holiday calendar '{code}' (add data/holidays/{code}.yaml)")
        cal = calendars[code]
        if kind == "countdown":
            return "\n\n" + render_countdown(cal, lang) + "\n\n"
        if not year:
            raise CalendarError(f"[[{kind}:{code}]] needs a year, e.g. [[{kind}:{code}:2027]]")
        if kind == "remaining":
            return "\n\n" + render_remaining(cal, int(year), lang, today) + "\n\n"
        render = render_holiday_table if kind == "holidays" else render_long_breaks
        return "\n\n" + render(cal, int(year), lang) + "\n\n"

    def timeline(m: re.Match) -> str:
        codes = [c for c in (m.group(1) or "").split(",") if c]
        return "\n\n" + render_timeline(calendars, codes or None, lang) + "\n\n"

    def stats(m: re.Match) -> str:
        codes = [c for c in (m.group(2) or "").split(",") if c]
        return "\n\n" + render_holiday_stats(calendars, int(m.group(1)), lang, codes or None) + "\n\n"

    md_text = _TIMELINE.sub(timeline, md_text)
    md_text = _STATS.sub(stats, md_text)
    return _SHORTCODE.sub(replace, md_text)
